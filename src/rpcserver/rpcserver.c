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
#include <dirent.h>
#include <stdbool.h>
#include "protos/rpc.pb-c.h"

bool handle_showobject(int sockfd, Rpc__CmdShowObject *cmd);

int handle_showclass(int sockfd, Rpc__CmdShowClass *cmd);

int handle_get_class_list(int sockfd, Rpc__CmdGetClassList *cmd);

#ifdef __APPLE__

#include <CoreFoundation/CoreFoundation.h>
#include <mach/mach.h>

#else

bool handle_showobject(int sockfd, Rpc__CmdShowObject *cmd) { return 0; }

int handle_showclass(int sockfd, Rpc__CmdShowClass *cmd) { return 0; }

int handle_get_class_list(int sockfd, Rpc__CmdGetClassList *cmd) { return 0; }

#endif // __APPLE__

#include "common.h"

#define DEFAULT_PORT ("5910")
#define DEFAULT_SHELL ("/bin/sh")
#define USAGE ("Usage: %s [-p port] [-o (stdout|syslog|file:filename)] \n\
-h  show this help message \n\
-o  output. can be all of the following: stdout, syslog and file:filename. can be passed multiple times \n\
\n\
Example usage: \n\
%s -p 5910 -o syslog -o stdout -o file:/tmp/log.txt\n")
#define MAGIC (0x12345678)
#define MAX_CONNECTIONS (1024)

#define MAX_OPTION_LEN (256)
#define BUFFERSIZE (64 * 1024)
#define INVALID_PID (0xffffffff)
#define WORKER_CLIENT_SOCKET_FD (3)
#define CLOBBERD_LIST "x0", "x1", "x2", "x3", "x4", "x5", "x6", "x7", "x8","x19","x20","x21","x22","x23","x24","x25","x26"

#define SERVER_MAGIC_VERSION (0x88888807)
extern char **environ;

void *get_in_addr(struct sockaddr *sa) // get sockaddr, IPv4 or IPv6:
{
    return sa->sa_family == AF_INET ? (void *) &(((struct sockaddr_in *) sa)->sin_addr)
                                    : (void *) &(((struct sockaddr_in6 *) sa)->sin6_addr);
}

bool internal_spawn(bool background, char **argv, char **envp, pid_t *pid, int *master_fd) {
    bool ret = RPC_FAILURE;
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

    if (!background) {
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
    } else {
        CHECK(0 == posix_spawn_file_actions_addopen(&actions, STDIN_FILENO, "/dev/null", O_RDONLY, 0));
        CHECK(0 == posix_spawn_file_actions_addopen(&actions, STDOUT_FILENO, "/dev/null", O_WRONLY, 0));
        CHECK(0 == posix_spawn_file_actions_addopen(&actions, STDERR_FILENO, "/dev/null", O_WRONLY, 0));
    }

    CHECK(0 == posix_spawnp(pid, argv[0], &actions, &attr, argv, envp));
    CHECK(*pid != INVALID_PID);

    posix_spawnattr_destroy(&attr);
    posix_spawn_file_actions_destroy(&actions);

    ret = RPC_SUCCESS;

    error:
    if (slave_fd != -1) {
        close(slave_fd);
    }
    if (!ret) {
        if (*master_fd != -1) {
            close(*master_fd);
        }
        *pid = INVALID_PID;
    }
    return ret;
}

bool spawn_worker_server(int client_socket, const char *argv[], int argc) {
    bool ret = RPC_FAILURE;

    // append -w to original argv
    int new_argc = argc + 1;
    const char **new_argv = malloc((new_argc + 1) * sizeof(char *));
    for (int i = 0; i < argc; ++i) {
        new_argv[i] = argv[i];
    }
    new_argv[new_argc - 1] = "-w";
    new_argv[new_argc] = NULL;

    pid_t pid;
    posix_spawn_file_actions_t actions;
    CHECK(0 == posix_spawn_file_actions_init(&actions));
    CHECK(0 == posix_spawn_file_actions_adddup2(&actions, STDIN_FILENO, STDIN_FILENO));
    CHECK(0 == posix_spawn_file_actions_adddup2(&actions, STDOUT_FILENO, STDOUT_FILENO));
    CHECK(0 == posix_spawn_file_actions_adddup2(&actions, STDERR_FILENO, STDERR_FILENO));
    CHECK(0 == posix_spawn_file_actions_adddup2(&actions, client_socket, WORKER_CLIENT_SOCKET_FD));

    CHECK(0 == posix_spawnp(&pid, new_argv[0], &actions, NULL, (char *const *) new_argv, environ));
    CHECK(pid != INVALID_PID);

    TRACE("Spawned Worker Process: %d", pid);
    ret = RPC_SUCCESS;

    error:
    posix_spawn_file_actions_destroy(&actions);
    free(new_argv);
    close(client_socket);
    return ret;
}

