#include "common.h"
#include <execinfo.h>
#include <spawn.h>
#include <sys/socket.h>
#include <sys/utsname.h>
#include <syslog.h>
#include <unistd.h>

#ifdef __APPLE__
#include <os/log.h>

struct os_log_s {
    int a;
};

struct os_log_s _os_log_default;
#endif// __APPLE__

bool g_stdout = false;
bool g_syslog = false;
FILE *g_file = NULL;
pending_pty_t g_pending_pty = {.pid = 0, .master = -1, .valid = false};

#define BT_BUF_SIZE (100)

void print_backtrace() {
    int nptrs;
    void *buffer[BT_BUF_SIZE];
    char **strings;

    nptrs = backtrace(buffer, BT_BUF_SIZE);
    trace("BACKTRACE", "backtrace() returned %d addresses", nptrs);

    /* The call backtrace_symbols_fd(buffer, nptrs, STDOUT_FILENO)
        would produce similar output to the following: */

    strings = backtrace_symbols(buffer, nptrs);
    if (strings == NULL) {
        perror("backtrace_symbols");
        return;
    }

    for (int j = 0; j < nptrs; j++) {
        trace("BACKTRACE:\t", "%s", strings[j]);
    }

    free(strings);
}

void trace(const char *prefix, const char *fmt, ...) {
    if (!g_stdout && !g_syslog) {
        return;
    }

    char line[1022];
    char prefixed_line[1024];

    va_list args;
    va_start(args, fmt);
    vsprintf(line, fmt, args);
    va_end(args);

    sprintf(prefixed_line, "%s: %s", prefix, line);

    if (g_stdout) {
        puts(prefixed_line);
        fflush(stdout);
    }
    if (g_syslog) {
#ifdef __APPLE__
        os_log(&_os_log_default, "%{public}s", prefixed_line);
#else // __APPLE__
        syslog(LOG_DEBUG, "%s", prefixed_line);
#endif// !__APPLE__
    }
    if (g_file) {
        fprintf(g_file, "%s\n", prefixed_line);
        fflush(g_file);
    }
}
bool copy_arr_with_null(char ***dest, char **src, size_t n_src) {
    bool ret = false;
    if (n_src > 0) {
        *dest = (char **) calloc(n_src + 1, sizeof(char *));
        CHECK(*dest != NULL);
        memcpy(*dest, src, sizeof(char *) * n_src);
    }
    ret = true;
error:
    return ret;
}

bool internal_spawn(bool background, char **argv, char **envp, pid_t *pid, int *master_fd) {
    bool ret = false;
    int slave_fd = -1;
    *master_fd = -1;
    *pid = INVALID_PID;

    // call setsid() on child so Ctrl-C and all other control characters are set
    // in a different terminal and process group
    posix_spawnattr_t attr;
    CHECK(0 == posix_spawnattr_init(&attr));
    CHECK(0 == posix_spawnattr_setflags(&attr, POSIX_SPAWN_SETSID));

    posix_spawn_file_actions_t actions;
    CHECK(0 == posix_spawn_file_actions_init(&actions));

    if (!background) {
        // We need a new pseudoterminal to avoid bufferring problems. The 'atos'
        // tool in particular detects when it's talking to a pipe and forgets to
        // flush the output stream after sending a response.
        *master_fd = posix_openpt(O_RDWR);
        CHECK(-1 != *master_fd);
        CHECK(0 == grantpt(*master_fd));
        CHECK(0 == unlockpt(*master_fd));

        char slave_pty_name[128];
        CHECK(0 == ptsname_r(*master_fd, slave_pty_name, sizeof(slave_pty_name)));

        TRACE("slave_pty_name: %s", slave_pty_name);

        slave_fd = open(slave_pty_name, O_RDWR);
        CHECK(-1 != slave_fd);

        CHECK(0 == posix_spawn_file_actions_adddup2(&actions, slave_fd, STDIN_FILENO));
        CHECK(0 == posix_spawn_file_actions_adddup2(&actions, slave_fd, STDOUT_FILENO));
        CHECK(0 == posix_spawn_file_actions_adddup2(&actions, slave_fd, STDERR_FILENO));
        CHECK(0 == posix_spawn_file_actions_addclose(&actions, slave_fd));
        CHECK(0 == posix_spawn_file_actions_addclose(&actions, *master_fd));
    } else {
        CHECK(0 == posix_spawn_file_actions_addopen(&actions, STDIN_FILENO, "/dev/null", O_RDONLY, 0));
        CHECK(0 == posix_spawn_file_actions_addopen(&actions, STDOUT_FILENO, "/dev/null", O_WRONLY, 0));
        CHECK(0 == posix_spawn_file_actions_addopen(&actions, STDERR_FILENO, "/dev/null", O_WRONLY, 0));
    }

    CHECK(0 == posix_spawnp(pid, argv[0], &actions, &attr, argv, envp));
    CHECK(*pid != INVALID_PID);

    posix_spawnattr_destroy(&attr);
    posix_spawn_file_actions_destroy(&actions);

    ret = true;

error:
    if (slave_fd != -1) {
        close(slave_fd);
    }
    if (!ret) {
        if (*master_fd != -1) {
            close(*master_fd);
        }
        *pid = INVALID_PID;
    }
    return ret;
}

