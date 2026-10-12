"""
mDNSResponder access: read its DNS cache and state, inject local records and flush cached ones.

Everything here requires rpcserver to run as root.
"""

import asyncio
import dataclasses
import ipaddress
import plistlib
import posixpath
import re
from typing import TYPE_CHECKING, Any, Generic

from rpcclient.clients.darwin._types import DarwinSymbolT_co
from rpcclient.core._types import ClientBound
from rpcclient.core.structs.consts import RTLD_NOW
from rpcclient.core.symbol import AbstractSymbol
from rpcclient.exceptions import ArgumentError, BadReturnValueError, MissingLibraryError


if TYPE_CHECKING:
    from rpcclient.clients.darwin.client import DarwinClient
    from rpcclient.clients.darwin.subsystems.xpc import XPCDictionary

# mDNSResponder's state-dump XPC protocol, as used by `dns-sd -O`
_LOG_UTILITY_SERVICE = "com.apple.mDNSResponder.log_utility"
_STATE_DUMP_KEY = "mDNSResponderStateDump"
_STATE_DUMP_FULL = 1  # plain-text dump written under /private/var/log/mDNSResponder
_DUMP_PATH_KEY = "mDNSResponderDumpFilePath"
_REPLY_STATUS_KEY = "DaemonReplyStatusToClient"
_ERROR_DESCRIPTION_KEY = "ErrorDescription"
_XPC_ERROR_DESCRIPTION_KEY = "XPCErrorDescription"

# mDNSResponder refuses state dumps unless EnableStateDump is set in its managed preferences, which is what Apple's
# mDNSResponder logging profile installs
_ENABLE_STATE_DUMP_KEY = "EnableStateDump"
_PREFERENCES_IOS = "/private/var/Managed Preferences/mobile/com.apple.mDNSResponder.plist"
_PREFERENCES_MACOS = "/Library/Managed Preferences/com.apple.mDNSResponder.plist"

# mDNSResponder's private record-cache flush SPI, which requires the com.apple.private.mDNSResponder.record-cache.flush
# entitlement. It only reports its result asynchronously, so the daemon is given a moment to handle the request.
_MRC_LIBRARIES = ("/usr/lib/libmrc.dylib", "/usr/lib/libmdns.dylib")
_MRC_FLUSH_SETTLE_TIME = 0.5
_FLUSH_ENTITLEMENT = "com.apple.private.mDNSResponder.record-cache.flush"

# dns_sd.h
_FLAGS_SHARED = 0x10
_INTERFACE_LOCAL_ONLY = 0xFFFFFFFF
_CLASS_IN = 1

RECORD_TYPES = {"A": 1, "NS": 2, "CNAME": 5, "PTR": 12, "TXT": 16, "AAAA": 28}
DEFAULT_TTL = 3600
# mDNSResponder refuses local-only records of these types outside the local domains, so that clients can't redirect
# e.g. www.bigbank.com (see _handle_regrecord_request_start() in mDNSShared/uds_daemon.c)
_LOCAL_DOMAIN_ONLY_TYPES = frozenset({RECORD_TYPES["A"], RECORD_TYPES["AAAA"], RECORD_TYPES["CNAME"]})

# a "Cache" section row, printed as "%3d %s%8d %-7s%s %-6s   %-40s%s": slot, active-question marker, remaining TTL,
# interface, kind marker, type, DNSSEC status and the record ("%4d %##s %s " rdlength, name and type, then the rdata)
_CACHE_ROW = re.compile(
    r"^\s*\d+ (?P<active>[* ])\s*(?P<ttl>-?\d+) (?P<interface>\S+)\s*(?P<kind>[ +\-]) (?P<type>\S+)\s*(?P<rest>.*)$"
)
_CACHE_RECORD = re.compile(r"^(?P<dnssec>.*?)\s*\d+ (?P<name>\S+) \S+(?: (?P<rdata>.*))?$")
_CACHE_SIZE = re.compile(
    r"Cache size (?P<entities>\d+) entities; (?P<in_use>\d+) in use \((?P<groups>\d+) group, "
    r"(?P<multicast>\d+) multicast, (?P<unicast>\d+) unicast\); "
    r"(?P<referenced_by_questions>\d+) referenced by active questions"
)
_CACHE_KINDS = {" ": "unique", "+": "shared", "-": "negative"}
_UNICAST_INTERFACE = "-U-"
_PRIVATE_RECORD = "<private record description>"
_DECIMAL_ESCAPE = re.compile(r"\\(\d{3})")
_TABLE_NAME_WIDTH = 50


