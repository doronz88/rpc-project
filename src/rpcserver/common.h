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
// Define macros for general-purpose registers
#define X0_REG x0
#define X1_REG x1
#define X2_REG x2
#define X3_REG x3
#define X4_REG x4
#define X5_REG x5
#define X6_REG x6
#define X7_REG x7

// Define macros for floating-point registers
#define D0_REG d0
#define D1_REG d1
#define D2_REG d2
#define D3_REG d3
#define D4_REG d4
#define D5_REG d5
#define D6_REG d6
#define D7_REG d7
//#define SET_REGISTER_GP(reg, value) __asm__ volatile("mov " #reg ", %0" : : "r"(value))
#define CALL_FUNCTION(address) __asm__ volatile("blr %0" : : "r"((intptr_t)(address)))

#define SET_REGISTER_GP(register_number, value) \
    do { \
        switch (register_number) { \
            case 0: __asm__ volatile("mov x0, %0" : : "r"((uint64_t)(value))); break; \
            case 1: __asm__ volatile("mov x1, %0" : : "r"((uint64_t)(value))); break; \
            case 2: __asm__ volatile("mov x2, %0" : : "r"((uint64_t)(value))); break; \
            case 3: __asm__ volatile("mov x3, %0" : : "r"((uint64_t)(value))); break; \
            case 4: __asm__ volatile("mov x4, %0" : : "r"((uint64_t)(value))); break; \
            case 5: __asm__ volatile("mov x5, %0" : : "r"((uint64_t)(value))); break; \
            case 6: __asm__ volatile("mov x6, %0" : : "r"((uint64_t)(value))); break; \
            case 7: __asm__ volatile("mov x7, %0" : : "r"((uint64_t)(value))); break; \
            default: \
                /* Handle an error or provide a default case */ \
                break; \
        } \
    } while(0)

#define SET_REGISTER_FP(register_number, value) \
    do { \
        switch (register_number) { \
            case 0: __asm__ volatile("fmov d0, %0" : : "r"((double)(value))); break; \
            case 1: __asm__ volatile("fmov d1, %0" : : "r"((double)(value))); break; \
            case 2: __asm__ volatile("fmov d2, %0" : : "r"((double)(value))); break; \
            case 3: __asm__ volatile("fmov d3, %0" : : "r"((double)(value))); break; \
            case 4: __asm__ volatile("fmov d4, %0" : : "r"((double)(value))); break; \
            case 5: __asm__ volatile("fmov d5, %0" : : "r"((double)(value))); break; \
            case 6: __asm__ volatile("fmov d6, %0" : : "r"((double)(value))); break; \
            case 7: __asm__ volatile("fmov d7, %0" : : "r"((double)(value))); break; \
            default: \
                /* Handle an error or provide a default case */ \
                break; \
        } \
    } while(0)

#define GET_REGISTER_GP(register_number, result) \
    do { \
        switch (register_number) { \
            case 0: __asm__ volatile("mov %0, x0" : "=r"(result)); break; \
            case 1: __asm__ volatile("mov %0, x1" : "=r"(result)); break; \
            case 2: __asm__ volatile("mov %0, x2" : "=r"(result)); break; \
            case 3: __asm__ volatile("mov %0, x3" : "=r"(result)); break; \
            case 4: __asm__ volatile("mov %0, x4" : "=r"(result)); break; \
            case 5: __asm__ volatile("mov %0, x5" : "=r"(result)); break; \
            case 6: __asm__ volatile("mov %0, x6" : "=r"(result)); break; \
            case 7: __asm__ volatile("mov %0, x7" : "=r"(result)); break; \
            default: \
                /* Handle an error or provide a default case */ \
                break; \
        } \
    } while(0)
#define GET_REGISTER_FP(register_number, result) \
    do { \
        switch (register_number) { \
            case 0: __asm__ volatile("fmov %0, d0" : "=r"(result)); break; \
            case 1: __asm__ volatile("fmov %0, d1" : "=r"(result)); break; \
            case 2: __asm__ volatile("fmov %0, d2" : "=r"(result)); break; \
            case 3: __asm__ volatile("fmov %0, d3" : "=r"(result)); break; \
            case 4: __asm__ volatile("fmov %0, d4" : "=r"(result)); break; \
            case 5: __asm__ volatile("fmov %0, d5" : "=r"(result)); break; \
            case 6: __asm__ volatile("fmov %0, d6" : "=r"(result)); break; \
            case 7: __asm__ volatile("fmov %0, d7" : "=r"(result)); break; \
            default: \
                /* Handle an error or provide a default case */ \
                break; \
        } \
    } while(0)

// Macro to initialize response error with function name and error number
#define RESPONSE_ERROR(response) \
    Rpc__ResponseError error = RPC__RESPONSE_ERROR__INIT; \
    response.type_case = RPC__RESPONSE__TYPE_ERROR; \
    error.func_name = (char*) __func__; \
        error.error_num = errno; \
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

bool sendall(int sockfd, const char *buf, size_t len);

bool writeall(int fd, const char *buf, size_t len);

bool message_send(int sockfd, const uint8_t *buf, size_t len);

bool send_response(int sockfd, const Rpc__Response *response);

bool message_receive(int sockfd, char *buf, size_t *size);


#endif // __COMMON_H_