from construct import PaddedString, Struct, Int32ul, Int16ul, Int64ul, Int8ul, this, Int32sl, Padding, Array, Int64sl, \
    Bytes, Computed, FlagsEnum

from pyzshell.structs.generic import uid_t, gid_t, long, mode_t

MAXPATHLEN = 1024
_SYS_NAMELEN = 256

utsname = Struct(
    'sysname' / PaddedString(_SYS_NAMELEN, 'utf8'),
    'nodename' / PaddedString(_SYS_NAMELEN, 'utf8'),
    'release' / PaddedString(_SYS_NAMELEN, 'utf8'),
    'version' / PaddedString(_SYS_NAMELEN, 'utf8'),
    'machine' / PaddedString(_SYS_NAMELEN, 'utf8'),
)

pid_t = Int32ul
exitcode_t = Int32sl
ino_t = Int32ul
dev_t = Int32ul
off_t = Int32ul
nlink_t = Int16ul
blkcnt_t = Int32ul
blksize_t = Int32ul
ino64_t = Int64ul
fsid_t = Int64ul

timespec = Struct(
    'tv_sec' / long,
    'tv_nsec' / long,
)
dirent32 = Struct(
    'd_ino' / ino_t,
    'd_offset' / Int16ul,
    'd_reclen' / Int8ul,
    'd_namelen' / Int8ul,
    'd_name' / PaddedString(this.d_namelen, 'utf8'),
)
dirent64 = Struct(
    'd_ino' / ino64_t,
    'd_offset' / Int64ul,
    'd_reclen' / Int16ul,
    'd_namelen' / Int16ul,
    'd_type' / Int8ul,
    'd_name' / PaddedString(this.d_namelen, 'utf8'),
)
stat32 = Struct(
    'st_dev' / dev_t,  # device inode resides on
    'st_ino' / ino_t,  # inode's number
    'st_mode' / mode_t,  # inode protection mode
    'st_nlink' / nlink_t,  # number of hard links to the file
    'st_uid' / uid_t,  # user-id of owner
    'st_gid' / gid_t,  # group-id of owner
    'st_rdev' / dev_t,  # device type, for special file inode

    'st_atimespec' / timespec,  # time of last access
    'st_mtimespec' / timespec,  # time of last data modification
    'st_ctimespec' / timespec,  # time of last file status change

    'st_blksize' / Int32sl,  # optimal blocksize for I/O
    'st_blocks' / Int32sl,  # blocks allocated for file
    'st_flags' / Int32ul,  # blocks allocated for file
    'st_gen' / Int32ul,  # user defined flags for file
)
stat64 = Struct(
    'st_dev' / dev_t,  # device inode resides on
    'st_mode' / mode_t,  # inode protection mode
    'st_nlink' / nlink_t,  # number of hard links to the file
    'st_ino' / ino64_t,  # inode's number
    'st_uid' / uid_t,  # user-id of owner
    'st_gid' / gid_t,  # group-id of owner
    'st_rdev' / dev_t,  # device type, for special file inode
    Padding(4),

    'st_atimespec' / timespec,  # time of last access
    'st_mtimespec' / timespec,  # time of last data modification
    'st_ctimespec' / timespec,  # time of last file status change
    'st_birthtimespec' / timespec,  # time of file creation(birth)

    'st_size' / off_t,
    'st_blocks' / blkcnt_t,  # blocks allocated for file
    'st_blksize' / blksize_t,  # optimal blocksize for I/O
    'st_flags' / Int32ul,  # blocks allocated for file
    'st_gen' / Int32ul,  # user defined flags for file
    'st_lspare' / Int32ul,
    'st_qspare' / Array(2, Int64sl),
)

PROC_ALL_PIDS = 1

