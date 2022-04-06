#ifndef __APPLE__
#define _XOPEN_SOURCE (600)
#define _GNU_SOURCE (1)
#endif // __APPLE__
#include <stdlib.h>
#include <arpa/inet.h>
#include <errno.h>
#include <fcntl.h>
#include <netdb.h>
#include <netinet/in.h>
#include <signal.h>
#include <stdio.h>
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
#include <dlfcn.h>
#include <sys/stat.h>
#include <sys/ioctl.h>
#include <sys/utsname.h>

#ifdef __APPLE__
#include <CoreFoundation/CoreFoundation.h>
#include <mach/mach.h>
#endif // __APPLE__

#include "common.h"

#define HANDSHAKE_SYSNAME_LEN (256)
#define DEFAULT_PORT ("5910")
#define DEFAULT_SHELL ("/bin/sh")
#define USAGE ("Usage: %s [-p port] [-o (stdout|syslog|file:filename)] \n\
-h  show this help message \n\
-o  output. can be all of the following: stdout, syslog and file:filename. can be passed multiple times \n\
\n\
Example usage: \n\
%s -p 5910 -o syslog -o stdout -o file:/tmp/log.txt\n")
#define SERVER_MAGIC_VERSION (0x88888801)
#define MAGIC (0x12345678)
#define MAX_CONNECTIONS (1024)

#define MAX_PATH_LEN (1024)
#define MAX_OPTION_LEN (256)
#define BUFFERSIZE (64 * 1024)
#define INVALID_PID (0xffffffff)
#define WORKER_CLIENT_SOCKET_FD (3)

extern char **environ;

typedef enum
{
    CMD_EXEC = 0,
    CMD_DLOPEN = 1,
    CMD_DLCLOSE = 2,
    CMD_DLSYM = 3,
    CMD_CALL = 4,
    CMD_PEEK = 5,
    CMD_POKE = 6,
    CMD_REPLY_ERROR = 7,
    CMD_REPLY_PEEK = 8,
    CMD_GET_DUMMY_BLOCK = 9,
    CMD_CLOSE = 10,
    CMD_REPLY_POKE = 11,
} cmd_type_t;

typedef enum
{
    CMD_EXEC_CHUNK_TYPE_STDOUT = 0,
    CMD_EXEC_CHUNK_TYPE_EXITCODE = 1,
} cmd_exec_chunk_type_t;

typedef enum
{
    ARCH_UNKNOWN = 0,
    ARCH_ARM64 = 1,
} arch_t;

typedef struct
{
    u32 magic;
    u32 arch; // arch_t
    char sysname[HANDSHAKE_SYSNAME_LEN];
} protocol_handshake_t;

typedef struct
{
    u32 type;
    u32 size;
} cmd_exec_chunk_t;

typedef struct
{
    char filename[MAX_PATH_LEN];
    u32 mode;
} cmd_dlopen_t;

typedef struct
{
    u64 lib;
} cmd_dlclose_t;

typedef struct
{
    u64 lib;
    char symbol_name[MAX_PATH_LEN];
} cmd_dlsym_t;

typedef struct
{
    u64 type;
    u64 value;
} argument_t;

typedef struct
{
    u64 address;
    u64 argc;
    argument_t argv[0];
} cmd_call_t;

typedef struct
{
    u64 address;
    u64 size;
} cmd_peek_t;

typedef struct
{
    u64 address;
    u64 size;
    u8 data[0];
} cmd_poke_t;

typedef struct
{
    u32 magic;
    u32 cmd_type;
} protocol_message_t;

typedef struct
{
    u64 x[8];
    u64 d[8];
} return_registers_arm_t;

typedef struct
{
    union
    {
        return_registers_arm_t arm_registers;
        u64 return_value;
    } return_values;
} call_response_t;

void *get_in_addr(struct sockaddr *sa) // get sockaddr, IPv4 or IPv6:
{
    return sa->sa_family == AF_INET ? (void *)&(((struct sockaddr_in *)sa)->sin_addr) : (void *)&(((struct sockaddr_in6 *)sa)->sin6_addr);
}

