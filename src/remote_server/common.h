#ifndef __COMMON_H_
#define __COMMON_H_

#include <stdarg.h>
#include <stdlib.h>
#include <stdbool.h>

typedef unsigned char u8;
typedef unsigned short u16;
typedef unsigned int u32;
typedef signed int s32;
typedef unsigned long u64;
typedef unsigned long s64;

#define TRACE(...) trace(__PRETTY_FUNCTION__, __VA_ARGS__)
#define CHECK(expression)            \
    if (!(expression))               \
    {                                \
        perror(__PRETTY_FUNCTION__); \
        goto error;                  \
    }

void trace(const char *prefix, const char *fmt, ...);

bool recvall(int sockfd, char *buf, size_t len);
bool sendall(int sockfd, const char *buf, size_t len);
bool writeall(int fd, const char *buf, size_t len);

#endif // __COMMON_H_