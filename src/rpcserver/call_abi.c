#include "common.h"
#include "protos/rpc.pb-c.h"
#include <stddef.h>
#include <stdint.h>
#define CLOBBERD_LIST                                                                                                  \
    "x0", "x1", "x2", "x3", "x4", "x5", "x6", "x7", "x8", "x19", "x20", "x21", "x22", "x23", "x24", "x25", "x26"
#ifdef __ARM_ARCH_ISA_A64

void call_function(intptr_t address, size_t va_list_index, size_t argc, Rpc__Api__Argument **p_argv, Rpc__Api__ReplyCall *resp) {

    arm_args_t args = {0};
    uint64_t regs_backup[GPR_COUNT] = {0};
    uint32_t idx_fp = 0, idx_gp = 0, idx_stack = 0, idx_argv = 0;
    intptr_t *current_target = NULL, *current_arg = NULL;
    for (idx_argv = 0; idx_argv < argc; idx_argv++) {
        switch (p_argv[idx_argv]->type_case) {
        case RPC__API__ARGUMENT__TYPE_V_STR:
        case RPC__API__ARGUMENT__TYPE_V_BYTES:
        case RPC__API__ARGUMENT__TYPE_V_INT:
            // Assign target register if available, otherwise set to `NULL`
            current_target = (idx_gp < MAX_REGS_ARGS) ? (intptr_t *) &args.x[idx_gp++] : NULL;
            break;
        case RPC__API__ARGUMENT__TYPE_V_DOUBLE:
            // Assign target register if available, otherwise set to `NULL`
            current_target = (idx_fp < MAX_REGS_ARGS) ? (intptr_t *) &args.d[idx_fp++] : NULL;
            break;
        default: break;
        }
        // Use the stack if `va_list_index` or if the target register is not
        // available
        if (idx_argv >= va_list_index || !current_target) {
            current_target = (intptr_t *) &args.stack[idx_stack++];
        }
        // `v_int`, `v_str`, and `v_double` all point to the same place, so we use
        // `v_int` for convenience. However, `v_bytes` requires access to
        // `v_bytes.data`.
        current_arg =
            (p_argv[idx_argv]->type_case == RPC__API__ARGUMENT__TYPE_V_BYTES ? (intptr_t *) &p_argv[idx_argv]->v_bytes.data
                                                                        : (intptr_t *) &p_argv[idx_argv]->v_int);
        *current_target = *current_arg;
    }

    __asm__ __volatile__("mov x19, %[address]\n"
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
                         : [regs_backup] "r"(&regs_backup), [args_registers] "r"(&args), [args_stack] "r"(&args.stack),
                           [max_args] "r"((uint64_t) MAX_STACK_ARGS), [address] "r"(address),
                           [result_registers] "r"(&resp->arm_registers->x0)
                         : CLOBBERD_LIST);
}

#else

typedef u64 (*call_argc_t)(u64, u64, u64, u64, u64, u64, u64, u64, u64, u64, u64, u64, u64, u64, u64, u64, u64);

void call_function(intptr_t address, size_t va_list_index, size_t argc, Rpc__Api__Argument **p_argv,
                   Rpc__Api__ReplyCall *response) {
    s64 return_val;
    TRACE("enter");
    call_argc_t call = (call_argc_t) address;
    u64 args[MAX_ARGS] = {0};
    for (size_t i = 0; i < argc; i++) {
        switch (p_argv[i]->type_case) {
        case RPC__API__ARGUMENT__TYPE_V_DOUBLE: args[i] = p_argv[i]->v_double; break;
        case RPC__API__ARGUMENT__TYPE_V_INT: args[i] = p_argv[i]->v_int; break;
        case RPC__API__ARGUMENT__TYPE_V_STR: args[i] = (uint64_t) p_argv[i]->v_str; break;
        case RPC__API__ARGUMENT__TYPE_V_BYTES: args[i] = (uint64_t) p_argv[i]->v_bytes.data; break;
        default: break;
        }
    }
    return_val = call(args[0], args[1], args[2], args[3], args[4], args[5], args[6], args[7], args[8], args[9],
                      args[10], args[11], args[12], args[13], args[14], args[15], args[16]);
    response->return_values_case = RPC__API__REPLY_CALL__RETURN_VALUES_RETURN_VALUE;
    response->return_value = return_val;
}

#endif// __ARM_ARCH_ISA_A64