# Flavors for proc_pidinfo()
PROC_PIDLISTFDS = 1
PROC_PIDTASKALLINFO = 2
PROC_PIDTBSDINFO = 3
PROC_PIDTASKINFO = 4
PROC_PIDTHREADINFO = 5
PROC_PIDLISTTHREADS = 6
PROC_PIDREGIONINFO = 7
PROC_PIDREGIONPATHINFO = 8
PROC_PIDVNODEPATHINFO = 9
PROC_PIDTHREADPATHINFO = 10
PROC_PIDPATHINFO = 11
PROC_PIDWORKQUEUEINFO = 12
PROC_PIDT_SHORTBSDINFO = 13
PROC_PIDLISTFILEPORTS = 14
PROC_PIDTHREADID64INFO = 15
PROC_PID_RUSAGE = 16
PROC_PIDUNIQIDENTIFIERINFO = 17
PROC_PIDT_BSDINFOWITHUNIQID = 18
PROC_PIDARCHINFO = 19
PROC_PIDCOALITIONINFO = 20
PROC_PIDNOTEEXIT = 21
PROC_PIDREGIONPATHINFO2 = 22
PROC_PIDREGIONPATHINFO3 = 23

# Flavors for proc_pidfdinfo
PROC_PIDFDVNODEINFO = 1
PROC_PIDFDVNODEPATHINFO = 2
PROC_PIDFDSOCKETINFO = 3
PROC_PIDFDPSEMINFO = 4
PROC_PIDFDPSHMINFO = 5
PROC_PIDFDPIPEINFO = 6
PROC_PIDFDKQUEUEINFO = 7
PROC_PIDFDATALKINFO = 8

# Flavors for proc_pidfileportinfo
PROC_PIDFILEPORTVNODEPATHINFO = 2  # out: vnode_fdinfowithpath
PROC_PIDFILEPORTPSHMINFO = 5  # out: pshm_fdinfo
PROC_PIDFILEPORTPIPEINFO = 6  # out: pipe_fdinfo
# used for proc_setcontrol
PROC_SELFSET_PCONTROL = 1
PROC_SELFSET_THREADNAME = 2
PROC_SELFSET_VMRSRCOWNER = 3
PROC_SELFSET_DELAYIDLESLEEP = 4
# used for proc_dirtycontrol
PROC_DIRTYCONTROL_TRACK = 1
PROC_DIRTYCONTROL_SET = 2
PROC_DIRTYCONTROL_GET = 3
PROC_DIRTYCONTROL_CLEAR = 4
# proc_track_dirty() flags
PROC_DIRTY_TRACK = 0x1
PROC_DIRTY_ALLOW_IDLE_EXIT = 0x2
PROC_DIRTY_DEFER = 0x4
PROC_DIRTY_LAUNCH_IN_PROGRESS = 0x8
# proc_get_dirty() flags
PROC_DIRTY_TRACKED = 0x1
PROC_DIRTY_ALLOWS_IDLE_EXIT = 0x2
PROC_DIRTY_IS_DIRTY = 0x4
PROC_DIRTY_LAUNCH_IS_IN_PROGRESS = 0x8

# Flavors for proc_pidoriginatorinfo
PROC_PIDORIGINATOR_UUID = 0x1
PROC_PIDORIGINATOR_BGSTATE = 0x2
# __proc_info() call numbers
PROC_INFO_CALL_LISTPIDS = 0x1
PROC_INFO_CALL_PIDINFO = 0x2
PROC_INFO_CALL_PIDFDINFO = 0x3
PROC_INFO_CALL_KERNMSGBUF = 0x4
PROC_INFO_CALL_SETCONTROL = 0x5
PROC_INFO_CALL_PIDFILEPORTINFO = 0x6
PROC_INFO_CALL_TERMINATE = 0x7
PROC_INFO_CALL_DIRTYCONTROL = 0x8
PROC_INFO_CALL_PIDRUSAGE = 0x9
PROC_INFO_CALL_PIDORIGINATORINFO = 0xa