bool internal_spawn(bool background, char *const *argv, char *const *envp, pid_t *pid, int *master_fd)
{
    bool success = false;
    int slave_fd = -1;
    *master_fd = -1;
    *pid = INVALID_PID;

    // call setsid() on child so Ctrl-C and all other control characters are set in a different terminal
    // and process group
    posix_spawnattr_t attr;
    CHECK(0 == posix_spawnattr_init(&attr));
    CHECK(0 == posix_spawnattr_setflags(&attr, POSIX_SPAWN_SETSID));

    posix_spawn_file_actions_t actions;
    CHECK(0 == posix_spawn_file_actions_init(&actions));

    if (!background)
    {
        // We need a new pseudoterminal to avoid bufferring problems. The 'atos' tool
        // in particular detects when it's talking to a pipe and forgets to flush the
        // output stream after sending a response.
        *master_fd = posix_openpt(O_RDWR);
        CHECK(-1 != *master_fd);
        CHECK(0 == grantpt(*master_fd));
        CHECK(0 == unlockpt(*master_fd));

        char slave_pty_name[128];
        CHECK(0 == ptsname_r(*master_fd, slave_pty_name, sizeof(slave_pty_name)));

        TRACE("slave_pty_name: %s", slave_pty_name);

        slave_fd = open(slave_pty_name, O_RDWR);
        CHECK(-1 != slave_fd);

        CHECK(0 == posix_spawn_file_actions_adddup2(&actions, slave_fd, STDIN_FILENO));
        CHECK(0 == posix_spawn_file_actions_adddup2(&actions, slave_fd, STDOUT_FILENO));
        CHECK(0 == posix_spawn_file_actions_adddup2(&actions, slave_fd, STDERR_FILENO));
        CHECK(0 == posix_spawn_file_actions_addclose(&actions, slave_fd));
        CHECK(0 == posix_spawn_file_actions_addclose(&actions, *master_fd));
    }
    else
    {
        CHECK(0 == posix_spawn_file_actions_addopen(&actions, STDIN_FILENO, "/dev/null", O_RDONLY, 0));
        CHECK(0 == posix_spawn_file_actions_addopen(&actions, STDOUT_FILENO, "/dev/null", O_WRONLY, 0));
        CHECK(0 == posix_spawn_file_actions_addopen(&actions, STDERR_FILENO, "/dev/null", O_WRONLY, 0));
    }

    CHECK(0 == posix_spawnp(pid, argv[0], &actions, &attr, argv, envp));
    CHECK(*pid != INVALID_PID);

    posix_spawnattr_destroy(&attr);
    posix_spawn_file_actions_destroy(&actions);

    success = true;

error:
    if (slave_fd != -1)
    {
        close(slave_fd);
    }
    if (!success)
    {
        if (*master_fd != -1)
        {
            close(*master_fd);
        }
        *pid = INVALID_PID;
    }
    return success;
}

bool spawn_worker_server(int client_socket, const char *argv[], int argc)
{
    bool success = false;

    // append -w to original argv
    int new_argc = argc + 1;
    const char **new_argv = malloc((new_argc+1)*sizeof(char*));
    for(int i=0; i < argc; ++i) {
        new_argv[i] = argv[i];
    }
    new_argv[new_argc-1] = "-w";
    new_argv[new_argc] = NULL;
    
    pid_t pid;
    posix_spawn_file_actions_t actions;
    CHECK(0 == posix_spawn_file_actions_init(&actions));
    CHECK(0 == posix_spawn_file_actions_adddup2(&actions, STDIN_FILENO, STDIN_FILENO));
    CHECK(0 == posix_spawn_file_actions_adddup2(&actions, STDOUT_FILENO, STDOUT_FILENO));
    CHECK(0 == posix_spawn_file_actions_adddup2(&actions, STDERR_FILENO, STDERR_FILENO));
    CHECK(0 == posix_spawn_file_actions_adddup2(&actions, client_socket, WORKER_CLIENT_SOCKET_FD));

    CHECK(0 == posix_spawnp(&pid, new_argv[0], &actions, NULL, (char *const *)new_argv, environ));
    CHECK(pid != INVALID_PID);

    TRACE("Spawned Worker Process: %d", pid);
    success = true;

error:
    posix_spawn_file_actions_destroy(&actions);
    free(new_argv);
    close(client_socket);
    return success;
}

bool send_reply(int sockfd, cmd_type_t type)
{
    protocol_message_t protocol_message = {.magic = MAGIC, .cmd_type = type};
    CHECK(sendall(sockfd, (char *)&protocol_message, sizeof(protocol_message)));
    return true;
error:
    return false;
}

typedef struct
{
    int sockfd;
    pid_t pid;
} thread_notify_client_spawn_error_t;

void thread_waitpid(pid_t pid)
{
    TRACE("enter");
    s32 err;
    waitpid(pid, &err, 0);
}