def _normalize(name: str) -> str:
    return name.rstrip(".").lower()


def _unescape(text: str) -> str:
    """Decode the "\\\\DDD" escapes mDNSResponder prints names and data with (e.g. "\\\\032" for a space)."""
    return _DECIMAL_ESCAPE.sub(lambda match: chr(int(match[1])), text)


def is_local_domain(name: str) -> bool:
    """
    Tell whether a name is resolved via link-local multicast, as mDNSResponder's IsLocalDomain() defines it.

    :param name: domain name, with or without the trailing dot
    :return: True for names under "local.", "254.169.in-addr.arpa." and "{8,9,a,b}.e.f.ip6.arpa."
    """
    labels = _normalize(name).split(".")
    return (
        labels[-1] == "local"
        or labels[-4:] == ["254", "169", "in-addr", "arpa"]
        or (len(labels) >= 5 and labels[-5] in {"8", "9", "a", "b"} and labels[-4:] == ["e", "f", "ip6", "arpa"])
    )


async def _xpc_string(dictionary: "XPCDictionary", key: str) -> str | None:
    # XPCDictionary.get_string() would read a missing key's NULL string on the target
    return await dictionary.get_string(key) if await dictionary.get_value(key) != 0 else None


def _check_dnssd(function: str, result: AbstractSymbol) -> None:
    """Raise if a dns_sd function returned an error (DNSServiceErrorType is a negative int32)."""
    if (error := result.c_int32) != 0:
        raise BadReturnValueError(f"{function} failed: {error}")


def _record_type(rrtype: str | int) -> int:
    if isinstance(rrtype, int):
        return rrtype
    try:
        return RECORD_TYPES[rrtype.upper()]
    except KeyError:
        raise ValueError(f"unknown record type: {rrtype}") from None


def _length_prefixed(data: bytes) -> bytes:
    if len(data) > 255:
        raise ValueError(f"{data[:16]!r}... is longer than 255 bytes")
    return bytes([len(data)]) + data


def _encode_name(name: str) -> bytes:
    labels = [label.encode() for label in name.rstrip(".").split(".")]
    if not all(0 < len(label) < 64 for label in labels) or sum(len(label) + 1 for label in labels) >= 255:
        raise ValueError(f"invalid domain name: {name}")
    return b"".join(bytes([len(label)]) + label for label in labels) + b"\x00"


def encode_rdata(rrtype: int, rdata: str | bytes | list[str]) -> bytes:
    """
    Encode record data into its wire format.

    :param rrtype: record type number (see RECORD_TYPES)
    :param rdata: an IP address for A/AAAA, a domain name for CNAME/PTR/NS, a string or list of strings for TXT, or
        already-encoded bytes for any type
    :return: the wire-format rdata
    :raises TypeError: for a list of strings for a type other than TXT
    :raises ValueError: for malformed rdata, or a type that can only be given as bytes
    """
    if isinstance(rdata, bytes):
        return rdata
    if rrtype == RECORD_TYPES["TXT"]:
        return b"".join(_length_prefixed(s.encode()) for s in ([rdata] if isinstance(rdata, str) else rdata))
    if not isinstance(rdata, str):
        raise TypeError(f"rdata of record type {rrtype} must be a string")
    if rrtype == RECORD_TYPES["A"]:
        return ipaddress.IPv4Address(rdata).packed
    if rrtype == RECORD_TYPES["AAAA"]:
        return ipaddress.IPv6Address(rdata).packed
    if rrtype in (RECORD_TYPES["CNAME"], RECORD_TYPES["PTR"], RECORD_TYPES["NS"]):
        return _encode_name(rdata)
    raise ValueError(f"don't know how to encode rdata of record type {rrtype}; pass it as bytes")


