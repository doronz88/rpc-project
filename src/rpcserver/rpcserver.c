#include <spawn.h>
#ifndef __APPLE__
#define _XOPEN_SOURCE (600)
#define _GNU_SOURCE (1)
#endif// __APPLE__

#include "common.h"
#include "routines.h"
#include <arpa/inet.h>
#include <dirent.h>
#include <netdb.h>
#include <netinet/in.h>
#include <signal.h>
#include <sys/select.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <termios.h>
#include <unistd.h>

#ifdef __APPLE__
#include <CoreFoundation/CoreFoundation.h>
#endif// __APPLE__

#define DEFAULT_PORT ("5910")
#define USAGE                                                                                                          \
    ("Usage: %s [-p port] [-o (stdout|syslog|file:filename)] [-d disable worker] \n\
-h  show this help message \n\
-o  output. can be all of the following: stdout, syslog and file:filename. can be passed multiple times \n\
-d  disable worker. for debugging perpuses, handle clients inprocess instead spawn worker \n\
\n\
Example usage: \n\
%s -p 5910 -o syslog -o stdout -o file:/tmp/log.txt\n")
#define MAX_CONNECTIONS (1024)
#define MAX_OPTION_LEN (256)
#define WORKER_CLIENT_SOCKET_FD (3)
#define CLOBBERD_LIST                                                                                                  \
    "x0", "x1", "x2", "x3", "x4", "x5", "x6", "x7", "x8", "x19", "x20", "x21", "x22", "x23", "x24", "x25", "x26"

void *get_in_addr(struct sockaddr *sa)// get sockaddr, IPv4 or IPv6:
{
    return sa->sa_family == AF_INET ? (void *) &(((struct sockaddr_in *) sa)->sin_addr)
                                    : (void *) &(((struct sockaddr_in6 *) sa)->sin6_addr);
}

/**
 * Facilitates communication using a pseudo-terminal (PTY) between a server and client.
 * This function handles bidirectional data transfer between the PTY master and the
 * client socket, monitors for input on both file descriptors, and sends or processes data
 * accordingly. Once the PTY process exits, it communicates the exit status to the client.
 *
 * @param sockfd The socket file descriptor used for communication with the client.
 */
static void enter_pty_mode(int sockfd) {
    int master = g_pending_pty.master;
    pid_t pid = g_pending_pty.pid;

    g_pending_pty.valid = false;

    fd_set readfds;
    char buf[RPC__PROTOCOL_CONSTANTS__RPC_PTY_BUFFER_SIZE];
    int nbytes = 0;

    while (1) {
        FD_ZERO(&readfds);
        FD_SET(master, &readfds);
        FD_SET(sockfd, &readfds);
        int maxfd = (master > sockfd) ? master : sockfd;

        if (select(maxfd + 1, &readfds, NULL, NULL, NULL) <= 0) {
            break;
        }

        if (FD_ISSET(master, &readfds)) {
            nbytes = (int) read(master, buf, sizeof(buf));
            if (nbytes <= 0) {
                TRACE("PTY master EOF/break");
                break;
            }

            Rpc__RpcPtyMessage pty_msg = RPC__RPC_PTY_MESSAGE__INIT;
            pty_msg.type_case = RPC__RPC_PTY_MESSAGE__TYPE_BUFFER;
            pty_msg.buffer.data = (uint8_t *) buf;
            pty_msg.buffer.len = (size_t) nbytes;
            CHECK(proto_msg_send(sockfd, (ProtobufCMessage *) &pty_msg) == MSG_SUCCESS);
        }
        if (FD_ISSET(sockfd, &readfds)) {
            nbytes = (int) recv(sockfd, buf, sizeof(buf), 0);
            if (nbytes <= 0) {
                TRACE("Client closed input during PTY");
                break;
            }
            CHECK(writeall(master, buf, (size_t) nbytes));
        }
    }

    int status = 0;
    (void) waitpid(pid, &status, 0);

    Rpc__RpcPtyMessage pty_msg = RPC__RPC_PTY_MESSAGE__INIT;
    pty_msg.type_case = RPC__RPC_PTY_MESSAGE__TYPE_EXIT_CODE;
    pty_msg.exit_code = status;
    CHECK(proto_msg_send(sockfd, (ProtobufCMessage *) &pty_msg) == MSG_SUCCESS);

error:
    if (master >= 0) {
        close(master);
    }
    g_pending_pty.pid = 0;
    g_pending_pty.master = -1;
    g_pending_pty.valid = false;
}