bool handle_exec(int sockfd)
{
    u8 byte;
    pthread_t thread = 0;
    thread_notify_client_spawn_error_t *thread_params = NULL;
    pid_t pid = INVALID_PID;
    int master = -1;
    int success = false;
    char **argv = NULL;
    char **envp = NULL;
    u32 argc;
    u32 envc;
    u8 background;

    CHECK(recvall(sockfd, (char *)&background, sizeof(background)));

    CHECK(recvall(sockfd, (char *)&argc, sizeof(argc)));
    CHECK(argc > 0);

    // +1 for additional NULL at end of list
    size_t argv_size = (argc + 1) * sizeof(char *);
    argv = (char **)malloc(argv_size * sizeof(char *));
    memset(argv, 0, argv_size * sizeof(char *));

    for (u32 i = 0; i < argc; ++i)
    {
        u32 len;
        CHECK(recvall(sockfd, (char *)&len, sizeof(len)));

        // +1 for additional \0 at end of each string
        size_t str_size = (len + 1) * sizeof(char);
        argv[i] = malloc(str_size * sizeof(char));
        CHECK(argv[i] != NULL);

        CHECK(recvall(sockfd, argv[i], len * sizeof(char)));
        argv[i][len] = '\0';
    }

    CHECK(recvall(sockfd, (char *)&envc, sizeof(envc)));

    // +1 for additional NULL at end of list
    size_t envp_size = (envc + 1) * sizeof(char *);
    envp = (char **)malloc(envp_size * sizeof(char *));
    memset(envp, 0, envp_size * sizeof(char *));

    for (u32 i = 0; i < envc; ++i)
    {
        u32 len;
        CHECK(recvall(sockfd, (char *)&len, sizeof(len)));

        // +1 for additional \0 at end of each string
        size_t str_size = (len + 1) * sizeof(char);
        envp[i] = malloc(str_size * sizeof(char));
        CHECK(envp[i] != NULL);

        CHECK(recvall(sockfd, envp[i], len * sizeof(char)));
        envp[i][len] = '\0';
    }

    CHECK(internal_spawn(background, (char *const *)argv, envc ? (char *const *)envp : environ, &pid, &master));
    CHECK(sendall(sockfd, (char *)&pid, sizeof(u32)));

    if (background)
    {
        CHECK(0 == pthread_create(&thread, NULL, (void *(*)(void *))thread_waitpid, (void *)(intptr_t)pid));
    }
    else
    {
        // make sure we have the process fd for its stdout and stderr
        CHECK(master >= 0);

        fd_set readfds;
        char buf[BUFFERSIZE];
        int maxfd = master > sockfd ? master : sockfd;
        int nbytes = 0;

        fd_set errfds;

        while (true)
        {
            FD_ZERO(&readfds);
            FD_SET(master, &readfds);
            FD_SET(sockfd, &readfds);

            CHECK(select(maxfd + 1, &readfds, NULL, &errfds, NULL) != -1);

            if (FD_ISSET(master, &readfds))
            {
                nbytes = read(master, buf, BUFFERSIZE);
                if (nbytes < 1)
                {
                    TRACE("read master failed. break");
                    break;
                }

                TRACE("master->sock");

                cmd_exec_chunk_t chunk;
                chunk.type = CMD_EXEC_CHUNK_TYPE_STDOUT;
                chunk.size = nbytes;

                CHECK(sendall(sockfd, (char *)&chunk, sizeof(chunk)));
                CHECK(sendall(sockfd, buf, chunk.size));
            }

            if (FD_ISSET(sockfd, &readfds))
            {
                nbytes = recv(sockfd, buf, BUFFERSIZE, 0);
                if (nbytes < 1)
                {
                    break;
                }

                TRACE("sock->master");

                CHECK(writeall(master, buf, nbytes));
            }
        }

        TRACE("wait for process to finish");
        s32 error;
        CHECK(pid == waitpid(pid, &error, 0));

        cmd_exec_chunk_t chunk;
        chunk.type = CMD_EXEC_CHUNK_TYPE_EXITCODE;
        chunk.size = sizeof(error);

        CHECK(sendall(sockfd, (const char *)&chunk, sizeof(chunk)));
        CHECK(sendall(sockfd, (const char *)&error, sizeof(error)));
    }

    success = true;

error:
    if (thread_params)
    {
        free(thread_params);
    }

    if (INVALID_PID == pid)
    {
        TRACE("invalid pid");

        // failed to create process somewhere in the prolog, at least notify
        sendall(sockfd, (char *)&pid, sizeof(u32));
    }

    if (argv)
    {
        for (u32 i = 0; i < argc; ++i)
        {
            if (argv[i])
            {
                free(argv[i]);
            }
        }
        free(argv);
    }

    if (envp)
    {
        for (u32 i = 0; i < envc; ++i)
        {
            if (envp[i])
            {
                free(envp[i]);
            }
        }
        free(envp);
    }

    if (-1 != master)
    {
        TRACE("close master: %d", master);
        if (0 != close(master))
        {
            perror("close");
        }
    }

    return success;
}