typedef struct {
    int sockfd;
    pid_t pid;
} thread_notify_client_spawn_error_t;

void thread_waitpid(pid_t pid) {
    TRACE("enter");
    s32 err;
    waitpid(pid, &err, 0);
}


bool handle_exec(int sockfd, Rpc__CmdExec *cmd) {
    int ret = RPC_FAILURE;

    u8 byte;
    pthread_t thread = 0;
    thread_notify_client_spawn_error_t *thread_params = NULL;
    pid_t pid = INVALID_PID;
    int master = -1;
    char **argv = NULL;
    char **envp = NULL;
    u32 argc;
    u32 envc;
    u8 background;


    CHECK(cmd->n_argv > 0);
    COPY_ARR_WITH_NULL(cmd->argv, argv, cmd->n_argv);
    COPY_ARR_WITH_NULL(cmd->envp, envp, cmd->n_envp);

    Rpc__Response response = RPC__RESPONSE__INIT;
    Rpc__ResponseCmdExec resp_exec = RPC__RESPONSE_CMD_EXEC__INIT;

    response.type_case = RPC__RESPONSE__TYPE_EXEC;


    CHECK(internal_spawn(cmd->background, argv, cmd->n_envp ? envp : environ, &pid, &master));

    resp_exec.pid = pid;
    response.exec = &resp_exec;
    send_response(sockfd, &response);

    if (cmd->background) {
        CHECK(0 == pthread_create(&thread, NULL, (void *(*)(void *)) thread_waitpid, (void *) (intptr_t) pid));
    } else {
        Rpc__ResponseCmdExecChunk resp_exec_chunk = RPC__RESPONSE_CMD_EXEC_CHUNK__INIT;
        response.type_case = RPC__RESPONSE__TYPE_EXEC_CHUNK;

        // make sure we have the process fd for its stdout and stderr
        CHECK(master >= 0);
        uint8_t *resp_buff = NULL;

        fd_set readfds;
        char buf[BUFFERSIZE];
        int maxfd = master > sockfd ? master : sockfd;
        int nbytes = 0;

        fd_set errfds;

        while (true) {
            FD_ZERO(&readfds);
            FD_SET(master, &readfds);
            FD_SET(sockfd, &readfds);

            CHECK(select(maxfd + 1, &readfds, NULL, &errfds, NULL) != -1);

            if (FD_ISSET(master, &readfds)) {
                nbytes = read(master, buf, BUFFERSIZE);
                if (nbytes < 1) {
                    TRACE("read master failed. break");
                    break;
                }

                TRACE("master->sock");
                resp_exec_chunk.buffer.len = nbytes;
                resp_exec_chunk.buffer.data = (uint8_t *) buf;
                resp_exec_chunk.type_case = RPC__RESPONSE_CMD_EXEC_CHUNK__TYPE_BUFFER;
                response.exec_chunk = &resp_exec_chunk;
                send_response(sockfd, &response);

            }

            if (FD_ISSET(sockfd, &readfds)) {
                nbytes = recv(sockfd, buf, BUFFERSIZE, 0);
                if (nbytes < 1) {
                    break;
                }
                TRACE("sock->master");
                CHECK(writeall(master, buf, nbytes));
            }
        }
        s32 error;
        TRACE("wait for process to finish");
#ifndef DEBUG
        CHECK(pid == waitpid(pid, &error, 0));
#endif
        resp_exec_chunk.type_case = RPC__RESPONSE_CMD_EXEC_CHUNK__TYPE_EXIT_CODE;
        resp_exec_chunk.exit_code = error;
        response.exec_chunk = &resp_exec_chunk;
        send_response(sockfd, &response);

    }

    ret = RPC_SUCCESS;

    error:
    SAFE_FREE(argv);
    SAFE_FREE(envp);
    SAFE_FREE(thread_params);

    if (INVALID_PID == pid) {
        TRACE("invalid pid");
        // failed to create process somewhere in the prolog, at least notify
        RESPONSE_ERROR(response);
        send_response(sockfd, &response);
    }

    if (-1 != master) {
        TRACE("close master: %d", master);
        if (0 != close(master)) {
            perror("close");
        }
    }

    return ret;
}

