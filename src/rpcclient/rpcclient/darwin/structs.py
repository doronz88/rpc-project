from construct import Adapter, Aligned, Array, BitsInteger, BitStruct, Bytes, Computed, CString, Default, Enum, \
    FlagsEnum, GreedyRange, Hex, Int8ul, Int16sl, Int16ub, Int16ul, Int32sl, Int32ub, Int32ul, Int64sl, Int64ul, \
    LazyArray, Octet, PaddedString, Padding, Seek, Struct, Switch, Tell, Union, this

from rpcclient.structs.consts import AF_INET, AF_INET6, AF_UNIX
from rpcclient.structs.generic import UNIX_PATH_MAX, gid_t, in_addr, long, mode_t, short, st_flags, time_t, u_char, \
    u_int32_t, u_short, uid_t, uint8_t, uint32_t, uint64_t

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
off_t = Int64ul
nlink_t = Int16ul
blkcnt_t = Int64ul
blksize_t = Int32ul
ino64_t = Int64ul
fsid_t = Array(2, Int32sl)
mach_port_t = Int64ul
io_name_t = PaddedString(1024, 'utf8')
io_object_t = Int64ul
vm_prot_t = Int32ul
vm_inherit_t = Int32ul
boolean_t = Int32ul
memory_object_offset_t = Int64ul
vm_behavior_t = Int32ul
mach_vm_address_t = Int64ul
mach_vm_size_t = Int64ul
integer_t = Int32sl

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
    'st_atime' / Computed(this.st_atimespec.tv_sec + (this.st_atimespec.tv_nsec / 10 ** 9)),
    'st_mtimespec' / timespec,  # time of last data modification
    'st_mtime' / Computed(this.st_mtimespec.tv_sec + (this.st_mtimespec.tv_nsec / 10 ** 9)),
    'st_ctimespec' / timespec,  # time of last file status change
    'st_ctime' / Computed(this.st_ctimespec.tv_sec + (this.st_ctimespec.tv_nsec / 10 ** 9)),
    'st_size' / off_t,  # file size, in bytes
    'st_blocks' / blkcnt_t,  # blocks allocated for file
    'st_blksize' / blksize_t,  # optimal blocksize for I/O
    'st_flags' / Int32ul,  # user defined flags for file
    'st_gen' / Int32ul,
    'st_lspare' / Int32sl,
    'st_qspare' / Array(2, Int64sl),
    Padding(24),  # Compiled size is 144
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
    'st_atime' / Computed(this.st_atimespec.tv_sec + (this.st_atimespec.tv_nsec / 10 ** 9)),
    'st_mtimespec' / timespec,  # time of last data modification
    'st_mtime' / Computed(this.st_mtimespec.tv_sec + (this.st_mtimespec.tv_nsec / 10 ** 9)),
    'st_ctimespec' / timespec,  # time of last file status change
    'st_ctime' / Computed(this.st_ctimespec.tv_sec + (this.st_ctimespec.tv_nsec / 10 ** 9)),
    'st_birthtimespec' / timespec,  # time of file creation(birth)
    'st_btime' / Computed(this.st_birthtimespec.tv_sec + (this.st_birthtimespec.tv_nsec / 10 ** 9)),

    'st_size' / off_t,
    'st_blocks' / blkcnt_t,  # blocks allocated for file
    'st_blksize' / blksize_t,  # optimal blocksize for I/O
    'st_flags' / st_flags,  # blocks allocated for file
    'st_gen' / Int32ul,  # user defined flags for file
    # seems like this value doesn't really exist
    # 'st_lspare' / Int32ul,
    'st_qspare' / Array(2, Int64sl),
)

MFSNAMELEN = 15  # length of fs type name, not inc. nul
MNAMELEN = 90  # length of buffer for returned name