bool handle_dlopen(int sockfd)
{
    int result = false;
    cmd_dlopen_t cmd;
    CHECK(recvall(sockfd, (char *)&cmd, sizeof(cmd)));

    u64 err = (u64)dlopen(cmd.filename, cmd.mode);
    CHECK(sendall(sockfd, (char *)&err, sizeof(err)));

    result = true;

error:
    return result;
}

bool handle_dlclose(int sockfd)
{
    int result = false;
    cmd_dlclose_t cmd;
    CHECK(recvall(sockfd, (char *)&cmd, sizeof(cmd)));

    u64 err = (u64)dlclose((void *)cmd.lib);
    CHECK(sendall(sockfd, (char *)&err, sizeof(err)));

    result = true;

error:
    return result;
}

bool handle_dlsym(int sockfd)
{
    int result = false;
    cmd_dlsym_t cmd;
    CHECK(recvall(sockfd, (char *)&cmd, sizeof(cmd)));

    u64 ptr = (u64)dlsym((void *)cmd.lib, cmd.symbol_name);
    CHECK(sendall(sockfd, (char *)&ptr, sizeof(ptr)));

    TRACE("%s = %p", cmd.symbol_name, ptr);

    result = true;

error:
    return result;
}

#ifdef __ARM_ARCH_ISA_A64
bool call_function(int sockfd, intptr_t address, size_t argc, argument_t **p_argv);
__asm__(
    "_call_function:\n"
    // the "stack_arguments" must be the first local ([sp, 0]) to serialize stack arguments
    // the 0x100 is enough to store 0x100/8 = 32 stack arguments which should be enough for
    // every function
    ".set stack_arguments, 0\n"
    ".set result, stack_arguments+0x100\n"
    ".set address, result+0x08\n"
    ".set argc, address+0x08\n"
    ".set argv, argc+0x08\n"
    ".set sockfd, argv+0x08\n"

    ".set register_x0, sockfd+0x08\n"
    ".set register_x1, register_x0+0x08\n"
    ".set register_x2, register_x1+0x08\n"
    ".set register_x3, register_x2+0x08\n"
    ".set register_x4, register_x3+0x08\n"
    ".set register_x5, register_x4+0x08\n"
    ".set register_x6, register_x5+0x08\n"
    ".set register_x7, register_x6+0x08\n"

    ".set register_d0, register_x7+0x08\n"
    ".set register_d1, register_d0+0x08\n"
    ".set register_d2, register_d1+0x08\n"
    ".set register_d3, register_d2+0x08\n"
    ".set register_d4, register_d3+0x08\n"
    ".set register_d5, register_d4+0x08\n"
    ".set register_d6, register_d5+0x08\n"
    ".set register_d7, register_d6+0x08\n"

    ".set register_end, register_d7+0x08\n"

    ".set size, register_end+0x08\n"

    // backup registers x19 -> x30 = 8*12 bytes = 0x60 bytes
    // according to arm abi, the stack is structured as follows:
    // -------------------------
    // | x30(lr)               | 0x58
    // | x29(frame pointer)    | 0x50
    // | register backup       | 0x00
    // -------------------------
    "stp x28, x27, [sp, -0x60]!\n"
    "stp x26, x25, [sp, 0x10]\n"
    "stp x23, x24, [sp, 0x20]\n"
    "stp x21, x22, [sp, 0x30]\n"
    "stp x19, x20, [sp, 0x40]\n"
    "stp x29, x30, [sp, 0x50]\n"
    // current x29 should point to previous x29
    "add x29, sp, 0x50\n"

    // allocate stack locals
    "sub sp, sp, size\n"

    // backup arguments to stack
    "str x0, [sp, sockfd]\n"
    "str x1, [sp, address]\n"
    "str x2, [sp, argc]\n"
    "str x3, [sp, argv]\n"

    // result = 0
    "str xzr, [sp, result]\n"

    // x19 = argument = *argv
    // x24 = argc
    // x21 = integer_offset = 0
    // x22 = double_offset = 0
    // x23 = current_arg_index = 0
    // x26 = stack_offset = 0
    "ldr x19, [sp, argv]\n"
    "ldr x19, [x19]\n"
    "ldr x24, [sp, argc]\n"
    "mov x21, 0\n"
    "mov x22, 0\n"
    "mov x23, 0\n"
    "mov x26, 0\n"

    "1:\n"
    // if (current_arg_index == argc) goto 3
    "cmp x23, x24\n"
    "beq 3f\n"

    // x20 = argument.type
    "ldr x20, [x19]\n"

    // argument++
    "add x19, x19, 8\n"

    // if (argument.type == INTEGER) goto 2
    "cmp x20, 0\n"
    "beq 2f\n"

    // else {

    // -- double argument

    // x20 = argument.value
    "ldr x20, [x19]\n"
    "add x19, x19, 8\n"

    // if (double_offset*8 >= MAX_DOUBLE_REG*8) goto 7
    "cmp x22, 8 * 8\n"
    "bge 7f\n"

    // 6[double_offset]()
    "adr x25, 6f\n"
    "add x25, x25, x22\n"
    "blr x25\n"

    // double_offset += 8
    "add x22, x22, 8\n"

    // current_arg_index += 1
    "add x23, x23, 1\n"

    // goto 1
    "b 1b\n"

    "2:\n"
    // -- integer argument

    // x20 = argument.value
    "ldr x20, [x19]\n"

    // argument++
    "add x19, x19, 8\n"

    // if (integer_offset*8 >= MAX_INT_REG*8) goto 7
    "cmp x21, 8 * 8\n"
    "bge 7f\n"

    // 5[integer_offset]()
    "adr x25, 5f\n"
    "add x25, x25, x21\n"
    "blr x25\n"

    // integer_offset += 8
    "add x21, x21, 8\n"

    // current_arg_index += 1
    "add x23, x23, 1\n"

    // goto 1
    "b 1b\n"

    "3:\n"
    // err.integer, err.double = address(params)
    "ldr x19, [sp, address]\n"
    "blr x19\n"

    "str x0, [sp, register_x0]\n"
    "str x1, [sp, register_x1]\n"
    "str x2, [sp, register_x2]\n"
    "str x3, [sp, register_x3]\n"
    "str x4, [sp, register_x4]\n"
    "str x5, [sp, register_x5]\n"
    "str x6, [sp, register_x6]\n"
    "str x7, [sp, register_x7]\n"

    "str d0, [sp, register_d0]\n"
    "str d1, [sp, register_d1]\n"
    "str d2, [sp, register_d2]\n"
    "str d3, [sp, register_d3]\n"
    "str d4, [sp, register_d4]\n"
    "str d5, [sp, register_d5]\n"
    "str d6, [sp, register_d6]\n"
    "str d7, [sp, register_d7]\n"

    // if (!sendall(sockfd, &err, register_end - register_x0)) goto 4;
    "ldr x0, [sp, sockfd]\n"
    "add x1, sp, register_x0\n"
    "mov x2, register_end - register_x0\n"
    "bl _sendall\n"
    "cmp x0, 0\n"
    "beq 4f\n"

    // result = true
    "mov x0, 1\n"
    "str x0, [sp, result]\n"

    "4:\n"
    // return result
    "ldr x0, [sp, result]\n"
    "add sp, sp, size\n"

    // restore backed up registers
    "ldp x29, x30, [sp, 0x50]\n"
    "ldp x19, x20, [sp, 0x40]\n"
    "ldp x21, x22, [sp, 0x30]\n"
    "ldp x23, x24, [sp, 0x20]\n"
    "ldp x25, x26, [sp, 0x10]\n"
    "ldp x27, x28, [sp], 0x60\n"

    "ret\n"

    "5:\n"
    "mov x0, x20\n"
    "ret\n"
    "mov x1, x20\n"
    "ret\n"
    "mov x2, x20\n"
    "ret\n"
    "mov x3, x20\n"
    "ret\n"
    "mov x4, x20\n"
    "ret\n"
    "mov x5, x20\n"
    "ret\n"
    "mov x6, x20\n"
    "ret\n"
    "mov x7, x20\n"
    "ret\n"

    "6:\n"
    "fmov d0, x20\n"
    "ret\n"
    "fmov d1, x20\n"
    "ret\n"
    "fmov d2, x20\n"
    "ret\n"
    "fmov d3, x20\n"
    "ret\n"
    "fmov d4, x20\n"
    "ret\n"
    "fmov d5, x20\n"
    "ret\n"
    "fmov d6, x20\n"
    "ret\n"
    "fmov d7, x20\n"
    "ret\n"

    "7:\n"
    // -- stack argument

    // x20 = argument.value
    "ldr x20, [x19]\n"
    "add x19, x19, 8\n"

    // pack into stack (into stack_arguments+x26)
    "str x20, [sp, x26]\n"
    // current_arg_index += 1
    "add x23, x23, 1\n"
    // stack_offset += 8
    "add x26, x26, 8\n"

    "b 1b\n");