# defns of process file desc type
PROX_FDTYPE_ATALK = 0
PROX_FDTYPE_VNODE = 1
PROX_FDTYPE_SOCKET = 2
PROX_FDTYPE_PSHM = 3
PROX_FDTYPE_PSEM = 4
PROX_FDTYPE_KQUEUE = 5
PROX_FDTYPE_PIPE = 6
PROX_FDTYPE_FSEVENTS = 7

pbi_flags_t = FlagsEnum(Int32ul,
                        # pbi_flags values
                        PROC_FLAG_SYSTEM=1,  # System process
                        PROC_FLAG_TRACED=2,  # process currently being traced, possibly by gdb
                        PROC_FLAG_INEXIT=4,  # process is working its way in exit()
                        PROC_FLAG_PPWAIT=8,
                        PROC_FLAG_LP64=0x10,  # 64bit process
                        PROC_FLAG_SLEADER=0x20,  # The process is the session leader
                        PROC_FLAG_CTTY=0x40,  # process has a control tty
                        PROC_FLAG_CONTROLT=0x80,  # Has a controlling terminal
                        PROC_FLAG_THCWD=0x100,  # process has a thread with cwd
                        # process control bits for resource starvation
                        PROC_FLAG_PC_THROTTLE=0x200,
                        # In resource starvation situations, this process is to be throttled
                        PROC_FLAG_PC_SUSP=0x400,  # In resource starvation situations, this process is to be suspended
                        PROC_FLAG_PC_KILL=0x600,  # In resource starvation situations, this process is to be terminated
                        PROC_FLAG_PC_MASK=0x600,
                        # process action bits for resource starvation
                        PROC_FLAG_PA_THROTTLE=0x800,  # The process is currently throttled due to resource starvation
                        PROC_FLAG_PA_SUSP=0x1000,  # The process is currently suspended due to resource starvation
                        PROC_FLAG_PSUGID=0x2000,  # process has set privileges since last exec
                        PROC_FLAG_EXEC=0x4000,  # process has called exec
                        PROC_FLAG_DARWINBG=0x8000,  # process in darwin background
                        PROC_FLAG_EXT_DARWINBG=0x10000,  # process in darwin background - external enforcement
                        PROC_FLAG_IOS_APPLEDAEMON=0x20000,  # Process is apple daemon
                        PROC_FLAG_DELAYIDLESLEEP=0x40000,  # Process is marked to delay idle sleep on disk IO
                        PROC_FLAG_IOS_IMPPROMOTION=0x80000,  # Process is daemon which receives importane donation
                        PROC_FLAG_ADAPTIVE=0x100000,  # Process is adaptive
                        PROC_FLAG_ADAPTIVE_IMPORTANT=0x200000,  # Process is adaptive, and is currently important
                        PROC_FLAG_IMPORTANCE_DONOR=0x400000,  # Process is marked as an importance donor
                        PROC_FLAG_SUPPRESSED=0x800000,  # Process is suppressed
                        PROC_FLAG_APPLICATION=0x1000000,  # Process is an application
                        PROC_FLAG_IOS_APPLICATION=0x1000000,  # Process is an application
                        )

MAXCOMLEN = 16

proc_bsdinfo = Struct(
    'pbi_flags' / pbi_flags_t,  # 64bit emulated etc
    'pbi_status' / Int32ul,
    'pbi_xstatus' / Int32ul,
    'pbi_pid' / Int32ul,
    'pbi_ppid' / Int32ul,
    'pbi_uid' / uid_t,
    'pbi_gid' / gid_t,
    'pbi_ruid' / uid_t,
    'pbi_rgid' / gid_t,
    'pbi_svuid' / uid_t,
    'pbi_svgid' / gid_t,
    'rfu_1' / Int32ul,  # reserved
    '_pbi_comm' / Bytes(MAXCOMLEN),
    'pbi_comm' / Computed(lambda x: x._pbi_comm.split(b'\x00', 1)[0].decode()),
    '_pbi_name' / Bytes(2 * MAXCOMLEN),  # empty if no name is registered
    'pbi_name' / Computed(lambda x: x._pbi_name.split(b'\x00', 1)[0].decode()),
    'pbi_nfiles' / Int32ul,
    'pbi_pgid' / Int32ul,
    'pbi_pjobc' / Int32ul,
    'e_tdev' / Int32ul,  # controlling tty dev
    'e_tpgid' / Int32ul,  # tty process group id
    'pbi_nice' / Int32sl,
    'pbi_start_tvsec' / Int64ul,
    'pbi_start_tvusec' / Int64ul,
)

