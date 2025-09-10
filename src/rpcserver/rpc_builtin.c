#include "common.h"

// exported for client hooks
bool get_true() { return true; }

// exported for client hooks
bool get_false() { return false; }

// exported for testing
void test_16args(uint64_t *out, uint64_t arg1, uint64_t arg2, uint64_t arg3, uint64_t arg4, uint64_t arg5,
                 uint64_t arg6, uint64_t arg7, uint64_t arg8, uint64_t arg9, uint64_t arg10, uint64_t arg11,
                 uint64_t arg12, uint64_t arg13, uint64_t arg14, uint64_t arg15, uint64_t arg16) {
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
