#include <arpa/inet.h>
#include <errno.h>
#include <fcntl.h>
#include <netdb.h>
#include <netinet/in.h>
#include <util.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/select.h>
#include <sys/socket.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <termios.h>
#include <unistd.h>
#include <pthread.h>
#include <stdarg.h>
#include <spawn.h>
#include <sys/ioctl.h>

#include "common.h"

#define DEFAULT_PORT ("5910")
#define DEFAULT_SHELL ("/bin/sh")
#define USAGE ("Usage: %s [-p port] [-s shell]")

#define MAX_OPTION_LEN (256)
#define BUFFERSIZE (64 * 1024)

extern char **environ;

static char g_shell_path[MAX_OPTION_LEN] = DEFAULT_SHELL;

void sigchld_handler(int s)
{
    (void)s;
    while (waitpid(-1, NULL, WNOHANG) > 0)
        ;
    TRACE("Connection closed.");
}

void *get_in_addr(struct sockaddr *sa) // get sockaddr, IPv4 or IPv6:
{
    return sa->sa_family == AF_INET ? (void *)&(((struct sockaddr_in *)sa)->sin_addr) : (void *)&(((struct sockaddr_in6 *)sa)->sin6_addr);
}

int internal_spawn(char *const *argv, pid_t *pid)
{
    int master_fd = -1;
    int slave_fd = -1;
    int res = 0;

    // We need a new pseudoterminal to avoid bufferring problems. The 'atos' tool
    // in particular detects when it's talking to a pipe and forgets to flush the
    // output stream after sending a response.
    master_fd = posix_openpt(O_RDWR);
    CHECK(-1 != master_fd);
    CHECK(0 == grantpt(master_fd));
    CHECK(0 == unlockpt(master_fd));

    // Use TIOCPTYGNAME instead of ptsname() to avoid threading problems.
    char slave_pty_name[128];
    CHECK(-1 != ioctl(master_fd, TIOCPTYGNAME, slave_pty_name));

    TRACE("slave_pty_name: %s", slave_pty_name);

    slave_fd = open(slave_pty_name, O_RDWR);
    CHECK(-1 != slave_fd);

    posix_spawn_file_actions_t actions;
    CHECK(0 == posix_spawn_file_actions_init(&actions));
    CHECK(0 == posix_spawn_file_actions_adddup2(&actions, slave_fd, STDIN_FILENO));
    CHECK(0 == posix_spawn_file_actions_adddup2(&actions, slave_fd, STDOUT_FILENO));
    CHECK(0 == posix_spawn_file_actions_adddup2(&actions, slave_fd, STDERR_FILENO));
    CHECK(0 == posix_spawn_file_actions_addclose(&actions, slave_fd));
    CHECK(0 == posix_spawn_file_actions_addclose(&actions, master_fd));
    CHECK(0 == posix_spawnp(pid, argv[0], &actions, NULL, argv, environ));

    close(slave_fd);
    slave_fd = -1;

    return master_fd;

error:
    if (master_fd != -1)
    {
        close(master_fd);
    }
    if (slave_fd != -1)
    {
        close(slave_fd);
    }
    return -1;
}

void handle_client(int sockfd)
{
    TRACE("enter. fd: %d", sockfd);

    pid_t pid;
    int master;
    const char *argv[] = {g_shell_path, NULL};
    master = internal_spawn((char *const *)argv, &pid);
    CHECK(master >= 0);

    fd_set readfds;
    char buf[BUFFERSIZE];
    int maxfd = master > sockfd ? master : sockfd;
    int nbytes = 0;

    while (true)
    {
        FD_ZERO(&readfds);
        FD_SET(master, &readfds);
        FD_SET(sockfd, &readfds);

        CHECK(select(maxfd + 1, &readfds, NULL, NULL, NULL) != -1);

        if (FD_ISSET(master, &readfds))
        {
            nbytes = read(master, buf, BUFFERSIZE);
            CHECK(nbytes >= 1);
            CHECK(sendall(sockfd, buf, nbytes));
        }

        if (FD_ISSET(sockfd, &readfds))
        {
            nbytes = recv(sockfd, buf, BUFFERSIZE, 0);
            CHECK(nbytes >= 1);
            CHECK(writeall(master, buf, nbytes));
        }
    }

error:
    close(sockfd);
}

int main(int argc, const char *argv[])
{
    int opt;
    char port[MAX_OPTION_LEN] = DEFAULT_PORT;

    while ((opt = getopt(argc, (char *const *)argv, "p:s:")) != -1)
    {
        switch (opt)
        {
        case 'p':
        {
            strncpy(port, optarg, sizeof(port) - 1);
            break;
        }
        case 's':
        {
            strncpy(g_shell_path, optarg, sizeof(g_shell_path) - 1);
            break;
        }
        default: /* '?' */
        {
            TRACE(USAGE, argv[0]);
            exit(EXIT_FAILURE);
        }
        }
    }

    int err = 0;
    int server_fd = -1;
    struct addrinfo hints;
    memset(&hints, 0, sizeof(hints));
    hints.ai_socktype = SOCK_STREAM;
    hints.ai_flags = AI_PASSIVE; // use my IP. "| AI_ADDRCONFIG"
    hints.ai_family = AF_UNSPEC; // AF_INET or AF_INET6 to force version
    hints.ai_family = AF_INET6;  // IPv4 addresses will be like ::ffff:127.0.0.1

    struct addrinfo *servinfo;
    CHECK(0 == getaddrinfo(NULL, port, &hints, &servinfo));

    struct addrinfo *servinfo2 = servinfo; // servinfo->ai_next;
    char ipstr[INET6_ADDRSTRLEN];
    inet_ntop(servinfo2->ai_family, get_in_addr(servinfo2->ai_addr), ipstr, sizeof(ipstr));
    TRACE("Waiting for connections on [%s]:%s", ipstr, port);

    server_fd = socket(servinfo2->ai_family, servinfo2->ai_socktype, servinfo2->ai_protocol);
    CHECK(server_fd >= 0);

    int yes_1 = 1;
    CHECK(0 == setsockopt(server_fd, SOL_SOCKET, SO_REUSEADDR, &yes_1, sizeof(yes_1)));
    CHECK(0 == bind(server_fd, servinfo2->ai_addr, servinfo2->ai_addrlen));

    freeaddrinfo(servinfo); // all done with this structure

    CHECK(0 == listen(server_fd, 10));

    struct sigaction sa;
    sa.sa_handler = sigchld_handler; // reap all dead processes
    sigemptyset(&sa.sa_mask);
    sa.sa_flags = SA_RESTART;
    CHECK(0 == sigaction(SIGCHLD, &sa, NULL));

    while (1)
    {
        struct sockaddr_storage their_addr; // connector's address information
        socklen_t addr_size = sizeof(their_addr);
        int client_fd = accept(server_fd, (struct sockaddr *)&their_addr, &addr_size);

        char ipstr[INET6_ADDRSTRLEN];
        inet_ntop(their_addr.ss_family, get_in_addr((struct sockaddr *)&their_addr), ipstr, sizeof(ipstr));
        TRACE("Got a connection from %s [%d]", ipstr, client_fd);

        pthread_t thread;
        CHECK(0 == pthread_create(&thread, NULL, (void *_Nullable (*_Nonnull)(void *_Nullable))handle_client, (void *)(long)client_fd));
    }

error:
    err = 1;

clean:
    if (-1 != server_fd)
    {
        close(server_fd);
    }

    return err;
}