# when _DARWIN_FEATURE_64_BIT_INODE is NOT defined
statfs64 = Struct(
    'f_otype' / Int16sl,  # type of file system (reserved: zero)
    'f_oflags' / Int16sl,  # copy of mount flags (reserved: zero)
    Padding(4),
    'f_bsize' / Int64ul,  # fundamental file system block size
    'f_iosize' / Int64ul,  # optimal transfer block size
    'f_blocks' / Int64ul,  # total data blocks in file system
    'f_bfree' / Int64ul,  # free blocks in fs
    'f_bavail' / Int64ul,  # free blocks avail to non-superuser
    'f_files' / Int64ul,  # total file nodes in file system
    'f_ffree' / Int64ul,  # free file nodes in fs
    'f_fsid' / fsid_t,  # file system id
    'f_owner' / uid_t,  # user that mounted the file system
    Padding(4),
    'f_reserved1' / Int16sl,  # reserved for future use
    'f_type' / Int16sl,  # type of file system (reserved)
    Padding(4),
    'f_flags' / Int64ul,  # copy of mount flags
    'f_reserved2' / Int64ul,  # reserved for future use
    'f_fstypename' / PaddedString(MFSNAMELEN, 'utf8'),  # fs type name
    'f_mntonname' / PaddedString(MNAMELEN, 'utf8'),  # directory on which mounted
    'f_mntfromname' / PaddedString(MNAMELEN, 'utf8'),  # mounted file system
    'f_reserved3' / Int8ul,  # reserved for future use
    'f_reserved4' / Int64ul,  # reserved for future use
)

MFSTYPENAMELEN = 16  # length of fs type name including null
MNAMELEN = MAXPATHLEN

# when _DARWIN_FEATURE_64_BIT_INODE is defined
statfs32 = Struct(
    'f_bsize' / Int32ul,  # fundamental file system block size
    'f_iosize' / Int32sl,  # optimal transfer block size
    'f_blocks' / Int64ul,  # total data blocks in file system
    'f_bfree' / Int64ul,  # free blocks in fs
    'f_bavail' / Int64ul,  # free blocks avail to non-superuser
    'f_files' / Int64ul,  # total file nodes in file system
    'f_ffree' / Int64ul,  # free file nodes in fs
    'f_fsid' / fsid_t,  # file system id
    'f_owner' / uid_t,  # user that mounted the filesystem
    'f_type' / Int32ul,  # type of filesystem
    'f_flags' / Int32ul,  # copy of mount exported flags
    'f_fssubtype' / Int32ul,  # fs sub-type (flavor)
    'f_fstypename' / PaddedString(MFSTYPENAMELEN, 'utf8'),  # fs type name
    'f_mntonname' / PaddedString(MAXPATHLEN, 'utf8'),  # directory on which mounted
    'f_mntfromname' / PaddedString(MAXPATHLEN, 'utf8'),  # mounted filesystem
    'f_reserved' / Int32ul[8],  # For future use
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
    '_vip_path' / Bytes(MAXPATHLEN),
    'vip_path' / Computed(lambda x: x._vip_path.split(b'\x00', 1)[0].decode()),
)

vnode_fdinfowithpath = Struct(
    'pfi' / proc_fileinfo,
    'pvip' / vnode_info_path,
)

sockbuf_info = Struct(
    'sbi_cc' / uint32_t,
    'sbi_hiwat' / uint32_t,  # SO_RCVBUF, SO_SNDBUF
    'sbi_mbcnt' / uint32_t,
    'sbi_mbmax' / uint32_t,
    'sbi_lowat' / uint32_t,
    'sbi_flags' / short,
    'sbi_timeo' / short,
)

# TCP Sockets

TSI_T_REXMT = 0  # retransmit
TSI_T_PERSIST = 1  # retransmit persistence
TSI_T_KEEP = 2  # keep alive
TSI_T_2MSL = 3  # 2*msl quiet time timer
TSI_T_NTIMERS = 4


class IpAddressAdapter(Adapter):
    def _decode(self, obj, context, path):
        return ".".join(map(str, obj))

    def _encode(self, obj, context, path):
        return list(map(int, obj.split(".")))


in4in6_addr = Struct(
    'i46a_pad32' / u_int32_t[3],
    'i46a_addr4' / IpAddressAdapter(in_addr),
)

in6_addr = Struct(
    'i46a_pad32' / u_int32_t[3],
    'i46a_addr4' / IpAddressAdapter(in_addr),
)