#else
bool call_function(int sockfd, intptr_t address, size_t argc, argument_t **p_argv)
{
    typedef u64 (*call_argc0_t)();
    typedef u64 (*call_argc1_t)(u64);
    typedef u64 (*call_argc2_t)(u64, u64);
    typedef u64 (*call_argc3_t)(u64, u64, u64);
    typedef u64 (*call_argc4_t)(u64, u64, u64, u64);
    typedef u64 (*call_argc5_t)(u64, u64, u64, u64, u64);
    typedef u64 (*call_argc6_t)(u64, u64, u64, u64, u64, u64);
    typedef u64 (*call_argc7_t)(u64, u64, u64, u64, u64, u64, u64);
    typedef u64 (*call_argc8_t)(u64, u64, u64, u64, u64, u64, u64, u64);
    typedef u64 (*call_argc9_t)(u64, u64, u64, u64, u64, u64, u64, u64, u64);
    typedef u64 (*call_argc10_t)(u64, u64, u64, u64, u64, u64, u64, u64, u64, u64);
    typedef u64 (*call_argc11_t)(u64, u64, u64, u64, u64, u64, u64, u64, u64, u64, u64);

    bool result = false;
    s64 err;

    argument_t *argv = *p_argv;

    TRACE("enter");

    switch (argc)
    {
    case 0:
        err = ((call_argc0_t)address)();
        break;
    case 1:
        err = ((call_argc1_t)address)(argv[0].value);
        break;
    case 2:
        err = ((call_argc2_t)address)(argv[0].value, argv[1].value);
        break;
    case 3:
        err = ((call_argc3_t)address)(argv[0].value, argv[1].value, argv[2].value);
        break;
    case 4:
        err = ((call_argc4_t)address)(argv[0].value, argv[1].value, argv[2].value, argv[3].value);
        break;
    case 5:
        err = ((call_argc5_t)address)(argv[0].value, argv[1].value, argv[2].value, argv[3].value, argv[4].value);
        break;
    case 6:
        err = ((call_argc6_t)address)(argv[0].value, argv[1].value, argv[2].value, argv[3].value, argv[4].value, argv[5].value);
        break;
    case 7:
        err = ((call_argc7_t)address)(argv[0].value, argv[1].value, argv[2].value, argv[3].value, argv[4].value, argv[5].value, argv[6].value);
        break;
    case 8:
        err = ((call_argc8_t)address)(argv[0].value, argv[1].value, argv[2].value, argv[3].value, argv[4].value, argv[5].value, argv[6].value, argv[7].value);
        break;
    case 9:
        err = ((call_argc9_t)address)(argv[0].value, argv[1].value, argv[2].value, argv[3].value, argv[4].value, argv[5].value, argv[6].value, argv[7].value, argv[8].value);
        break;
    case 10:
        err = ((call_argc10_t)address)(argv[0].value, argv[1].value, argv[2].value, argv[3].value, argv[4].value, argv[5].value, argv[6].value, argv[7].value, argv[8].value, argv[9].value);
        break;
    case 11:
        err = ((call_argc11_t)address)(argv[0].value, argv[1].value, argv[2].value, argv[3].value, argv[4].value, argv[5].value, argv[6].value, argv[7].value, argv[8].value, argv[9].value, argv[10].value);
        break;
    }

    call_response_t response = {0};
    response.return_values.return_value = err;

    CHECK(sendall(sockfd, (char *)&response, sizeof(response)));

    result = true;

error:
    return result;
}
#endif // __ARM_ARCH_ISA_A64

