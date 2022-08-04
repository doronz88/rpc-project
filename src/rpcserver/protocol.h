#ifndef __PROTOCOL_H_
#define __PROTOCOL_H_
#include <sys/types.h>

#include "common.h"

#define SERVER_MAGIC_VERSION (0x88888805)
#define HANDSHAKE_SYSNAME_LEN (256)
#define MAX_PATH_LEN (1024)

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
    CMD_LISTDIR = 12,
    CMD_SHOWOBJECT = 13,
    CMD_SHOWCLASS = 14
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
    u64 va_list_index;
    u64 argc;
    argument_t argv[0];
} cmd_call_t;

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
    char filename[MAX_PATH_LEN];
} cmd_listdir_t;

typedef struct
{
    u64 errno1;
    u64 st_dev;     /* [XSI] ID of device containing file */
    u64 st_mode;    /* [XSI] Mode of file (see below) */
    u64 st_nlink;   /* [XSI] Number of hard links */
    u64 st_ino;     /* [XSI] File serial number */
    u64 st_uid;     /* [XSI] User ID of the file */
    u64 st_gid;     /* [XSI] Group ID of the file */
    u64 st_rdev;    /* [XSI] Device ID */
    u64 st_size;    /* [XSI] file size, in bytes */
    u64 st_blocks;  /* [XSI] blocks allocated for file */
    u64 st_blksize; /* [XSI] optimal blocksize for I/O */
    u64 st_atime1;  /* time of last access */
    u64 st_mtime1;  /* time of last data modification */
    u64 st_ctime1;  /* time of last file status change */
} listdir_entry_stat_t;

typedef struct
{
    u64 magic;
    u64 type;
    u64 namelen;

    listdir_entry_stat_t lstat;
    listdir_entry_stat_t stat;

    char name[0];
} listdir_entry_t;

typedef struct
{
    uint64_t address;
} cmd_showobject_t;

typedef struct
{
    uint64_t address;
} cmd_showclass_t;

#endif // __PROTOCOL_H_