#include <execinfo.h>
#include <stdarg.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/socket.h>
#include <syslog.h>
#include <unistd.h>

#include "common.h"

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

void safe_free(void **ptr) {
    if (!*ptr) {
        return;
    }
    free(*ptr);
    *ptr = NULL;
}

static bool sock_io_all(ssize_t (*op)(int, void *, size_t, int),
                        int fd, void *buf, size_t len, int flags, bool is_read) {
    uint8_t *p = (uint8_t *) buf;
    size_t done = 0;
    while (done < len) {
        ssize_t n = op(fd, p + done, len - done, flags);
        if (n > 0) {
            done += (size_t) n;
            continue;
        }

        if (n == 0) {
            /* for reads, 0 = EOF/peer closed; for writes, treat as "try again" */
            if (is_read) {
                return false;
            }
            continue;
        }
        /* Interrupted by a signal (e.g., debugger attach/SIGCHLD); not a real error. */
        if (errno == EINTR) {
            continue;
        }
        if (errno == EAGAIN || errno == EWOULDBLOCK) {
            continue;
        }
        /* real error */
        return false;
    }
    return true;
}

static bool recvall(int sockfd, void *buf, size_t len) {
    return sock_io_all((ssize_t(*)(int, void *, size_t, int)) recv,
                       sockfd, buf, len, /*flags=*/0, /*is_read=*/true);
}

static bool sendall(int sockfd, const void *buf, size_t len) {
    return sock_io_all((ssize_t(*)(int, void *, size_t, int)) send,
                       sockfd, (void *) buf, len, /*flags=*/MSG_NOSIGNAL, /*is_read=*/false);
}

bool receive_message(int sockfd, char **buf, size_t *size) {
    *buf = NULL;
    *size = 0;
    bool ret = false;

    size_t n = 0;
    CHECK(recvall(sockfd, &n, sizeof(n)));
    CHECK(n > 0);

    char *tmp = (char *) malloc(n);

    CHECK(tmp);
    CHECK(recvall(sockfd, tmp, n))

    *buf = tmp;
    *size = n;
    ret = true;
error:
    if (!ret) {
        safe_free((void **) &tmp);
    }
    return ret;
}

bool send_message(int sockfd, const uint8_t *buf, size_t len) {
    bool ret = false;
    CHECK(sendall(sockfd, &len, sizeof(len)));
    CHECK(sendall(sockfd, buf, len));
    ret = true;
error:
    return ret;
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

bool send_response(int sockfd, ProtobufCMessage *resp) {
    bool ret = false;
    Rpc__Response response = RPC__RESPONSE__INIT;
    char *c_name = (char *) (ProtobufCMessageDescriptor *) resp->descriptor->c_name;

    if (strcmp("Rpc__ResponseCmdExec", c_name) == 0) {
        response.type_case = RPC__RESPONSE__TYPE_EXEC;
        response.exec = (Rpc__ResponseCmdExec *) resp;
    } else if (strcmp("Rpc__ResponseCmdExecChunk", c_name) == 0) {
        response.type_case = RPC__RESPONSE__TYPE_EXEC_CHUNK;
        response.exec_chunk = (Rpc__ResponseCmdExecChunk *) resp;
    } else if (strcmp("Rpc__ResponseDlopen", c_name) == 0) {
        response.type_case = RPC__RESPONSE__TYPE_DLOPEN;
        response.dlopen = (Rpc__ResponseDlopen *) resp;
    } else if (strcmp("Rpc__ResponseDlclose", c_name) == 0) {
        response.type_case = RPC__RESPONSE__TYPE_DLCLOSE;
        response.dlclose = (Rpc__ResponseDlclose *) resp;
    } else if (strcmp("Rpc__ResponseDlsym", c_name) == 0) {
        response.type_case = RPC__RESPONSE__TYPE_DLSYM;
        response.dlsym = (Rpc__ResponseDlsym *) resp;
    } else if (strcmp("Rpc__ResponsePeek", c_name) == 0) {
        response.type_case = RPC__RESPONSE__TYPE_PEEK;
        response.peek = (Rpc__ResponsePeek *) resp;
    } else if (strcmp("Rpc__ResponsePoke", c_name) == 0) {
        response.type_case = RPC__RESPONSE__TYPE_POKE;
        response.poke = (Rpc__ResponsePoke *) resp;
    } else if (strcmp("Rpc__ResponseCall", c_name) == 0) {
        response.type_case = RPC__RESPONSE__TYPE_CALL;
        response.call = (Rpc__ResponseCall *) resp;
    } else if (strcmp("Rpc__ResponseError", c_name) == 0) {
        response.type_case = RPC__RESPONSE__TYPE_ERROR;
        response.error = (Rpc__ResponseError *) resp;
    } else if (strcmp("Rpc__ResponseDummyBlock", c_name) == 0) {
        response.type_case = RPC__RESPONSE__TYPE_DUMMY_BLOCK;
        response.dummy_block = (Rpc__ResponseDummyBlock *) resp;
    } else if (strcmp("Rpc__ResponseShowObject", c_name) == 0) {
        response.type_case = RPC__RESPONSE__TYPE_SHOW_OBJECT;
        response.show_object = (Rpc__ResponseShowObject *) resp;
    } else if (strcmp("Rpc__ResponseGetClassList", c_name) == 0) {
        response.type_case = RPC__RESPONSE__TYPE_CLASS_LIST;
        response.class_list = (Rpc__ResponseGetClassList *) resp;
    } else if (strcmp("Rpc__ResponseShowClass", c_name) == 0) {
        response.type_case = RPC__RESPONSE__TYPE_SHOW_CLASS;
        response.show_class = (Rpc__ResponseShowClass *) resp;
    } else if (strcmp("Rpc__ResponseListdir", c_name) == 0) {
        response.type_case = RPC__RESPONSE__TYPE_LIST_DIR;
        response.list_dir = (Rpc__ResponseListdir *) resp;
    } else {
        TRACE("Unknown response type_case: %s\n", c_name);
        goto error;
    }
    uint8_t *buffer = NULL;
    size_t len = rpc__response__get_packed_size(&response);
    CHECK(len > 0);
    buffer = (uint8_t *) malloc(len * sizeof(uint8_t));
    CHECK(buffer != NULL);
    CHECK(rpc__response__pack(&response, buffer) > 0);
    CHECK(send_message(sockfd, buffer, len));
    ret = true;

error:
    safe_free((void **) &buffer);
    return ret;
}