bool handle_dlopen(int sockfd, Rpc__CmdDlopen *cmd) {
    int ret = RPC_FAILURE;
    Rpc__Response response = RPC__RESPONSE__INIT;
    Rpc__ResponseDlopen resp_dlopen = RPC__RESPONSE_DLOPEN__INIT;
    response.type_case = RPC__RESPONSE__TYPE_DLOPEN;
    uint64_t res = 0;
    res = (uint64_t) dlopen(cmd->filename, cmd->mode);
    if (!res) {
        RESPONSE_ERROR(response);
    } else {
        resp_dlopen.handle = res;
        response.dlopen = &resp_dlopen;
        ret = RPC_SUCCESS;
    }
    send_response(sockfd, &response);
    return ret;
}

bool handle_dlclose(int sockfd, Rpc__CmdDlclose *cmd) {
    int ret = RPC_FAILURE;
    Rpc__Response response = RPC__RESPONSE__INIT;
    Rpc__ResponseDlclose resp_dlclose = RPC__RESPONSE_DLCLOSE__INIT;
    response.type_case = RPC__RESPONSE__TYPE_DLCLOSE;
    uint64_t res = 0;
    res = (uint64_t) dlclose((void *) cmd->handle);
    if (res == -1) {
        RESPONSE_ERROR(response);
    } else {
        resp_dlclose.res = res;
        response.dlclose = &resp_dlclose;
        ret = RPC_SUCCESS;
    }
    send_response(sockfd, &response);
    return ret;
}

bool handle_dlsym(int sockfd, Rpc__CmdDlsym *cmd) {
    int ret = RPC_FAILURE;
    uint64_t res = 0;
    Rpc__Response response = RPC__RESPONSE__INIT;
    Rpc__ResponseDlsym resp_dlsym = RPC__RESPONSE_DLSYM__INIT;
    response.type_case = RPC__RESPONSE__TYPE_DLSYM;
    res = (uint64_t) dlsym((void *) cmd->handle, cmd->symbol_name);
    if (!res) {
        RESPONSE_ERROR(response);
    } else {
        resp_dlsym.ptr = res;
        response.dlsym = &resp_dlsym;
        ret = RPC_SUCCESS;
    }
    TRACE("%s = %p", cmd->symbol_name, res);
    send_response(sockfd, &response);
    return ret;
}

#ifdef __ARM_ARCH_ISA_A64


#define MAX_STACK_ARGS (16)
#define MAX_REGS_ARGS (8)


typedef struct {
    uint64_t x[MAX_REGS_ARGS];
    double d[MAX_REGS_ARGS];
    uint64_t stack[MAX_STACK_ARGS];
} arm_args_t;


