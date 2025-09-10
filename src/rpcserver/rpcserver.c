#ifndef __APPLE__
#define _XOPEN_SOURCE (600)
#define _GNU_SOURCE (1)
#endif// __APPLE__

#include "common.h"
#include "protos/rpc.pb-c.h"
#include <arpa/inet.h>
#include <dirent.h>
#include <dlfcn.h>
#include <errno.h>
#include <fcntl.h>
#include <netdb.h>
#include <netinet/in.h>
#include <pthread.h>
#include <signal.h>
#include <spawn.h>
#include <stdarg.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/select.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/utsname.h>
#include <sys/wait.h>
#include <termios.h>
#include <unistd.h>

bool handle_showobject(int sockfd, Rpc__CmdShowObject *cmd);

bool handle_showclass(int sockfd, Rpc__CmdShowClass *cmd);

bool handle_get_class_list(int sockfd, Rpc__CmdGetClassList *cmd);

#ifdef __APPLE__

#include <CoreFoundation/CoreFoundation.h>
#include <mach/mach.h>

#else
bool handle_showobject(int sockfd, Rpc__CmdShowObject *cmd) { return 0; }
bool handle_showclass(int sockfd, Rpc__CmdShowClass *cmd) { return 0; }
bool handle_get_class_list(int sockfd, Rpc__CmdGetClassList *cmd) { return 0; }
#endif// __APPLE__

#define DEFAULT_PORT ("5910")
#define USAGE \
    ("Usage: %s [-p port] [-o (stdout|syslog|file:filename)] [-d disable worker] \n\
-h  show this help message \n\
-o  output. can be all of the following: stdout, syslog and file:filename. can be passed multiple times \n\
-d  disable worker. for debugging perpuses, handle clients inprocess instead spawn worker \n\
\n\
Example usage: \n\
%s -p 5910 -o syslog -o stdout -o file:/tmp/log.txt\n")
#define MAX_CONNECTIONS (1024)

#define MAX_OPTION_LEN (256)
#define BUFFERSIZE (64 * 1024)
#define INVALID_PID (0xffffffff)
#define WORKER_CLIENT_SOCKET_FD (3)
#define CLOBBERD_LIST                                                          \
    "x0", "x1", "x2", "x3", "x4", "x5", "x6", "x7", "x8", "x19", "x20", "x21", \
        "x22", "x23", "x24", "x25", "x26"

extern char **environ;

typedef struct {
    int sockfd;
    pid_t pid;
} thread_notify_client_spawn_error_t;

void *get_in_addr(struct sockaddr *sa) // get sockaddr, IPv4 or IPv6:
{
    return sa->sa_family == AF_INET
               ? (void *) &(((struct sockaddr_in *) sa)->sin_addr)
               : (void *) &(((struct sockaddr_in6 *) sa)->sin6_addr);
}

