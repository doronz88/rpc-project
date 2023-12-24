#ifndef __COMMON_H_
#define __COMMON_H_

#include "protos/rpc.pb-c.h"
#include <errno.h>
#include <stdarg.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef unsigned char u8;
typedef unsigned int u32;
typedef signed int s32;
typedef unsigned long u64;
typedef unsigned long s64;

extern bool g_stdout;
extern bool g_syslog;
extern FILE *g_file;

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

#define TRACE(...) trace(__PRETTY_FUNCTION__, __VA_ARGS__)
#define CHECK(expression)                                                                                               \
    if (!(expression)) {                                                                                                \
        if (errno) {                                                                                                    \
            trace(__PRETTY_FUNCTION__, "ERROR on expression: %s: errno: %d (%s)", #expression, errno, strerror(errno)); \
        }                                                                                                               \
        print_backtrace();                                                                                              \
        goto error;                                                                                                     \
    }

void print_backtrace();

void trace(const char *prefix, const char *fmt, ...);

bool recvall(int sockfd, char *buf, size_t len);

bool writeall(int fd, const char *buf, size_t len);

bool send_message(int sockfd, const uint8_t *buf, size_t len);

bool send_response(int sockfd, ProtobufCMessage *resp);

bool receive_message(int sockfd, char **buf, size_t *size);

void safe_free(void **ptr);

bool copy_arr_with_null(char ***dest, char **src, size_t n_src);

#endif// __COMMON_H_