volatile bool call_function(intptr_t address, size_t va_list_index, size_t argc, Rpc__Argument **p_argv,
                            Rpc__ResponseCall *resp) {

    arm_args_t args = {0};
    uint64_t regs_backup[30] = {0};
    uint32_t idx_fp = 0, idx_gp = 0, idx_stack = 0, idx_argv = 0;
    intptr_t *current_target = NULL, *current_arg = NULL;
    for (idx_argv = 0; idx_argv < argc; idx_argv++) {
        switch (p_argv[idx_argv]->type_case) {
            case RPC__ARGUMENT__TYPE_V_STR:
            case RPC__ARGUMENT__TYPE_V_BYTES:
            case RPC__ARGUMENT__TYPE_V_INT:
                // Assign target register if available, otherwise set to `NULL`
                current_target = (idx_gp < MAX_REGS_ARGS) ? (intptr_t *) &args.x[idx_gp++] : NULL;
                break;
            case RPC__ARGUMENT__TYPE_V_DOUBLE:
                // Assign target register if available, otherwise set to `NULL`
                current_target = (idx_fp < MAX_REGS_ARGS) ? (intptr_t *) &args.d[idx_fp++] : NULL;
                break;
            default:
                break;
        }
        // Use the stack if `va_list_index` or if the target register is not available
        if (idx_argv >= va_list_index || !current_target) {
            current_target = (intptr_t *) &args.stack[idx_stack++];
        }
        // `v_int`, `v_str`, and `v_double` all point to the same place, so we use `v_int` for convenience. However, `v_bytes` requires access to `v_bytes.data`.
        current_arg = (p_argv[idx_argv]->type_case == RPC__ARGUMENT__TYPE_V_BYTES
                       ? (intptr_t *) &p_argv[idx_argv]->v_bytes.data
                       : (intptr_t *) &p_argv[idx_argv]->v_int);
        *current_target = *current_arg;
    }


    __asm__ __volatile__(
            "mov x19, %[address]\n"
            "mov x20, %[args_registers]\n"
            "mov x21, %[max_args]\n"
            "mov x22, %[args_stack]\n"
            "mov x23, %[regs_backup]\n"
            "mov x24, %[result_registers]\n"
            "mov x25, #0\n" // counter
            "mov x26, #0\n" // temp stack current_arg

            // Backup registers
            "stp x8,  x9,  [x23]\n"
            "stp x10, x11, [x23, #16]\n"
            "stp x12, x13, [x23, #32]\n"
            "stp x14, x15, [x23, #48]\n"
            "stp x16, x17, [x23, #64]\n"
            "stp x18, x19, [x23, #80]\n"
            "stp x20, x21, [x23, #96]\n"
            "stp x22, x23, [x23, #112]\n"
            "stp x24, x25, [x23, #128]\n"
            "stp x26, x27, [x23, #144]\n"

            // Prepare register arguments
            "ldp x0, x1, [x20]\n"
            "ldp x2, x3, [x20, #16]\n"
            "ldp x4, x5, [x20, #32]\n"
            "ldp x6, x7, [x20, #48]\n"
            "ldp d0, d1, [x20, #64]\n"
            "ldp d2, d3, [x20, #80]\n"
            "ldp d4, d5, [x20, #96]\n"
            "ldp d6, d7, [x20, #112]\n"

            // Prepare stack arguments
            "sub sp, sp, x21\n"
            "1:\n"
            "ldr x26, [x22, x25, lsl #3]\n"
            "str x26, [sp, x25, lsl #3]\n"
            "add x25, x25, #1\n"
            "cmp x25, x21\n"
            "bne 1b\n"

            // Call function
            "blr x19\n"

            // Deallocate space on the stack
            "add sp, sp, x21\n"

            // Get return values
            "stp x0, x1, [x24]\n"
            "stp x2, x3, [x24, #16]\n"
            "stp x4, x5, [x24, #32]\n"
            "stp x6, x7, [x24, #48]\n"
            "stp d0, d1, [x24, #64]\n"
            "stp d2, d3, [x24, #80]\n"
            "stp d4, d5, [x24, #96]\n"
            "stp d6, d7, [x24, #112]\n"

            // Restore
            "ldp x8,  x9,  [x23]\n"
            "ldp x10, x11, [x23, #16]\n"
            "ldp x12, x13, [x23, #32]\n"
            "ldp x14, x15, [x23, #48]\n"
            "ldp x16, x17, [x23, #64]\n"
            "ldp x18, x19, [x23, #80]\n"
            "ldp x20, x21, [x23, #96]\n"
            "ldp x22, x23, [x23, #112]\n"
            "ldp x24, x25, [x23, #128]\n"
            "ldp x26, x27, [x23, #144]\n"
            :
            :
    [regs_backup] "r"(&regs_backup),
    [args_registers] "r"(&args),
    [args_stack] "r"(&args.stack),
    [max_args] "r"((uint64_t) MAX_STACK_ARGS),
    [address] "r"(address),
    [result_registers] "r"(&resp->arm_registers->x0)
    :CLOBBERD_LIST
    );
    return RPC_SUCCESS;
}


#else

typedef u64 (*call_argc_t)(u64, u64, u64, u64, u64, u64, u64, u64, u64, u64, u64);

volatile bool call_function(intptr_t address, size_t va_list_index, size_t argc, Rpc__Argument **p_argv,
                            Rpc__ResponseCall *response) {
    s64 return_val;
    TRACE("enter");
    call_argc_t call = (call_argc_t) address;
    u64 args[11] = {0};
    for (size_t i = 0; i < argc; i++) {
        switch (p_argv[i]->type_case) {
            case RPC__ARGUMENT__TYPE_V_DOUBLE:
                args[i] = p_argv[i]->v_double;
                break;
            case RPC__ARGUMENT__TYPE_V_INT:
                args[i] = p_argv[i]->v_int;
                break;
            case RPC__ARGUMENT__TYPE_V_STR:
                args[i] = (uint64_t) p_argv[i]->v_str;
                break;
            case RPC__ARGUMENT__TYPE_V_BYTES:
                args[i] = (uint64_t) p_argv[i]->v_bytes.data;
                break;
            default:
                break;
        }
    }
    return_val = call(args[0], args[1], args[2], args[3], args[4], args[5], args[6], args[7], args[8], args[9],
                      args[10]);
    response->return_values_case = RPC__RESPONSE_CALL__RETURN_VALUES_RETURN_VALUE;
    response->return_value = return_val;

    return RPC_SUCCESS;
}