@dataclasses.dataclass
class DnsCacheRecord:
    """A resource record held in mDNSResponder's cache."""

    name: str | None  # owner name (e.g. "www.apple.com."), None if mDNSResponder redacted it
    type: str  # record type as mDNSResponder prints it (e.g. "Addr" for A, "AAAA", "CNAME")
    ttl: int  # remaining TTL in seconds
    interface: str | None  # interface it was received on, None for unicast DNS
    kind: str  # "unique", "shared" or "negative" (a cached "no such record" answer)
    active_question: bool  # whether an active question currently references it
    dnssec: str  # DNSSEC validation status, empty if not applicable
    rdata: str | None  # human-readable record data (e.g. "17.253.144.10"), None if redacted
    raw: str  # the original dump line

    @property
    def unicast(self) -> bool:
        return self.interface is None

    @property
    def negative(self) -> bool:
        return self.kind == "negative"

    @property
    def display_name(self) -> str:
        """The owner name with mDNSResponder's escapes decoded."""
        return "<private>" if self.name is None else _unescape(self.name)

    @property
    def display_data(self) -> str:
        """The record data with mDNSResponder's escapes decoded."""
        if self.negative:
            return "<no such record>"
        return "<private>" if self.rdata is None else _unescape(self.rdata)

    def __str__(self) -> str:
        return (
            f"{self.display_name} {self.type} {self.display_data} "
            f"(ttl={self.ttl}, {self.interface or 'unicast'}, {self.kind})"
        )


@dataclasses.dataclass
class DnsCache:
    """A snapshot of mDNSResponder's DNS cache. Prints as a table."""

    records: list[DnsCacheRecord]
    entities: int | None = None  # allocated cache entities
    in_use: int | None = None  # entities in use
    groups: int | None = None  # cache groups (one per owner name)
    multicast: int | None = None  # records learned via multicast DNS
    unicast: int | None = None  # records learned via unicast DNS
    referenced_by_questions: int | None = None  # records referenced by active questions

    def find(self, name: str) -> list[DnsCacheRecord]:
        """
        Get the cached records of a name.

        :param name: owner name; case-insensitive and the trailing dot is optional
        """
        name = _normalize(name)
        return [record for record in self.records if record.name is not None and _normalize(record.name) == name]

    def __str__(self) -> str:
        summary = f"DNS cache: {len(self.records)} records"
        if self.entities is not None:
            summary += (
                f" ({self.in_use}/{self.entities} entities in use, {self.unicast} unicast, {self.multicast} multicast,"
                f" {self.referenced_by_questions} referenced by active questions)"
            )
        if not self.records:
            return summary

        rows = [("", "NAME", "TYPE", "TTL", "IF", "KIND", "DNSSEC", "DATA")] + [
            (
                "*" if record.active_question else "",
                record.display_name[:_TABLE_NAME_WIDTH],
                record.type,
                str(record.ttl),
                record.interface or "unicast",
                record.kind,
                record.dnssec,
                record.display_data,
            )
            for record in self.records
        ]
        widths = [max(map(len, column)) for column in zip(*rows, strict=True)]
        table = "\n".join(
            " ".join(cell.ljust(width) for cell, width in zip(row, widths, strict=True)).rstrip() for row in rows
        )
        return f"{summary}\n\n{table}\n\n* = referenced by an active question"

    def _repr_pretty_(self, printer: Any, cycle: bool) -> None:
        printer.text(str(self))


class DnsStateDump(str):
    """An mDNSResponder state dump. Prints as plain text and splits into its "---- Title ----" sections."""

    _SECTION = re.compile(r"^-{2,}\s*(?P<title>[^-\s].*?)\s*-{2,}$")  # a line of dashes alone is just a separator
    _LOG_BOUNDARY = re.compile(r"^-+\s*(BEGIN|END) STATE LOG\s*-+")

    def sections(self) -> dict[str, str]:
        """Get the dump's sections as {title: body}, e.g. "Cache", "Questions" or "DNS Services"."""
        sections: dict[str, list[str]] = {}
        body = None
        for line in self.splitlines():
            if self._LOG_BOUNDARY.match(line):
                body = None
            elif (header := self._SECTION.match(line)) is not None:
                body = sections[header["title"]] = []
            elif body is not None:
                body.append(line)
        return {title: "\n".join(lines) for title, lines in sections.items()}

    def section(self, title: str) -> str:
        """
        Get a section's body.

        :param title: section title, case-insensitive
        :raises KeyError: if there is no such section
        """
        sections = {name.lower(): body for name, body in self.sections().items()}
        try:
            return sections[title.lower()]
        except KeyError:
            raise KeyError(f"no such section: {title}; available: {', '.join(self.sections())}") from None

    def _repr_pretty_(self, printer: Any, cycle: bool) -> None:
        printer.text(str(self))


