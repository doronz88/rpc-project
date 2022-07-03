import struct
from enum import IntEnum

from rpcclient.darwin.symbol import DarwinSymbol


class CTL(IntEnum):
    UNSPEC = 0,  # unused
    KERN = 1,  # "high kernel": proc, limits
    VM = 2,  # virtual memory
    VFS = 3,  # file system, mount type is next
    NET = 4,  # network, see socket.h
    DEBUG = 5,  # debugging parameters
    HW = 6,  # generic cpu/io
    MACHDEP = 7,  # machine dependent
    USER = 8,  # user-level
    MAXID = 9,  # number of valid top-level ids


class KERN(IntEnum):
    OSTYPE = 1  # string: system version
    OSRELEASE = 2  # string: system release
    OSREV = 3  # int: system revision
    VERSION = 4  # string: compile time info
    MAXVNODES = 5  # int: max vnodes
    MAXPROC = 6  # int: max processes
    MAXFILES = 7  # int: max open files
    ARGMAX = 8  # int: max arguments to exec
    SECURELVL = 9  # int: system security level
    HOSTNAME = 10  # string: hostname
    HOSTID = 11  # int: host identifier
    CLOCKRATE = 12  # struct: struct clockrate
    VNODE = 13  # struct: vnode structures
    PROC = 14  # struct: process entries
    FILE = 15  # struct: file entries
    PROF = 16  # node: kernel profiling info
    POSIX1 = 17  # int: POSIX.1 version
    NGROUPS = 18  # int: # of supplemental group ids
    JOB_CONTROL = 19  # int: is job control available
    SAVED_IDS = 20  # int: saved set-user/group-ID
    BOOTTIME = 21  # struct: time kernel was booted
    NISDOMAINNAME = 22  # string: YP domain name
    DOMAINNAME = NISDOMAINNAME  # ERN_MAXPARTITIONS = 23  # int: number of partitions/disk
    KDEBUG = 24  # int: kernel trace points
    UPDATEINTERVAL = 25  # int: update process sleep time
    OSRELDATE = 26  # int: OS release date
    NTP_PLL = 27  # node: NTP PLL control
    BOOTFILE = 28  # string: name of booted kernel
    MAXFILESPERPROC = 29  # int: max open files per proc
    MAXPROCPERUID = 30  # int: max processes per uid
    DUMPDEV = 31  # dev_t: device to dump on
    IPC = 32  # node: anything related to IPC
    DUMMY = 33  # unused
    PS_STRINGS = 34  # int: address of PS_STRINGS
    USRSTACK32 = 35  # int: address of USRSTACK
    LOGSIGEXIT = 36  # int: do we log sigexit procs?
    SYMFILE = 37  # string: kernel symbol filename
    PROCARGS = 38  # * 39 was PCSAMPLES... now obsolete
    NETBOOT = 40  # int: are we netbooted? 1=yes,0=no
    # 41 was PANICINFO : panic UI information (deprecated)
    SYSV = 42  # node: System V IPC information
    AFFINITY = 43  # xxx
    TRANSLATE = 44  # xxx
    CLASSIC = TRANSLATE  # XXX backwards compat
    EXEC = 45  # xxx
    CLASSICHANDLER = EXEC  # XXX backwards compatibility
    AIOMAX = 46  # int: max aio requests
    AIOPROCMAX = 47  # int: max aio requests per process
    AIOTHREADS = 48  # int: max aio worker threads
    # ifdef __APPLE_API_UNSTABLE
    PROCARGS2 = 49  # endif # __APPLE_API_UNSTA
    COREFILE = 50  # string: corefile format string
    COREDUMP = 51  # int: whether to coredump at all
    SUGID_COREDUMP = 52  # int: whether to dump SUGID cores
    PROCDELAYTERM = 53  # int: set/reset current proc for delayed termination during shutdown
    SHREG_PRIVATIZABLE = 54  # int: can shared regions be privatized ?
    # 55 was PROC_LOW_PRI_IO... now deprecated
    LOW_PRI_WINDOW = 56  # int: set/reset throttle window - milliseconds
    LOW_PRI_DELAY = 57  # int: set/reset throttle delay - milliseconds
    POSIX = 58  # node: posix tunables
    USRSTACK64 = 59  # LP64 user stack query
    NX_PROTECTION = 60  # int: whether no-execute protection is enabled
    TFP = 61  # Task for pid settings
    PROCNAME = 62  # setup process program  name(2*MAXCOMLEN)
    THALTSTACK = 63  # for compat with older x86 and does nothing
    SPECULATIVE_READS = 64  # int: whether speculative reads are disabled
    OSVERSION = 65  # for build number i.e. 9A127
    SAFEBOOT = 66  # are we booted safe?
    # 67 was LCTX (login context)
    RAGEVNODE = 68  # ERN_TTY = 69  # node: tty settings
    CHECKOPENEVT = 70  # spi: check the VOPENEVT flag on vnodes at open time
    THREADNAME = 71  # set/get thread name
    MAXID = 72  # number of valid kern ids