#endif // __ARM_ARCH_ISA_A64

bool handle_call(int sockfd, Rpc__CmdCall *cmd) {
    TRACE("enter");
    int ret = RPC_FAILURE;
    Rpc__Response response = RPC__RESPONSE__INIT;
    Rpc__ResponseCall resp_call = RPC__RESPONSE_CALL__INIT;
#ifdef __ARM_ARCH_ISA_A64
    Rpc__ReturnRegistersArm regs = RPC__RETURN_REGISTERS_ARM__INIT;
    resp_call.arm_registers = &regs;
    resp_call.return_values_case = RPC__RESPONSE_CALL__RETURN_VALUES_ARM_REGISTERS;
#else
    resp_call.return_values_case = RPC__RESPONSE_CALL__RETURN_VALUES_RETURN_VALUE;
#endif
    response.type_case = RPC__RESPONSE__TYPE_CALL;
    TRACE("address: %p", cmd->address);
    CHECK(call_function(cmd->address, cmd->va_list_index, cmd->n_argv, cmd->argv, &resp_call));
    response.call = &resp_call;
    send_response(sockfd, &response);
    ret = RPC_SUCCESS;
    error:
    return ret;
}

bool handle_peek(int sockfd, Rpc__CmdPeek *cmd) {
    TRACE("enter");
    int ret = RPC_FAILURE;
    uint8_t *buffer = NULL;
    Rpc__Response response = RPC__RESPONSE__INIT;
    Rpc__ResponsePeek peek = RPC__RESPONSE_PEEK__INIT;
    response.type_case = RPC__RESPONSE__TYPE_PEEK;

#if defined(SAFE_READ_WRITES) && defined(__APPLE__)
    mach_msg_type_number_t size;
    if (vm_read(mach_task_self(), cmd->address, cmd->size, (vm_offset_t *) &buffer, &size) == KERN_SUCCESS) {
        peek.data.data = (uint8_t *) buffer;
        peek.data.len = size;
        response.peek = &peek;
        send_response(sockfd, &response);
        CHECK(vm_deallocate(mach_task_self(), (vm_address_t) buffer, size) == KERN_SUCCESS);
        buffer = NULL;
    } else {
        RESPONSE_ERROR(response);
        send_response(sockfd, &response);
    }
#else  // __APPLE__
    peek.data.data = (uint8_t *) cmd->address;
    peek.data.len = cmd->size;
    response.peek = &peek;
    send_response(sockfd, &response);

#endif // __APPLE__
    ret = RPC_SUCCESS;

    error:
    SAFE_FREE(buffer);

    return ret;
}

bool handle_poke(int sockfd, Rpc__CmdPoke *cmd) {
    TRACE("Enter");
    int ret = RPC_FAILURE;
    char *data = NULL;
    Rpc__Response response = RPC__RESPONSE__INIT;
    Rpc__ResponsePoke poke = RPC__RESPONSE_POKE__INIT;
    response.type_case = RPC__RESPONSE__TYPE_POKE;

#if defined(SAFE_READ_WRITES) && defined(__APPLE__)
    if (vm_write(mach_task_self(), cmd->address, (vm_offset_t) cmd->data.data, cmd->data.len) == KERN_SUCCESS) {
        poke.result = RPC_SUCCESS;
        response.poke = &poke;
    } else {
        RESPONSE_ERROR(response);
    }
#else  // __APPLE__
    memcpy((uint64_t *) cmd->address, cmd->data.data, cmd->data.len);
    poke.result = RPC_SUCCESS;
    response.poke = &poke;
#endif // __APPLE__
    CHECK(send_response(sockfd, &response));
    ret = RPC_SUCCESS;

    error:
    SAFE_FREE(data);
    return ret;
}

// exported for client hooks
bool get_true() {
    return true;
}

// exported for client hooks
bool get_false() {
    return false;
}

#if __APPLE__

void (^dummy_block)(void) = ^{
};

