#include <arpa/inet.h>
#include <errno.h>
#include <fcntl.h>
#include <netdb.h>
#include <netinet/in.h>
#include <util.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/select.h>
#include <sys/socket.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <termios.h>
#include <unistd.h>
#include <pthread.h>
#include <stdarg.h>
#include <spawn.h>
#include <dlfcn.h>
#include <sys/stat.h>
#include <sys/ioctl.h>

#include "common.h"

#define DEFAULT_PORT ("5910")
#define DEFAULT_SHELL ("/bin/sh")
#define USAGE ("Usage: %s [-p port] [-s shell]")
#define MAGIC (0x12345678)
#define MAX_CONNECTIONS (1024)

#define MAX_PATH_LEN (1024)
#define MAX_OPTION_LEN (256)
#define BUFFERSIZE (64 * 1024)

extern char **environ;

typedef enum
{
    CMD_EXEC = 0,
    CMD_DLOPEN = 1,
    CMD_DLCLOSE = 2,
    CMD_DLSYM = 3,
    CMD_CALL = 4,
    CMD_PEEK = 5,
    CMD_POKE = 6,
} cmd_type_t;

typedef enum
{
    CMD_EXEC_CHUNK_TYPE_STDOUT = 0,
    CMD_EXEC_CHUNK_TYPE_EXITCODE = 1,
} cmd_exec_chunk_type_t;

typedef struct
{
    u32 type;
    u32 size;
} cmd_exec_chunk_t;

typedef struct
{
    char filename[MAX_PATH_LEN];
    u32 mode;
} cmd_dlopen_t;

typedef struct
{
    u64 lib;
} cmd_dlclose_t;

typedef struct
{
    u64 lib;
    char symbol_name[MAX_PATH_LEN];
} cmd_dlsym_t;

typedef struct
{
    u64 address;
    u64 argc;
    u64 argv[0];
} cmd_call_t;

typedef struct
{
    u64 address;
    u64 size;
} cmd_peek_t;

typedef struct
{
    u64 address;
    u64 size;
    u8 data[0];
} cmd_poke_t;

typedef struct
{
    u32 magic;
    u32 cmd_type;
} protocol_message_t;

void sigchld_handler(int s)
{
    (void)s;

    // TODO: close socket associated with this pid
    while (waitpid(-1, NULL, WNOHANG) > 0)
        ;
    TRACE("child died.");
}

void *get_in_addr(struct sockaddr *sa) // get sockaddr, IPv4 or IPv6:
{
    return sa->sa_family == AF_INET ? (void *)&(((struct sockaddr_in *)sa)->sin_addr) : (void *)&(((struct sockaddr_in6 *)sa)->sin6_addr);
}

int internal_spawn(char *const *argv, pid_t *pid)
{
    int master_fd = -1;
    int slave_fd = -1;
    int res = 0;

    // We need a new pseudoterminal to avoid bufferring problems. The 'atos' tool
    // in particular detects when it's talking to a pipe and forgets to flush the
    // output stream after sending a response.
    master_fd = posix_openpt(O_RDWR);
    CHECK(-1 != master_fd);
    CHECK(0 == grantpt(master_fd));
    CHECK(0 == unlockpt(master_fd));

    // Use TIOCPTYGNAME instead of ptsname() to avoid threading problems.
    char slave_pty_name[128];
    CHECK(-1 != ioctl(master_fd, TIOCPTYGNAME, slave_pty_name));

    TRACE("slave_pty_name: %s", slave_pty_name);

    slave_fd = open(slave_pty_name, O_RDWR);
    CHECK(-1 != slave_fd);

    posix_spawn_file_actions_t actions;
    CHECK(0 == posix_spawn_file_actions_init(&actions));
    CHECK(0 == posix_spawn_file_actions_adddup2(&actions, slave_fd, STDIN_FILENO));
    CHECK(0 == posix_spawn_file_actions_adddup2(&actions, slave_fd, STDOUT_FILENO));
    CHECK(0 == posix_spawn_file_actions_adddup2(&actions, slave_fd, STDERR_FILENO));
    CHECK(0 == posix_spawn_file_actions_addclose(&actions, slave_fd));
    CHECK(0 == posix_spawn_file_actions_addclose(&actions, master_fd));
    CHECK(0 == posix_spawnp(pid, argv[0], &actions, NULL, argv, environ));

    close(slave_fd);
    slave_fd = -1;

    return master_fd;

error:
    if (master_fd != -1)
    {
        close(master_fd);
    }
    if (slave_fd != -1)
    {
        close(slave_fd);
    }
    return -1;
}