bool handle_call(int sockfd)
{
    TRACE("enter");
    s64 err = 0;
    int result = false;
    argument_t *argv = NULL;
    cmd_call_t cmd;
    CHECK(recvall(sockfd, (char *)&cmd, sizeof(cmd)));

    argv = (argument_t *)malloc(sizeof(argument_t) * cmd.argc);
    CHECK(recvall(sockfd, (char *)argv, sizeof(argument_t) * cmd.argc));

    TRACE("address: %p", cmd.address);
    CHECK(call_function(sockfd, cmd.address, cmd.argc, (argument_t **)cmd.argv));

    result = true;

error:
    if (argv)
    {
        free(argv);
    }
    return result;
}

bool handle_peek(int sockfd)
{
    TRACE("enter");
    s64 err = 0;
    int result = false;
    u64 *argv = NULL;
    cmd_peek_t cmd;

#ifdef __APPLE__
    mach_port_t task;
    vm_offset_t data = 0;
    mach_msg_type_number_t size;

    CHECK(recvall(sockfd, (char *)&cmd, sizeof(cmd)));
    CHECK(task_for_pid(mach_task_self(), getpid(), &task) == KERN_SUCCESS);
    if (vm_read(task, cmd.address, cmd.size, &data, &size) == KERN_SUCCESS)
    {
        CHECK(send_reply(sockfd, CMD_REPLY_PEEK));
        CHECK(sendall(sockfd, (char *)cmd.address, cmd.size));
    }
    else
    {
        CHECK(send_reply(sockfd, CMD_REPLY_ERROR));
    }
#else  // __APPLE__
    CHECK(recvall(sockfd, (char *)&cmd, sizeof(cmd)));
    CHECK(send_reply(sockfd, CMD_REPLY_PEEK));
    CHECK(sendall(sockfd, (char *)cmd.address, cmd.size));
#endif // __APPLE__

    result = true;

error:
    if (argv)
    {
        free(argv);
    }

#ifdef __APPLE__
    if (data)
    {
        vm_deallocate(task, data, size);
    }
#endif // __APPLE__
    return result;
}