/**
 * Spawns a worker server process for handling communications with a client.
 * This function creates a new process using `posix_spawnp`, passing modified
 * arguments to include a worker mode flag (-w). It establishes necessary file
 * descriptor mappings for standard input/output/error and the client socket.
 * The function also ensures the appropriate cleanup for allocated resources and
 * the client socket.
 *
 * @param client_socket The file descriptor for the client socket to be passed to the worker.
 * @param argv The original argument array to modify and pass to the worker process.
 * @param argc The number of arguments in the original argument array.
 * @return True if the worker process was successfully spawned; false otherwise.
 */
bool spawn_worker_server(int client_socket, const char *argv[], int argc) {
    bool ret = false;

    // append -w to original argv
    int new_argc = argc + 1;
    const char **new_argv = malloc((new_argc + 1) * sizeof(char *));
    CHECK(new_argv != NULL)
    for (int i = 0; i < argc; ++i) {
        new_argv[i] = argv[i];
    }
    new_argv[new_argc - 1] = "-w";
    new_argv[new_argc] = NULL;

    pid_t pid;
    posix_spawn_file_actions_t actions;
    CHECK(0 == posix_spawn_file_actions_init(&actions));
    CHECK(0 == posix_spawn_file_actions_adddup2(&actions, STDIN_FILENO, STDIN_FILENO));
    CHECK(0 == posix_spawn_file_actions_adddup2(&actions, STDOUT_FILENO, STDOUT_FILENO));
    CHECK(0 == posix_spawn_file_actions_adddup2(&actions, STDERR_FILENO, STDERR_FILENO));
    CHECK(0 == posix_spawn_file_actions_adddup2(&actions, client_socket, WORKER_CLIENT_SOCKET_FD));

    CHECK(0 == posix_spawnp(&pid, new_argv[0], &actions, NULL, (char *const *) new_argv, environ));
    CHECK(pid != INVALID_PID);

    TRACE("Spawned Worker Process: %d", pid);
    ret = true;

error:
    posix_spawn_file_actions_destroy(&actions);
    safe_free(new_argv);
    close(client_socket);
    return ret;
}

void signal_handler(int sig) {
    int status;
    pid_t pid;

    if (SIGCHLD == sig) {
        pid = waitpid(-1, &status, 0);
        TRACE("PID: %d exited with status: %d", pid, status);
        return;
    }

    TRACE("entered with signal code: %d", sig);
}

/**
 * Handles a single RPC request: receives it, dispatches it and sends back the reply.
 * If the request asked for a pty (foreground process spawn), the pty session is entered
 * before returning.
 *
 * @param sockfd The socket file descriptor associated with the connected client.
 * @return True while the connection should keep being served, false once it must be torn down
 *         (protocol error, peer disconnect, or an explicit close request).
 */
static bool handle_client_request(int sockfd) {
    bool keep_serving = false;
    Rpc__RpcMessage *request = NULL;
    Rpc__RpcMessage reply = RPC__RPC_MESSAGE__INIT;
    uint32_t msg_id = 0;

    CHECK(rpc_msg_recv(sockfd, &request) == MSG_SUCCESS);
    CHECK(request->magic == RPC__PROTOCOL_CONSTANTS__MESSAGE_MAGIC);
    msg_id = request->msg_id;

    TRACE("client fd: %d, msg_id: %u", sockfd, msg_id);

    rpc_dispatch(request, &reply);

    CHECK(proto_msg_send(sockfd, (ProtobufCMessage *) &reply) == MSG_SUCCESS);

    // Keep serving unless the client explicitly asked to close the connection.
    keep_serving = msg_id != RPC__API__MSG_ID__REQ_CLOSE_CLIENT;

error:
    if (request) {
        rpc__rpc_message__free_unpacked(request, NULL);
    }
    if (reply.payload.data) {
        free(reply.payload.data);
    }

    // If a user requested pty (foreground process spawn), now handle it.
    if (keep_serving && g_pending_pty.valid) {
        enter_pty_mode(sockfd);
    }

    return keep_serving;
}

#ifdef __APPLE__

typedef struct {
    int sockfd;
    CFRunLoopRef runloop;
    volatile bool done;
} client_thread_args_t;

#define CLIENT_THREAD_STACK_SIZE (8 * 1024 * 1024)
#define RUNLOOP_POLL_INTERVAL (1.0)