bool handle_exec(int sockfd)
{
    int master = -1;
    int result = false;
    char **argv = NULL;
    u32 argc;
    CHECK(recvall(sockfd, (char *)&argc, sizeof(argc)));

    // +1 for additional NULL at end of list
    size_t argv_size = (argc + 1) * sizeof(char *);
    argv = (char **)malloc(argv_size * sizeof(char *));
    memset(argv, 0, argv_size * sizeof(char *));

    for (u32 i = 0; i < argc; ++i)
    {
        u32 len;
        CHECK(recvall(sockfd, (char *)&len, sizeof(len)));

        // +1 for additional \0 at end of each string
        size_t str_size = (len + 1) * sizeof(char);
        argv[i] = malloc(str_size * sizeof(char));
        CHECK(argv[i] != NULL);

        CHECK(recvall(sockfd, argv[i], len * sizeof(char)));
        argv[i][len] = '\0';
    }

    pid_t pid;

    master = internal_spawn((char *const *)argv, &pid);
    CHECK(master >= 0);
    CHECK(sendall(sockfd, (char *)&pid, sizeof(u32)));

    fd_set readfds;
    char buf[BUFFERSIZE];
    int maxfd = master > sockfd ? master : sockfd;
    int nbytes = 0;

    while (true)
    {
        FD_ZERO(&readfds);
        FD_SET(master, &readfds);
        FD_SET(sockfd, &readfds);

        CHECK(select(maxfd + 1, &readfds, NULL, NULL, NULL) != -1);

        if (FD_ISSET(master, &readfds))
        {
            nbytes = read(master, buf, BUFFERSIZE);
            if (nbytes < 1)
            {
                break;
            }

            cmd_exec_chunk_t chunk;
            chunk.type = CMD_EXEC_CHUNK_TYPE_STDOUT;
            chunk.size = nbytes;

            CHECK(sendall(sockfd, (char *)&chunk, sizeof(chunk)));
            CHECK(sendall(sockfd, buf, chunk.size));
        }

        if (FD_ISSET(sockfd, &readfds))
        {
            nbytes = recv(sockfd, buf, BUFFERSIZE, 0);
            if (nbytes < 1)
            {
                break;
            }
            CHECK(writeall(master, buf, nbytes));
        }
    }

    // TODO: real value
    s32 err = 0;
    cmd_exec_chunk_t chunk;
    chunk.type = CMD_EXEC_CHUNK_TYPE_EXITCODE;
    chunk.size = sizeof(err);

    CHECK(sendall(sockfd, (char *)&chunk, sizeof(chunk)));
    CHECK(sendall(sockfd, (char *)&err, chunk.size));

    TRACE("sent exit code to client fd: %d", sockfd);

    result = true;

error:
    if (argv)
    {
        for (u32 i = 0; i < argc; ++i)
        {
            if (argv[i])
            {
                free(argv[i]);
            }
        }
        free(argv);
    }

    if (-1 != master)
    {
        TRACE("close master: %d", master);
        if (0 != close(master))
        {
            perror("close");
        }
    }

    return result;
}

bool handle_dlopen(int sockfd)
{
    int result = false;
    cmd_dlopen_t cmd;
    CHECK(recvall(sockfd, (char *)&cmd, sizeof(cmd)));

    u64 err = (u64)dlopen(cmd.filename, cmd.mode);
    CHECK(sendall(sockfd, (char *)&err, sizeof(err)));

    result = true;

error:
    return result;
}

bool handle_dlclose(int sockfd)
{
    int result = false;
    cmd_dlclose_t cmd;
    CHECK(recvall(sockfd, (char *)&cmd, sizeof(cmd)));

    u64 err = (u64)dlclose((void *)cmd.lib);
    CHECK(sendall(sockfd, (char *)&err, sizeof(err)));

    result = true;

error:
    return result;
}

bool handle_dlsym(int sockfd)
{
    int result = false;
    cmd_dlsym_t cmd;
    CHECK(recvall(sockfd, (char *)&cmd, sizeof(cmd)));

    u64 err = (u64)dlsym((void *)cmd.lib, cmd.symbol_name);
    CHECK(sendall(sockfd, (char *)&err, sizeof(err)));

    result = true;

error:
    return result;
}