bool handle_poke(int sockfd)
{
    TRACE("enter");
    s64 err = 0;
    int success = false;
    u64 *argv = NULL;
    char *data = NULL;
    cmd_poke_t cmd;

#ifdef __APPLE__
    mach_port_t task;
    CHECK(task_for_pid(mach_task_self(), getpid(), &task) == KERN_SUCCESS);
    CHECK(recvall(sockfd, (char *)&cmd, sizeof(cmd)));

    // TODO: consider splitting recieve chunks
    data = malloc(cmd.size);
    CHECK(data);
    CHECK(recvall(sockfd, data, cmd.size));

    if (vm_write(task, cmd.address, (vm_offset_t)data, cmd.size) == KERN_SUCCESS)
    {
        CHECK(send_reply(sockfd, CMD_REPLY_POKE));
    }
    else
    {
        CHECK(send_reply(sockfd, CMD_REPLY_ERROR));
    }
#else  // __APPLE__
    CHECK(recvall(sockfd, (char *)&cmd, sizeof(cmd)));
    CHECK(recvall(sockfd, (char *)cmd.address, cmd.size));
    CHECK(send_reply(sockfd, CMD_REPLY_POKE));
#endif // __APPLE__

    success = true;

error:
    if (argv)
    {
        free(argv);
    }
    if (data)
    {
        free(data);
    }
    return success;
}

#if __APPLE__

void (^dummy_block)(void) = ^{
};

bool handle_get_dummy_block(int sockfd)
{
    TRACE("enter");
    CHECK(sendall(sockfd, (const char *)&dummy_block, sizeof(&dummy_block)));
    return true;
error:
    return false;
}

#else // !__APPLE__

bool handle_get_dummy_block(int sockfd)
{
    return true;
}

#endif // __APPLE__

void handle_client(int sockfd)
{
    bool disconnected = false;
    TRACE("enter. fd: %d", sockfd);

    struct utsname uname_buf;
    CHECK(0 == uname(&uname_buf));

    protocol_handshake_t handshake = {0};
    handshake.magic = SERVER_MAGIC_VERSION;
    handshake.arch = ARCH_UNKNOWN;
    strncpy(handshake.sysname, uname_buf.sysname, HANDSHAKE_SYSNAME_LEN - 1);

#ifdef __ARM_ARCH_ISA_A64
    handshake.arch = ARCH_ARM64;
#endif

    CHECK(sendall(sockfd, (char *)&handshake, sizeof(handshake)));

    while (true)
    {
        protocol_message_t cmd;
        TRACE("recv");
        if (!recvall_ext(sockfd, (char *)&cmd, sizeof(cmd), &disconnected))
        {
            goto error;
        }
        CHECK(cmd.magic == MAGIC);

        TRACE("client fd: %d, cmd type: %d", sockfd, cmd.cmd_type);

        switch (cmd.cmd_type)
        {
        case CMD_EXEC:
        {
            handle_exec(sockfd);
            break;
        }
        case CMD_DLOPEN:
        {
            handle_dlopen(sockfd);
            break;
        }
        case CMD_DLSYM:
        {
            handle_dlsym(sockfd);
            break;
        }
        case CMD_CALL:
        {
            handle_call(sockfd);
            break;
        }
        case CMD_PEEK:
        {
            handle_peek(sockfd);
            break;
        }
        case CMD_POKE:
        {
            handle_poke(sockfd);
            break;
        }
        case CMD_GET_DUMMY_BLOCK:
        {
            handle_get_dummy_block(sockfd);
            break;
        }
        case CMD_CLOSE:
        {
            // client requested to close connection
            goto error;
        }
        default:
        {
            TRACE("unknown cmd");
        }
        }
    }

error:
    close(sockfd);
}