in_sockinfo = Struct(
    'insi_fport' / Int16ub,
    Padding(2),
    'insi_lport' / Int16ub,
    Padding(2),
    'insi_gencnt' / uint64_t,
    'insi_flags' / uint32_t,
    'insi_flow' / uint32_t,
    'insi_vflag' / uint8_t,
    'insi_ip_ttl' / uint8_t,
    Padding(2),
    'rfu_1' / uint32_t,

    # protocol dependent part
    'insi_faddr' / Union(None,
                         'ina_46' / in4in6_addr,
                         'ina_6' / in6_addr),

    'insi_laddr' / Union(None,
                         'ina_46' / in4in6_addr,
                         'ina_6' / in6_addr),

    'insi_v4' / Struct(
        'in4_tos' / u_char,
    ),

    'insi_v6' / Struct(
        'in6_hlim' / uint8_t,
        'in6_cksum' / Int32sl,
        'in6_ifindex' / u_short,
        'in6_hops' / short,
    ),
)

tcp_sockinfo = Struct(
    'tcpsi_ini' / in_sockinfo,
    'in_sockinfo' / Int32sl,
    'tcpsi_timer' / Int32sl[TSI_T_NTIMERS],
    'tcpsi_mss' / Int32sl,
    'tcpsi_flags' / uint32_t,
    'rfu_1' / uint32_t,  # reserved
    'tcpsi_tp' / uint64_t,  # opaque handle of TCP protocol control block
)

SOCK_MAXADDRLEN = 255

# Unix Domain Sockets

# we can't use sockaddr_un since the sun_path may contain utf8 invalid characters
sockaddr_un_raw = Struct(
    'sun_len' / Int8ul,
    'sun_family' / Default(Int8ul, AF_UNIX),
    '_sun_path' / Bytes(UNIX_PATH_MAX),
    'sun_path' / Computed(lambda x: x._sun_path.split(b'\x00', 1)[0].decode())
)

un_sockinfo = Struct(
    'unsi_conn_so' / uint64_t,
    'unsi_conn_pcb' / uint64_t,
    'unsi_addr' / Union(None,
                        'ua_sun' / sockaddr_un_raw,
                        'ua_dummy' / Bytes(SOCK_MAXADDRLEN)),
    'unsi_caddr' / Union(None,
                         'ua_sun' / sockaddr_un_raw,
                         'ua_dummy' / Bytes(SOCK_MAXADDRLEN)),
)

IF_NAMESIZE = 16

# PF_NDRV Sockets

ndrv_info = Struct(
    'ndrvsi_if_family' / uint32_t,
    'ndrvsi_if_unit' / uint32_t,
    'ndrvsi_if_name' / Bytes(IF_NAMESIZE),
)

# Kernel Event Sockets

kern_event_info = Struct(
    'kesi_vendor_code_filter' / uint32_t,
    'kesi_class_filter' / uint32_t,
    'kesi_subclass_filter' / uint32_t,
)

# Kernel Control Sockets

MAX_KCTL_NAME = 96

kern_ctl_info = Struct(
    'kcsi_id' / uint32_t,
    'kcsi_reg_unit' / uint32_t,
    'kcsi_flags' / uint32_t,
    'kcsi_recvbufsize' / uint32_t,
    'kcsi_sendbufsize' / uint32_t,
    'kcsi_unit' / uint32_t,
    'kcsi_name' / Bytes(MAX_KCTL_NAME),
)

so_kind_t = Enum(Int32ul,
                 SOCKINFO_GENERIC=0,
                 SOCKINFO_IN=1,
                 SOCKINFO_TCP=2,
                 SOCKINFO_UN=3,
                 SOCKINFO_NDRV=4,
                 SOCKINFO_KERN_EVENT=5,
                 SOCKINFO_KERN_CTL=6
                 )

so_family_t = Enum(Int32ul,
                   AF_INET=AF_INET,
                   AF_INET6=AF_INET6,
                   )

socket_info = Struct(
    'soi_stat' / vinfo_stat,
    'soi_so' / uint64_t,  # opaque handle of socket
    'soi_pcb' / uint64_t,  # opaque handle of protocol control block
    'soi_type' / Int32sl,
    'soi_protocol' / Int32sl,
    'soi_family' / so_family_t,
    'soi_options' / short,
    'soi_linger' / short,
    'soi_state' / short,
    'soi_qlen' / short,
    'soi_incqlen' / short,
    'soi_qlimit' / short,
    'soi_timeo' / short,
    'soi_error' / u_short,
    'soi_oobmark' / uint32_t,
    'soi_rcv' / sockbuf_info,
    'soi_snd' / sockbuf_info,
    'soi_kind' / so_kind_t,
    'rfu_1' / uint32_t,  # reserved

    'soi_proto' / Switch(this.soi_kind, {
        so_kind_t.SOCKINFO_IN: Struct('pri_in' / in_sockinfo),
        so_kind_t.SOCKINFO_TCP: Struct('pri_tcp' / tcp_sockinfo),
        so_kind_t.SOCKINFO_UN: Struct('pri_un' / un_sockinfo),
        so_kind_t.SOCKINFO_NDRV: Struct('pri_ndrv' / ndrv_info),
        so_kind_t.SOCKINFO_KERN_EVENT: Struct('pri_kern_event' / kern_event_info),
        so_kind_t.SOCKINFO_KERN_CTL: Struct('pri_kern_ctl' / kern_ctl_info),
    }),
)