bool handle_call(int sockfd)
{
    typedef u64 (*call_argc0_t)();
    typedef u64 (*call_argc1_t)(u64);
    typedef u64 (*call_argc2_t)(u64, u64);
    typedef u64 (*call_argc3_t)(u64, u64, u64);
    typedef u64 (*call_argc4_t)(u64, u64, u64, u64);
    typedef u64 (*call_argc5_t)(u64, u64, u64, u64, u64);
    typedef u64 (*call_argc6_t)(u64, u64, u64, u64, u64, u64);
    typedef u64 (*call_argc7_t)(u64, u64, u64, u64, u64, u64, u64);
    typedef u64 (*call_argc8_t)(u64, u64, u64, u64, u64, u64, u64, u64);
    typedef u64 (*call_argc9_t)(u64, u64, u64, u64, u64, u64, u64, u64, u64);
    typedef u64 (*call_argc10_t)(u64, u64, u64, u64, u64, u64, u64, u64, u64, u64);
    typedef u64 (*call_argc11_t)(u64, u64, u64, u64, u64, u64, u64, u64, u64, u64, u64);

    TRACE("enter");
    s64 err = 0;
    int result = false;
    u64 *argv = NULL;
    cmd_call_t cmd;
    CHECK(recvall(sockfd, (char *)&cmd, sizeof(cmd)));

    argv = (u64 *)malloc(sizeof(u64) * cmd.argc);
    CHECK(recvall(sockfd, (char *)argv, sizeof(u64) * cmd.argc));

    switch (cmd.argc)
    {
    case 0:
        err = ((call_argc0_t)cmd.address)();
        break;
    case 1:
        err = ((call_argc1_t)cmd.address)(argv[0]);
        break;
    case 2:
        err = ((call_argc2_t)cmd.address)(argv[0], argv[1]);
        break;
    case 3:
        err = ((call_argc3_t)cmd.address)(argv[0], argv[1], argv[2]);
        break;
    case 4:
        err = ((call_argc4_t)cmd.address)(argv[0], argv[1], argv[2], argv[3]);
        break;
    case 5:
        err = ((call_argc5_t)cmd.address)(argv[0], argv[1], argv[2], argv[3], argv[4]);
        break;
    case 6:
        err = ((call_argc6_t)cmd.address)(argv[0], argv[1], argv[2], argv[3], argv[4], argv[5]);
        break;
    case 7:
        err = ((call_argc7_t)cmd.address)(argv[0], argv[1], argv[2], argv[3], argv[4], argv[5], argv[6]);
        break;
    case 8:
        err = ((call_argc8_t)cmd.address)(argv[0], argv[1], argv[2], argv[3], argv[4], argv[5], argv[6], argv[7]);
        break;
    case 9:
        err = ((call_argc9_t)cmd.address)(argv[0], argv[1], argv[2], argv[3], argv[4], argv[5], argv[6], argv[7], argv[8]);
        break;
    case 10:
        err = ((call_argc10_t)cmd.address)(argv[0], argv[1], argv[2], argv[3], argv[4], argv[5], argv[6], argv[7], argv[8], argv[9]);
        break;
    case 11:
        err = ((call_argc11_t)cmd.address)(argv[0], argv[1], argv[2], argv[3], argv[4], argv[5], argv[6], argv[7], argv[8], argv[9], argv[10]);
        break;
    }

    CHECK(sendall(sockfd, (char *)&err, sizeof(err)));

    result = true;

error:
    if (argv)
    {
        free(argv);
    }
    return result;
}

bool handle_peek(int sockfd)
{
    TRACE("enter");
    s64 err = 0;
    int result = false;
    u64 *argv = NULL;
    cmd_peek_t cmd;
    CHECK(recvall(sockfd, (char *)&cmd, sizeof(cmd)));
    CHECK(sendall(sockfd, (char *)cmd.address, cmd.size));

    result = true;

error:
    if (argv)
    {
        free(argv);
    }
    return result;
}

bool handle_poke(int sockfd)
{
    TRACE("enter");
    s64 err = 0;
    int result = false;
    u64 *argv = NULL;
    cmd_poke_t cmd;
    CHECK(recvall(sockfd, (char *)&cmd, sizeof(cmd)));
    CHECK(recvall(sockfd, (char *)cmd.address, cmd.size));

    result = true;

error:
    if (argv)
    {
        free(argv);
    }
    return result;
}