/**
 * Gives the calling thread a real autorelease pool page, the way the main thread always has one.
 *
 * A freshly created thread has no autorelease pool page at all, and the objc runtime answers the
 * first objc_autoreleasePoolPush() on such a thread with EMPTY_POOL_PLACEHOLDER (0x1) instead of
 * an address inside a page. Clients walking a pool they pushed themselves would then be handed
 * that placeholder and scan unmapped memory. The second push installs the page for real.
 *
 * Neither pool is ever popped, matching what the main thread used to do: nothing drains the
 * objects a request autoreleased, so they stay valid for the next request to use.
 */
static void prepare_autorelease_pool(void) {
    extern void *objc_autoreleasePoolPush(void);

    objc_autoreleasePoolPush();
    objc_autoreleasePoolPush();
}

/**
 * Serves the client connection until it is torn down, then stops the run loop the main thread
 * is pumping.
 */
static void *client_thread(void *arg) {
    client_thread_args_t *args = (client_thread_args_t *) arg;

    prepare_autorelease_pool();

    while (handle_client_request(args->sockfd)) {}

    close(args->sockfd);
    args->done = true;
    CFRunLoopStop(args->runloop);
    return NULL;
}

/**
 * Serves the client from a dedicated thread while the main thread pumps its run loop.
 *
 * The main thread used to sit in recv() for the entire lifetime of the connection, so nothing ever
 * drained the main dispatch queue or the main run loop. Everything that needs them to make progress
 * - blocks dispatched to the main queue, run loop timers and sources, framework callbacks and
 * notifications delivered on the main run loop - silently did nothing for as long as a client was
 * connected. The only workaround was calling CFRunLoopRun() over RPC, which hangs the session that
 * called it.
 *
 * Requests are served on a dedicated thread rather than from a run loop source on the main thread
 * on purpose: a run loop drains an autorelease pool on every iteration, which would release every
 * autoreleased object a request handed back to the client before the next request can use it.
 *
 * @param sockfd The socket file descriptor associated with the connected client.
 */
static void serve_client_with_runloop(int sockfd) {
    bool attr_initialized = false;
    bool joinable = false;
    pthread_t thread;
    pthread_attr_t attr;
    client_thread_args_t args = {.sockfd = sockfd, .runloop = CFRunLoopGetCurrent(), .done = false};

    CHECK(0 == pthread_attr_init(&attr));
    attr_initialized = true;
    // Match the main thread's stack size, the served requests used to run on it.
    CHECK(0 == pthread_attr_setstacksize(&attr, CLIENT_THREAD_STACK_SIZE));
    CHECK(0 == pthread_create(&thread, &attr, client_thread, &args));
    joinable = true;

    // Pump the run loop until the connection is done with. The timeout also covers the case of a
    // connection that ends before this loop is entered, where CFRunLoopStop() had nothing to stop.
    while (!args.done) {
        CFRunLoopRunInMode(kCFRunLoopDefaultMode, RUNLOOP_POLL_INTERVAL, false);
    }

error:
    if (attr_initialized) {
        pthread_attr_destroy(&attr);
    }
    if (joinable) {
        pthread_join(thread, NULL);
    } else {
        close(sockfd);
    }
}

#endif// __APPLE__

/**
 * Manages client communication over a socket using the RPC (Remote Procedure Call) protocol.
 * This function performs message exchange with the connected client, processes incoming requests,
 * and sends appropriate responses. It ensures data integrity and protocol compliance and manages
 * specific client requests, such as pseudo-terminal handling or connection termination.
 *
 * @param sockfd The socket file descriptor associated with the connected client.
 */
void handle_client(int sockfd) {
    TRACE("enter. fd: %d", sockfd);

    CHECK(-1 != fcntl(sockfd, F_SETFD, FD_CLOEXEC));

    // Send handshake
    CHECK(rpc_send_handshake(sockfd) == MSG_SUCCESS);

#ifdef __APPLE__
    // The client socket is closed by serve_client_with_runloop().
    serve_client_with_runloop(sockfd);
    return;
#else
    while (handle_client_request(sockfd)) {}
#endif// __APPLE__

error:
    close(sockfd);
}

/**
 * The main entry point for the RPC server. Processes command-line arguments, initializes the server,
 * and manages client connections.
 *
 * Command-line options:
 * - `-p <port>`: Sets the port on which the server listens for incoming connections.
 * - `-o <output>`: Configures the output destination. Values:
 *   - `"stdout"`: Enables output to the standard output.
 *   - `"syslog"`: Enables output to the system logger.
 *   - `"file:<filename>"`: Enables logging output to the specified file.
 * - `-w`: Spawns a worker to handle incoming client connections.
 * - `-d`: Disables worker spawning, and handles the client directly.
 * - `-h`: Displays usage information and exits.
 *
 * @param argc The number of command-line arguments.
 * @param argv The array of command-line argument strings.
 * @return Returns 0 on success; non-zero if an error occurs during execution.
 */
