#ifndef __COMMON_H_
#define __COMMON_H_

#include <stdio.h>
#include <stdarg.h>
#include <stdlib.h>
#include <stdbool.h>
#include <errno.h>
#include <string.h>
#include "protos/rpc.pb-c.h"

typedef unsigned char u8;
typedef unsigned short u16;
typedef unsigned int u32;
typedef signed int s32;
typedef unsigned long u64;
typedef unsigned long s64;

extern bool g_stdout;
extern bool g_syslog;
extern FILE *g_file;

#define RPC_SUCCESS (1)
#define RPC_FAILURE (0)
#define MAX_STACK_ARGS (16)
#define MAX_REGS_ARGS (8)


typedef struct {
    uint64_t x[MAX_REGS_ARGS];
    double d[MAX_REGS_ARGS];
    uint64_t stack[MAX_STACK_ARGS];
} arm_args_t;



// Macro to initialize response error with function name and error number
#define RESPONSE_ERROR(response) \
    Rpc__ResponseError error = RPC__RESPONSE_ERROR__INIT; \
    response.type_case = RPC__RESPONSE__TYPE_ERROR; \
    error.func_name = (char*) __func__; \
    response.error = &error

#define COPY_ARR_WITH_NULL(src, dest, n_src) \
    do { \
        if (n_src > 0) { \
            dest = (char **) malloc(sizeof(char *) * (n_src + 1)); \
            CHECK(dest != NULL); \
            for(uint64_t i=0;i< n_src;i++){   \
                dest[i] = src[i];            \
            } \
            dest[n_src] = NULL; \
        } \
    } while (0)


#define SAFE_FREE(ptr) do { \
    if (ptr) { \
        free(ptr); \
        ptr = NULL; \
    } \
} while(0)


#define TRACE(...) trace(__PRETTY_FUNCTION__, __VA_ARGS__)
#define CHECK(expression)            \
    if (!(expression))               \
    {                                \
        if (errno)                   \
        {                            \
            trace(__PRETTY_FUNCTION__, "ERROR on expression: %s: errno: %d (%s)", #expression, errno, strerror(errno)); \
        }                            \
        print_backtrace();           \
        goto error;                  \
    }

void print_backtrace();
void trace(const char *prefix, const char *fmt, ...);
bool recvall_ext(int sockfd, char *buf, size_t len, bool *disconnected);
bool recvall(int sockfd, char *buf, size_t len);
bool writeall(int fd, const char *buf, size_t len);
bool message_send(int sockfd, const uint8_t *buf, size_t len);
bool send_response(int sockfd, const Rpc__Response *response);
bool message_receive(int sockfd, char *buf, size_t *size);

#endif // __COMMON_H_