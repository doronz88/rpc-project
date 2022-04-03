#include <stdarg.h>
#include <stdlib.h>
#include <stdio.h>
#include <stdbool.h>
#include <unistd.h>
#include <syslog.h>
#include <fcntl.h>
#include <execinfo.h>
#include <netinet/in.h>
#include <sys/socket.h>
#include <arpa/inet.h>

#include "common.h"

bool g_stdout = false;
bool g_syslog = false;
FILE *g_file = NULL;

#define BT_BUF_SIZE (100)
#define MAX_CONNECT_RETRY_ATTEMPTS (5)
#define CONNECT_RETRY_SLEEP (5)

void print_backtrace()
{
    int nptrs;
    void *buffer[BT_BUF_SIZE];
    char **strings;

    nptrs = backtrace(buffer, BT_BUF_SIZE);
    trace("BACKTRACE", "backtrace() returned %d addresses", nptrs);

    /* The call backtrace_symbols_fd(buffer, nptrs, STDOUT_FILENO)
        would produce similar output to the following: */

    strings = backtrace_symbols(buffer, nptrs);
    if (strings == NULL)
    {
        perror("backtrace_symbols");
        return;
    }

    for (int j = 0; j < nptrs; j++)
    {
        trace("BACKTRACE:\t", "%s", strings[j]);
    }

    free(strings);
}

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
        fflush(stdout);
    }
    if (g_syslog)
    {
        syslog(LOG_DEBUG, "%s", prefixed_line);
    }
    if (g_file)
    {
        fprintf(g_file, "%s\n", prefixed_line);
        fflush(g_file);
    }
}

bool recvall_ext(int sockfd, char *buf, size_t len, bool *disconnected)
{
    size_t total_bytes = 0;
    size_t bytes = 0;
    *disconnected = false;

    while (len > 0)
    {
        bytes = recv(sockfd, buf + total_bytes, len, 0);
        if (0 == bytes)
        {
            TRACE("client fd: %d disconnected", sockfd);
            *disconnected = true;
            return false;
        }
        CHECK(bytes > 0);

        total_bytes += bytes;
        len -= bytes;
    }

    return true;

error:
    return false;
}

bool recvall(int sockfd, char *buf, size_t len)
{
    bool disconnected;
    return recvall_ext(sockfd, buf, len, &disconnected);
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

int connect_with_retry(int fd, const struct sockaddr *servaddr, int address_size)
{
    int saved_errno;
    for (int attempts = 0; attempts < MAX_CONNECT_RETRY_ATTEMPTS; ++attempts)
    {
        int res = connect(fd, servaddr, address_size);
        if (0 == res)
        {
            return 0;
        }

        if (EADDRNOTAVAIL != errno)
        {
            return -1;
        }

        if (MAX_CONNECT_RETRY_ATTEMPTS != (attempts + 1))
        {
            TRACE("No available sockets, Waiting %d seconds for OS to clear closed fds. Attempt: %d", CONNECT_RETRY_SLEEP, attempts + 1);
            sleep(CONNECT_RETRY_SLEEP);
        }
    }

    return -1;
}

int tcp_connect(sa_family_t family, const char *ipstr, int port)
{
    int sockfd = -1;
    int result = -1;

    sockfd = socket(family, SOCK_STREAM, 0);
    CHECK(sockfd != -1);

    switch (family)
    {
    case AF_INET:
    {
        struct sockaddr_in servaddr;
        servaddr.sin_family = family;
        servaddr.sin_addr.s_addr = inet_addr(ipstr);
        servaddr.sin_port = htons(port);
        CHECK(0 == connect_with_retry(sockfd, (const struct sockaddr *)&servaddr, sizeof(servaddr)));
        break;
    }
    case AF_INET6:
    {
        struct sockaddr_in6 servaddr;
        servaddr.sin6_family = family;
        CHECK(inet_pton(family, ipstr, &servaddr.sin6_addr) == 1);
        servaddr.sin6_port = htons(port);
        CHECK(0 == connect_with_retry(sockfd, (const struct sockaddr *)&servaddr, sizeof(servaddr)));
        break;
    }
    }

    CHECK(-1 != fcntl(sockfd, F_SETFD, FD_CLOEXEC));
    result = sockfd;

error:
    if (-1 == result)
    {
        if (sockfd != -1)
        {
            close(sockfd);
        }
    }

    return result;
}