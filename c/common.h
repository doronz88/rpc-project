#ifndef __COMMON_H_
#define __COMMON_H_

#include <stdarg.h>
#include <stdlib.h>
#include <stdbool.h>

#define TRACE(...) trace(__PRETTY_FUNCTION__, __VA_ARGS__)
#define CHECK(expression) if (!(expression)) { goto error; }

void trace(const char *prefix, const char *fmt, ...);

bool sendall(int sockfd, const char *buf, size_t len);



#endif // __COMMON_H_