@dataclasses.dataclass(eq=False)
class DnsRecord:
    """A record injected into mDNSResponder by Dns.add() or Dns.update()."""

    name: str
    type: int  # record type number (see RECORD_TYPES)
    rdata: bytes  # wire-format record data
    ttl: int
    ref: int = dataclasses.field(repr=False)  # the DNSRecordRef

    @property
    def type_name(self) -> str:
        return next((name for name, value in RECORD_TYPES.items() if value == self.type), str(self.type))


def _parse_cache_row(line: str) -> DnsCacheRecord | None:
    row = _CACHE_ROW.match(line)
    if row is None:
        return None
    record = _CACHE_RECORD.match(row["rest"].strip())
    return DnsCacheRecord(
        name=record["name"] if record else None,
        type=row["type"],
        ttl=int(row["ttl"]),
        interface=None if row["interface"] == _UNICAST_INTERFACE else row["interface"],
        kind=_CACHE_KINDS[row["kind"]],
        active_question=row["active"] == "*",
        dnssec=(record["dnssec"] if record else row["rest"].replace(_PRIVATE_RECORD, "")).strip(),
        rdata=(record["rdata"] or "").strip() if record else None,
        raw=line,
    )


def parse_dns_cache(state_dump: str) -> DnsCache:
    """
    Parse the "Cache" section of an mDNSResponder state dump.

    :param state_dump: the dump, as returned by Dns.state_dump()
    """
    lines = iter(state_dump.splitlines())
    for line in lines:
        if line.startswith("Slt Q"):  # the cache table header
            break
    records = []
    for line in lines:
        if (size := _CACHE_SIZE.search(line)) is not None:
            return DnsCache(records, **{key: int(value) for key, value in size.groupdict().items()})
        if line.startswith("---"):
            break
        if (record := _parse_cache_row(line)) is not None:
            records.append(record)
    return DnsCache(records)