MAX_SIZE = 0x40000


class Sysctl:
    """ sysctl utils. read man page for sysctl(3) for more details """

    def __init__(self, client):
        self._client = client

    def get(self, ctl: CTL, kern: KERN, arg: int = None, size=MAX_SIZE) -> bytes:
        """ call sysctl(int *name, u_int namelen, void *oldp, size_t *oldlenp, void *newp, size_t newlen) on remote """
        namelen = 2

        with self._client.safe_malloc(4 * 3) as mib:
            mib.item_size = 4
            mib[0] = ctl
            mib[1] = kern
            if arg is not None:
                mib[2] = int(arg)
                namelen += 1
            with self._client.safe_malloc(8) as oldenp:
                oldenp[0] = size
                with self._client.safe_malloc(size) as oldp:
                    if self._client.symbols.sysctl(mib, namelen, oldp, oldenp, 0, 0):
                        self._client.raise_errno_exception('sysctl() failed')
                    return oldp.peek(oldenp[0])

    def set(self, ctl: CTL, kern: KERN, oldp: DarwinSymbol, oldenp: DarwinSymbol, arg: int = None):
        """ call sysctl(int *name, u_int namelen, void *oldp, size_t *oldlenp, void *newp, size_t newlen) on remote """
        namelen = 2

        with self._client.safe_malloc(4 * 3) as mib:
            mib.item_size = 4
            mib[0] = ctl
            mib[1] = kern
            if arg is not None:
                mib[2] = int(arg)
                namelen += 1
            if self._client.symbols.sysctl(mib, namelen, oldp, oldenp, 0, 0):
                self._client.raise_errno_exception('sysctl() failed')

    def get_str_by_name(self, name: str) -> str:
        """ equivalent of: sysctl <name> """
        return self.get_by_name(name).strip(b'\x00').decode()

    def get_int_by_name(self, name: str) -> int:
        """ equivalent of: sysctl <name> """
        return struct.unpack('<I', self.get_by_name(name))[0]

    def set_int_by_name(self, name: str, value: int):
        """ equivalent of: sysctl <name> -w value """
        self.set_by_name(name, struct.pack('<I', value))

    def set_str_by_name(self, name: str, value: str):
        """ equivalent of: sysctl <name> -w value """
        self.set_by_name(name, value.encode() + b'\x00')

    def set_by_name(self, name: str, value: bytes):
        """ equivalent of: sysctl <name> -w value """
        if self._client.symbols.sysctlbyname(name, 0, 0, value, len(value)):
            self._client.raise_errno_exception('sysctlbyname() failed')

    def get_by_name(self, name: str, size=MAX_SIZE) -> bytes:
        """ equivalent of: sysctl <name> """
        oldval_len = size
        with self._client.safe_malloc(8) as p_oldval_len:
            p_oldval_len[0] = oldval_len
            with self._client.safe_malloc(oldval_len) as oldval:
                if self._client.symbols.sysctlbyname(name, oldval, p_oldval_len, 0, 0):
                    self._client.raise_errno_exception('sysctlbyname() failed')
                return oldval.peek(p_oldval_len[0])
