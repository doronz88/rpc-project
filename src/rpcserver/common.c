#include <stdarg.h>
#include <stdlib.h>
#include <stdio.h>
#include <stdbool.h>
#include <unistd.h>
#include <syslog.h>
#include <sys/socket.h>

#include "common.h"

bool g_stdout = false;
bool g_syslog = false;

void trace(const char *prefix, const char *fmt, ...)
{
    if (!g_stdout && !g_syslog)
    {
        return;
    }

    char line[1022];
    char prefixed_line[1024];

    va_list args;
    va_start(args, fmt);
    vsprintf(line, fmt, args);
    va_end(args);

    sprintf(prefixed_line, "%s: %s", prefix, line);

    if (g_stdout)
    {
        puts(prefixed_line);
    }
    if (g_syslog)
    {
        syslog(LOG_DEBUG, "%s", prefixed_line);
    }
}

bool recvall(int sockfd, char *buf, size_t len)
{
    size_t total_bytes = 0;
    size_t bytes = 0;

    while (len > 0)
    {
        bytes = recv(sockfd, buf + total_bytes, len, 0);
        CHECK(bytes > 0);

        total_bytes += bytes;
        len -= bytes;
    }

    return true;

error:
    if (0 == bytes)
    {
        TRACE("client fd: %d disconnected", sockfd);
    }

    return false;
}

bool sendall(int sockfd, const char *buf, size_t len)
{
    size_t total_bytes = 0;
    size_t bytes = 0;

    while (len > 0)
    {
        bytes = send(sockfd, buf + total_bytes, len, 0);
        CHECK(bytes != -1);

        total_bytes += bytes;
        len -= bytes;
    }

    return true;

error:
    return false;
}

bool writeall(int fd, const char *buf, size_t len)
{
    size_t total_bytes = 0;
    size_t bytes = 0;

    while (len > 0)
    {
        bytes = write(fd, buf + total_bytes, len);
        CHECK(bytes != -1);

        total_bytes += bytes;
        len -= bytes;
    }

    return true;

error:
    return false;
}