bool internal_spawn(bool background, char **argv, char **envp, pid_t *pid,
                    int *master_fd) {
    bool ret = false;
    int slave_fd = -1;
    *master_fd = -1;
    *pid = INVALID_PID;

    // call setsid() on child so Ctrl-C and all other control characters are set
    // in a different terminal and process group
    posix_spawnattr_t attr;
    CHECK(0 == posix_spawnattr_init(&attr));
    CHECK(0 == posix_spawnattr_setflags(&attr, POSIX_SPAWN_SETSID));

    posix_spawn_file_actions_t actions;
    CHECK(0 == posix_spawn_file_actions_init(&actions));

    if (!background) {
        // We need a new pseudoterminal to avoid bufferring problems. The 'atos'
        // tool in particular detects when it's talking to a pipe and forgets to
        // flush the output stream after sending a response.
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

    ret = true;

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
    bool ret = false;

    // append -w to original argv
    int new_argc = argc + 1;
    const char **new_argv = malloc((new_argc + 1) * sizeof(char *));
    CHECK(new_argv != NULL)
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
    ret = true;

error:
    posix_spawn_file_actions_destroy(&actions);
    free(new_argv);
    close(client_socket);
    return ret;
}

void thread_waitpid(pid_t pid) {
    TRACE("enter");
    s32 err;
    waitpid(pid, &err, 0);
}

bool handle_exec(int sockfd, Rpc__CmdExec *cmd) {
    bool ret = false;
    Rpc__ResponseCmdExec resp_exec = RPC__RESPONSE_CMD_EXEC__INIT;

    pthread_t thread = 0;
    thread_notify_client_spawn_error_t *thread_params = NULL;
    pid_t pid = INVALID_PID;
    int master = -1;
    char **argv = NULL;
    char **envp = NULL;

    CHECK(cmd->n_argv > 0);

    CHECK(copy_arr_with_null(&argv, cmd->argv, cmd->n_argv));
    CHECK(copy_arr_with_null(&envp, cmd->envp, cmd->n_envp));

    CHECK(internal_spawn(cmd->background, argv, cmd->n_envp ? envp : environ, &pid, &master));

    resp_exec.pid = pid;
    CHECK(send_response(sockfd, (ProtobufCMessage *) &resp_exec,RPC__STATUS_CODE__OK));

    if (cmd->background) {
        CHECK(0 == pthread_create(&thread, NULL, (void *(*) (void *) ) thread_waitpid, (void *) (intptr_t) pid));
    } else {
        Rpc__ResponseCmdExecChunk resp_exec_chunk = RPC__RESPONSE_CMD_EXEC_CHUNK__INIT;
        // make sure we have the process fd for its stdout and stderr
        CHECK(master >= 0);
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
                CHECK(send_response(sockfd, (ProtobufCMessage *) &resp_exec_chunk,RPC__STATUS_CODE__OK));
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
#ifndef SINGLE_THREAD
        CHECK(pid == waitpid(pid, &error, 0));
#endif
        resp_exec_chunk.type_case = RPC__RESPONSE_CMD_EXEC_CHUNK__TYPE_EXIT_CODE;
        resp_exec_chunk.exit_code = error;
        CHECK(send_response(sockfd, (ProtobufCMessage *) &resp_exec_chunk,RPC__STATUS_CODE__OK));
    }

    ret = true;

error:
    safe_free((void **) &argv);
    safe_free((void **) &envp);
    safe_free((void **) &thread_params);

    if (INVALID_PID == pid) {
        TRACE("invalid pid");
        // failed to create process somewhere in the prolog, at least notify
        Rpc__ResponseError error = RPC__RESPONSE_ERROR__INIT;
        error.code = RPC__STATUS_CODE__SPAWN_FAILED;
        send_response(sockfd, (ProtobufCMessage *) &error,RPC__STATUS_CODE__SPAWN_FAILED);
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
    Rpc__ResponseDlopen resp_dlopen = RPC__RESPONSE_DLOPEN__INIT;
    resp_dlopen.handle = (uint64_t) dlopen(cmd->filename, cmd->mode);
    return send_response(sockfd, (ProtobufCMessage *) &resp_dlopen,RPC__STATUS_CODE__OK);
}

bool handle_dlclose(int sockfd, Rpc__CmdDlclose *cmd) {
    Rpc__ResponseDlclose resp_dlclose = RPC__RESPONSE_DLCLOSE__INIT;
    resp_dlclose.res = (uint64_t) dlclose((void *) cmd->handle);
    return send_response(sockfd, (ProtobufCMessage *) &resp_dlclose,RPC__STATUS_CODE__OK);
}

bool handle_dlsym(int sockfd, Rpc__CmdDlsym *cmd) {
    Rpc__ResponseDlsym resp_dlsym = RPC__RESPONSE_DLSYM__INIT;
    resp_dlsym.ptr = (uint64_t) dlsym((void *) cmd->handle, cmd->symbol_name);
    TRACE("%s = %p", cmd->symbol_name, resp_dlsym.ptr);
    return send_response(sockfd, (ProtobufCMessage *) &resp_dlsym,RPC__STATUS_CODE__OK);
}

#ifdef __ARM_ARCH_ISA_A64

void call_function(intptr_t address, size_t va_list_index, size_t argc,
                   Rpc__Argument **p_argv, Rpc__ResponseCall *resp) {
    arm_args_t args = {0};
    uint64_t regs_backup[GPR_COUNT] = {0};
    uint32_t idx_fp = 0, idx_gp = 0, idx_stack = 0, idx_argv = 0;
    intptr_t *current_target = NULL, *current_arg = NULL;
    for (idx_argv = 0; idx_argv < argc; idx_argv++) {
        switch (p_argv[idx_argv]->type_case) {
            case RPC__ARGUMENT__TYPE_V_STR:
            case RPC__ARGUMENT__TYPE_V_BYTES:
            case RPC__ARGUMENT__TYPE_V_INT:
                // Assign target register if available, otherwise set to `NULL`
                current_target =
                        (idx_gp < MAX_REGS_ARGS) ? (intptr_t *) &args.x[idx_gp++] : NULL;
                break;
            case RPC__ARGUMENT__TYPE_V_DOUBLE:
                // Assign target register if available, otherwise set to `NULL`
                current_target =
                        (idx_fp < MAX_REGS_ARGS) ? (intptr_t *) &args.d[idx_fp++] : NULL;
                break;
            default:
                break;
        }
        // Use the stack if `va_list_index` or if the target register is not
        // available
        if (idx_argv >= va_list_index || !current_target) {
            current_target = (intptr_t *) &args.stack[idx_stack++];
        }
        // `v_int`, `v_str`, and `v_double` all point to the same place, so we use
        // `v_int` for convenience. However, `v_bytes` requires access to
        // `v_bytes.data`.
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
        "mov x25, #0\n"// counter
        "mov x26, #0\n"// temp stack current_arg

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
        : [regs_backup] "r"(&regs_backup), [args_registers] "r"(&args),
        [args_stack] "r"(&args.stack), [max_args] "r"((uint64_t) MAX_STACK_ARGS),
        [address] "r"(address), [result_registers] "r"(&resp->arm_registers->x0)
        : CLOBBERD_LIST);
}

#else

typedef u64 (*call_argc_t)(u64, u64, u64, u64, u64, u64, u64, u64, u64, u64,
                           u64, u64, u64, u64, u64, u64, u64);

void call_function(intptr_t address, size_t va_list_index, size_t argc,
                   Rpc__Argument **p_argv,
                   Rpc__ResponseCall *response) {
    s64 return_val;
    TRACE("enter");
    call_argc_t call = (call_argc_t) address;
    u64 args[MAX_ARGS] = {0};
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
    return_val = call(args[0], args[1], args[2], args[3], args[4], args[5],
                      args[6], args[7], args[8], args[9], args[10], args[11], args[12], args[13], args[14], args[15],
                      args[16]);
    response->return_values_case = RPC__RESPONSE_CALL__RETURN_VALUES_RETURN_VALUE;
    response->return_value = return_val;
}

#endif// __ARM_ARCH_ISA_A64

bool handle_call(int sockfd, Rpc__CmdCall *cmd) {
    TRACE("enter");
    Rpc__ResponseCall resp_call = RPC__RESPONSE_CALL__INIT;
#ifdef __ARM_ARCH_ISA_A64
    Rpc__ReturnRegistersArm regs = RPC__RETURN_REGISTERS_ARM__INIT;
    resp_call.arm_registers = &regs;
    resp_call.return_values_case = RPC__RESPONSE_CALL__RETURN_VALUES_ARM_REGISTERS;
#else
    resp_call.return_values_case = RPC__RESPONSE_CALL__RETURN_VALUES_RETURN_VALUE;
#endif
    TRACE("address: %p", cmd->address);
    call_function(cmd->address, cmd->va_list_index, cmd->n_argv, cmd->argv,
                  &resp_call);
    return send_response(sockfd, (ProtobufCMessage *) &resp_call,RPC__STATUS_CODE__OK);
}

bool handle_peek(int sockfd, Rpc__CmdPeek *cmd) {
    TRACE("enter");
    uint8_t *buffer = NULL;
    Rpc__ResponsePeek resp_peek = RPC__RESPONSE_PEEK__INIT;
    bool ret = false;

#if defined(SAFE_READ_WRITES) && defined(__APPLE__)
    mach_msg_type_number_t size;
    if (vm_read(mach_task_self(), cmd->address, cmd->size, (vm_offset_t *) &buffer,
                &size)
        == KERN_SUCCESS) {
        resp_peek.data.data = (uint8_t *) buffer;
        resp_peek.data.len = size;
        CHECK(send_response(sockfd, (ProtobufCMessage *) &resp_peek,RPC__STATUS_CODE__OK));
        CHECK(vm_deallocate(mach_task_self(), (vm_address_t) buffer, size) == KERN_SUCCESS);
        buffer = NULL;
        ret = true;
    } else {
        Rpc__ResponseError error = RPC__RESPONSE_ERROR__INIT;
        error.code = RPC__STATUS_CODE__MEMORY_ACCESS;
        CHECK(send_response(sockfd, (ProtobufCMessage *) &error,RPC__STATUS_CODE__MEMORY_ACCESS))
    }
#else // __APPLE__
    resp_peek.data.data = (uint8_t *) cmd->address;
    resp_peek.data.len = cmd->size;
    CHECK(send_response(sockfd, (ProtobufCMessage *) &resp_peek));
#endif// __APPLE__
    ret = true;
error:
    safe_free((void **) &buffer);
    return ret;
}

bool handle_poke(int sockfd, Rpc__CmdPoke *cmd) {
    TRACE("Enter");
    bool ret = false;
    char *data = NULL;
    Rpc__ResponsePoke resp_poke = RPC__RESPONSE_POKE__INIT;

#if defined(SAFE_READ_WRITES) && defined(__APPLE__)
    if (vm_write(mach_task_self(), cmd->address, (vm_offset_t) cmd->data.data, cmd->data.len) == KERN_SUCCESS) {
        CHECK(send_response(sockfd, (ProtobufCMessage *) &resp_poke,RPC__STATUS_CODE__OK));
    } else {
        Rpc__ResponseError error = RPC__RESPONSE_ERROR__INIT;
        error.code = RPC__STATUS_CODE__MEMORY_ACCESS;
        CHECK(send_response(sockfd, (ProtobufCMessage *) &error,RPC__STATUS_CODE__MEMORY_ACCESS));
    }

#else // __APPLE__
    memcpy((uint64_t *) cmd->address, cmd->data.data, cmd->data.len);
    CHECK(send_response(sockfd, (ProtobufCMessage *) &resp_poke));
#endif// __APPLE__
    ret = true;

error:
    safe_free((void **) &data);
    return ret;
}

// exported for client hooks
bool get_true() { return true; }

// exported for client hooks
bool get_false() { return false; }

// exported for testing
void test_16args(uint64_t *out, uint64_t arg1, uint64_t arg2, uint64_t arg3, uint64_t arg4, uint64_t arg5,
                 uint64_t arg6,
                 uint64_t arg7, uint64_t arg8, uint64_t arg9, uint64_t arg10, uint64_t arg11, uint64_t arg12,
                 uint64_t arg13, uint64_t arg14, uint64_t arg15, uint64_t arg16) {
    out[0] = arg1;
    out[1] = arg2;
    out[2] = arg3;
    out[3] = arg4;
    out[4] = arg5;
    out[5] = arg6;
    out[6] = arg7;
    out[7] = arg8;
    out[8] = arg9;
    out[9] = arg10;
    out[10] = arg11;
    out[11] = arg12;
    out[12] = arg13;
    out[13] = arg14;
    out[14] = arg15;
    out[15] = arg16;
}

#if __APPLE__

void (


^
dummy_block
)
(


void
)
=
^
{
};

bool handle_get_dummy_block(int sockfd, Rpc__CmdDummyBlock *cmd) {
    TRACE("enter");
    Rpc__ResponseDummyBlock resp_dummy_block = RPC__RESPONSE_DUMMY_BLOCK__INIT;
    resp_dummy_block.address = (uint64_t) dummy_block;
    resp_dummy_block.size = sizeof(dummy_block);
    return send_response(sockfd, (ProtobufCMessage *) &resp_dummy_block,RPC__STATUS_CODE__OK);
}

#else// !__APPLE__

bool handle_get_dummy_block(int sockfd, Rpc__CmdDummyBlock *cmd) {
    return true;
}

#endif// __APPLE__

bool handle_listdir(int sockfd, Rpc__CmdListDir *cmd) {
    TRACE("enter");
    bool ret = false;
    DIR *dirp = NULL;
    size_t entry_count = 0;
    size_t idx = 0;
    struct dirent *entry = {0};

    Rpc__ResponseListdir resp_list_dir = RPC__RESPONSE_LISTDIR__INIT;
    Rpc__DirEntry *d_entry = NULL;
    Rpc__DirEntryStat *d_stat = NULL, *l_stat = NULL;
    Rpc__ResponseError error = RPC__RESPONSE_ERROR__INIT;

    dirp = opendir(cmd->path);
    if (NULL == dirp) {
        error.code = RPC__STATUS_CODE__FILE_SYSTEM;
        CHECK(send_response(sockfd, (ProtobufCMessage *) &error,RPC__STATUS_CODE__FILE_SYSTEM));
        return true;
    }
    for (entry = readdir(dirp); entry != NULL; entry = readdir(dirp)) {
        entry_count++;
    }
    CHECK(0 == closedir(dirp));

    dirp = opendir(cmd->path);
    CHECK(dirp != NULL);

    resp_list_dir.magic = RPC__PROTOCOL_CONSTANTS__MESSAGE_MAGIC;
    resp_list_dir.dirp = (uint64_t) dirp;
    resp_list_dir.n_dir_entries = entry_count;
    resp_list_dir.dir_entries =
            (Rpc__DirEntry **) malloc(sizeof(Rpc__DirEntry *) * entry_count);
    CHECK(resp_list_dir.dir_entries != NULL);

    while ((entry = readdir(dirp)) != NULL && entry_count > idx) {
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

        // Init l_stat
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
    CHECK(send_response(sockfd, (ProtobufCMessage *) &resp_list_dir,RPC__STATUS_CODE__OK));
    ret = true;

error:
    if (dirp) {
        closedir(dirp);
    }

    for (uint64_t i = 0; i < entry_count; i++) {
        safe_free((void **) &resp_list_dir.dir_entries[i]->d_name);
        safe_free((void **) &resp_list_dir.dir_entries[i]->stat);
        safe_free((void **) &resp_list_dir.dir_entries[i]->lstat);
        safe_free((void **) &resp_list_dir.dir_entries[i]);
    }
    safe_free((void **) &resp_list_dir.dir_entries);
    TRACE("exit");

    return ret;
}

void handle_client(int sockfd) {
    TRACE("enter. fd: %d", sockfd);

    struct utsname uname_buf;
    uint8_t buffer[BUFFERSIZE] = {0};
    size_t message_size;

    CHECK(0 == uname(&uname_buf));
    Rpc__Handshake handshake = RPC__HANDSHAKE__INIT;
    handshake.magic = RPC__PROTOCOL_CONSTANTS__SERVER_VERSION;
    handshake.arch = RPC__ARCH__ARCH_UNKNOWN;
    handshake.sysname = uname_buf.sysname;
    handshake.machine = uname_buf.machine;
    handshake.client_id = getpid();
    handshake.platform = PLATFORM;

    CHECK(-1 != fcntl(sockfd, F_SETFD, FD_CLOEXEC));

#ifdef __ARM_ARCH_ISA_A64
    handshake.arch = RPC__ARCH__ARCH_ARM64;
#endif
    message_size = rpc__handshake__pack(&handshake, buffer);
    CHECK(0 != message_size);
    CHECK(send_message(sockfd, (const uint8_t *) &buffer, message_size));

    while (true) {
        Rpc__Command *request;
        char *recv_buff = NULL;
        message_size = 0;
        CHECK(receive_message(sockfd, &recv_buff, &message_size))

        TRACE("recv");
        request = rpc__command__unpack(NULL, message_size, (uint8_t *) recv_buff);
        CHECK(request != NULL);
        TRACE("client fd: %d, client_id %d, cmd id: %d", sockfd, request->client_id, request->cmd_id);
        CHECK(request->magic == RPC__PROTOCOL_CONSTANTS__MESSAGE_MAGIC);
        switch (request->cmd_id) {
            case RPC__COMMAND_ID__CMD_EXEC: {
                Rpc__CmdExec *cmd = rpc__cmd_exec__unpack(NULL, request->payload.len, request->payload.data);
                CHECK(handle_exec(sockfd, cmd));
                break;
            }
            case RPC__COMMAND_ID__CMD_DLOPEN: {
                Rpc__CmdDlopen *cmd = rpc__cmd_dlopen__unpack(NULL, request->payload.len, request->payload.data);
                CHECK(handle_dlopen(sockfd, cmd));
                break;
            }
            case RPC__COMMAND_ID__CMD_DLSYM: {
                Rpc__CmdDlsym *cmd = rpc__cmd_dlsym__unpack(NULL, request->payload.len, request->payload.data);
                CHECK(handle_dlsym(sockfd, cmd));
                break;
            }
            case RPC__COMMAND_ID__CMD_DLCLOSE: {
                Rpc__CmdDlclose *cmd = rpc__cmd_dlclose__unpack(NULL, request->payload.len, request->payload.data);
                CHECK(handle_dlclose(sockfd, cmd));
                break;
            }
            case RPC__COMMAND_ID__CMD_CALL: {
                Rpc__CmdCall *cmd = rpc__cmd_call__unpack(NULL, request->payload.len, request->payload.data);
                CHECK(handle_call(sockfd, cmd));
                break;
            }
            case RPC__COMMAND_ID__CMD_PEEK: {
                Rpc__CmdPeek *cmd = rpc__cmd_peek__unpack(NULL, request->payload.len, request->payload.data);
                CHECK(handle_peek(sockfd, cmd));
                break;
            }
            case RPC__COMMAND_ID__CMD_POKE: {
                Rpc__CmdPoke *cmd = rpc__cmd_poke__unpack(NULL, request->payload.len, request->payload.data);
                CHECK(handle_poke(sockfd, cmd));
                break;
            }
            case RPC__COMMAND_ID__CMD_DUMMY_BLOCK: {
                Rpc__CmdDummyBlock *cmd = rpc__cmd_dummy_block__unpack(NULL, request->payload.len, request->payload.data);
                CHECK(handle_get_dummy_block(sockfd, cmd));
                break;
            }
            case RPC__COMMAND_ID__CMD_LIST_DIR: {
                Rpc__CmdListDir *cmd = rpc__cmd_list_dir__unpack(NULL, request->payload.len, request->payload.data);
                CHECK(handle_listdir(sockfd, cmd));
                break;
            }
            case RPC__COMMAND_ID__CMD_SHOW_OBJECT: {
                Rpc__CmdShowObject *cmd = rpc__cmd_show_object__unpack(NULL, request->payload.len, request->payload.data);
                CHECK(handle_showobject(sockfd, cmd));
                break;
            }
            case RPC__COMMAND_ID__CMD_SHOW_CLASS: {
                Rpc__CmdShowClass *cmd = rpc__cmd_show_class__unpack(NULL, request->payload.len, request->payload.data);
                CHECK(handle_showclass(sockfd, cmd));
                break;
            }
            case RPC__COMMAND_ID__CMD_GET_CLASS_LIST: {
                Rpc__CmdGetClassList *cmd = rpc__cmd_get_class_list__unpack(NULL, request->payload.len, request->payload.data);
                CHECK(handle_get_class_list(sockfd, cmd));
                break;
            }
            case RPC__COMMAND_ID__CMD_CLOSE: {
                // client requested to close connection
                goto error;
            }
            default: {
                TRACE("unknown cmd: %d", request->cmd_id);
                Rpc__ResponseError error = RPC__RESPONSE_ERROR__INIT;
                error.code = RPC__STATUS_CODE__UNSUPPORTED_COMMAND;
                CHECK(send_response(sockfd, (ProtobufCMessage *) &error,RPC__STATUS_CODE__UNSUPPORTED_COMMAND));
            }
        }
        rpc__command__free_unpacked(request, NULL);
        safe_free((void **) &recv_buff);
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
    bool disable_worker = false;
    char port[MAX_OPTION_LEN] = DEFAULT_PORT;

    while ((opt = getopt(argc, (char *const *) argv, "hwdo:p:")) != -1) {
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
            case 'd': {
                disable_worker = true;
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
    hints.ai_family = AF_INET6;

    struct addrinfo *servinfo;
    CHECK(0 == getaddrinfo(NULL, port, &hints, &servinfo));

    struct addrinfo *servinfo2 = servinfo; // servinfo->ai_next;
    char ipstr[INET6_ADDRSTRLEN];
    CHECK(inet_ntop(servinfo2->ai_family, get_in_addr(servinfo2->ai_addr), ipstr,
        sizeof(ipstr)));
    TRACE("Waiting for connections on [%s]:%s", ipstr, port);

    server_fd = socket(servinfo2->ai_family, servinfo2->ai_socktype,
                       servinfo2->ai_protocol);
    CHECK(server_fd >= 0);
    CHECK(-1 != fcntl(server_fd, F_SETFD, FD_CLOEXEC));

    int yes_1 = 1;
    CHECK(0 == setsockopt(server_fd, SOL_SOCKET, SO_REUSEADDR, &yes_1, sizeof(yes_1)));
    CHECK(0 == bind(server_fd, servinfo2->ai_addr, servinfo2->ai_addrlen));

    freeaddrinfo(servinfo);

    CHECK(0 == listen(server_fd, MAX_CONNECTIONS));

#ifdef __APPLE__
    pthread_t runloop_thread;
    CHECK(0 == pthread_create(&runloop_thread, NULL, (void *(*) (void *) ) CFRunLoopRun, NULL));
#endif// __APPLE__

    signal(SIGCHLD, signal_handler);

    while (1) {
        struct sockaddr_storage their_addr; // connector's address information
        socklen_t addr_size = sizeof(their_addr);
        int client_fd =
                accept(server_fd, (struct sockaddr *) &their_addr, &addr_size);
        CHECK(client_fd >= 0);
        CHECK(-1 != fcntl(client_fd, F_SETFD, FD_CLOEXEC));

        char ipstr[INET6_ADDRSTRLEN];
        CHECK(inet_ntop(their_addr.ss_family,
            get_in_addr((struct sockaddr *) &their_addr), ipstr,
            sizeof(ipstr)));
        TRACE("Got a connection from %s [%d]", ipstr, client_fd);
        if (disable_worker) {
            TRACE("Direct mode: handling client without spawning worker");
            handle_client(client_fd);
        } else {
            CHECK(spawn_worker_server(client_fd, argv, argc));
        }
    }

error:
    err = 1;

clean:
    if (-1 != server_fd) {
        close(server_fd);
    }

    return err;
}
