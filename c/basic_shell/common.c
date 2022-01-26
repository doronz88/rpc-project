#include <stdarg.h>
#include <stdlib.h>
#include <stdio.h>
#include <stdbool.h>
#include <unistd.h>
#include <string.h>
#include <sys/socket.h>

#include "common.h"

void trace(const char *prefix, const char *fmt, ...)
{
    char line[1024];
    char prefixed_line[1024];

    va_list args;
    va_start(args, fmt);
    vsprintf(line, fmt, args);
    va_end(args);

    sprintf(prefixed_line, "%s: %s", prefix, line);
    puts(prefixed_line);
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
    TRACE("error");
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
    TRACE("error");
    return false;
}

// You must free the result if result is non-NULL.
char *str_replace(char *orig, char *rep, char *with)
{
    char *result;  // the return string
    char *ins;     // the next insert point
    char *tmp;     // varies
    int len_rep;   // length of rep (the string to remove)
    int len_with;  // length of with (the string to replace rep with)
    int len_front; // distance between rep and end of last rep
    int count;     // number of replacements

    // sanity checks and initialization
    if (!orig || !rep)
        return NULL;
    len_rep = strlen(rep);
    if (len_rep == 0)
        return NULL; // empty rep causes infinite loop during count
    if (!with)
        with = "";
    len_with = strlen(with);

    // count the number of replacements needed
    ins = orig;
    for (count = 0; (tmp = strstr(ins, rep)); ++count)
    {
        ins = tmp + len_rep;
    }

    tmp = result = malloc(strlen(orig) + (len_with - len_rep) * count + 1);

    if (!result)
        return NULL;

    // first time through the loop, all the variable are set correctly
    // from here on,
    //    tmp points to the end of the result string
    //    ins points to the next occurrence of rep in orig
    //    orig points to the remainder of orig after "end of rep"
    while (count--)
    {
        ins = strstr(orig, rep);
        len_front = ins - orig;
        tmp = strncpy(tmp, orig, len_front) + len_front;
        tmp = strcpy(tmp, with) + len_with;
        orig += len_front + len_rep; // move to next "end of rep"
    }
    strcpy(tmp, orig);
    return result;
}