socket_fdinfo = Struct(
    'pfi' / proc_fileinfo,
    'psi' / socket_info,
)

pipe_info = Struct(
    'pipe_stat' / vinfo_stat,
    'pipe_handle' / uint64_t,
    'pipe_peerhandle' / uint64_t,
    'pipe_status' / Int32sl,
    'rfu_1' / Int32sl  # reserved
)

pipe_fdinfo = Struct(
    'pfi' / proc_fileinfo,
    'pipeinfo' / pipe_info,
)

vm_region_basic_info = Struct(
    'protection' / vm_prot_t,
    'max_protection' / vm_prot_t,
    'inheritance' / vm_inherit_t,
    'shared' / boolean_t,
    'reserved' / boolean_t,
    Padding(4),
    'offset' / memory_object_offset_t,
    'behavior' / vm_behavior_t,
    'user_wired_count' / Int16ul,
)

vm_region_basic_info_64 = Struct(
    'protection' / vm_prot_t,
    'max_protection' / vm_prot_t,
    'inheritance' / vm_inherit_t,
    'shared' / boolean_t,
    'reserved' / boolean_t,
    Padding(4),
    'offset' / memory_object_offset_t,
    'behavior' / vm_behavior_t,
    'user_wired_count' / Int16ul,
)

VM_REGION_BASIC_INFO_COUNT_64 = vm_region_basic_info_64.sizeof() // 4
vm_region_basic_info_data_t = vm_region_basic_info
natural_t = Int32ul

task_dyld_info = Struct(
    'all_image_info_addr' / mach_vm_address_t,
    'all_image_info_size' / mach_vm_size_t,
    'all_image_info_format' / integer_t,
)

uuid_t = Struct(
    'time_low' / Int64ul,
    'time_mid' / Int32ul,
    'time_hi_and_version' / Int32ul,
    'clock_seq_hi_and_reserved' / Int8ul,
    'clock_seq_low' / Int8ul,
    'node' / Array(6, Int8ul)
)

dyld_image_info_t = Struct(
    'imageLoadAddress' / Int64ul,
    'imageFilePath' / Int64ul,
    'imageFileModDate' / Int64ul
)

all_image_infos_t = Struct(
    'version' / Int32ul,
    'infoArrayCount' / Int32ul,
    'infoArray' / Int64ul,
)

task_dyld_info_data_t = task_dyld_info
TASK_DYLD_INFO_COUNT = task_dyld_info_data_t.sizeof() / natural_t.sizeof()

STRUCT_ARM_THREAD_STATE64 = Struct(
    'x' / Array(29, uint64_t),
    'fp' / Default(uint64_t, 0),
    'lr' / Default(uint64_t, 0),
    'sp' / Default(uint64_t, 0),
    'pc' / Default(uint64_t, 0),
    'cpsr' / Default(uint32_t, 0),
    Padding(4),
)

arm_thread_state64_t = STRUCT_ARM_THREAD_STATE64
ARM_THREAD_STATE64_COUNT = arm_thread_state64_t.sizeof() // uint32_t.sizeof()

STRUCT_X86_THREAD_STATE32 = Struct(
    'eax' / Int32sl,
    'ebx' / Int32sl,
    'ecx' / Int32sl,
    'edx' / Int32sl,
    'edi' / Int32sl,
    'esi' / Int32sl,
    'ebp' / Int32sl,
    'esp' / Int32sl,
    'ss' / Int32sl,
    'eflags' / Int32sl,
    'eip' / Int32sl,
    'cs' / Int32sl,
    'ds' / Int32sl,
    'es' / Int32sl,
    'fs' / Int32sl,
    'gs' / Int32sl,
)