/**
 * Handles the sending or receiving of the complete specified data buffer over a socket,
 * using the provided I/O operation function. Ensures all bytes are transferred or
 * returns false upon encountering an error or EOF (if reading).
 *
 * @param io_op The I/O operation function (e.g., send or recv) to be used for data transfer.
 * @param sockfd The socket file descriptor on which the operation is performed.
 * @param buffer A pointer to the data buffer to be sent or where data is received into.
 * @param total_len The total number of bytes to be sent or received.
 * @param io_flags Flags to be used with the I/O operation.
 * @param reading Indicates whether the operation is a read (true) or write (false).
 * @return Returns true if the entire buffer is successfully transferred, false otherwise.
 */
static bool sock_io_all(ssize_t (*io_op)(int, void *, size_t, int), int sockfd, void *buffer, size_t total_len,
                        int io_flags, bool reading) {
    uint8_t *bytes = (uint8_t *) buffer;
    size_t transferred = 0;
    errno = 0;// avoid stale errno being reported by CHECK
    while (transferred < total_len) {
        ssize_t rc = io_op(sockfd, bytes + transferred, total_len - transferred, io_flags);
        if (rc > 0) {
            transferred += (size_t) rc;
            continue;
        }

        if (rc == 0) {
            // For reads, 0 = EOF/peer closed; mark as connection closed.
            if (reading) {
                errno = 0;// indicate clean EOF (avoid misleading ENOENT)
                return false;
            }
            // For writes, treat as try again.
            continue;
        }
        if (errno == EINTR) {
            continue;
        }
        if (errno == EAGAIN || errno == EWOULDBLOCK) {
            continue;
        }
        // real error
        return false;
    }
    return true;
}

static bool recvall(int sockfd, void *buf, size_t len) {
    return sock_io_all((ssize_t(*)(int, void *, size_t, int)) recv, sockfd, buf, len, /*flags=*/0, /*is_read=*/true);
}

static bool sendall(int sockfd, const void *buf, size_t len) {
    return sock_io_all((ssize_t(*)(int, void *, size_t, int)) send, sockfd, (void *) buf, len, /*flags=*/MSG_NOSIGNAL,
                       /*is_read=*/false);
}

bool writeall(int fd, const char *buf, size_t len) {
    bool ret = false;

    size_t total_bytes = 0;
    size_t bytes;

    while (len > 0) {
        bytes = write(fd, buf + total_bytes, len);
        CHECK(bytes != -1);

        total_bytes += bytes;
        len -= bytes;
    }
    ret = true;
error:
    return ret;
}

/**
 * Sends a handshake message over the specified socket descriptor. The handshake
 * message contains system and architecture information, platform details, server
 * version, client ID, and a magic number for identifying the message type.
 *
 * @param sockfd The socket file descriptor over which the handshake message is sent.
 * @return Returns MSG_SUCCESS if the handshake message is successfully sent;
 *         otherwise, returns MSG_FAILURE if an error occurs.
 */