proc_taskinfo = Struct(
    'pti_virtual_size' / Int64ul,  # virtual memory size (bytes)
    'pti_resident_size' / Int64ul,  # resident memory size (bytes)
    'pti_total_user' / Int64ul,  # total time
    'pti_total_system' / Int64ul,
    'pti_threads_user' / Int64ul,  # existing threads only
    'pti_threads_system' / Int64ul,
    'pti_policy' / Int32sl,  # default policy for new threads
    'pti_faults' / Int32sl,  # number of page faults
    'pti_pageins' / Int32sl,  # number of actual pageins
    'pti_cow_faults' / Int32sl,  # number of copy-on-write faults
    'pti_messages_sent' / Int32sl,  # number of messages sent
    'pti_messages_received' / Int32sl,  # number of messages received
    'pti_syscalls_mach' / Int32sl,  # number of mach system calls
    'pti_syscalls_unix' / Int32sl,  # number of unix system calls
    'pti_csw' / Int32sl,  # number of context switches
    'pti_threadnum' / Int32sl,  # number of threads in the task
    'pti_numrunning' / Int32sl,  # number of running threads
    'pti_priority' / Int32sl,  # task priority
)

proc_taskallinfo = Struct(
    'pbsd' / proc_bsdinfo,
    'ptinfo' / proc_taskinfo,
)

proc_regioninfo = Struct(
    'pri_protection' / Int32ul,
    'pri_max_protection' / Int32ul,
    'pri_inheritance' / Int32ul,
    'pri_flags' / Int32ul,  # shared, external pager, is submap
    'pri_offset' / Int64ul,
    'pri_behavior' / Int32ul,
    'pri_user_wired_count' / Int32ul,
    'pri_user_tag' / Int32ul,
    'pri_pages_resident' / Int32ul,
    'pri_pages_shared_now_private' / Int32ul,
    'pri_pages_swapped_out' / Int32ul,
    'pri_pages_dirtied' / Int32ul,
    'pri_ref_count' / Int32ul,
    'pri_shadow_depth' / Int32ul,
    'pri_share_mode' / Int32ul,
    'pri_private_pages_resident' / Int32ul,
    'pri_shared_pages_resident' / Int32ul,
    'pri_obj_id' / Int32ul,
    'pri_depth' / Int32ul,
    'pri_address' / Int64ul,
    'pri_size' / Int64ul,
)

proc_fdinfo = Struct(
    'proc_fd' / Int32sl,
    'proc_fdtype' / Int32ul,
)

proc_fileinfo = Struct(
    'fi_openflags' / Int32ul,
    'fi_status' / Int32ul,
    'fi_offset' / off_t,
    'fi_guardflags' / Int32ul,
)

# A copy of stat64 with static sized fields.
vinfo_stat = stat64

vnode_info = Struct(
    'vi_stat' / vinfo_stat,
    'vi_type' / Int32sl,
    'vi_pad' / Int32sl,
    'vi_fsid' / fsid_t,
)

vnode_info_path = Struct(
    'vip_vi' / vnode_info,
    Padding(8),
    '_vip_path' / Bytes(MAXPATHLEN),
    'vip_path' / Computed(lambda x: x._vip_path.split(b'\x00', 1)[0].decode()),
)

vnode_fdinfowithpath = Struct(
    'pfi' / proc_fileinfo,
    'pvip' / vnode_info_path,
)