x86_thread_state32_t = STRUCT_X86_THREAD_STATE32

STRUCT_X86_THREAD_STATE64 = Struct(
    'rax' / uint64_t,
    'rbx' / uint64_t,
    'rcx' / uint64_t,
    'rdx' / uint64_t,
    'rdi' / uint64_t,
    'rsi' / uint64_t,
    'rbp' / uint64_t,
    'rsp' / uint64_t,
    'r8' / uint64_t,
    'r9' / uint64_t,
    'r10' / uint64_t,
    'r11' / uint64_t,
    'r12' / uint64_t,
    'r13' / uint64_t,
    'r14' / uint64_t,
    'r15' / uint64_t,
    'rip' / uint64_t,
    'rflags' / uint64_t,
    'cs' / uint64_t,
    'fs' / uint64_t,
    'gs' / uint64_t,
)

x86_thread_state64_t = STRUCT_X86_THREAD_STATE64

suseconds_t = uint32_t

timeval = Struct(
    'tv_sec' / time_t,
    Padding(4),
    'tv_usec' / suseconds_t,
    Padding(4),
)

procargs2_t = Struct(
    'argc' / Int32ul,
    'executable' / Aligned(4, CString('utf8')),
    'argv' / Array(this.argc, CString('utf8')),
    '_environ_apple' / GreedyRange(CString('utf8')),
    'environ_apple' / Computed(lambda ctx: [s for s in ctx._environ_apple if s]),
)

# See: https://opensource.apple.com/source/xnu/xnu-7195.81.3/EXTERNAL_HEADERS/mach-o/loader.h
LC_REQ_DYLD = 0x80000000

LOAD_COMMAND_TYPE = Enum(Int32ul,
                         LC_SEGMENT=0x1,
                         LC_SYMTAB=0x2,
                         LC_SYMSEG=0x3,
                         LC_THREAD=0x4,
                         LC_UNIXTHREAD=0x5,
                         LC_LOADFVMLIB=0x6,
                         LC_IDFVMLIB=0x7,
                         LC_IDENT=0x8,
                         LC_FVMFILE=0x9,
                         LC_PREPAGE=0xa,
                         LC_DYSYMTAB=0xb,
                         LC_LOAD_DYLIB=0xc,
                         LC_ID_DYLIB=0xd,
                         LC_LOAD_DYLINKER=0xe,
                         LC_ID_DYLINKER=0xf,
                         LC_PREBOUND_DYLIB=0x10,
                         LC_ROUTINES=0x11,
                         LC_SUB_FRAMEWORK=0x12,
                         LC_SUB_UMBRELLA=0x13,
                         LC_SUB_CLIENT=0x14,
                         LC_SUB_LIBRARY=0x15,
                         LC_TWOLEVEL_HINTS=0x16,
                         LC_PREBIND_CKSUM=0x17,
                         LC_LOAD_WEAK_DYLIB=(0x18 | LC_REQ_DYLD),
                         LC_SEGMENT_64=0x19,
                         LC_ROUTINES_64=0x1a,
                         LC_UUID=0x1b,
                         LC_RPATH=(0x1c | LC_REQ_DYLD),
                         LC_CODE_SIGNATURE=0x1d,
                         LC_SEGMENT_SPLIT_INFO=0x1e,
                         LC_REEXPORT_DYLIB=0x1f | LC_REQ_DYLD,
                         LC_LAZY_LOAD_DYLIB=0x20,
                         LC_ENCRYPTION_INFO=0x21,
                         LC_DYLD_INFO=0x22,
                         LC_DYLD_INFO_ONLY=(0x22 | LC_REQ_DYLD),
                         LC_LOAD_UPWARD_DYLIB=(0x23 | LC_REQ_DYLD),
                         LC_VERSION_MIN_MACOSX=0x24,
                         LC_VERSION_MIN_IPHONEOS=0x25,
                         LC_FUNCTION_STARTS=0x26,
                         LC_DYLD_ENVIRONMENT=0x27,
                         LC_MAIN=(0x28 | LC_REQ_DYLD),
                         LC_DATA_IN_CODE=0x29,
                         LC_SOURCE_VERSION=0x2A,
                         LC_DYLIB_CODE_SIGN_DRS=0x2B,
                         LC_ENCRYPTION_INFO_64=0x2C,
                         LC_LINKER_OPTION=0x2D,
                         LC_LINKER_OPTIMIZATION_HINT=0x2E,
                         LC_VERSION_MIN_TVOS=0x2F,
                         LC_VERSION_MIN_WATCHOS=0x30,
                         LC_NOTE=0x31,
                         LC_BUILD_VERSION=0x32,
                         LC_DYLD_EXPORTS_TRIE=(0x33 | LC_REQ_DYLD),
                         LC_DYLD_CHAINED_FIXUPS=(0x34 | LC_REQ_DYLD),
                         LC_FILESET_ENTRY=(0x35 | LC_REQ_DYLD)
                         )