bool handle_get_dummy_block(int sockfd, Rpc__CmdDummyBlock *cmd) {
    TRACE("enter");
    bool ret = RPC_FAILURE;
    Rpc__Response response = RPC__RESPONSE__INIT;
    Rpc__ResponseDummyBlock block = RPC__RESPONSE_DUMMY_BLOCK__INIT;
    response.type_case = RPC__RESPONSE__TYPE_DUMMY_BLOCK;
    block.address = (uint64_t) &dummy_block;
    block.size = sizeof(&dummy_block);
    response.dummy_block = &block;
    CHECK(send_response(sockfd, &response));
    ret = RPC_SUCCESS;
    error:
    return ret;
}

#else // !__APPLE__

bool handle_get_dummy_block(int sockfd, Rpc__CmdDummyBlock *cmd) {
    return true;
}

#endif // __APPLE__

bool handle_listdir(int sockfd, Rpc__CmdListDir *cmd) {

    TRACE("enter");
    bool ret = RPC_FAILURE;
    DIR *dirp = NULL;
    size_t entry_count = 0;
    size_t idx = 0;
    struct dirent *entry = {0};

    Rpc__Response response = RPC__RESPONSE__INIT;
    Rpc__ResponseListdir resp_list_dir = RPC__RESPONSE_LISTDIR__INIT;
    Rpc__DirEntry *d_entry = NULL;
    Rpc__DirEntryStat *d_stat = NULL, *l_stat = NULL;

    response.type_case = RPC__RESPONSE__TYPE_LIST_DIR;
    response.list_dir = &resp_list_dir;

    dirp = opendir(cmd->path);
    if (!dirp) {
        TRACE("invalid dir");
        goto error;
    }
    for (entry = readdir(dirp); entry != NULL; entry = readdir(dirp)) {
        entry_count++;
    }
    closedir(dirp);

    dirp = opendir(cmd->path);
    if (!dirp) {
        TRACE("invalid dir");
        goto error;
    }

    resp_list_dir.magic = MAGIC;
    resp_list_dir.dirp = (uint64_t) dirp;
    resp_list_dir.n_dir_entries = entry_count;
    resp_list_dir.dir_entries = (Rpc__DirEntry **) malloc(sizeof(Rpc__DirEntry) * entry_count);
    CHECK(resp_list_dir.dir_entries != NULL);

    while ((entry = readdir(dirp)) != NULL) {
        struct stat system_lstat = {0};
        struct stat system_stat = {0};
        char fullpath[FILENAME_MAX] = {0};
        CHECK(0 < sprintf(fullpath, "%s/%s", cmd->path, entry->d_name));


        u64 lstat_error = 0;
        u64 stat_error = 0;

        if (lstat(fullpath, &system_lstat)) {
            lstat_error = errno;
        }
        if (stat(fullpath, &system_stat)) {
            stat_error = errno;
        }

        d_entry = (Rpc__DirEntry *) malloc(sizeof(Rpc__DirEntry));
        d_stat = (Rpc__DirEntryStat *) malloc(sizeof(Rpc__DirEntryStat));
        l_stat = (Rpc__DirEntryStat *) malloc(sizeof(Rpc__DirEntryStat));
        CHECK(d_entry != NULL && d_stat != NULL && l_stat != NULL);

        rpc__dir_entry__init(d_entry);
        rpc__dir_entry_stat__init(d_stat);
        rpc__dir_entry_stat__init(l_stat);

        // Init d_stat
        d_stat->errno1 = stat_error;
        d_stat->st_dev = system_stat.st_dev;
        d_stat->st_mode = system_stat.st_mode;
        d_stat->st_nlink = system_stat.st_nlink;
        d_stat->st_ino = system_stat.st_ino;
        d_stat->st_uid = system_stat.st_uid;
        d_stat->st_gid = system_stat.st_gid;
        d_stat->st_rdev = system_stat.st_rdev;
        d_stat->st_size = system_stat.st_size;
        d_stat->st_blocks = system_stat.st_blocks;
        d_stat->st_blksize = system_stat.st_blksize;
        d_stat->st_atime1 = system_stat.st_atime;
        d_stat->st_mtime1 = system_stat.st_mtime;
        d_stat->st_ctime1 = system_stat.st_ctime;

        //Init l_stat
        l_stat->errno1 = lstat_error;
        l_stat->st_dev = system_lstat.st_dev;
        l_stat->st_mode = system_lstat.st_mode;
        l_stat->st_nlink = system_lstat.st_nlink;
        l_stat->st_ino = system_lstat.st_ino;
        l_stat->st_uid = system_lstat.st_uid;
        l_stat->st_gid = system_lstat.st_gid;
        l_stat->st_rdev = system_lstat.st_rdev;
        l_stat->st_size = system_lstat.st_size;
        l_stat->st_blocks = system_lstat.st_blocks;
        l_stat->st_blksize = system_lstat.st_blksize;
        l_stat->st_atime1 = system_lstat.st_atime;
        l_stat->st_mtime1 = system_lstat.st_mtime;
        l_stat->st_ctime1 = system_lstat.st_ctime;

        d_entry->d_type = entry->d_type;
        d_entry->d_name = strdup(entry->d_name);
        d_entry->stat = d_stat;
        d_entry->lstat = l_stat;

        resp_list_dir.dir_entries[idx] = d_entry;
        idx++;
    }


    error:
    if (dirp) {
        closedir(dirp);
    }

    send_response(sockfd, &response);
    for (uint64_t i = 0; i < entry_count; i++) {
        SAFE_FREE(resp_list_dir.dir_entries[i]->d_name);
        SAFE_FREE(resp_list_dir.dir_entries[i]->stat);
        SAFE_FREE(resp_list_dir.dir_entries[i]->lstat);
        SAFE_FREE(resp_list_dir.dir_entries[i]);
    }
    SAFE_FREE(resp_list_dir.dir_entries);
    TRACE("exit");

    return ret;
}