void handle_client(int sockfd)
{
    TRACE("enter. fd: %d", sockfd);

    while (true)
    {
        protocol_message_t cmd;
        TRACE("recv");
        CHECK(recvall(sockfd, (char *)&cmd, sizeof(cmd)));
        CHECK(cmd.magic == MAGIC);

        TRACE("cmd type: %d", cmd.cmd_type);

        switch (cmd.cmd_type)
        {
        case CMD_EXEC:
        {
            handle_exec(sockfd);
            break;
        }
        case CMD_DLOPEN:
        {
            handle_dlopen(sockfd);
            break;
        }
        case CMD_DLSYM:
        {
            handle_dlsym(sockfd);
            break;
        }
        case CMD_CALL:
        {
            handle_call(sockfd);
            break;
        }
        case CMD_PEEK:
        {
            handle_peek(sockfd);
            break;
        }
        case CMD_POKE:
        {
            handle_poke(sockfd);
            break;
        }
        default:
        {
            TRACE("unknown cmd");
        }
        }
    }

error:
    TRACE("close client fd: %d", sockfd);
    if (0 != close(sockfd))
    {
        perror("close");
    }
}

int main(int argc, const char *argv[])
{
    int opt;
    char port[MAX_OPTION_LEN] = DEFAULT_PORT;

    while ((opt = getopt(argc, (char *const *)argv, "p:")) != -1)
    {
        switch (opt)
        {
        case 'p':
        {
            strncpy(port, optarg, sizeof(port) - 1);
            break;
        }
        default: /* '?' */
        {
            TRACE(USAGE, argv[0]);
            exit(EXIT_FAILURE);
        }
        }
    }

    int err = 0;
    int server_fd = -1;
    struct addrinfo hints;
    memset(&hints, 0, sizeof(hints));
    hints.ai_socktype = SOCK_STREAM;
    hints.ai_flags = AI_PASSIVE; // use my IP. "| AI_ADDRCONFIG"
    hints.ai_family = AF_UNSPEC; // AF_INET or AF_INET6 to force version
    hints.ai_family = AF_INET6;  // IPv4 addresses will be like ::ffff:127.0.0.1

    struct addrinfo *servinfo;
    CHECK(0 == getaddrinfo(NULL, port, &hints, &servinfo));

    struct addrinfo *servinfo2 = servinfo; // servinfo->ai_next;
    char ipstr[INET6_ADDRSTRLEN];
    CHECK(inet_ntop(servinfo2->ai_family, get_in_addr(servinfo2->ai_addr), ipstr, sizeof(ipstr)));
    TRACE("Waiting for connections on [%s]:%s", ipstr, port);

    server_fd = socket(servinfo2->ai_family, servinfo2->ai_socktype, servinfo2->ai_protocol);
    CHECK(server_fd >= 0);

    int yes_1 = 1;
    CHECK(0 == setsockopt(server_fd, SOL_SOCKET, SO_REUSEADDR, &yes_1, sizeof(yes_1)));
    CHECK(0 == bind(server_fd, servinfo2->ai_addr, servinfo2->ai_addrlen));

    freeaddrinfo(servinfo); // all done with this structure

    CHECK(0 == listen(server_fd, MAX_CONNECTIONS));

    struct sigaction sa;
    sa.sa_handler = sigchld_handler; // reap all dead processes
    sigemptyset(&sa.sa_mask);
    sa.sa_flags = SA_RESTART;
    CHECK(0 == sigaction(SIGCHLD, &sa, NULL));

    while (1)
    {
        struct sockaddr_storage their_addr; // connector's address information
        socklen_t addr_size = sizeof(their_addr);
        int client_fd = accept(server_fd, (struct sockaddr *)&their_addr, &addr_size);
        CHECK(client_fd >= 0);

        char ipstr[INET6_ADDRSTRLEN];
        CHECK(inet_ntop(their_addr.ss_family, get_in_addr((struct sockaddr *)&their_addr), ipstr, sizeof(ipstr)));
        TRACE("Got a connection from %s [%d]", ipstr, client_fd);

        pthread_t thread;
        CHECK(0 == pthread_create(&thread, NULL, (void *_Nullable (*_Nonnull)(void *_Nullable))handle_client, (void *)(long)client_fd));
    }

error:
    err = 1;

clean:
    if (-1 != server_fd)
    {
        close(server_fd);
    }

    return err;
}
