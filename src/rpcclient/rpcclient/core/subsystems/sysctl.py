import struct
from enum import IntEnum
from typing import TYPE_CHECKING

import zyncio

from rpcclient.core._types import ClientBound, ClientT_co
from rpcclient.core.symbol import SymbolT_co


if TYPE_CHECKING:
    from rpcclient.core.client import BaseCoreClient


class CTL(IntEnum):
    UNSPEC = 0  # unused
    KERN = 1  # "high kernel": proc, limits
    VM = 2  # virtual memory
    VFS = 3  # file system, mount type is next
    NET = 4  # network, see socket.h
    DEBUG = 5  # debugging parameters
    HW = 6  # generic cpu/io
    MACHDEP = 7  # machine dependent
    USER = 8  # user-level
    MAXID = 9  # number of valid top-level ids


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


class Sysctl(ClientBound[ClientT_co]):
    """Helpers for reading and writing sysctl MIB values on the remote host."""

    def __init__(self, client: ClientT_co) -> None:
        self._client = client

    @zyncio.zmethod
    async def get(self, ctl: CTL, kern: KERN, arg: int | None = None, size: int = MAX_SIZE) -> bytes:
        """call sysctl(int *name, u_int namelen, void *oldp, size_t *oldlenp, void *newp, size_t newlen) on remote"""
        namelen = 2

        async with self._client.safe_malloc.z(4 * 3) as mib:
            mib.item_size = 4
            await mib.setindex(0, ctl)
            await mib.setindex(1, kern)
            if arg is not None:
                await mib.setindex(2, int(arg))
                namelen += 1
            async with self._client.safe_malloc.z(8) as oldenp:
                await oldenp.setindex(0, size)
                async with self._client.safe_malloc.z(size) as oldp:
                    if await self._client.symbols.sysctl.z(mib, namelen, oldp, oldenp, 0, 0):
                        await self._client.raise_errno_exception.z("sysctl() failed")
                    return await oldp.peek.z(await oldenp.getindex(0))

    @zyncio.zmethod
    async def set(
        self: "Sysctl[BaseCoreClient[SymbolT_co]]",
        ctl: CTL,
        kern: KERN,
        oldp: SymbolT_co,
        oldenp: SymbolT_co,
        arg: int | None = None,
    ) -> None:
        """call sysctl(int *name, u_int namelen, void *oldp, size_t *oldlenp, void *newp, size_t newlen) on remote"""
        namelen = 2

        async with self._client.safe_malloc.z(4 * 3) as mib:
            mib.item_size = 4
            await mib.setindex(0, ctl)
            await mib.setindex(1, kern)
            if arg is not None:
                await mib.setindex(2, int(arg))
                namelen += 1
            if await self._client.symbols.sysctl.z(mib, namelen, oldp, oldenp, 0, 0):
                await self._client.raise_errno_exception.z("sysctl() failed")

    @zyncio.zmethod
    async def get_str_by_name(self, name: str) -> str:
        """equivalent of: sysctl <name>"""
        return (await self.get_by_name.z(name)).strip(b"\x00").decode()

    @zyncio.zmethod
    async def get_int_by_name(self, name: str) -> int:
        """equivalent of: sysctl <name>"""
        return struct.unpack("<I", await self.get_by_name.z(name))[0]

    @zyncio.zmethod
    async def set_int_by_name(self, name: str, value: int):
        """equivalent of: sysctl <name> -w value"""
        await self.set_by_name.z(name, struct.pack("<I", value))

    @zyncio.zmethod
    async def set_str_by_name(self, name: str, value: str):
        """equivalent of: sysctl <name> -w value"""
        await self.set_by_name.z(name, value.encode() + b"\x00")

    @zyncio.zmethod
    async def set_by_name(self, name: str, value: bytes) -> None:
        """equivalent of: sysctl <name> -w value"""
        if await self._client.symbols.sysctlbyname.z(name, 0, 0, value, len(value)):
            await self._client.raise_errno_exception.z("sysctlbyname() failed")

    @zyncio.zmethod
    async def get_by_name(self, name: str, size=MAX_SIZE) -> bytes:
        """equivalent of: sysctl <name>"""
        oldval_len = size
        async with self._client.safe_malloc.z(8) as p_oldval_len:
            await p_oldval_len.setindex(0, oldval_len)
            async with self._client.safe_malloc.z(oldval_len) as oldval:
                if await self._client.symbols.sysctlbyname.z(name, oldval, p_oldval_len, 0, 0):
                    await self._client.raise_errno_exception.z("sysctlbyname() failed")
                return await oldval.peek.z(await p_oldval_len.getindex(0))
