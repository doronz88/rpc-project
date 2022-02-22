#ifndef __COMMON_H_
#define __COMMON_H_

#include <stdio.h>
#include <stdarg.h>
#include <stdlib.h>
#include <stdbool.h>
#include <errno.h>
#include <string.h>

typedef unsigned char u8;
typedef unsigned short u16;
typedef unsigned int u32;
typedef signed int s32;
typedef unsigned long u64;
typedef unsigned long s64;

bool g_stdout;
bool g_syslog;
FILE *g_file;

#define TRACE(...) trace(__PRETTY_FUNCTION__, __VA_ARGS__)
#define CHECK(expression)            \
    if (!(expression))               \
    {                                \
        if (errno)                   \
        {                            \
            trace(__PRETTY_FUNCTION__, "ERROR: errno: %d (%s)", errno, strerror(errno)); \
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

#endif // __COMMON_H_