msg_return_t rpc_send_handshake(int sockfd) {
    struct utsname uname_buf;

    CHECK(0 == uname(&uname_buf));
    Rpc__Handshake handshake = RPC__HANDSHAKE__INIT;
    handshake.arch = RPC__ARCH__ARCH_UNKNOWN;
    handshake.sysname = uname_buf.sysname;
    handshake.machine = uname_buf.machine;
    handshake.platform = PLATFORM;
    handshake.server_version = RPC__PROTOCOL_CONSTANTS__SERVER_VERSION;
    handshake.client_id = getpid();
    handshake.magic = RPC__PROTOCOL_CONSTANTS__MESSAGE_MAGIC;

#ifdef __ARM_ARCH_ISA_A64
    handshake.arch = RPC__ARCH__ARCH_ARM64;
#endif

    return proto_msg_send(sockfd, (ProtobufCMessage *) &handshake);

error:
    return MSG_FAILURE;
}

/**
 * Sends a Protobuf message over a socket. The method first serializes the message
 * and transmits its packed size followed by the serialized data to the specified socket.
 *
 * @param sockfd The socket file descriptor to send the message through.
 * @param msg A pointer to the ProtobufCMessage struct representing the message to be sent.
 * @return Returns MSG_SUCCESS if the operation is successful, otherwise MSG_FAILURE.
 */
msg_return_t proto_msg_send(int sockfd, const ProtobufCMessage *msg) {
    uint8_t *buffer = NULL;
    msg_return_t ret = MSG_FAILURE;
    // Get packed size and pack the message
    const size_t packed_size = protobuf_c_message_get_packed_size(msg);
    buffer = (uint8_t *) malloc(packed_size);
    CHECK(buffer != NULL);

    // Send size first, then data
    CHECK(sendall(sockfd, &packed_size, sizeof(packed_size)));
    CHECK(protobuf_c_message_pack(msg, buffer) == packed_size);
    CHECK(sendall(sockfd, buffer, packed_size));

    ret = MSG_SUCCESS;
error:
    safe_free(buffer);
    return ret;
}
/**
 * Receives and parses a Protobuf message from a socket. This function retrieves
 * the message size, allocates memory for the message, reads the serialized data, and
 * unpacks it into a ProtobufCMessage structure using the provided descriptor.
 *
 * @param sockfd The socket file descriptor from which the message is received.
 * @param msg A double pointer to a ProtobufCMessage, where the unpacked message will be stored.
 * @param descriptor The ProtobufCMessageDescriptor that describes the structure of the message to be unpacked.
 * @return Returns MSG_SUCCESS if the message is successfully received and unpacked,
 *         otherwise returns MSG_FAILURE.
 */
msg_return_t proto_msg_recv(int sockfd, ProtobufCMessage **msg, const ProtobufCMessageDescriptor *descriptor) {
    uint8_t *buffer = NULL;
    msg_return_t ret = MSG_FAILURE;
    size_t msg_size;

    CHECK(recvall(sockfd, &msg_size, sizeof(msg_size)));
    buffer = (uint8_t *) malloc(msg_size);
    CHECK(buffer != NULL);

    // Read the complete message
    CHECK(recvall(sockfd, buffer, msg_size));
    CHECK(descriptor->magic == PROTOBUF_C__MESSAGE_DESCRIPTOR_MAGIC);

    // Unpack the message using the provided descriptor
    *msg = protobuf_c_message_unpack(descriptor, NULL, msg_size, buffer);
    CHECK(*msg != NULL);

    ret = MSG_SUCCESS;
error:
    safe_free(buffer);
    return ret;
}

/**
 * Receives an RPC message over the specified socket file descriptor and
 * deserializes it into the provided message structure. The function wraps
 * the proto_msg_recv function and handles messages defined by the rpc__rpc_message__descriptor.
 *
 * @param sockfd The socket file descriptor from which the RPC message is received.
 * @param msg Double pointer to an Rpc__RpcMessage structure where the deserialized
 *            message will be stored. The caller is responsible for freeing the memory
 *            allocated for the message after use.
 * @return Returns MSG_SUCCESS if the message is successfully received and deserialized,
 *         or MSG_FAILURE in case of an error or if the received data is invalid.
 */
msg_return_t rpc_msg_recv(int sockfd, Rpc__RpcMessage **msg) {
    return proto_msg_recv(sockfd, (ProtobufCMessage **) msg, &rpc__rpc_message__descriptor);
}