int main(int argc, const char *argv[]) {
    int opt;
    bool worker_spawn = false;
    bool disable_worker = false;
    char port[MAX_OPTION_LEN] = DEFAULT_PORT;

    while ((opt = getopt(argc, (char *const *) argv, "hwdo:p:")) != -1) {
        switch (opt) {
        case 'p': {
            strncpy(port, optarg, sizeof(port) - 1);
            break;
        }
        case 'o': {
            if (0 == strcmp(optarg, "stdout")) {
                g_stdout = true;
            }
            if (0 == strcmp(optarg, "syslog")) {
                g_syslog = true;
            }
            char *file = strstr(optarg, "file:");
            if (file) {
                g_file = fopen(file + 5, "wb");
                if (!g_file) {
                    printf("failed to open %s for writing\n", optarg);
                }
            }
            break;
        }
        case 'w': {
            worker_spawn = true;
            break;
        }
        case 'd': {
            disable_worker = true;
            break;
        }
        case 'h':
        case '?':
        default: /* '?' */
        {
            printf(USAGE, argv[0], argv[0]);
            exit(EXIT_FAILURE);
        }
        }
    }

    signal(SIGPIPE, signal_handler);

    if (worker_spawn) {
        TRACE("New worker spawned");
        handle_client(WORKER_CLIENT_SOCKET_FD);
        exit(EXIT_SUCCESS);
    }

    int err = 0;
    int server_fd = -1;
    struct addrinfo hints;
    memset(&hints, 0, sizeof(hints));
    hints.ai_socktype = SOCK_STREAM;
    hints.ai_flags = AI_PASSIVE;// use my IP. "| AI_ADDRCONFIG"
    hints.ai_family = AF_INET6;

    struct addrinfo *servinfo;
    CHECK(0 == getaddrinfo(NULL, port, &hints, &servinfo));

    struct addrinfo *servinfo2 = servinfo;// servinfo->ai_next;
    char ipstr[INET6_ADDRSTRLEN];
    CHECK(inet_ntop(servinfo2->ai_family, get_in_addr(servinfo2->ai_addr), ipstr, sizeof(ipstr)));
    TRACE("Waiting for connections on [%s]:%s", ipstr, port);

    server_fd = socket(servinfo2->ai_family, servinfo2->ai_socktype, servinfo2->ai_protocol);
    CHECK(server_fd >= 0);
    CHECK(-1 != fcntl(server_fd, F_SETFD, FD_CLOEXEC));

    int yes_1 = 1;
    CHECK(0 == setsockopt(server_fd, SOL_SOCKET, SO_REUSEADDR, &yes_1, sizeof(yes_1)));
    CHECK(0 == bind(server_fd, servinfo2->ai_addr, servinfo2->ai_addrlen));

    freeaddrinfo(servinfo);

    CHECK(0 == listen(server_fd, MAX_CONNECTIONS));

#ifdef __APPLE__
    pthread_t runloop_thread;
    CHECK(0 == pthread_create(&runloop_thread, NULL, (void *(*) (void *) ) CFRunLoopRun, NULL));
#endif// __APPLE__

    signal(SIGCHLD, signal_handler);

    while (1) {
        struct sockaddr_storage their_addr;// connector's address information
        socklen_t addr_size = sizeof(their_addr);
        const int client_fd = accept(server_fd, (struct sockaddr *) &their_addr, &addr_size);
        CHECK(client_fd >= 0);
        CHECK(-1 != fcntl(client_fd, F_SETFD, FD_CLOEXEC));

        char ipstr[INET6_ADDRSTRLEN];
        CHECK(inet_ntop(their_addr.ss_family, get_in_addr((struct sockaddr *) &their_addr), ipstr, sizeof(ipstr)));
        TRACE("Got a connection from %s [%d]", ipstr, client_fd);
        if (disable_worker) {
            TRACE("Direct mode: handling client without spawning worker");
            handle_client(client_fd);
        } else {
            CHECK(spawn_worker_server(client_fd, argv, argc));
        }
    }

error:
    err = 1;
    if (-1 != server_fd) {
        close(server_fd);
    }

    return err;
}