# Load commands:
# reference - https://opensource.apple.com/source/xnu/xnu-2050.18.24/EXTERNAL_HEADERS/mach-o/loader.h

FAT_MAGIC = 0xcafebabe
FAT_CIGAM = 0xbebafeca

cpu_type_t = Int32ul
cpu_subtype_t = Int32ul

version_t = BitStruct(
    'major' / BitsInteger(16),
    'minor' / Octet,
    'bug' / Octet
)

segment_command_t = Struct(
    'segname' / PaddedString(16, 'utf8'),
    'vmaddr' / Int64ul,
    'vmsize' / Int64ul,
    'fileoff' / Int64ul,
    'filesize' / Int64ul,
    'maxprot' / Int32ul,
    'initprot' / Int32ul,
    'nsects' / Int32ul,
    'flags' / Int32ul,
)

uuid_command_t = Struct(
    'uuid' / Array(16, Int8ul)
)

build_tool_version = Struct(
    'tool' / Int32ul,
    'version' / Int32ul
)

build_version_command_t = Struct(
    'platform' / Int32ul,
    'minos' / version_t,
    'sdk' / version_t,
    'ntools' / Int32ul,
)

encryption_info_command = Struct(
    'cryptoff' / Int32ul,  # file offset of encrypted range
    'cryptsize' / Int32ul,  # file size of encrypted range
    'cryptid' / Int32ul,  # which encryption system, 0 means not-encrypted yet
)

encryption_info_command_64 = Struct(
    'cryptoff' / Int32ul,  # file offset of encrypted range
    'cryptsize' / Int32ul,  # file size of encrypted range
    'cryptid_offset' / Tell,
    'cryptid' / Int32ul,  # which encryption system, 0 means not-encrypted yet
    '_pad' / Int32ul,
)

load_command_t = Struct(
    '_start' / Tell,
    'cmd' / LOAD_COMMAND_TYPE,
    'cmdsize' / Int32ul,
    '_data_offset' / Tell,
    'data' / Switch(this.cmd, {
        LOAD_COMMAND_TYPE.LC_BUILD_VERSION: build_version_command_t,
        LOAD_COMMAND_TYPE.LC_UUID: uuid_command_t,
        LOAD_COMMAND_TYPE.LC_SEGMENT_64: segment_command_t,
        LOAD_COMMAND_TYPE.LC_ENCRYPTION_INFO_64: encryption_info_command_64,
        LOAD_COMMAND_TYPE.LC_ENCRYPTION_INFO: encryption_info_command,
    }, Bytes(this.cmdsize - (this._data_offset - this._start))),
    Seek(this._start + this.cmdsize),
)

mach_header_t = Struct(
    'load_address' / Tell,
    'magic' / Hex(Int32ul),
    'cputype' / Hex(cpu_type_t),
    'cpusubtype' / Hex(cpu_subtype_t),
    'filetype' / Hex(Int32ul),
    'ncmds' / Hex(Int32ul),
    'sizeofcmds' / Hex(Int32ul),
    'flags' / Hex(Int32ul),
    'reserved' / Hex(Int32ul),
    'load_commands' / LazyArray(this.ncmds, load_command_t),
)

fat_arch = Struct(
    'cputype' / Hex(Int32ub),
    'cpusubtype' / Hex(Int32ub),
    'offset' / Hex(Int32ub),
    'size' / Hex(Int32ub),
    'align' / Hex(Int32ub),
)

fat_header = Struct(
    'magic' / Hex(Int32ul),
    'nfat_arch' / Hex(Int32ub),
    'archs' / Array(this.nfat_arch, fat_arch)
)
