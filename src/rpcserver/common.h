#ifndef __COMMON_H_
#define __COMMON_H_
#ifndef __APPLE__
#define _XOPEN_SOURCE (600)
#define _GNU_SOURCE (1)
#endif// __APPLE__

#include "protos/rpc.pb-c.h"
#include "protos/rpc_api.pb-c.h"

#include <errno.h>
#include <fcntl.h>
#include <pthread.h>
#include <stdarg.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/wait.h>

typedef unsigned char u8;
typedef unsigned int u32;
typedef signed int s32;
typedef unsigned long u64;
typedef unsigned long s64;

#ifdef __ARM_ARCH_ISA_A64
#define MAX_STACK_ARGS (16)
#define MAX_REGS_ARGS (8)
#define GPR_COUNT (30)
typedef struct {
    uint64_t x[MAX_REGS_ARGS];
    double d[MAX_REGS_ARGS];
    uint64_t stack[MAX_STACK_ARGS];
} arm_args_t;
#else
#define MAX_ARGS (17)
#endif

#define INVALID_PID (0xffffffff)
#define TRACE(...) trace(__PRETTY_FUNCTION__, __VA_ARGS__)
#define CHECK(expression)                                                                                              \
    if (!(expression)) {                                                                                               \
        if (errno) {                                                                                                   \
            trace(__PRETTY_FUNCTION__, "ERROR on expression: %s: errno: %d (%s)", #expression, errno,                  \
                  strerror(errno));                                                                                    \
        }                                                                                                              \
        print_backtrace();                                                                                             \
        goto error;                                                                                                    \
    }

#define safe_free(ptr)                                                                                                 \
    do {                                                                                                               \
        if (ptr) {                                                                                                     \
            free(ptr);                                                                                                 \
            (ptr) = NULL;                                                                                              \
        }                                                                                                              \
    } while (0)

typedef enum {
    MSG_SUCCESS,
    MSG_FAILURE,
} msg_return_t;

extern char **environ;
typedef struct {
    pid_t pid;
    int master;
    bool valid;
} pending_pty_t;

extern bool g_stdout;
extern bool g_syslog;
extern FILE *g_file;
extern pending_pty_t g_pending_pty;

bool internal_spawn(bool background, char **argv, char **envp, pid_t *pid, int *master_fd);

msg_return_t proto_msg_send(int sockfd, const ProtobufCMessage *msg);
msg_return_t proto_msg_recv(int sockfd, ProtobufCMessage **msg, const ProtobufCMessageDescriptor *descriptor);
msg_return_t rpc_send_handshake(int sockfd);
msg_return_t rpc_send_error(int sockfd, char *message);
msg_return_t rpc_msg_recv(int sockfd, Rpc__RpcMessage **msg);

void print_backtrace();

void trace(const char *prefix, const char *fmt, ...);

bool writeall(int fd, const char *buf, size_t len);

bool copy_arr_with_null(char ***dest, char **src, size_t n_src);

#endif// __COMMON_H_