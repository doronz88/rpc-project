from construct import Struct, PaddedString, Int8ul, Int16ul, Int32ul, this, Int64ul, Int64sl, Int32sl, Array, Padding

dev_t = Int32ul
ino_t = Int32ul
mode_t = Int16ul
off_t = Int32ul
nlink_t = Int16ul
uid_t = Int32ul
gid_t = Int32ul

time_t = Int32ul
long = Int64ul
blkcnt_t = Int32ul
blksize_t = Int32ul

ino64_t = Int64ul

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