void handle_client(int sockfd) {
    bool disconnected = false;
    TRACE("enter. fd: %d", sockfd);

    struct utsname uname_buf;
    uint8_t buffer[BUFFERSIZE] = {0};
    size_t message_size;


    CHECK(0 == uname(&uname_buf));
    Rpc__Handshake handshake = RPC__HANDSHAKE__INIT;
    handshake.magic = SERVER_MAGIC_VERSION;
    handshake.arch = RPC__ARCH__ARCH_UNKNOWN;
    handshake.sysname = uname_buf.sysname;
    handshake.machine = uname_buf.machine;
    CHECK(-1 != fcntl(sockfd, F_SETFD, FD_CLOEXEC));

#ifdef __ARM_ARCH_ISA_A64
    handshake.arch = RPC__ARCH__ARCH_ARM64;
#endif
    message_size = rpc__handshake__pack(&handshake, buffer); // TODO: CHCK MACRO
    CHECK(message_send(sockfd, (const uint8_t *) &buffer, message_size));

    while (true) {
        Rpc__Command *cmd;
        message_size = 0;
        CHECK(message_receive(sockfd, (char *) &buffer, &message_size))

        TRACE("recv");
        cmd = rpc__command__unpack(NULL, message_size, buffer);
        TRACE("client fd: %d, cmd type: %d", sockfd, cmd->type_case);
        CHECK(cmd->magic == MAGIC);

        switch (cmd->type_case) {
            case RPC__COMMAND__TYPE_EXEC: {
                handle_exec(sockfd, cmd->exec);
                break;
            }
            case RPC__COMMAND__TYPE_DLOPEN: {
                handle_dlopen(sockfd, cmd->dlopen);
                break;
            }
            case RPC__COMMAND__TYPE_DLSYM: {
                handle_dlsym(sockfd, cmd->dlsym);
                break;
            }
            case RPC__COMMAND__TYPE_DLCLOSE: {
                handle_dlclose(sockfd, cmd->dlclose);
                break;
            }
            case RPC__COMMAND__TYPE_CALL: {
                handle_call(sockfd, cmd->call);
                break;
            }
            case RPC__COMMAND__TYPE_PEEK: {
                handle_peek(sockfd, cmd->peek);
                break;
            }
            case RPC__COMMAND__TYPE_POKE: {
                handle_poke(sockfd, cmd->poke);
                break;
            }
            case RPC__COMMAND__TYPE_DUMMY_BLOCK: {
                handle_get_dummy_block(sockfd, cmd->dummy_block);
                break;
            }
            case RPC__COMMAND__TYPE_LIST_DIR: {
                handle_listdir(sockfd, cmd->list_dir);
                break;
            }
            case RPC__COMMAND__TYPE_SHOW_OBJECT: {
                handle_showobject(sockfd, cmd->show_object);
                break;
            }
            case RPC__COMMAND__TYPE_SHOW_CLASS: {
                handle_showclass(sockfd, cmd->show_class);
                break;
            }
            case RPC__COMMAND__TYPE_CLASS_LIST: {
                handle_get_class_list(sockfd, cmd->class_list);
                break;
            }
            case RPC__COMMAND__TYPE_CLOSE: {     // client requested to close connection
                goto error;
            }
            default: {
                TRACE("unknown cmd: %d", cmd->type_case);
            }
        }
        rpc__command__free_unpacked(cmd, NULL);
    }

    error:
    close(sockfd);
}

