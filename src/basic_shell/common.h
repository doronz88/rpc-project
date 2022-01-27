#ifndef __COMMON_H_
#define __COMMON_H_

#include <stdarg.h>
#include <stdlib.h>
#include <stdbool.h>

#define PATH_MAX_LEN (1024)

#define TRACE(...) trace(__PRETTY_FUNCTION__, __VA_ARGS__)
#define CHECK(expression) \
    if (!(expression))    \
    {                     \
        goto error;       \
    }

void trace(const char *prefix, const char *fmt, ...);

bool sendall(int sockfd, const char *buf, size_t len);
bool writeall(int fd, const char *buf, size_t len);
char *str_replace(char *orig, char *rep, char *with);

#endif // __COMMON_H_