class Dns(ClientBound["DarwinClient[DarwinSymbolT_co]"], Generic[DarwinSymbolT_co]):
    """
    mDNSResponder's DNS cache: read it, inject local records into it and flush records from it.

    - read: cache(), state_dump()
    - create: add()
    - update: update()
    - delete: remove(), delete(), remove_all(), clear()

    Reading needs the state dump enabled once per device, see enable_state_dump().
    """

    def __init__(self, client: "DarwinClient[DarwinSymbolT_co]") -> None:
        self._client = client
        self._connection: DarwinSymbolT_co | None = None
        self._records: list[DnsRecord] = []
        self._mrc_loaded = False

    async def state_dump(self, keep_file: bool = False) -> DnsStateDump:
        """
        Get mDNSResponder's full state dump, like `dns-sd -O`: its cache, questions, registered records, resolver
        configuration and more.

        :param keep_file: keep the file mDNSResponder writes the dump to, under /private/var/log/mDNSResponder
        :raises BadReturnValueError: if mDNSResponder refuses, e.g. because the state dump isn't enabled
        """
        xpc = self._client.xpc
        message = await xpc.create_xpc_dictionary()
        reply = None
        try:
            await message.set_uint64(_STATE_DUMP_KEY, _STATE_DUMP_FULL)
            reply = await xpc.send_xpc_dictionary(_LOG_UTILITY_SERVICE, message)
            if await reply.get_value(_REPLY_STATUS_KEY) == 0:  # an XPC error object, e.g. the service is unreachable
                error = await _xpc_string(reply, _XPC_ERROR_DESCRIPTION_KEY) or "unexpected reply"
                raise BadReturnValueError(f"mDNSResponder state dump failed: {error}")
            status = await reply.get_uint64(_REPLY_STATUS_KEY)
            if status != 0:
                error = await _xpc_string(reply, _ERROR_DESCRIPTION_KEY) or f"status {status}"
                if "privacy" in error:
                    error = "it is disabled by the system privacy settings; enable it with `p.dns.enable_state_dump()`"
                raise BadReturnValueError(f"mDNSResponder state dump failed: {error}")
            path = await _xpc_string(reply, _DUMP_PATH_KEY)
            if path is None:
                raise BadReturnValueError("mDNSResponder state dump failed: the reply has no dump file")
        finally:
            await message.release()
            if reply is not None:
                await reply.release()

        try:
            return DnsStateDump((await self._client.fs.read_file(path)).decode(errors="replace"))
        finally:
            if not keep_file:
                await self._client.fs.remove(path, force=True)

    async def enable_state_dump(self) -> None:
        """
        Allow mDNSResponder to produce state dumps, which cache(), state_dump() and delete() need.

        This does what Apple's mDNSResponder logging profile does: it sets EnableStateDump in mDNSResponder's managed
        preferences, then restarts mDNSResponder to apply it (see clear()). The setting persists across reboots.
        """
        await self._set_state_dump_enabled(True)

    async def disable_state_dump(self) -> None:
        """Undo enable_state_dump(), restarting mDNSResponder (see clear())."""
        await self._set_state_dump_enabled(False)

    async def cache(self) -> DnsCache:
        """Get the records in mDNSResponder's DNS cache, with their remaining TTL, interface, data and DNSSEC status."""
        return parse_dns_cache(await self.state_dump())

    def records(self, name: str | None = None) -> list[DnsRecord]:
        """
        Get the records injected by add()/update() that are still registered. They aren't part of cache(), which only
        holds what mDNSResponder learned from the network.

        :param name: only get the records of this name
        """
        if name is None:
            return list(self._records)
        name = _normalize(name)
        return [record for record in self._records if _normalize(record.name) == name]

    async def add(
        self, name: str, rdata: str | bytes | list[str], rrtype: str | int = "A", ttl: int = DEFAULT_TTL
    ) -> DnsRecord:
        """
        Inject a record into mDNSResponder, which then answers queries for its name with it before consulting its
        cache or the network. The name's cached records are flushed so they aren't served alongside it.

        Only local domains can get A, AAAA and CNAME records: names under "local." (e.g. "test.local"),
        "254.169.in-addr.arpa." and "{8,9,a,b}.e.f.ip6.arpa.". mDNSResponder refuses them for any other name, root
        and entitlements notwithstanding, so that clients can't redirect other hosts. Other types can be added for
        any name.

        A name can have several records of the same type. They stay registered until they're removed, or until
        mDNSResponder or rpcserver exits.

        :param name: owner name (e.g. "test.local")
        :param rdata: record data, see encode_rdata()
        :param rrtype: record type name (e.g. "AAAA") or number
        :param ttl: TTL to answer with, in seconds
        :raises ArgumentError: for an A, AAAA or CNAME record outside the local domains
        """
        rrtype = _record_type(rrtype)
        if rrtype in _LOCAL_DOMAIN_ONLY_TYPES and not is_local_domain(name):
            raise ArgumentError(
                f"mDNSResponder only accepts A, AAAA and CNAME records for local domains (e.g. "
                f'"{name.split(".")[0]}.local"), not "{name}"'
            )
        encoded = encode_rdata(rrtype, rdata)
        connection = await self._get_connection()
        async with self._client.safe_calloc(8) as p_record:
            # the reply callback is only invoked from DNSServiceProcessResult(), which is never called, so any
            # function pointer will do
            result = await self._client.symbols.DNSServiceRegisterRecord(
                connection,
                p_record,
                _FLAGS_SHARED,
                _INTERFACE_LOCAL_ONLY,
                name,
                rrtype,
                _CLASS_IN,
                len(encoded),
                encoded,
                ttl,
                await self._client.symbols.getpid.resolve(),
                0,
            )
            _check_dnssd("DNSServiceRegisterRecord", result)
            record = DnsRecord(name, rrtype, encoded, ttl, await p_record.getindex(0))
        self._records.append(record)
        await self._flush_cached(name)
        return record

    async def update(
        self, name: str, rdata: str | bytes | list[str], rrtype: str | int = "A", ttl: int = DEFAULT_TTL
    ) -> DnsRecord:
        """
        Make rdata the only record injected for a name and type: replace the records add()/update() injected for them,
        or inject it if there are none. See add() for the parameters.
        """
        rrtype = _record_type(rrtype)
        existing = [record for record in self.records(name) if record.type == rrtype]
        if not existing:
            return await self.add(name, rdata, rrtype, ttl)

        encoded = encode_rdata(rrtype, rdata)
        record, *extra = existing
        result = await self._client.symbols.DNSServiceUpdateRecord(
            await self._get_connection(), record.ref, 0, len(encoded), encoded, ttl
        )
        _check_dnssd("DNSServiceUpdateRecord", result)
        record.rdata, record.ttl = encoded, ttl
        for other in extra:
            await self.remove(other)
        return record

    async def remove(self, record: DnsRecord) -> None:
        """
        Remove a record injected by add()/update().

        :raises ArgumentError: if the record isn't registered (anymore)
        """
        # its DNSRecordRef is freed once removed, and must never reach dns_sd again
        if record not in self._records:
            raise ArgumentError(f"{record.name} {record.type_name} record isn't registered")
        result = await self._client.symbols.DNSServiceRemoveRecord(await self._get_connection(), record.ref, 0)
        _check_dnssd("DNSServiceRemoveRecord", result)
        self._records.remove(record)

    async def remove_all(self) -> None:
        """Remove every record injected by add()/update(), leaving the cache as is."""
        if self._connection is not None:
            # mDNSResponder drops a connection's records along with it
            await self._client.symbols.DNSServiceRefDeallocate(self._connection)
            self._connection = None
        self._records.clear()

    async def delete(self, name: str) -> None:
        """
        Remove every record of a name: those injected by add()/update(), and all cached ones (any type, unicast and
        multicast).

        Flushing the cache requires rpcserver to be signed with the com.apple.private.mDNSResponder.record-cache.flush
        entitlement. Records referenced by an active question are re-resolved right away, so they may reappear.

        :param name: owner name (e.g. "www.apple.com")
        :raises BadReturnValueError: if records no active question references are still cached afterwards
        """
        for record in self.records(name):
            await self.remove(record)
        await self._flush_cached(name)
        remaining = [record for record in (await self.cache()).find(name) if not record.active_question]
        if remaining:
            raise BadReturnValueError(
                f"{len(remaining)} record(s) of {name} are still cached; is rpcserver signed with the "
                f"{_FLUSH_ENTITLEMENT} entitlement?"
            )

    async def clear(self) -> None:
        """
        Empty mDNSResponder's whole cache by restarting it, like network.flush_dns(). This removes the records injected
        by add()/update() too. Multicast (Bonjour) records are relearned right away, so the cache doesn't stay empty.
        """
        await self._client.network.flush_dns()
        await self.remove_all()

    async def _set_state_dump_enabled(self, enabled: bool) -> None:
        fs = self._client.fs
        path = _PREFERENCES_IOS if await self._client.is_idevice() else _PREFERENCES_MACOS
        preferences = plistlib.loads(await fs.read_file(path)) if await fs.accessible(path) else {}
        if enabled:
            preferences[_ENABLE_STATE_DUMP_KEY] = True
        else:
            preferences.pop(_ENABLE_STATE_DUMP_KEY, None)

        if preferences:
            await fs.mkdir(posixpath.dirname(path), parents=True, exist_ok=True)
            await fs.write_file(path, plistlib.dumps(preferences), access=0o644)
        elif await fs.accessible(path):
            await fs.remove(path)
        await self.clear()  # mDNSResponder only reads its managed preferences on startup

    async def _get_connection(self) -> DarwinSymbolT_co:
        if self._connection is None:
            async with self._client.safe_calloc(8) as p_connection:
                _check_dnssd(
                    "DNSServiceCreateConnection", await self._client.symbols.DNSServiceCreateConnection(p_connection)
                )
                self._connection = await p_connection.getindex(0)
        return self._connection

    async def _flush_cached(self, name: str) -> None:
        """Ask mDNSResponder to drop a name's cached records. It doesn't report whether it did."""
        if not self._mrc_loaded:
            for library in _MRC_LIBRARIES:
                if await self._client.dlopen(library, RTLD_NOW) == 0:
                    raise MissingLibraryError(f"failed to load {library}")
            self._mrc_loaded = True

        symbols = self._client.symbols
        domain = await symbols.mdns_domain_name_create(name, 0, 0)
        if domain == 0:
            raise BadReturnValueError(f"invalid domain name: {name}")
        try:
            flush = await symbols.mrc_record_cache_flush_create()
            if flush == 0:
                raise BadReturnValueError("failed to create a record cache flush")
            try:
                await symbols.mrc_record_cache_flush_set_queue(flush, await symbols.dispatch_get_global_queue(0, 0))
                await symbols.mrc_record_cache_flush_set_record_name(flush, domain)
                await symbols.mrc_record_cache_flush_set_result_handler(flush, await self._client.get_dummy_block())
                await symbols.mrc_record_cache_flush_activate(flush)
                await asyncio.sleep(_MRC_FLUSH_SETTLE_TIME)
            finally:
                await symbols.mrc_record_cache_flush_invalidate(flush)
                await symbols.mrc_release(flush)
        finally:
            await symbols.mdns_release(domain)