void signal_handler(int sig) {
    int status;
    pid_t pid;

    if (SIGCHLD == sig) {
        pid = waitpid(-1, &status, 0);
        TRACE("PID: %d exited with status: %d", pid, status);
        return;
    }

    TRACE("entered with signal code: %d", sig);
}


int main(int argc, const char *argv[]) {
    int opt;
    bool worker_spawn = false;
    char port[MAX_OPTION_LEN] = DEFAULT_PORT;
#ifdef DEBUG
    uint8_t test[10] = {0x41, 0x41, 0x41, 0x41, 0x41, 0x41, 0x41, 0x41, 0x41};
    Rpc__CmdCall cmdcall = RPC__CMD_CALL__INIT;
    cmdcall.address = (uint64_t) printf;
    cmdcall.va_list_index = 1;
    cmdcall.n_argv = 10;
    cmdcall.argv = (Rpc__Argument **) malloc(cmdcall.n_argv * sizeof(Rpc__Argument *));
    for (int i = 0; i < cmdcall.n_argv; i++) {
        cmdcall.argv[i] = (Rpc__Argument *) malloc(cmdcall.n_argv * sizeof(Rpc__Argument));
        cmdcall.argv[i]->type_case = RPC__ARGUMENT__TYPE_V_INT;
        cmdcall.argv[i]->v_int = i;
    }
    printf("Expected:\n");

    cmdcall.argv[0]->type_case = RPC__ARGUMENT__TYPE_V_STR;
    cmdcall.argv[0]->v_str = "printf test %d %d %d %d %d %d %d %d %d %d\n";

    handle_call(1, &cmdcall);
    for (int i = 0; i < cmdcall.n_argv; i++) {
        SAFE_FREE(cmdcall.argv[i]);
    }
    SAFE_FREE(cmdcall.argv);
    exit(0);
#endif

    while ((opt = getopt(argc, (char *const *) argv, "hp:o:w")) != -1) {
        switch (opt) {
            case 'p': {
                strncpy(port, optarg, sizeof(port) - 1);
                break;
            }
            case 'o': {
                if (0 == strcmp(optarg, "stdout")) {
                    g_stdout = true;
                }
                if (0 == strcmp(optarg, "syslog")) {
                    g_syslog = true;
                }
                char *file = strstr(optarg, "file:");
                if (file) {
                    g_file = fopen(file + 5, "wb");
                    if (!g_file) {
                        printf("failed to open %s for writing\n", optarg);
                    }
                }
                break;
            }
            case 'w': {
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

    signal(SIGPIPE, signal_handler);

    if (worker_spawn) {
        TRACE("New worker spawned");
        handle_client(WORKER_CLIENT_SOCKET_FD);
        exit(EXIT_SUCCESS);
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
    CHECK(0 == pthread_create(&runloop_thread, NULL, (void *(*)(void *)) CFRunLoopRun, NULL));
#endif // __APPLE__

    signal(SIGCHLD, signal_handler);

    while (1) {
        struct sockaddr_storage their_addr; // connector's address information
        socklen_t addr_size = sizeof(their_addr);
        int client_fd = accept(server_fd, (struct sockaddr *) &their_addr, &addr_size);
        CHECK(client_fd >= 0);
        CHECK(-1 != fcntl(client_fd, F_SETFD, FD_CLOEXEC));

        char ipstr[INET6_ADDRSTRLEN];
        CHECK(inet_ntop(their_addr.ss_family, get_in_addr((struct sockaddr *) &their_addr), ipstr, sizeof(ipstr)));
        TRACE("Got a connection from %s [%d]", ipstr, client_fd);
#ifdef DEBUG
        handle_client(client_fd);
#else
        CHECK(spawn_worker_server(client_fd, argv, argc));
#endif

    }

    error:
    err = 1;

    clean:
    if (-1 != server_fd) {
        close(server_fd);
    }

    return err;
}