void signal_handler(int sig)
{
    TRACE("entered with signal code: %d", sig);
}

void wait_for_workers()
{
    int status;
    pid_t pid;
    while(true) {
        pid_t pid = waitpid(-1, &status, 0);
        if(-1 == pid) {
            sleep(1);
            continue;
        }
        TRACE("PID: %d exited with status: %d", pid, status);
    }
}

int main(int argc, const char *argv[])
{
    int opt;
    bool worker_spawn = false;
    char port[MAX_OPTION_LEN] = DEFAULT_PORT;

    while ((opt = getopt(argc, (char *const *)argv, "hp:o:w")) != -1)
    {
        switch (opt)
        {
        case 'p':
        {
            strncpy(port, optarg, sizeof(port) - 1);
            break;
        }
        case 'o':
        {
            if (0 == strcmp(optarg, "stdout"))
            {
                g_stdout = true;
            }
            if (0 == strcmp(optarg, "syslog"))
            {
                g_syslog = true;
            }
            char *file = strstr(optarg, "file:");
            if (file)
            {
                g_file = fopen(file + 5, "wb");
                if (!g_file)
                {
                    printf("failed to open %s for writing\n", optarg);
                }
            }
            break;
        }
        case 'w':
        {
            worker_spawn = true;
            break;
        }
        case 'h':
        case '?':
        default: /* '?' */
        {
            printf(USAGE, argv[0], argv[0]);
            exit(EXIT_FAILURE);
        }
        }
    }

    if(worker_spawn) {
        TRACE("New worker spawned");
        handle_client(WORKER_CLIENT_SOCKET_FD);
        exit(EXIT_SUCCESS);
    }

    signal(SIGPIPE, signal_handler);

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
    CHECK(inet_ntop(servinfo2->ai_family, get_in_addr(servinfo2->ai_addr), ipstr, sizeof(ipstr)));
    TRACE("Waiting for connections on [%s]:%s", ipstr, port);

    server_fd = socket(servinfo2->ai_family, servinfo2->ai_socktype, servinfo2->ai_protocol);
    CHECK(server_fd >= 0);
    CHECK(-1 != fcntl(server_fd, F_SETFD, FD_CLOEXEC));

    int yes_1 = 1;
    CHECK(0 == setsockopt(server_fd, SOL_SOCKET, SO_REUSEADDR, &yes_1, sizeof(yes_1)));
    CHECK(0 == bind(server_fd, servinfo2->ai_addr, servinfo2->ai_addrlen));

    freeaddrinfo(servinfo); // all done with this structure

    CHECK(0 == listen(server_fd, MAX_CONNECTIONS));

#ifdef __APPLE__
    pthread_t runloop_thread;
    CHECK(0 == pthread_create(&runloop_thread, NULL, (void *(*)(void *))CFRunLoopRun, NULL));
#endif // __APPLE__

    pthread_t wait_thread;
    CHECK(0 == pthread_create(&wait_thread, NULL, (void *(*)(void *))wait_for_workers, NULL));

    while (1)
    {
        struct sockaddr_storage their_addr; // connector's address information
        socklen_t addr_size = sizeof(their_addr);
        int client_fd = accept(server_fd, (struct sockaddr *)&their_addr, &addr_size);
        CHECK(client_fd >= 0);
        CHECK(-1 != fcntl(client_fd, F_SETFD, FD_CLOEXEC));

        char ipstr[INET6_ADDRSTRLEN];
        CHECK(inet_ntop(their_addr.ss_family, get_in_addr((struct sockaddr *)&their_addr), ipstr, sizeof(ipstr)));
        TRACE("Got a connection from %s [%d]", ipstr, client_fd);

        CHECK(spawn_worker_server(client_fd, argv, argc));
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
