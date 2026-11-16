# Darwin subsystems

Subsystems available on Darwin (macOS/iOS) clients, reached as attributes of the client (e.g. `p.fs`, `p.network`, `p.processes`).

## Filesystem

## rpcclient.clients.darwin.subsystems.fs

### DarwinFs

Bases: `Fs['DarwinClient[DarwinSymbolT_co]']`, `Generic[DarwinSymbolT_co]`

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/fs.py`

```
class DarwinFs(Fs["DarwinClient[DarwinSymbolT_co]"], Generic[DarwinSymbolT_co]):
    async def stat(self, path: str | PurePath) -> Container:
        """Return stat64 info for a remote path."""
        return await do_stat(self._client, "stat64", path)

    async def lstat(self, path: str | PurePath) -> Container:
        """Return lstat64 info for a remote path (does not follow symlinks)."""
        return await do_stat(self._client, "lstat64", path)

    async def setxattr(self, path: str | PurePath, name: str, value: bytes) -> None:
        """set an extended attribute value"""
        count = (await self._client.symbols.setxattr(path, name, value, len(value), 0, 0)).c_int64
        if count == -1:
            await self._client.raise_errno_exception(f"failed to setxattr(): {path}")

    async def removexattr(self, path: str | PurePath, name: str) -> None:
        """remove an extended attribute value"""
        count = (await self._client.symbols.removexattr(path, name, 0)).c_int64
        if count == -1:
            await self._client.raise_errno_exception(f"failed to removexattr(): {path}")

    async def listxattr(self, path: str | PurePath) -> list[str]:
        """list extended attribute names"""
        max_buf_len = 1024
        async with self._client.safe_malloc(max_buf_len) as xattributes_names:
            count = (await self._client.symbols.listxattr(path, xattributes_names, max_buf_len, 0)).c_int64
            if count == -1:
                await self._client.raise_errno_exception(f"failed to listxattr(): {path}")
            return [s.decode() for s in (await xattributes_names.peek(count)).split(b"\x00")[:-1]]

    async def getxattr(self, path: str | PurePath, name: str) -> bytes:
        """get an extended attribute value"""
        max_buf_len = 1024
        async with self._client.safe_malloc(max_buf_len) as value:
            count = (await self._client.symbols.getxattr(path, name, value, max_buf_len, 0, 0)).c_int64
            if count == -1:
                await self._client.raise_errno_exception(f"failed to getxattr(): {path}")
            return await value.peek(count)

    async def dictxattr(self, path: str | PurePath) -> dict[str, bytes]:
        """get a dictionary of all extended attributes"""
        result = {}
        for k in await self.listxattr(path):
            result[k] = await self.getxattr(path, k)
        return result

    async def statfs(self, path: str | PurePath) -> Container:
        async with self._client.safe_malloc(statfs64.sizeof()) as buf:
            if await self._client.symbols.statfs64(path, buf) != 0:
                await self._client.raise_errno_exception(f"statfs failed for: {path}")
            return await buf.parse(statfs64)

    async def chflags(self, path: str | PurePath, flags: int = 0) -> None:
        """Set BSD file flags on a remote path."""
        if (await self._client.symbols.chflags(path, flags)) != 0:
            await self._client.raise_errno_exception(f"chflags failed for: {path}")
```

#### stat

```
stat(path: str | PurePath) -> Container
```

Return stat64 info for a remote path.

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/fs.py`

```
async def stat(self, path: str | PurePath) -> Container:
    """Return stat64 info for a remote path."""
    return await do_stat(self._client, "stat64", path)
```

#### lstat

```
lstat(path: str | PurePath) -> Container
```

Return lstat64 info for a remote path (does not follow symlinks).

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/fs.py`

```
async def lstat(self, path: str | PurePath) -> Container:
    """Return lstat64 info for a remote path (does not follow symlinks)."""
    return await do_stat(self._client, "lstat64", path)
```

#### setxattr

```
setxattr(path: str | PurePath, name: str, value: bytes) -> None
```

set an extended attribute value

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/fs.py`

```
async def setxattr(self, path: str | PurePath, name: str, value: bytes) -> None:
    """set an extended attribute value"""
    count = (await self._client.symbols.setxattr(path, name, value, len(value), 0, 0)).c_int64
    if count == -1:
        await self._client.raise_errno_exception(f"failed to setxattr(): {path}")
```

#### removexattr

```
removexattr(path: str | PurePath, name: str) -> None
```

remove an extended attribute value

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/fs.py`

```
async def removexattr(self, path: str | PurePath, name: str) -> None:
    """remove an extended attribute value"""
    count = (await self._client.symbols.removexattr(path, name, 0)).c_int64
    if count == -1:
        await self._client.raise_errno_exception(f"failed to removexattr(): {path}")
```

#### listxattr

```
listxattr(path: str | PurePath) -> list[str]
```

list extended attribute names

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/fs.py`

```
async def listxattr(self, path: str | PurePath) -> list[str]:
    """list extended attribute names"""
    max_buf_len = 1024
    async with self._client.safe_malloc(max_buf_len) as xattributes_names:
        count = (await self._client.symbols.listxattr(path, xattributes_names, max_buf_len, 0)).c_int64
        if count == -1:
            await self._client.raise_errno_exception(f"failed to listxattr(): {path}")
        return [s.decode() for s in (await xattributes_names.peek(count)).split(b"\x00")[:-1]]
```

#### getxattr

```
getxattr(path: str | PurePath, name: str) -> bytes
```

get an extended attribute value

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/fs.py`

```
async def getxattr(self, path: str | PurePath, name: str) -> bytes:
    """get an extended attribute value"""
    max_buf_len = 1024
    async with self._client.safe_malloc(max_buf_len) as value:
        count = (await self._client.symbols.getxattr(path, name, value, max_buf_len, 0, 0)).c_int64
        if count == -1:
            await self._client.raise_errno_exception(f"failed to getxattr(): {path}")
        return await value.peek(count)
```

#### dictxattr

```
dictxattr(path: str | PurePath) -> dict[str, bytes]
```

get a dictionary of all extended attributes

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/fs.py`

```
async def dictxattr(self, path: str | PurePath) -> dict[str, bytes]:
    """get a dictionary of all extended attributes"""
    result = {}
    for k in await self.listxattr(path):
        result[k] = await self.getxattr(path, k)
    return result
```

#### chflags

```
chflags(path: str | PurePath, flags: int = 0) -> None
```

Set BSD file flags on a remote path.

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/fs.py`

```
async def chflags(self, path: str | PurePath, flags: int = 0) -> None:
    """Set BSD file flags on a remote path."""
    if (await self._client.symbols.chflags(path, flags)) != 0:
        await self._client.raise_errno_exception(f"chflags failed for: {path}")
```

### do_stat

```
do_stat(client: DarwinClient[DarwinSymbol], stat_name: str, filename: str | PurePath) -> Container
```

Return a stat64 struct for a remote path.

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/fs.py`

```
async def do_stat(client: "DarwinClient[DarwinSymbol]", stat_name: str, filename: str | PurePath) -> Container:
    """Return a stat64 struct for a remote path."""
    async with client.safe_malloc(stat64.sizeof()) as buf:
        err = await client.symbols[stat_name].call(filename, buf)
        if err != 0:
            await client.raise_errno_exception(f"failed to stat(): {filename}")
        return await buf.parse(stat64)
```

## Network

## rpcclient.clients.darwin.subsystems.network

### DarwinNetwork

Bases: `Network['DarwinClient[DarwinSymbolT_co]']`, `Generic[DarwinSymbolT_co]`

Network utils

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/network.py`

```
class DarwinNetwork(Network["DarwinClient[DarwinSymbolT_co]"], Generic[DarwinSymbolT_co]):
    """Network utils"""

    def __init__(self, client: "DarwinClient[DarwinSymbolT_co]") -> None:
        super().__init__(client)

    async def proxy_settings(self) -> dict:
        """Get proxy settings"""
        return await (await self._client.symbols.CFNetworkCopySystemProxySettings()).py(dict)

    async def set_http_proxy(self, ip: str, port: int) -> None:
        """Set http proxy"""
        async with await self._client.preferences.sc.open(SYSTEM_CONFIGURATION_PLIST) as config:
            await config.set(
                "Proxies",
                {
                    "HTTPProxyType": 1,
                    "HTTPEnable": 1,
                    "HTTPPort": port,
                    "HTTPSProxy": ip,
                    "HTTPSPort": port,
                    "HTTPProxy": ip,
                    "HTTPSEnable": 1,
                    "BypassAllowed": 0,
                },
            )
        await (await self._client.processes.get_by_basename("configd")).kill(SIGKILL)

    async def remove_http_proxy(self) -> None:
        """Remove http proxy settings"""
        async with await self._client.preferences.sc.open(SYSTEM_CONFIGURATION_PLIST) as config:
            await config.remove("Proxies")
        await (await self._client.processes.get_by_basename("configd")).kill(SIGKILL)

    async def remove_certificate_pinning(self) -> None:
        """Remove pinning rules from trustd"""
        async with self._client.fs.remote_file(PINNING_RULED_DB) as local_db_file:
            # truncate pinning rules
            conn = sqlite3.connect(local_db_file)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM rules")
            conn.commit()
            conn.close()

            # push new db
            await self._client.fs.push(local_db_file, PINNING_RULED_DB, force=True)

        # restart trustd for changes to take affect
        await self.kill_trustd()

    async def restore_certificate_pinning(self) -> None:
        """Restore pinning rules from trustd"""
        if await self._client.fs.accessible(PINNING_RULED_DB):
            await self._client.fs.remove(PINNING_RULED_DB)

        # Upon startup trustd to reloads pinning rules from the last MobileAsset
        await self.kill_trustd()

    async def kill_trustd(self) -> None:
        """Kill trustd processes"""
        for process in await self._client.processes.list():
            if await type(process).basename(process) == "trustd":
                await process.kill(SIGKILL)

    async def flush_dns(self) -> None:
        """Flush DNS cache"""
        await (await self._client.processes.get_by_basename("mDNSResponder")).kill(SIGKILL)
```

#### proxy_settings

```
proxy_settings() -> dict
```

Get proxy settings

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/network.py`

```
async def proxy_settings(self) -> dict:
    """Get proxy settings"""
    return await (await self._client.symbols.CFNetworkCopySystemProxySettings()).py(dict)
```

#### set_http_proxy

```
set_http_proxy(ip: str, port: int) -> None
```

Set http proxy

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/network.py`

```
async def set_http_proxy(self, ip: str, port: int) -> None:
    """Set http proxy"""
    async with await self._client.preferences.sc.open(SYSTEM_CONFIGURATION_PLIST) as config:
        await config.set(
            "Proxies",
            {
                "HTTPProxyType": 1,
                "HTTPEnable": 1,
                "HTTPPort": port,
                "HTTPSProxy": ip,
                "HTTPSPort": port,
                "HTTPProxy": ip,
                "HTTPSEnable": 1,
                "BypassAllowed": 0,
            },
        )
    await (await self._client.processes.get_by_basename("configd")).kill(SIGKILL)
```

#### remove_http_proxy

```
remove_http_proxy() -> None
```

Remove http proxy settings

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/network.py`

```
async def remove_http_proxy(self) -> None:
    """Remove http proxy settings"""
    async with await self._client.preferences.sc.open(SYSTEM_CONFIGURATION_PLIST) as config:
        await config.remove("Proxies")
    await (await self._client.processes.get_by_basename("configd")).kill(SIGKILL)
```

#### remove_certificate_pinning

```
remove_certificate_pinning() -> None
```

Remove pinning rules from trustd

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/network.py`

```
async def remove_certificate_pinning(self) -> None:
    """Remove pinning rules from trustd"""
    async with self._client.fs.remote_file(PINNING_RULED_DB) as local_db_file:
        # truncate pinning rules
        conn = sqlite3.connect(local_db_file)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM rules")
        conn.commit()
        conn.close()

        # push new db
        await self._client.fs.push(local_db_file, PINNING_RULED_DB, force=True)

    # restart trustd for changes to take affect
    await self.kill_trustd()
```

#### restore_certificate_pinning

```
restore_certificate_pinning() -> None
```

Restore pinning rules from trustd

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/network.py`

```
async def restore_certificate_pinning(self) -> None:
    """Restore pinning rules from trustd"""
    if await self._client.fs.accessible(PINNING_RULED_DB):
        await self._client.fs.remove(PINNING_RULED_DB)

    # Upon startup trustd to reloads pinning rules from the last MobileAsset
    await self.kill_trustd()
```

#### kill_trustd

```
kill_trustd() -> None
```

Kill trustd processes

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/network.py`

```
async def kill_trustd(self) -> None:
    """Kill trustd processes"""
    for process in await self._client.processes.list():
        if await type(process).basename(process) == "trustd":
            await process.kill(SIGKILL)
```

#### flush_dns

```
flush_dns() -> None
```

Flush DNS cache

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/network.py`

```
async def flush_dns(self) -> None:
    """Flush DNS cache"""
    await (await self._client.processes.get_by_basename("mDNSResponder")).kill(SIGKILL)
```

## DNS

## rpcclient.clients.darwin.subsystems.dns

mDNSResponder access: read its DNS cache and state, inject local records and flush cached ones.

Everything here requires rpcserver to run as root.

### DnsCacheRecord

A resource record held in mDNSResponder's cache.

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/dns.py`

```
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
```

#### display_name

```
display_name: str
```

The owner name with mDNSResponder's escapes decoded.

#### display_data

```
display_data: str
```

The record data with mDNSResponder's escapes decoded.

### DnsCache

A snapshot of mDNSResponder's DNS cache. Prints as a table.

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/dns.py`

```
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
```

#### find

```
find(name: str) -> list[DnsCacheRecord]
```

Get the cached records of a name.

Parameters:

| Name   | Type  | Description                                                   | Default    |
| ------ | ----- | ------------------------------------------------------------- | ---------- |
| `name` | `str` | owner name; case-insensitive and the trailing dot is optional | *required* |

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/dns.py`

```
def find(self, name: str) -> list[DnsCacheRecord]:
    """
    Get the cached records of a name.

    :param name: owner name; case-insensitive and the trailing dot is optional
    """
    name = _normalize(name)
    return [record for record in self.records if record.name is not None and _normalize(record.name) == name]
```

### DnsStateDump

Bases: `str`

An mDNSResponder state dump. Prints as plain text and splits into its "---- Title ----" sections.

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/dns.py`

```
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
```

#### sections

```
sections() -> dict[str, str]
```

Get the dump's sections as {title: body}, e.g. "Cache", "Questions" or "DNS Services".

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/dns.py`

```
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
```

#### section

```
section(title: str) -> str
```

Get a section's body.

Parameters:

| Name    | Type  | Description                     | Default    |
| ------- | ----- | ------------------------------- | ---------- |
| `title` | `str` | section title, case-insensitive | *required* |

Raises:

| Type       | Description                 |
| ---------- | --------------------------- |
| `KeyError` | if there is no such section |

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/dns.py`

```
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
```

### DnsRecord

A record injected into mDNSResponder by Dns.add() or Dns.update().

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/dns.py`

```
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
```

### Dns

Bases: `ClientBound['DarwinClient[DarwinSymbolT_co]']`, `Generic[DarwinSymbolT_co]`

mDNSResponder's DNS cache: read it, inject local records into it and flush records from it.

- read: cache(), state_dump()
- create: add()
- update: update()
- delete: remove(), delete(), remove_all(), clear()

Reading needs the state dump enabled once per device, see enable_state_dump().

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/dns.py`

```
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
```

#### state_dump

```
state_dump(keep_file: bool = False) -> DnsStateDump
```

Get mDNSResponder's full state dump, like `dns-sd -O`: its cache, questions, registered records, resolver configuration and more.

Parameters:

| Name        | Type   | Description                                                                          | Default |
| ----------- | ------ | ------------------------------------------------------------------------------------ | ------- |
| `keep_file` | `bool` | keep the file mDNSResponder writes the dump to, under /private/var/log/mDNSResponder | `False` |

Raises:

| Type                  | Description                                                         |
| --------------------- | ------------------------------------------------------------------- |
| `BadReturnValueError` | if mDNSResponder refuses, e.g. because the state dump isn't enabled |

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/dns.py`

```
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
```

#### enable_state_dump

```
enable_state_dump() -> None
```

Allow mDNSResponder to produce state dumps, which cache(), state_dump() and delete() need.

This does what Apple's mDNSResponder logging profile does: it sets EnableStateDump in mDNSResponder's managed preferences, then restarts mDNSResponder to apply it (see clear()). The setting persists across reboots.

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/dns.py`

```
async def enable_state_dump(self) -> None:
    """
    Allow mDNSResponder to produce state dumps, which cache(), state_dump() and delete() need.

    This does what Apple's mDNSResponder logging profile does: it sets EnableStateDump in mDNSResponder's managed
    preferences, then restarts mDNSResponder to apply it (see clear()). The setting persists across reboots.
    """
    await self._set_state_dump_enabled(True)
```

#### disable_state_dump

```
disable_state_dump() -> None
```

Undo enable_state_dump(), restarting mDNSResponder (see clear()).

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/dns.py`

```
async def disable_state_dump(self) -> None:
    """Undo enable_state_dump(), restarting mDNSResponder (see clear())."""
    await self._set_state_dump_enabled(False)
```

#### cache

```
cache() -> DnsCache
```

Get the records in mDNSResponder's DNS cache, with their remaining TTL, interface, data and DNSSEC status.

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/dns.py`

```
async def cache(self) -> DnsCache:
    """Get the records in mDNSResponder's DNS cache, with their remaining TTL, interface, data and DNSSEC status."""
    return parse_dns_cache(await self.state_dump())
```

#### records

```
records(name: str | None = None) -> list[DnsRecord]
```

Get the records injected by add()/update() that are still registered. They aren't part of cache(), which only holds what mDNSResponder learned from the network.

Parameters:

| Name   | Type  | Description | Default                           |
| ------ | ----- | ----------- | --------------------------------- |
| `name` | \`str | None\`      | only get the records of this name |

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/dns.py`

```
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
```

#### add

```
add(name: str, rdata: str | bytes | list[str], rrtype: str | int = 'A', ttl: int = DEFAULT_TTL) -> DnsRecord
```

Inject a record into mDNSResponder, which then answers queries for its name with it before consulting its cache or the network. The name's cached records are flushed so they aren't served alongside it.

Only local domains can get A, AAAA and CNAME records: names under "local." (e.g. "test.local"), "254.169.in-addr.arpa." and "{8,9,a,b}.e.f.ip6.arpa.". mDNSResponder refuses them for any other name, root and entitlements notwithstanding, so that clients can't redirect other hosts. Other types can be added for any name.

A name can have several records of the same type. They stay registered until they're removed, or until mDNSResponder or rpcserver exits.

Parameters:

| Name     | Type  | Description                    | Default                                  |
| -------- | ----- | ------------------------------ | ---------------------------------------- |
| `name`   | `str` | owner name (e.g. "test.local") | *required*                               |
| `rdata`  | \`str | bytes                          | list[str]\`                              |
| `rrtype` | \`str | int\`                          | record type name (e.g. "AAAA") or number |
| `ttl`    | `int` | TTL to answer with, in seconds | `DEFAULT_TTL`                            |

Raises:

| Type            | Description                                              |
| --------------- | -------------------------------------------------------- |
| `ArgumentError` | for an A, AAAA or CNAME record outside the local domains |

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/dns.py`

```
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
```

#### update

```
update(name: str, rdata: str | bytes | list[str], rrtype: str | int = 'A', ttl: int = DEFAULT_TTL) -> DnsRecord
```

Make rdata the only record injected for a name and type: replace the records add()/update() injected for them, or inject it if there are none. See add() for the parameters.

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/dns.py`

```
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
```

#### remove

```
remove(record: DnsRecord) -> None
```

Remove a record injected by add()/update().

Raises:

| Type            | Description                              |
| --------------- | ---------------------------------------- |
| `ArgumentError` | if the record isn't registered (anymore) |

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/dns.py`

```
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
```

#### remove_all

```
remove_all() -> None
```

Remove every record injected by add()/update(), leaving the cache as is.

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/dns.py`

```
async def remove_all(self) -> None:
    """Remove every record injected by add()/update(), leaving the cache as is."""
    if self._connection is not None:
        # mDNSResponder drops a connection's records along with it
        await self._client.symbols.DNSServiceRefDeallocate(self._connection)
        self._connection = None
    self._records.clear()
```

#### delete

```
delete(name: str) -> None
```

Remove every record of a name: those injected by add()/update(), and all cached ones (any type, unicast and multicast).

Flushing the cache requires rpcserver to be signed with the com.apple.private.mDNSResponder.record-cache.flush entitlement. Records referenced by an active question are re-resolved right away, so they may reappear.

Parameters:

| Name   | Type  | Description                       | Default    |
| ------ | ----- | --------------------------------- | ---------- |
| `name` | `str` | owner name (e.g. "www.apple.com") | *required* |

Raises:

| Type                  | Description                                                          |
| --------------------- | -------------------------------------------------------------------- |
| `BadReturnValueError` | if records no active question references are still cached afterwards |

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/dns.py`

```
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
```

#### clear

```
clear() -> None
```

Empty mDNSResponder's whole cache by restarting it, like network.flush_dns(). This removes the records injected by add()/update() too. Multicast (Bonjour) records are relearned right away, so the cache doesn't stay empty.

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/dns.py`

```
async def clear(self) -> None:
    """
    Empty mDNSResponder's whole cache by restarting it, like network.flush_dns(). This removes the records injected
    by add()/update() too. Multicast (Bonjour) records are relearned right away, so the cache doesn't stay empty.
    """
    await self._client.network.flush_dns()
    await self.remove_all()
```

### is_local_domain

```
is_local_domain(name: str) -> bool
```

Tell whether a name is resolved via link-local multicast, as mDNSResponder's IsLocalDomain() defines it.

Parameters:

| Name   | Type  | Description                                   | Default    |
| ------ | ----- | --------------------------------------------- | ---------- |
| `name` | `str` | domain name, with or without the trailing dot | *required* |

Returns:

| Type   | Description                                                                          |
| ------ | ------------------------------------------------------------------------------------ |
| `bool` | True for names under "local.", "254.169.in-addr.arpa." and "{8,9,a,b}.e.f.ip6.arpa." |

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/dns.py`

```
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
```

### encode_rdata

```
encode_rdata(rrtype: int, rdata: str | bytes | list[str]) -> bytes
```

Encode record data into its wire format.

Parameters:

| Name     | Type  | Description                           | Default     |
| -------- | ----- | ------------------------------------- | ----------- |
| `rrtype` | `int` | record type number (see RECORD_TYPES) | *required*  |
| `rdata`  | \`str | bytes                                 | list[str]\` |

Returns:

| Type    | Description           |
| ------- | --------------------- |
| `bytes` | the wire-format rdata |

Raises:

| Type         | Description                                                    |
| ------------ | -------------------------------------------------------------- |
| `TypeError`  | for a list of strings for a type other than TXT                |
| `ValueError` | for malformed rdata, or a type that can only be given as bytes |

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/dns.py`

```
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
```

### parse_dns_cache

```
parse_dns_cache(state_dump: str) -> DnsCache
```

Parse the "Cache" section of an mDNSResponder state dump.

Parameters:

| Name         | Type  | Description                               | Default    |
| ------------ | ----- | ----------------------------------------- | ---------- |
| `state_dump` | `str` | the dump, as returned by Dns.state_dump() | *required* |

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/dns.py`

```
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
```

## Processes

## rpcclient.clients.darwin.subsystems.processes

### Thread

Bases: `ClientBound[DarwinClientT_co]`

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/processes.py`

```
class Thread(ClientBound[DarwinClientT_co]):
    def __init__(self, client: DarwinClientT_co, thread_id: int) -> None:
        """Initialize a thread wrapper for the given client and thread id."""
        self._client = client
        self._thread_id: int = thread_id

    @property
    def thread_id(self) -> int:
        """Return the Mach thread id."""
        return self._thread_id

    async def get_state(self) -> Container:
        """Return the architecture-specific thread state."""
        raise NotImplementedError()

    async def set_state(self, state: dict) -> None:
        """Set the architecture-specific thread state."""
        raise NotImplementedError()

    async def resume(self) -> None:
        """Resume execution of the thread."""
        raise NotImplementedError()

    async def suspend(self) -> None:
        """Suspend execution of the thread."""
        raise NotImplementedError()

    def __repr__(self) -> str:
        """Return a debug representation of the thread."""
        return f"<{self.__class__.__name__} TID:{self._thread_id}>"
```

#### thread_id

```
thread_id: int
```

Return the Mach thread id.

#### get_state

```
get_state() -> Container
```

Return the architecture-specific thread state.

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/processes.py`

```
async def get_state(self) -> Container:
    """Return the architecture-specific thread state."""
    raise NotImplementedError()
```

#### set_state

```
set_state(state: dict) -> None
```

Set the architecture-specific thread state.

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/processes.py`

```
async def set_state(self, state: dict) -> None:
    """Set the architecture-specific thread state."""
    raise NotImplementedError()
```

#### resume

```
resume() -> None
```

Resume execution of the thread.

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/processes.py`

```
async def resume(self) -> None:
    """Resume execution of the thread."""
    raise NotImplementedError()
```

#### suspend

```
suspend() -> None
```

Suspend execution of the thread.

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/processes.py`

```
async def suspend(self) -> None:
    """Suspend execution of the thread."""
    raise NotImplementedError()
```

### IntelThread64

Bases: `Thread[DarwinClientT_co]`

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/processes.py`

```
class IntelThread64(Thread[DarwinClientT_co]):
    async def get_state(self) -> Container:
        """Fetch the x86_64 thread state."""
        async with (
            self._client.safe_malloc(x86_thread_state64_t.sizeof()) as p_state,
            self._client.safe_malloc(x86_thread_state64_t.sizeof()) as p_thread_state_count,
        ):
            await p_thread_state_count.setindex(0, x86_thread_state64_t.sizeof() // Int32ul.sizeof())
            if await self._client.symbols.thread_get_state(
                self._thread_id, x86_THREAD_STATE64, p_state, p_thread_state_count
            ):
                raise BadReturnValueError("thread_get_state() failed")
            return await p_state.parse(x86_thread_state64_t)

    async def set_state(self, state: dict) -> None:
        """Set the x86_64 thread state."""
        if await self._client.symbols.thread_set_state(
            self._thread_id,
            x86_THREAD_STATE64,
            x86_thread_state64_t.build(state),
            x86_thread_state64_t.sizeof() // Int32ul.sizeof(),
        ):
            raise BadReturnValueError("thread_set_state() failed")
```

#### get_state

```
get_state() -> Container
```

Fetch the x86_64 thread state.

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/processes.py`

```
async def get_state(self) -> Container:
    """Fetch the x86_64 thread state."""
    async with (
        self._client.safe_malloc(x86_thread_state64_t.sizeof()) as p_state,
        self._client.safe_malloc(x86_thread_state64_t.sizeof()) as p_thread_state_count,
    ):
        await p_thread_state_count.setindex(0, x86_thread_state64_t.sizeof() // Int32ul.sizeof())
        if await self._client.symbols.thread_get_state(
            self._thread_id, x86_THREAD_STATE64, p_state, p_thread_state_count
        ):
            raise BadReturnValueError("thread_get_state() failed")
        return await p_state.parse(x86_thread_state64_t)
```

#### set_state

```
set_state(state: dict) -> None
```

Set the x86_64 thread state.

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/processes.py`

```
async def set_state(self, state: dict) -> None:
    """Set the x86_64 thread state."""
    if await self._client.symbols.thread_set_state(
        self._thread_id,
        x86_THREAD_STATE64,
        x86_thread_state64_t.build(state),
        x86_thread_state64_t.sizeof() // Int32ul.sizeof(),
    ):
        raise BadReturnValueError("thread_set_state() failed")
```

### ArmThread64

Bases: `Thread[DarwinClientT_co]`

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/processes.py`

```
class ArmThread64(Thread[DarwinClientT_co]):
    async def get_state(self) -> Container:
        """Fetch the ARM64 thread state."""
        async with (
            self._client.safe_malloc(arm_thread_state64_t.sizeof()) as p_state,
            self._client.safe_malloc(arm_thread_state64_t.sizeof()) as p_thread_state_count,
        ):
            await p_thread_state_count.setindex(0, ARM_THREAD_STATE64_COUNT)
            if await self._client.symbols.thread_get_state(
                self._thread_id, ARMThreadFlavors.ARM_THREAD_STATE64, p_state, p_thread_state_count
            ):
                raise BadReturnValueError("thread_get_state() failed")
            return await p_state.parse(arm_thread_state64_t)

    async def set_state(self, state: dict) -> None:
        """Set the ARM64 thread state."""
        if await self._client.symbols.thread_set_state(
            self._thread_id,
            ARMThreadFlavors.ARM_THREAD_STATE64,
            arm_thread_state64_t.build(state),
            ARM_THREAD_STATE64_COUNT,
        ):
            raise BadReturnValueError("thread_set_state() failed")

    async def suspend(self) -> None:
        """Suspend execution of the ARM64 thread."""
        if await self._client.symbols.thread_suspend(self._thread_id):
            raise BadReturnValueError("thread_suspend() failed")

    async def resume(self) -> None:
        """Resume execution of the ARM64 thread."""
        if await self._client.symbols.thread_resume(self._thread_id):
            raise BadReturnValueError("thread_resume() failed")
```

#### get_state

```
get_state() -> Container
```

Fetch the ARM64 thread state.

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/processes.py`

```
async def get_state(self) -> Container:
    """Fetch the ARM64 thread state."""
    async with (
        self._client.safe_malloc(arm_thread_state64_t.sizeof()) as p_state,
        self._client.safe_malloc(arm_thread_state64_t.sizeof()) as p_thread_state_count,
    ):
        await p_thread_state_count.setindex(0, ARM_THREAD_STATE64_COUNT)
        if await self._client.symbols.thread_get_state(
            self._thread_id, ARMThreadFlavors.ARM_THREAD_STATE64, p_state, p_thread_state_count
        ):
            raise BadReturnValueError("thread_get_state() failed")
        return await p_state.parse(arm_thread_state64_t)
```

#### set_state

```
set_state(state: dict) -> None
```

Set the ARM64 thread state.

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/processes.py`

```
async def set_state(self, state: dict) -> None:
    """Set the ARM64 thread state."""
    if await self._client.symbols.thread_set_state(
        self._thread_id,
        ARMThreadFlavors.ARM_THREAD_STATE64,
        arm_thread_state64_t.build(state),
        ARM_THREAD_STATE64_COUNT,
    ):
        raise BadReturnValueError("thread_set_state() failed")
```

#### suspend

```
suspend() -> None
```

Suspend execution of the ARM64 thread.

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/processes.py`

```
async def suspend(self) -> None:
    """Suspend execution of the ARM64 thread."""
    if await self._client.symbols.thread_suspend(self._thread_id):
        raise BadReturnValueError("thread_suspend() failed")
```

#### resume

```
resume() -> None
```

Resume execution of the ARM64 thread.

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/processes.py`

```
async def resume(self) -> None:
    """Resume execution of the ARM64 thread."""
    if await self._client.symbols.thread_resume(self._thread_id):
        raise BadReturnValueError("thread_resume() failed")
```

### Region

Bases: `Generic[DarwinSymbolT_co]`

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/processes.py`

```
@dataclasses.dataclass
class Region(Generic[DarwinSymbolT_co]):
    region_type: str
    start: "ProcessSymbol[DarwinSymbolT_co]"
    end: int
    vsize: str | None
    protection: str
    protection_max: str
    region_detail: str | None

    @property
    def size(self) -> int:
        """Return the region size in bytes."""
        return self.end - self.start
```

#### size

```
size: int
```

Return the region size in bytes.

### Frame

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/processes.py`

```
@dataclasses.dataclass
class Frame:
    depth: int
    address: int
    section: str
    offset: int
    symbol_name: str

    def __repr__(self):
        """Return a formatted frame representation."""
        return (
            f"<{self.__class__.__name__} [{self.depth:3}] 0x{self.address:x} ({self.section} + 0x{self.offset:x}) "
            f"{self.symbol_name}>"
        )
```

### Backtrace

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/processes.py`

```
@dataclasses.dataclass(kw_only=True)
class Backtrace:
    flavor: str
    time_start: float | None = None
    time_end: float | None = None
    pid: int
    thread_id: int
    dispatch_queue_serial_num: int
    frames: list[Frame]

    @staticmethod
    async def _from_backtrace(vmu_backtrace: DarwinSymbol) -> "Backtrace":
        """Parse a VMU backtrace description into structured fields."""
        backtrace = await (await vmu_backtrace.objc_call("description")).py(str)
        match = re.match(
            (
                r"VMUBacktrace \(Flavor: (?P<flavor>.+?) Simple Time: (?P<time>.+?) "
                r"Process: (?P<pid>\d+) Thread: (?P<thread_id>.+?)  Dispatch queue serial num: "
                r"(?P<dispatch_queue_serial_num>\d+)\)"
            ),
            backtrace,
        )
        assert match is not None

        return Backtrace(
            flavor=match.group("flavor"),
            pid=int(match.group("pid")),
            thread_id=int(match.group("thread_id"), 16),
            dispatch_queue_serial_num=int(match.group("dispatch_queue_serial_num")),
            frames=[
                Frame(
                    depth=int(frame[0]),
                    address=int(frame[1], 0),
                    section=frame[2],
                    offset=int(frame[3], 0),
                    symbol_name=frame[4],
                )
                for frame in re.findall(_BACKTRACE_FRAME_REGEX, backtrace)
            ],
        )

    def __repr__(self) -> str:
        """Return a formatted backtrace representation."""
        buf = f"<{self.__class__.__name__} PID: {self.pid} TID: {self.thread_id}\n"
        for frame in self.frames:
            buf += f"    {frame}\n"
        buf += ">"
        return buf
```

### ProcessSymbol

Bases: `AbstractSymbol`, `ClientBound['DarwinClient[DarwinSymbolT_co]']`, `Generic[DarwinSymbolT_co]`

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/processes.py`

```
class ProcessSymbol(AbstractSymbol, ClientBound["DarwinClient[DarwinSymbolT_co]"], Generic[DarwinSymbolT_co]):
    def __init__(self, value: int, process: "Process[DarwinSymbolT_co]") -> None:
        self._client: DarwinClient[DarwinSymbolT_co] = process._client
        self.process: Process[DarwinSymbolT_co] = process

    def _symbol_from_value(self, value: int) -> Self:
        """Clone this symbol for the given value."""
        return type(self)(value, self.process)

    async def peek(self, count: int, offset: int = 0) -> bytes:
        """Read bytes from process memory at this address."""
        return await self.process.peek(self + offset, count)

    async def poke(self, buf: bytes, offset: int = 0) -> None:
        """Write bytes to process memory at this address."""
        return await self.process.poke(self + offset, buf)

    async def peek_str(self, encoding="utf-8") -> str:
        """peek string at given address"""
        return await self.process.peek_str(self, encoding)

    async def dl_info(self) -> Container:
        """Raise because dl_info is not available for remote process symbols."""
        raise NotImplementedError("dl_info isn't implemented for remote process symbols")

    async def name(self) -> str:
        """Return the symbol name for this address."""
        return await self.process.get_symbol_name(self)

    async def filename(self) -> str:
        """Return the image path containing this symbol."""
        return (await self.process.get_symbol_image(await type(self).name(self))).path

    async def get_dl_info(self) -> "Container":
        dl_info = Dl_info(self._client)
        sizeof = dl_info.sizeof()
        async with self._client.safe_malloc(sizeof) as info:
            if await self._client.symbols.dladdr(self, info) == 0:
                await self._client.raise_errno_exception(f"failed to extract info for: {self}")
            return dl_info.parse(await info.read(sizeof))

    @property
    def arch(self) -> object:
        return self._client.arch

    @property
    def endianness(self) -> str:
        return self._client._endianness

    def call(self, *args, **kwargs) -> NoReturn:
        """Disallow calling a process symbol as a function."""
        raise RpcClientException("ProcessSymbol is not callable")

    __call__ = call
```

#### peek

```
peek(count: int, offset: int = 0) -> bytes
```

Read bytes from process memory at this address.

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/processes.py`

```
async def peek(self, count: int, offset: int = 0) -> bytes:
    """Read bytes from process memory at this address."""
    return await self.process.peek(self + offset, count)
```

#### poke

```
poke(buf: bytes, offset: int = 0) -> None
```

Write bytes to process memory at this address.

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/processes.py`

```
async def poke(self, buf: bytes, offset: int = 0) -> None:
    """Write bytes to process memory at this address."""
    return await self.process.poke(self + offset, buf)
```

#### peek_str

```
peek_str(encoding='utf-8') -> str
```

peek string at given address

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/processes.py`

```
async def peek_str(self, encoding="utf-8") -> str:
    """peek string at given address"""
    return await self.process.peek_str(self, encoding)
```

#### dl_info

```
dl_info() -> Container
```

Raise because dl_info is not available for remote process symbols.

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/processes.py`

```
async def dl_info(self) -> Container:
    """Raise because dl_info is not available for remote process symbols."""
    raise NotImplementedError("dl_info isn't implemented for remote process symbols")
```

#### name

```
name() -> str
```

Return the symbol name for this address.

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/processes.py`

```
async def name(self) -> str:
    """Return the symbol name for this address."""
    return await self.process.get_symbol_name(self)
```

#### filename

```
filename() -> str
```

Return the image path containing this symbol.

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/processes.py`

```
async def filename(self) -> str:
    """Return the image path containing this symbol."""
    return (await self.process.get_symbol_image(await type(self).name(self))).path
```

#### call

```
call(*args, **kwargs) -> NoReturn
```

Disallow calling a process symbol as a function.

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/processes.py`

```
def call(self, *args, **kwargs) -> NoReturn:
    """Disallow calling a process symbol as a function."""
    raise RpcClientException("ProcessSymbol is not callable")
```

### MachPortKobjectInfo

Identity of the kernel object a port names (a task, thread, host, clock, IOKit object, ...).

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/processes.py`

```
@dataclasses.dataclass
class MachPortKobjectInfo:
    """Identity of the kernel object a port names (a task, thread, host, clock, IOKit object, ...)."""

    type_id: int  # raw IKOT_* value
    type: str  # human-readable IKOT_* name, e.g. "TASK_CONTROL"
    addr: int  # kernel object address (as reported by mach_port_kernel_object, may be truncated)
```

### MachPortExceptionInfo

A port registered as an exception handler (for a task or one of its threads).

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/processes.py`

```
@dataclasses.dataclass
class MachPortExceptionInfo:
    """A port registered as an exception handler (for a task or one of its threads)."""

    masks: list[str]  # decoded EXC_MASK_* names this handler is registered for
    behavior: int  # exception_behavior_t (raw, incl. MACH_EXCEPTION_* flags)
    flavor: int  # thread_state_flavor_t (raw)
```

### MachPortInfo

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/processes.py`

```
@dataclasses.dataclass
class MachPortInfo:
    task: int
    pid: int
    name: int
    rights: list[str]
    ipc_object: int
    dead: bool
    proc_name: str | None = None
    thread_info: MachPortThreadInfo | None = None
    kobject: MachPortKobjectInfo | None = None
    exception: MachPortExceptionInfo | None = None

    @property
    def has_recv_right(self) -> bool:
        """Return True if the port has a receive right."""
        return "recv" in self.rights

    @property
    def has_send_right(self) -> bool:
        """Return True if the port has a send right."""
        return "send" in self.rights

    @property
    def has_send_once_right(self) -> bool:
        """Return True if the port has a send-once right."""
        return "send-once" in self.rights
```

#### has_recv_right

```
has_recv_right: bool
```

Return True if the port has a receive right.

#### has_send_right

```
has_send_right: bool
```

Return True if the port has a send right.

#### has_send_once_right

```
has_send_once_right: bool
```

Return True if the port has a send-once right.

### SymbolOwner

Bases: `ClientBound['DarwinClient[DarwinSymbolT_co]']`, `Generic[DarwinSymbolT_co]`

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/processes.py`

```
class SymbolOwner(ClientBound["DarwinClient[DarwinSymbolT_co]"], Generic[DarwinSymbolT_co]):
    def __init__(
        self,
        client: "DarwinClient[DarwinSymbolT_co]",
        process: "Process[DarwinSymbolT_co]",
        symbol_owner_opaque1: ProcessSymbol[DarwinSymbolT_co],
        symbol_owner_opaque2: ProcessSymbol[DarwinSymbolT_co],
    ) -> None:
        """Initialize a symbol owner wrapper."""
        self._client: DarwinClient[DarwinSymbolT_co] = client
        self._process: Process[DarwinSymbolT_co] = process
        self.symbol_owner_opaque1: ProcessSymbol[DarwinSymbolT_co] = symbol_owner_opaque1
        self.symbol_owner_opaque2: ProcessSymbol[DarwinSymbolT_co] = symbol_owner_opaque2

    async def get_symbol_address(self, name: str) -> ProcessSymbol[DarwinSymbolT_co]:
        """Resolve a symbol address by name."""
        symbol = await self._client.symbols.CSSymbolOwnerGetSymbolWithName(
            self.symbol_owner_opaque1,
            self.symbol_owner_opaque2,
            name,
            return_raw=True,
        )

        return self._process.get_process_symbol(await self._client.symbols.CSSymbolGetRange(symbol.x0, symbol.x1))
```

#### get_symbol_address

```
get_symbol_address(name: str) -> ProcessSymbol[DarwinSymbolT_co]
```

Resolve a symbol address by name.

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/processes.py`

```
async def get_symbol_address(self, name: str) -> ProcessSymbol[DarwinSymbolT_co]:
    """Resolve a symbol address by name."""
    symbol = await self._client.symbols.CSSymbolOwnerGetSymbolWithName(
        self.symbol_owner_opaque1,
        self.symbol_owner_opaque2,
        name,
        return_raw=True,
    )

    return self._process.get_process_symbol(await self._client.symbols.CSSymbolGetRange(symbol.x0, symbol.x1))
```

### Symbolicator

Bases: `ClientBound['DarwinClient[DarwinSymbolT_co]']`, `Generic[DarwinSymbolT_co]`

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/processes.py`

```
class Symbolicator(ClientBound["DarwinClient[DarwinSymbolT_co]"], Generic[DarwinSymbolT_co]):
    def __init__(
        self,
        client: "DarwinClient[DarwinSymbolT_co]",
        process: "Process[DarwinSymbolT_co]",
        symbolicator_opaque1: ProcessSymbol[DarwinSymbolT_co],
        symbolicator_opaque2: ProcessSymbol[DarwinSymbolT_co],
    ) -> None:
        """Initialize a symbolicator wrapper."""
        self._client: DarwinClient[DarwinSymbolT_co] = client
        self._process: Process[DarwinSymbolT_co] = process
        self.symbolicator_opaque1: ProcessSymbol[DarwinSymbolT_co] = symbolicator_opaque1
        self.symbolicator_opaque2: ProcessSymbol[DarwinSymbolT_co] = symbolicator_opaque2

    async def get_symbol_owner(self, library_basename: str) -> SymbolOwner[DarwinSymbolT_co]:
        """Resolve a symbol owner by library basename."""
        symbol_owner = await self._client.symbols.CSSymbolicatorGetSymbolOwnerWithNameAtTime(
            self.symbolicator_opaque1,
            self.symbolicator_opaque2,
            library_basename,
            kCSNow,
            return_raw=True,
        )
        return SymbolOwner(self._client, self._process, symbol_owner.x0, symbol_owner.x1)
```

#### get_symbol_owner

```
get_symbol_owner(library_basename: str) -> SymbolOwner[DarwinSymbolT_co]
```

Resolve a symbol owner by library basename.

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/processes.py`

```
async def get_symbol_owner(self, library_basename: str) -> SymbolOwner[DarwinSymbolT_co]:
    """Resolve a symbol owner by library basename."""
    symbol_owner = await self._client.symbols.CSSymbolicatorGetSymbolOwnerWithNameAtTime(
        self.symbolicator_opaque1,
        self.symbolicator_opaque2,
        library_basename,
        kCSNow,
        return_raw=True,
    )
    return SymbolOwner(self._client, self._process, symbol_owner.x0, symbol_owner.x1)
```

### Process

Bases: `ClientBound['DarwinClient[DarwinSymbolT_co]']`, `Generic[DarwinSymbolT_co]`

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/processes.py`

```
class Process(ClientBound["DarwinClient[DarwinSymbolT_co]"], Generic[DarwinSymbolT_co]):
    PEEK_STR_CHUNK_SIZE = 0x100

    def __init__(self, client: "DarwinClient[DarwinSymbolT_co]", pid: int) -> None:
        """Initialize a process wrapper for a pid."""
        self._client = client
        self._pid: int = pid

        if self._client.arch == ARCH_ARM64:
            self._thread_class = ArmThread64
        else:
            self._thread_class = IntelThread64

    async def kill(self, sig: int = SIGTERM) -> None:
        """Send a signal to the remote process."""
        return await self._client.processes.kill(self._pid, sig)

    async def waitpid(self, flags: int = 0) -> int:
        """Wait for the remote process to change state and return status."""
        return await self._client.processes.waitpid(self._pid, flags)

    async def peek(self, address: int, size: int) -> bytes:
        """peek at memory address"""
        async with self._client.safe_malloc(size) as buf, self._client.safe_malloc(8) as p_size:
            await p_size.setindex(0, size)
            if await self._client.symbols.vm_read_overwrite(
                await type(self).task_read(self), address, size, buf, p_size
            ):
                raise BadReturnValueError("vm_read() failed")
            return await buf.peek(size)

    async def peek_str(self, address: int, encoding="utf-8") -> str:
        """peek string at memory address"""
        size = self.PEEK_STR_CHUNK_SIZE
        buf = b""

        while size:
            try:
                buf += await self.peek(address, size)
                if b"\x00" in buf:
                    return buf.split(b"\x00", 1)[0].decode(encoding)
                address += size
            except BadReturnValueError:
                size = size // 2
        else:
            raise RuntimeError("Failed to find string terminator")

    async def poke(self, address: int, buf: bytes) -> None:
        """poke at memory address"""
        if await self._client.symbols.vm_write(await type(self).task(self), address, buf, len(buf)):
            raise BadReturnValueError("vm_write() failed")

    async def get_symbol_name(self, address: int) -> str:
        """Resolve a symbol name for the given address."""
        if self._client.arch != ARCH_ARM64:
            raise NotImplementedError("implemented only on ARCH_ARM64")
        result = await (await type(self).vmu_object_identifier(self)).objc_call_raw("symbolForAddress:", address)
        if result.x0 == 0 and result.x1 == 0:
            raise SymbolAbsentError()
        return await (await self._client.symbols.CSSymbolGetName(result.x0, result.x1)).peek_str()

    async def get_symbol_image(self, name: str) -> Image:
        """Find the image containing the named symbol."""
        for image in await type(self).images(self):
            result = await self.get_symbol_address(name, posixpath.basename(image.path))
            if result:
                return image

        raise ProcessSymbolAbsentError()

    async def get_symbol_class_info(self, address: int) -> DarwinSymbolT_co:
        """Return Objective-C class info for the given address."""
        return await (await type(self).vmu_object_identifier(self)).objc_call("classInfoForMemory:length:", address, 8)

    async def get_symbol_address(
        self, name: str, lib: str | None = None
    ) -> DarwinSymbolT_co | ProcessSymbol[DarwinSymbolT_co]:
        """Resolve a symbol address, optionally within a library."""
        if lib is not None:
            address = (
                await (await type(self).vmu_object_identifier(self)).objc_call("addressOfSymbol:inLibrary:", name, lib)
            ).c_uint64
            if self.pid == await self._client.get_pid():
                return self._client.symbol(address)
            return self.get_process_symbol(address)

        image = await self.get_symbol_image(name)
        return await self.get_symbol_address(name, posixpath.basename(image.path))

    async def loaded_classes(self) -> AsyncGenerator[LoadedClass]:
        """Yield realized Objective-C classes for the process."""
        realized_classes = await (await type(self).vmu_object_identifier(self)).objc_call("realizedClasses")

        for i in range(1, await realized_classes.objc_call("count") + 1):
            class_info = await realized_classes.objc_call("classInfoForIndex:", i)
            name = await (await class_info.objc_call("className")).py(str)
            type_name = await (await class_info.objc_call("typeName")).py(str)
            binary_path = await (await class_info.objc_call("binaryPath")).py(str)
            yield LoadedClass(name=name, type_name=type_name, binary_path=binary_path)

    async def images(self) -> list[Image]:
        """get loaded image list"""
        result = []

        async with (
            self._client.safe_malloc(task_dyld_info_data_t.sizeof()) as dyld_info,
            self._client.safe_calloc(8) as count,
        ):
            await count.setindex(0, TASK_DYLD_INFO_COUNT)
            if await self._client.symbols.task_info(await type(self).task_read(self), TASK_DYLD_INFO, dyld_info, count):
                raise BadReturnValueError("task_info(TASK_DYLD_INFO) failed")
            dyld_info_data = await dyld_info.parse(task_dyld_info_data_t)

        all_image_infos = all_image_infos_t.parse(
            await self.peek(dyld_info_data.all_image_info_addr, dyld_info_data.all_image_info_size)
        )

        buf = await self.peek(all_image_infos.infoArray, all_image_infos.infoArrayCount * dyld_image_info_t.sizeof())
        for image in Array(all_image_infos.infoArrayCount, dyld_image_info_t).parse(buf):
            path = await self.peek_str(image.imageFilePath)
            result.append(Image(address=self.get_process_symbol(image.imageLoadAddress), path=path))
        return result

    async def app_images(self) -> list[Image]:
        """Return images that belong to the app bundle."""
        return [image for image in await type(self).images(self) if APP_SUFFIX in image.path]

    async def threads(self) -> list[Thread]:
        """Return the list of threads in the process."""
        result = []

        async with self._client.safe_malloc(8) as threads, self._client.safe_malloc(4) as count:
            count.item_size = 4
            if await self._client.symbols.task_threads(await type(self).task_read(self), threads, count):
                raise BadReturnValueError("task_threads() failed")

            for tid in Array((await count.getindex(0)).c_uint32, Int32ul).parse(
                await (await threads.getindex(0)).peek(await count.getindex(0) * 4)
            ):
                result.append(self._thread_class(self._client, tid))

        return result

    @property
    def pid(self) -> int:
        """get pid"""
        return self._pid

    async def fds(self) -> list[Fd]:
        """get a list of process opened file descriptors"""
        result = []
        for fdstruct in await self.fd_structs():
            fd = fdstruct.fd
            parsed = fdstruct.struct

            if fd.proc_fdtype == PROX_FDTYPE_VNODE:
                result.append(FileFd(fd=fd.proc_fd, path=parsed.pvip.vip_path))

            elif fd.proc_fdtype == PROX_FDTYPE_KQUEUE:
                result.append(KQueueFd(fd=fd.proc_fd))

            elif fd.proc_fdtype == PROX_FDTYPE_PIPE:
                result.append(PipeFd(fd=fd.proc_fd))

            elif fd.proc_fdtype == PROX_FDTYPE_PSHM:
                result.append(SharedMemoryFd(fd=fd.proc_fd, path=parsed.pshminfo.pshm_name))

            elif fd.proc_fdtype == PROX_FDTYPE_SOCKET:
                if parsed.psi.soi_kind in (so_kind_t.SOCKINFO_TCP, so_kind_t.SOCKINFO_IN):
                    correct_class = SOCKET_TYPE_DATACLASS[parsed.psi.soi_family][parsed.psi.soi_kind]

                    if parsed.psi.soi_kind == so_kind_t.SOCKINFO_TCP:
                        info = parsed.psi.soi_proto.pri_tcp.tcpsi_ini
                    else:
                        info = parsed.psi.soi_proto.pri_in
                    result.append(
                        correct_class(
                            fd=fd.proc_fd,
                            local_address=info.insi_laddr.ina_46.i46a_addr4,
                            local_port=info.insi_lport,
                            remote_address=info.insi_faddr.ina_46.i46a_addr4,
                            remote_port=info.insi_fport,
                        )
                    )

                elif parsed.psi.soi_kind == so_kind_t.SOCKINFO_UN:
                    result.append(UnixFd(fd=fd.proc_fd, path=parsed.psi.soi_proto.pri_un.unsi_addr.ua_sun.sun_path))

        return result

    async def fd_structs(self) -> list[FdStruct]:
        """get a list of process opened file descriptors as raw structs"""
        result = []
        size = await self._client.symbols.proc_pidinfo(self.pid, PROC_PIDLISTFDS, 0, 0, 0)

        vi_size = 8196  # should be enough for all structs
        async with self._client.safe_malloc(vi_size) as vi_buf:
            async with self._client.safe_malloc(size) as fdinfo_buf:
                size = int(await self._client.symbols.proc_pidinfo(self.pid, PROC_PIDLISTFDS, 0, fdinfo_buf, size))
                if not size:
                    raise BadReturnValueError("proc_pidinfo(PROC_PIDLISTFDS) failed")

                for fd in Array(size // proc_fdinfo.sizeof(), proc_fdinfo).parse(await fdinfo_buf.peek(size)):
                    if fd.proc_fdtype == PROX_FDTYPE_VNODE:
                        # file
                        vs = await self._client.symbols.proc_pidfdinfo(
                            self.pid, fd.proc_fd, PROC_PIDFDVNODEPATHINFO, vi_buf, vi_size
                        )
                        if not vs:
                            if await self._client.get_errno() == errno.EBADF:
                                # lsof treats this as fine
                                continue
                            raise BadReturnValueError(
                                f"proc_pidinfo(PROC_PIDFDVNODEPATHINFO) failed for fd: {fd.proc_fd} "
                                f"({await self._client.get_last_error()})"
                            )

                        result.append(
                            FdStruct(
                                fd=fd,
                                struct=vnode_fdinfowithpath.parse(await vi_buf.peek(vnode_fdinfowithpath.sizeof())),
                            )
                        )

                    elif fd.proc_fdtype == PROX_FDTYPE_KQUEUE:
                        result.append(FdStruct(fd=fd, struct=None))

                    elif fd.proc_fdtype == PROX_FDTYPE_SOCKET:
                        # socket
                        vs = await self._client.symbols.proc_pidfdinfo(
                            self.pid, fd.proc_fd, PROC_PIDFDSOCKETINFO, vi_buf, vi_size
                        )
                        if not vs:
                            if await self._client.get_errno() == errno.EBADF:
                                # lsof treats this as fine
                                continue
                            raise BadReturnValueError(
                                f"proc_pidinfo(PROC_PIDFDSOCKETINFO) failed ({await self._client.get_last_error()})"
                            )

                        result.append(FdStruct(fd=fd, struct=socket_fdinfo.parse(await vi_buf.peek(vi_size))))

                    elif fd.proc_fdtype == PROX_FDTYPE_PIPE:
                        # pipe
                        vs = await self._client.symbols.proc_pidfdinfo(
                            self.pid, fd.proc_fd, PROC_PIDFDPIPEINFO, vi_buf, vi_size
                        )
                        if not vs:
                            if await self._client.get_errno() == errno.EBADF:
                                # lsof treats this as fine
                                continue
                            raise BadReturnValueError(
                                f"proc_pidinfo(PROC_PIDFDPIPEINFO) failed ({await self._client.get_last_error()})"
                            )

                        result.append(FdStruct(fd=fd, struct=pipe_info.parse(await vi_buf.peek(pipe_info.sizeof()))))

                    elif fd.proc_fdtype == PROX_FDTYPE_PSHM:
                        vs = await self._client.symbols.proc_pidfdinfo(
                            self.pid, fd.proc_fd, PROC_PIDFDPSHMINFO, vi_buf, vi_size
                        )
                        if not vs:
                            if await self._client.get_errno() == errno.EBADF:
                                continue
                            raise BadReturnValueError(
                                f"proc_pidinfo(PROC_PIDFDPSHMINFO) failed ({await self._client.get_last_error()})"
                            )

                        result.append(
                            FdStruct(fd=fd, struct=pshm_fdinfo.parse(await vi_buf.peek(pshm_fdinfo.sizeof())))
                        )

            return result

    async def task_all_info(self) -> Container:
        """get a list of process opened file descriptors"""
        async with self._client.safe_malloc(proc_taskallinfo.sizeof()) as pti:
            if not await self._client.symbols.proc_pidinfo(
                self.pid, PROC_PIDTASKALLINFO, 0, pti, proc_taskallinfo.sizeof()
            ):
                raise BadReturnValueError("proc_pidinfo(PROC_PIDTASKALLINFO) failed")
            return await pti.parse(proc_taskallinfo)

    async def task_vm_info(self) -> Container:
        """get TASK_VM_INFO via task_info."""
        async with (
            self._client.safe_malloc(task_vm_info_data_t.sizeof()) as vm_info,
            self._client.safe_calloc(8) as count,
        ):
            await count.setindex(0, TASK_VM_INFO_COUNT)
            if await self._client.symbols.task_info(await type(self).task_read(self), TASK_VM_INFO, vm_info, count):
                raise BadReturnValueError("task_info(TASK_VM_INFO) failed")
            return await vm_info.parse(task_vm_info_data_t)

    async def backtraces(self) -> list[Backtrace]:
        """Collect backtraces for all threads in the process."""
        result = []
        backtraces = await (await self._client.symbols.objc_getClass("VMUSampler")).objc_call(
            "sampleAllThreadsOfTask:", await type(self).task_read(self)
        )
        for i in range(await backtraces.objc_call("count")):
            bt = await backtraces.objc_call("objectAtIndex:", i)
            result.append(await Backtrace._from_backtrace(bt))
        return result

    @cached_async_method
    async def vmu_proc_info(self) -> DarwinSymbolT_co:
        """Return the VMUProcInfo object for this task."""
        VMUProcInfo = await self._client.symbols.objc_getClass("VMUProcInfo")
        return await (await (VMUProcInfo).objc_call("alloc")).objc_call(
            "initWithTask:", await type(self).task_read(self)
        )

    @cached_async_method
    async def vmu_region_identifier(self) -> DarwinSymbolT_co:
        """Return the VMUVMRegionIdentifier object for this task."""

        VMUVMRegionIdentifier = await self._client.symbols.objc_getClass("VMUVMRegionIdentifier")
        return await (await (VMUVMRegionIdentifier).objc_call("alloc")).objc_call(
            "initWithTask:", await type(self).task_read(self)
        )

    @cached_async_method
    async def vmu_object_identifier(self) -> DarwinSymbolT_co:
        """Return the VMUObjectIdentifier object for this task."""
        VMUObjectIdentifier = await self._client.symbols.objc_getClass("VMUObjectIdentifier")
        return await (await (VMUObjectIdentifier).objc_call("alloc")).objc_call(
            "initWithTask:", await type(self).task_read(self)
        )

    @cached_async_method
    async def symbolicator(self) -> Symbolicator[DarwinSymbolT_co]:
        """Return a symbolicator for this task."""
        symbolicator = await self._client.symbols.CSSymbolicatorCreateWithTask(
            await type(self).task_read(self), return_raw=True
        )
        return Symbolicator(self._client, self, symbolicator.x0, symbolicator.x1)

    @cached_async_method
    async def task_read(self) -> int:
        """Return the task read port for this process."""
        self_task_port = await self._client.symbols.mach_task_self()

        if self.pid == await self._client.get_pid():
            return self_task_port

        async with self._client.safe_malloc(8) as p_task:
            ret = await self._client.symbols.task_read_for_pid(self_task_port, self.pid, p_task)
            if ret:
                raise BadReturnValueError("task_read_for_pid() failed")
            return (await p_task.getindex(0)).c_int64

    @cached_async_method
    async def task(self) -> int:
        """Return the full task port for this process."""
        self_task_port = await self._client.symbols.mach_task_self()

        if self.pid == await self._client.get_pid():
            return self_task_port

        async with self._client.safe_malloc(8) as p_task:
            if await self._client.symbols.task_for_pid(self_task_port, self.pid, p_task):
                raise BadReturnValueError("task_for_pid() failed")
            return (await p_task.getindex(0)).c_int64

    @cached_async_method
    async def path(self) -> str | None:
        """call proc_pidpath(filename, ...) at remote. review xnu header for more details."""
        async with self._client.safe_malloc(MAXPATHLEN) as path:
            path_len = await self._client.symbols.proc_pidpath(self.pid, path, MAXPATHLEN)
            return (await path.peek(path_len)).decode() if path_len else None

    @cached_async_method
    async def basename(self) -> str | None:
        """Return the basename of the process path."""
        path = await type(self).path(self)
        return PurePath(path).name if path else None

    @cached_async_method
    async def _get_pbsd(self) -> Container:
        return (await self.task_all_info()).pbsd

    async def name(self) -> str:
        """Return the process name from task info."""
        return (await self._get_pbsd()).pbi_name

    async def bundle_id(self) -> str | None:
        """Return the process's code-signing identity via ``csops(CS_OPS_IDENTITY)``.

        For a signed app or daemon this is its bundle identifier (e.g. ``com.apple.CrashReporter``) -
        the domain its ``NSUserDefaults standardUserDefaults`` uses. None if the process is unsigned
        or has no identity. Works for daemons too, unlike ``SBSCopyDisplayIdentifierForProcessID``.
        """
        size = 1024
        async with self._client.safe_malloc(size) as buf:
            if await self._client.symbols.csops(self.pid, CS_OPS_IDENTITY, buf, size):
                return None
            # blob layout: uint32 type, uint32 length (big-endian), then the identity C-string
            identity = (await buf.peek(size))[8:].split(b"\x00", 1)[0]
        return identity.decode() if identity else None

    async def ppid(self) -> int:
        """Return the parent process id."""
        return (await self._get_pbsd()).pbi_ppid

    async def uid(self) -> int:
        """Return the process user id."""
        return (await self._get_pbsd()).pbi_uid

    async def gid(self) -> int:
        """Return the process group id."""
        return (await self._get_pbsd()).pbi_gid

    async def ruid(self) -> int:
        """Return the real user id."""
        return (await self._get_pbsd()).pbi_ruid

    async def rgid(self) -> int:
        """Return the real group id."""
        return (await self._get_pbsd()).pbi_rgid

    _start_time: datetime | None = None

    async def start_time(self) -> datetime:
        """Return the process start time."""
        if self._start_time is None:
            if self._client.arch != ARCH_ARM64:
                raise NotImplementedError("implemented only on ARCH_ARM64")
            val = await (await type(self).vmu_proc_info(self)).objc_call_raw("startTime")
            tv_sec = val.x0
            tv_nsec = val.x1
            self._start_time = datetime.fromtimestamp(tv_sec + (tv_nsec / (10**9)))

        return self._start_time

    async def parent(self) -> Self:
        """Return a Process wrapper for the parent pid."""
        return type(self)(self._client, await type(self).ppid(self))

    async def environ(self) -> dict[str, str]:
        """Return the process environment as a ``KEY -> VALUE`` mapping."""
        entries = await (await (await type(self).vmu_proc_info(self)).objc_call("envVars")).py(list)
        return dict(entry.partition("=")[::2] for entry in entries)

    async def arguments(self) -> list[str]:
        """Return the process argument list."""
        return await (await (await type(self).vmu_proc_info(self)).objc_call("arguments")).py(list)

    async def raw_procargs2(self) -> bytes:
        """Return the raw PROCARGS2 sysctl buffer."""
        return await self._client.sysctl.get(CTL.KERN, KERN.PROCARGS2, self.pid)

    async def procargs2(self) -> Container:
        """Parse and return the PROCARGS2 buffer."""
        return procargs2_t.parse(await type(self).raw_procargs2(self))

    def preferences(
        self, application_id: str | None = None, *, any_user: bool = False
    ) -> "ProcessPreferences[DarwinSymbolT_co]":
        """Read/write a preference domain as *this* process resolves it (container, uid).

        With no ``application_id`` this is the process's own bundle-id domain - the
        ``standardUserDefaults`` domain. See ``ProcessPreferences``.
        """
        return ProcessPreferences(self, application_id, any_user=any_user)

    async def get_regions(self) -> list[Region[DarwinSymbolT_co]]:
        """Return the list of VM regions for the process."""
        result: list[Region[DarwinSymbolT_co]] = []

        # remove the '()' wrapping the list:
        #   (
        #       "item1",
        #       "item2",
        #   )
        regions_sym = await (await type(self).vmu_region_identifier(self)).objc_call("regions")
        buf = cast(str, await type(regions_sym).cfdesc(regions_sym)).split("\n")[1:-1]

        for line in buf:
            # remove line prefix and suffix and split into words
            line = line[_CF_STRING_ARRAY_PREFIX_LEN:-_CF_STRING_ARRAY_SUFFIX_LEN].split()
            i = 0

            region_type = line[i]
            i += 1

            while "-" not in line[i]:
                # skip till address range
                i += 1

            address_range = line[i]
            i += 1
            if not address_range.startswith("0x"):
                continue
            start, end = address_range.split("-")

            start = int(start, 16)
            end = int(end, 16)
            vsize = None
            if "V=" in line[i]:
                vsize = line[i].split("V=", 1)[1].split("]", 1)[0]

            while "/" not in line[i]:
                i += 1

            protection = line[i].split("/")
            i += 1

            region_detail = None
            if len(line) >= i + 1:
                region_detail = line[i]

            result.append(
                Region(
                    region_type=region_type,
                    start=self.get_process_symbol(start),
                    end=end,
                    vsize=vsize,
                    protection=protection[0],
                    protection_max=protection[1],
                    region_detail=region_detail,
                )
            )

        return result

    async def regions(self) -> list[Region[DarwinSymbolT_co]]:
        """Return the list of VM regions for the process."""
        return await self.get_regions()

    async def cdhash(self) -> bytes:
        """Return the code directory hash for the process."""
        async with self._client.safe_malloc(CDHASH_SIZE) as cdhash:
            # by reversing online-auth-agent
            if await self._client.symbols.csops(self.pid, 5, cdhash, CDHASH_SIZE) != 0:
                raise BadReturnValueError(f"failed to get cdhash for {self.pid}")
            return await cdhash.peek(CDHASH_SIZE)

    def get_process_symbol(self, address: int) -> ProcessSymbol[DarwinSymbolT_co]:
        """Create a process symbol for the given address."""
        return ProcessSymbol(address, self)

    async def vm_allocate(self, size: int) -> ProcessSymbol[DarwinSymbolT_co]:
        """Allocate memory in the target task and return its address."""
        async with self._client.safe_malloc(8) as out_address:
            if await self._client.symbols.vm_allocate(
                await type(self).task(self), out_address, size, VM_FLAGS_ANYWHERE
            ):
                raise BadReturnValueError("vm_allocate() failed")
            return self.get_process_symbol(await out_address.getindex(0))

    async def dump_app(self, output_dir: str | PurePath, chunk_size: int = CHUNK_SIZE) -> None:
        """
        Based on:
        https://github.com/AloneMonkey/frida-ios-dump/blob/master/dump.js
        """
        for image in await type(self).app_images(self):
            relative_name = image.path.split(APP_SUFFIX, 1)[1]
            output_file = Path(output_dir).expanduser() / relative_name
            output_file.parent.mkdir(exist_ok=True, parents=True)
            logger.debug(f"dumping: {output_file}")

            with open(output_file, "wb") as output_file:
                # Symbol reads are async, so fetch the header + load commands first and parse locally.
                # Offsets captured by `Tell` are then relative to the image start.
                header = await image.address.peek(MACH_HEADER_64_SIZE)
                sizeofcmds = Int32ul.parse(header[MACH_HEADER_SIZEOFCMDS_OFFSET:][:4])
                macho_in_memory = mach_header_t.parse(await image.address.peek(MACH_HEADER_64_SIZE + sizeofcmds))

                async with await self._client.fs.open(image.path, "r") as fat_file:
                    # locating the correct MachO offset within the FAT image (if FAT)
                    magic_in_fs = await fat_file.parse(Int32ul)
                    await fat_file.seek(0, SEEK_SET)
                    if magic_in_fs in (FAT_CIGAM, FAT_MAGIC):
                        parsed_fat = await fat_file.parse(fat_header)
                        for arch in parsed_fat.archs:
                            if (
                                arch.cputype == macho_in_memory.cputype
                                and arch.cpusubtype == macho_in_memory.cpusubtype
                            ):
                                # correct MachO offset found
                                file_offset = arch.offset
                                break
                        else:
                            raise RuntimeError("Failed to find file offset.")

                        await fat_file.seek(file_offset, SEEK_SET)

                    # perform actual MachO dump
                    output_file.seek(0, SEEK_SET)
                    while True:
                        chunk = await fat_file.read(chunk_size)
                        if len(chunk) == 0:
                            break
                        output_file.write(chunk)

                    offset_cryptid = None

                    # if image is encrypted, patch its encryption loader command
                    for load_command in macho_in_memory.load_commands:
                        if load_command.cmd in (
                            LOAD_COMMAND_TYPE.LC_ENCRYPTION_INFO_64,
                            LOAD_COMMAND_TYPE.LC_ENCRYPTION_INFO,
                        ):
                            # cryptid follows cryptoff and cryptsize in both command variants
                            offset_cryptid = load_command._data_offset + 8
                            crypt_offset = load_command.data.cryptoff
                            crypt_size = load_command.data.cryptsize
                            break
                    else:
                        raise RuntimeError("Failed to find LC_ENCRYPTION_INFO or LC_ENCRYPTION_INFO_64 command.")

                    if offset_cryptid is not None:
                        output_file.seek(offset_cryptid, SEEK_SET)
                        output_file.write(b"\x00" * 4)  # cryptid = 0
                        output_file.seek(crypt_offset, SEEK_SET)
                        output_file.flush()
                        output_file.write(await image.address.peek(crypt_size, crypt_offset))

    async def get_mach_ports(
        self, include_thread_info: bool = False, resolve_kobjects: bool = False
    ) -> AsyncGenerator[MachPortInfo]:
        """Enumerate this process's own mach ports, with rights, kobject type and exception handlers.

        :param include_thread_info: also collect this task's thread ids.
        :param resolve_kobjects: resolve each port's kernel-object type (IKOT_*); one extra RPC per
            port, so it is off by default (``MachPortInfo.kobject`` stays ``None`` when disabled).
        """
        async for port in self._client.processes.get_pid_mach_ports(
            self.pid, include_thread_info=include_thread_info, resolve_kobjects=resolve_kobjects
        ):
            yield port

    async def get_mach_port_cross_ref_info(self) -> list[MachPortCrossRefInfo]:
        """Get all allocated mach ports and cross-refs to get the recv right owner"""
        own_ports: list[MachPortInfo] = []
        cross_refs_info: dict[int, list[MachPortInfo]] = {}
        async for port in self._client.processes.get_mach_ports():
            if port.pid == self.pid:
                own_ports.append(port)
            if port.ipc_object not in cross_refs_info:
                cross_refs_info[port.ipc_object] = []
            cross_refs_info[port.ipc_object].append(port)

        return [
            MachPortCrossRefInfo(
                name=port.name,
                ipc_object=port.ipc_object,
                rights=port.rights,
                recv_right_pid=cross_ref_port_info.pid,
                recv_right_proc_name=cross_ref_port_info.proc_name,
            )
            for port in own_ports
            for cross_ref_port_info in cross_refs_info[port.ipc_object]
            if cross_ref_port_info.has_recv_right
        ]

    async def get_memgraph_snapshot(self) -> bytes:
        """Return a memory graph snapshot as plist bytes."""
        scanner = None
        try:
            # first attempt via new API
            scanner = await (await self._client.symbols.objc_getClass("VMUProcessObjectGraph")).objc_call(
                "createWithTask:", await type(self).task_read(self)
            )
            snapshot_graph = await (await scanner.objc_call("plistRepresentationWithOptions:", 0)).py(bytes)
        except UnrecognizedSelectorError:
            # if failed, attempt with old API
            scanner = await (
                await (await self._client.symbols.objc_getClass("VMUTaskMemoryScanner")).objc_call("alloc")
            ).objc_call("initWithTask:", await type(self).task_read(self))
            await scanner.objc_call("addRootNodesFromTask")
            await scanner.objc_call("addMallocNodesFromTask")
            snapshot_graph = await (
                await (await scanner.objc_call("processSnapshotGraph")).objc_call("plistRepresentationWithOptions:", 0)
            ).py(bytes)
        finally:
            if scanner is not None:
                # free object scanner so process can resume
                await scanner.objc_call("release")
        return snapshot_graph

    def __repr__(self) -> str:
        """Return a debug representation of the process."""
        path = getattr(self, "_path", "<not cached yet>")

        return f"<{self.__class__.__name__} PID:{self.pid} PATH:{path}>"
```

#### pid

```
pid: int
```

get pid

#### kill

```
kill(sig: int = SIGTERM) -> None
```

Send a signal to the remote process.

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/processes.py`

```
async def kill(self, sig: int = SIGTERM) -> None:
    """Send a signal to the remote process."""
    return await self._client.processes.kill(self._pid, sig)
```

#### waitpid

```
waitpid(flags: int = 0) -> int
```

Wait for the remote process to change state and return status.

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/processes.py`

```
async def waitpid(self, flags: int = 0) -> int:
    """Wait for the remote process to change state and return status."""
    return await self._client.processes.waitpid(self._pid, flags)
```

#### peek

```
peek(address: int, size: int) -> bytes
```

peek at memory address

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/processes.py`

```
async def peek(self, address: int, size: int) -> bytes:
    """peek at memory address"""
    async with self._client.safe_malloc(size) as buf, self._client.safe_malloc(8) as p_size:
        await p_size.setindex(0, size)
        if await self._client.symbols.vm_read_overwrite(
            await type(self).task_read(self), address, size, buf, p_size
        ):
            raise BadReturnValueError("vm_read() failed")
        return await buf.peek(size)
```

#### peek_str

```
peek_str(address: int, encoding='utf-8') -> str
```

peek string at memory address

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/processes.py`

```
async def peek_str(self, address: int, encoding="utf-8") -> str:
    """peek string at memory address"""
    size = self.PEEK_STR_CHUNK_SIZE
    buf = b""

    while size:
        try:
            buf += await self.peek(address, size)
            if b"\x00" in buf:
                return buf.split(b"\x00", 1)[0].decode(encoding)
            address += size
        except BadReturnValueError:
            size = size // 2
    else:
        raise RuntimeError("Failed to find string terminator")
```

#### poke

```
poke(address: int, buf: bytes) -> None
```

poke at memory address

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/processes.py`

```
async def poke(self, address: int, buf: bytes) -> None:
    """poke at memory address"""
    if await self._client.symbols.vm_write(await type(self).task(self), address, buf, len(buf)):
        raise BadReturnValueError("vm_write() failed")
```

#### get_symbol_name

```
get_symbol_name(address: int) -> str
```

Resolve a symbol name for the given address.

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/processes.py`

```
async def get_symbol_name(self, address: int) -> str:
    """Resolve a symbol name for the given address."""
    if self._client.arch != ARCH_ARM64:
        raise NotImplementedError("implemented only on ARCH_ARM64")
    result = await (await type(self).vmu_object_identifier(self)).objc_call_raw("symbolForAddress:", address)
    if result.x0 == 0 and result.x1 == 0:
        raise SymbolAbsentError()
    return await (await self._client.symbols.CSSymbolGetName(result.x0, result.x1)).peek_str()
```

#### get_symbol_image

```
get_symbol_image(name: str) -> Image
```

Find the image containing the named symbol.

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/processes.py`

```
async def get_symbol_image(self, name: str) -> Image:
    """Find the image containing the named symbol."""
    for image in await type(self).images(self):
        result = await self.get_symbol_address(name, posixpath.basename(image.path))
        if result:
            return image

    raise ProcessSymbolAbsentError()
```

#### get_symbol_class_info

```
get_symbol_class_info(address: int) -> DarwinSymbolT_co
```

Return Objective-C class info for the given address.

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/processes.py`

```
async def get_symbol_class_info(self, address: int) -> DarwinSymbolT_co:
    """Return Objective-C class info for the given address."""
    return await (await type(self).vmu_object_identifier(self)).objc_call("classInfoForMemory:length:", address, 8)
```

#### get_symbol_address

```
get_symbol_address(name: str, lib: str | None = None) -> DarwinSymbolT_co | ProcessSymbol[DarwinSymbolT_co]
```

Resolve a symbol address, optionally within a library.

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/processes.py`

```
async def get_symbol_address(
    self, name: str, lib: str | None = None
) -> DarwinSymbolT_co | ProcessSymbol[DarwinSymbolT_co]:
    """Resolve a symbol address, optionally within a library."""
    if lib is not None:
        address = (
            await (await type(self).vmu_object_identifier(self)).objc_call("addressOfSymbol:inLibrary:", name, lib)
        ).c_uint64
        if self.pid == await self._client.get_pid():
            return self._client.symbol(address)
        return self.get_process_symbol(address)

    image = await self.get_symbol_image(name)
    return await self.get_symbol_address(name, posixpath.basename(image.path))
```

#### loaded_classes

```
loaded_classes() -> AsyncGenerator[LoadedClass]
```

Yield realized Objective-C classes for the process.

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/processes.py`

```
async def loaded_classes(self) -> AsyncGenerator[LoadedClass]:
    """Yield realized Objective-C classes for the process."""
    realized_classes = await (await type(self).vmu_object_identifier(self)).objc_call("realizedClasses")

    for i in range(1, await realized_classes.objc_call("count") + 1):
        class_info = await realized_classes.objc_call("classInfoForIndex:", i)
        name = await (await class_info.objc_call("className")).py(str)
        type_name = await (await class_info.objc_call("typeName")).py(str)
        binary_path = await (await class_info.objc_call("binaryPath")).py(str)
        yield LoadedClass(name=name, type_name=type_name, binary_path=binary_path)
```

#### images

```
images() -> list[Image]
```

get loaded image list

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/processes.py`

```
async def images(self) -> list[Image]:
    """get loaded image list"""
    result = []

    async with (
        self._client.safe_malloc(task_dyld_info_data_t.sizeof()) as dyld_info,
        self._client.safe_calloc(8) as count,
    ):
        await count.setindex(0, TASK_DYLD_INFO_COUNT)
        if await self._client.symbols.task_info(await type(self).task_read(self), TASK_DYLD_INFO, dyld_info, count):
            raise BadReturnValueError("task_info(TASK_DYLD_INFO) failed")
        dyld_info_data = await dyld_info.parse(task_dyld_info_data_t)

    all_image_infos = all_image_infos_t.parse(
        await self.peek(dyld_info_data.all_image_info_addr, dyld_info_data.all_image_info_size)
    )

    buf = await self.peek(all_image_infos.infoArray, all_image_infos.infoArrayCount * dyld_image_info_t.sizeof())
    for image in Array(all_image_infos.infoArrayCount, dyld_image_info_t).parse(buf):
        path = await self.peek_str(image.imageFilePath)
        result.append(Image(address=self.get_process_symbol(image.imageLoadAddress), path=path))
    return result
```

#### app_images

```
app_images() -> list[Image]
```

Return images that belong to the app bundle.

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/processes.py`

```
async def app_images(self) -> list[Image]:
    """Return images that belong to the app bundle."""
    return [image for image in await type(self).images(self) if APP_SUFFIX in image.path]
```

#### threads

```
threads() -> list[Thread]
```

Return the list of threads in the process.

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/processes.py`

```
async def threads(self) -> list[Thread]:
    """Return the list of threads in the process."""
    result = []

    async with self._client.safe_malloc(8) as threads, self._client.safe_malloc(4) as count:
        count.item_size = 4
        if await self._client.symbols.task_threads(await type(self).task_read(self), threads, count):
            raise BadReturnValueError("task_threads() failed")

        for tid in Array((await count.getindex(0)).c_uint32, Int32ul).parse(
            await (await threads.getindex(0)).peek(await count.getindex(0) * 4)
        ):
            result.append(self._thread_class(self._client, tid))

    return result
```

#### fds

```
fds() -> list[Fd]
```

get a list of process opened file descriptors

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/processes.py`

```
async def fds(self) -> list[Fd]:
    """get a list of process opened file descriptors"""
    result = []
    for fdstruct in await self.fd_structs():
        fd = fdstruct.fd
        parsed = fdstruct.struct

        if fd.proc_fdtype == PROX_FDTYPE_VNODE:
            result.append(FileFd(fd=fd.proc_fd, path=parsed.pvip.vip_path))

        elif fd.proc_fdtype == PROX_FDTYPE_KQUEUE:
            result.append(KQueueFd(fd=fd.proc_fd))

        elif fd.proc_fdtype == PROX_FDTYPE_PIPE:
            result.append(PipeFd(fd=fd.proc_fd))

        elif fd.proc_fdtype == PROX_FDTYPE_PSHM:
            result.append(SharedMemoryFd(fd=fd.proc_fd, path=parsed.pshminfo.pshm_name))

        elif fd.proc_fdtype == PROX_FDTYPE_SOCKET:
            if parsed.psi.soi_kind in (so_kind_t.SOCKINFO_TCP, so_kind_t.SOCKINFO_IN):
                correct_class = SOCKET_TYPE_DATACLASS[parsed.psi.soi_family][parsed.psi.soi_kind]

                if parsed.psi.soi_kind == so_kind_t.SOCKINFO_TCP:
                    info = parsed.psi.soi_proto.pri_tcp.tcpsi_ini
                else:
                    info = parsed.psi.soi_proto.pri_in
                result.append(
                    correct_class(
                        fd=fd.proc_fd,
                        local_address=info.insi_laddr.ina_46.i46a_addr4,
                        local_port=info.insi_lport,
                        remote_address=info.insi_faddr.ina_46.i46a_addr4,
                        remote_port=info.insi_fport,
                    )
                )

            elif parsed.psi.soi_kind == so_kind_t.SOCKINFO_UN:
                result.append(UnixFd(fd=fd.proc_fd, path=parsed.psi.soi_proto.pri_un.unsi_addr.ua_sun.sun_path))

    return result
```

#### fd_structs

```
fd_structs() -> list[FdStruct]
```

get a list of process opened file descriptors as raw structs

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/processes.py`

```
async def fd_structs(self) -> list[FdStruct]:
    """get a list of process opened file descriptors as raw structs"""
    result = []
    size = await self._client.symbols.proc_pidinfo(self.pid, PROC_PIDLISTFDS, 0, 0, 0)

    vi_size = 8196  # should be enough for all structs
    async with self._client.safe_malloc(vi_size) as vi_buf:
        async with self._client.safe_malloc(size) as fdinfo_buf:
            size = int(await self._client.symbols.proc_pidinfo(self.pid, PROC_PIDLISTFDS, 0, fdinfo_buf, size))
            if not size:
                raise BadReturnValueError("proc_pidinfo(PROC_PIDLISTFDS) failed")

            for fd in Array(size // proc_fdinfo.sizeof(), proc_fdinfo).parse(await fdinfo_buf.peek(size)):
                if fd.proc_fdtype == PROX_FDTYPE_VNODE:
                    # file
                    vs = await self._client.symbols.proc_pidfdinfo(
                        self.pid, fd.proc_fd, PROC_PIDFDVNODEPATHINFO, vi_buf, vi_size
                    )
                    if not vs:
                        if await self._client.get_errno() == errno.EBADF:
                            # lsof treats this as fine
                            continue
                        raise BadReturnValueError(
                            f"proc_pidinfo(PROC_PIDFDVNODEPATHINFO) failed for fd: {fd.proc_fd} "
                            f"({await self._client.get_last_error()})"
                        )

                    result.append(
                        FdStruct(
                            fd=fd,
                            struct=vnode_fdinfowithpath.parse(await vi_buf.peek(vnode_fdinfowithpath.sizeof())),
                        )
                    )

                elif fd.proc_fdtype == PROX_FDTYPE_KQUEUE:
                    result.append(FdStruct(fd=fd, struct=None))

                elif fd.proc_fdtype == PROX_FDTYPE_SOCKET:
                    # socket
                    vs = await self._client.symbols.proc_pidfdinfo(
                        self.pid, fd.proc_fd, PROC_PIDFDSOCKETINFO, vi_buf, vi_size
                    )
                    if not vs:
                        if await self._client.get_errno() == errno.EBADF:
                            # lsof treats this as fine
                            continue
                        raise BadReturnValueError(
                            f"proc_pidinfo(PROC_PIDFDSOCKETINFO) failed ({await self._client.get_last_error()})"
                        )

                    result.append(FdStruct(fd=fd, struct=socket_fdinfo.parse(await vi_buf.peek(vi_size))))

                elif fd.proc_fdtype == PROX_FDTYPE_PIPE:
                    # pipe
                    vs = await self._client.symbols.proc_pidfdinfo(
                        self.pid, fd.proc_fd, PROC_PIDFDPIPEINFO, vi_buf, vi_size
                    )
                    if not vs:
                        if await self._client.get_errno() == errno.EBADF:
                            # lsof treats this as fine
                            continue
                        raise BadReturnValueError(
                            f"proc_pidinfo(PROC_PIDFDPIPEINFO) failed ({await self._client.get_last_error()})"
                        )

                    result.append(FdStruct(fd=fd, struct=pipe_info.parse(await vi_buf.peek(pipe_info.sizeof()))))

                elif fd.proc_fdtype == PROX_FDTYPE_PSHM:
                    vs = await self._client.symbols.proc_pidfdinfo(
                        self.pid, fd.proc_fd, PROC_PIDFDPSHMINFO, vi_buf, vi_size
                    )
                    if not vs:
                        if await self._client.get_errno() == errno.EBADF:
                            continue
                        raise BadReturnValueError(
                            f"proc_pidinfo(PROC_PIDFDPSHMINFO) failed ({await self._client.get_last_error()})"
                        )

                    result.append(
                        FdStruct(fd=fd, struct=pshm_fdinfo.parse(await vi_buf.peek(pshm_fdinfo.sizeof())))
                    )

        return result
```

#### task_all_info

```
task_all_info() -> Container
```

get a list of process opened file descriptors

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/processes.py`

```
async def task_all_info(self) -> Container:
    """get a list of process opened file descriptors"""
    async with self._client.safe_malloc(proc_taskallinfo.sizeof()) as pti:
        if not await self._client.symbols.proc_pidinfo(
            self.pid, PROC_PIDTASKALLINFO, 0, pti, proc_taskallinfo.sizeof()
        ):
            raise BadReturnValueError("proc_pidinfo(PROC_PIDTASKALLINFO) failed")
        return await pti.parse(proc_taskallinfo)
```

#### task_vm_info

```
task_vm_info() -> Container
```

get TASK_VM_INFO via task_info.

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/processes.py`

```
async def task_vm_info(self) -> Container:
    """get TASK_VM_INFO via task_info."""
    async with (
        self._client.safe_malloc(task_vm_info_data_t.sizeof()) as vm_info,
        self._client.safe_calloc(8) as count,
    ):
        await count.setindex(0, TASK_VM_INFO_COUNT)
        if await self._client.symbols.task_info(await type(self).task_read(self), TASK_VM_INFO, vm_info, count):
            raise BadReturnValueError("task_info(TASK_VM_INFO) failed")
        return await vm_info.parse(task_vm_info_data_t)
```

#### backtraces

```
backtraces() -> list[Backtrace]
```

Collect backtraces for all threads in the process.

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/processes.py`

```
async def backtraces(self) -> list[Backtrace]:
    """Collect backtraces for all threads in the process."""
    result = []
    backtraces = await (await self._client.symbols.objc_getClass("VMUSampler")).objc_call(
        "sampleAllThreadsOfTask:", await type(self).task_read(self)
    )
    for i in range(await backtraces.objc_call("count")):
        bt = await backtraces.objc_call("objectAtIndex:", i)
        result.append(await Backtrace._from_backtrace(bt))
    return result
```

#### vmu_proc_info

```
vmu_proc_info() -> DarwinSymbolT_co
```

Return the VMUProcInfo object for this task.

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/processes.py`

```
@cached_async_method
async def vmu_proc_info(self) -> DarwinSymbolT_co:
    """Return the VMUProcInfo object for this task."""
    VMUProcInfo = await self._client.symbols.objc_getClass("VMUProcInfo")
    return await (await (VMUProcInfo).objc_call("alloc")).objc_call(
        "initWithTask:", await type(self).task_read(self)
    )
```

#### vmu_region_identifier

```
vmu_region_identifier() -> DarwinSymbolT_co
```

Return the VMUVMRegionIdentifier object for this task.

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/processes.py`

```
@cached_async_method
async def vmu_region_identifier(self) -> DarwinSymbolT_co:
    """Return the VMUVMRegionIdentifier object for this task."""

    VMUVMRegionIdentifier = await self._client.symbols.objc_getClass("VMUVMRegionIdentifier")
    return await (await (VMUVMRegionIdentifier).objc_call("alloc")).objc_call(
        "initWithTask:", await type(self).task_read(self)
    )
```

#### vmu_object_identifier

```
vmu_object_identifier() -> DarwinSymbolT_co
```

Return the VMUObjectIdentifier object for this task.

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/processes.py`

```
@cached_async_method
async def vmu_object_identifier(self) -> DarwinSymbolT_co:
    """Return the VMUObjectIdentifier object for this task."""
    VMUObjectIdentifier = await self._client.symbols.objc_getClass("VMUObjectIdentifier")
    return await (await (VMUObjectIdentifier).objc_call("alloc")).objc_call(
        "initWithTask:", await type(self).task_read(self)
    )
```

#### symbolicator

```
symbolicator() -> Symbolicator[DarwinSymbolT_co]
```

Return a symbolicator for this task.

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/processes.py`

```
@cached_async_method
async def symbolicator(self) -> Symbolicator[DarwinSymbolT_co]:
    """Return a symbolicator for this task."""
    symbolicator = await self._client.symbols.CSSymbolicatorCreateWithTask(
        await type(self).task_read(self), return_raw=True
    )
    return Symbolicator(self._client, self, symbolicator.x0, symbolicator.x1)
```

#### task_read

```
task_read() -> int
```

Return the task read port for this process.

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/processes.py`

```
@cached_async_method
async def task_read(self) -> int:
    """Return the task read port for this process."""
    self_task_port = await self._client.symbols.mach_task_self()

    if self.pid == await self._client.get_pid():
        return self_task_port

    async with self._client.safe_malloc(8) as p_task:
        ret = await self._client.symbols.task_read_for_pid(self_task_port, self.pid, p_task)
        if ret:
            raise BadReturnValueError("task_read_for_pid() failed")
        return (await p_task.getindex(0)).c_int64
```

#### task

```
task() -> int
```

Return the full task port for this process.

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/processes.py`

```
@cached_async_method
async def task(self) -> int:
    """Return the full task port for this process."""
    self_task_port = await self._client.symbols.mach_task_self()

    if self.pid == await self._client.get_pid():
        return self_task_port

    async with self._client.safe_malloc(8) as p_task:
        if await self._client.symbols.task_for_pid(self_task_port, self.pid, p_task):
            raise BadReturnValueError("task_for_pid() failed")
        return (await p_task.getindex(0)).c_int64
```

#### path

```
path() -> str | None
```

call proc_pidpath(filename, ...) at remote. review xnu header for more details.

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/processes.py`

```
@cached_async_method
async def path(self) -> str | None:
    """call proc_pidpath(filename, ...) at remote. review xnu header for more details."""
    async with self._client.safe_malloc(MAXPATHLEN) as path:
        path_len = await self._client.symbols.proc_pidpath(self.pid, path, MAXPATHLEN)
        return (await path.peek(path_len)).decode() if path_len else None
```

#### basename

```
basename() -> str | None
```

Return the basename of the process path.

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/processes.py`

```
@cached_async_method
async def basename(self) -> str | None:
    """Return the basename of the process path."""
    path = await type(self).path(self)
    return PurePath(path).name if path else None
```

#### name

```
name() -> str
```

Return the process name from task info.

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/processes.py`

```
async def name(self) -> str:
    """Return the process name from task info."""
    return (await self._get_pbsd()).pbi_name
```

#### bundle_id

```
bundle_id() -> str | None
```

Return the process's code-signing identity via `csops(CS_OPS_IDENTITY)`.

For a signed app or daemon this is its bundle identifier (e.g. `com.apple.CrashReporter`) - the domain its `NSUserDefaults standardUserDefaults` uses. None if the process is unsigned or has no identity. Works for daemons too, unlike `SBSCopyDisplayIdentifierForProcessID`.

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/processes.py`

```
async def bundle_id(self) -> str | None:
    """Return the process's code-signing identity via ``csops(CS_OPS_IDENTITY)``.

    For a signed app or daemon this is its bundle identifier (e.g. ``com.apple.CrashReporter``) -
    the domain its ``NSUserDefaults standardUserDefaults`` uses. None if the process is unsigned
    or has no identity. Works for daemons too, unlike ``SBSCopyDisplayIdentifierForProcessID``.
    """
    size = 1024
    async with self._client.safe_malloc(size) as buf:
        if await self._client.symbols.csops(self.pid, CS_OPS_IDENTITY, buf, size):
            return None
        # blob layout: uint32 type, uint32 length (big-endian), then the identity C-string
        identity = (await buf.peek(size))[8:].split(b"\x00", 1)[0]
    return identity.decode() if identity else None
```

#### ppid

```
ppid() -> int
```

Return the parent process id.

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/processes.py`

```
async def ppid(self) -> int:
    """Return the parent process id."""
    return (await self._get_pbsd()).pbi_ppid
```

#### uid

```
uid() -> int
```

Return the process user id.

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/processes.py`

```
async def uid(self) -> int:
    """Return the process user id."""
    return (await self._get_pbsd()).pbi_uid
```

#### gid

```
gid() -> int
```

Return the process group id.

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/processes.py`

```
async def gid(self) -> int:
    """Return the process group id."""
    return (await self._get_pbsd()).pbi_gid
```

#### ruid

```
ruid() -> int
```

Return the real user id.

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/processes.py`

```
async def ruid(self) -> int:
    """Return the real user id."""
    return (await self._get_pbsd()).pbi_ruid
```

#### rgid

```
rgid() -> int
```

Return the real group id.

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/processes.py`

```
async def rgid(self) -> int:
    """Return the real group id."""
    return (await self._get_pbsd()).pbi_rgid
```

#### start_time

```
start_time() -> datetime
```

Return the process start time.

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/processes.py`

```
async def start_time(self) -> datetime:
    """Return the process start time."""
    if self._start_time is None:
        if self._client.arch != ARCH_ARM64:
            raise NotImplementedError("implemented only on ARCH_ARM64")
        val = await (await type(self).vmu_proc_info(self)).objc_call_raw("startTime")
        tv_sec = val.x0
        tv_nsec = val.x1
        self._start_time = datetime.fromtimestamp(tv_sec + (tv_nsec / (10**9)))

    return self._start_time
```

#### parent

```
parent() -> Self
```

Return a Process wrapper for the parent pid.

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/processes.py`

```
async def parent(self) -> Self:
    """Return a Process wrapper for the parent pid."""
    return type(self)(self._client, await type(self).ppid(self))
```

#### environ

```
environ() -> dict[str, str]
```

Return the process environment as a `KEY -> VALUE` mapping.

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/processes.py`

```
async def environ(self) -> dict[str, str]:
    """Return the process environment as a ``KEY -> VALUE`` mapping."""
    entries = await (await (await type(self).vmu_proc_info(self)).objc_call("envVars")).py(list)
    return dict(entry.partition("=")[::2] for entry in entries)
```

#### arguments

```
arguments() -> list[str]
```

Return the process argument list.

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/processes.py`

```
async def arguments(self) -> list[str]:
    """Return the process argument list."""
    return await (await (await type(self).vmu_proc_info(self)).objc_call("arguments")).py(list)
```

#### raw_procargs2

```
raw_procargs2() -> bytes
```

Return the raw PROCARGS2 sysctl buffer.

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/processes.py`

```
async def raw_procargs2(self) -> bytes:
    """Return the raw PROCARGS2 sysctl buffer."""
    return await self._client.sysctl.get(CTL.KERN, KERN.PROCARGS2, self.pid)
```

#### procargs2

```
procargs2() -> Container
```

Parse and return the PROCARGS2 buffer.

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/processes.py`

```
async def procargs2(self) -> Container:
    """Parse and return the PROCARGS2 buffer."""
    return procargs2_t.parse(await type(self).raw_procargs2(self))
```

#### preferences

```
preferences(application_id: str | None = None, *, any_user: bool = False) -> ProcessPreferences[DarwinSymbolT_co]
```

Read/write a preference domain as *this* process resolves it (container, uid).

With no `application_id` this is the process's own bundle-id domain - the `standardUserDefaults` domain. See `ProcessPreferences`.

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/processes.py`

```
def preferences(
    self, application_id: str | None = None, *, any_user: bool = False
) -> "ProcessPreferences[DarwinSymbolT_co]":
    """Read/write a preference domain as *this* process resolves it (container, uid).

    With no ``application_id`` this is the process's own bundle-id domain - the
    ``standardUserDefaults`` domain. See ``ProcessPreferences``.
    """
    return ProcessPreferences(self, application_id, any_user=any_user)
```

#### get_regions

```
get_regions() -> list[Region[DarwinSymbolT_co]]
```

Return the list of VM regions for the process.

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/processes.py`

```
async def get_regions(self) -> list[Region[DarwinSymbolT_co]]:
    """Return the list of VM regions for the process."""
    result: list[Region[DarwinSymbolT_co]] = []

    # remove the '()' wrapping the list:
    #   (
    #       "item1",
    #       "item2",
    #   )
    regions_sym = await (await type(self).vmu_region_identifier(self)).objc_call("regions")
    buf = cast(str, await type(regions_sym).cfdesc(regions_sym)).split("\n")[1:-1]

    for line in buf:
        # remove line prefix and suffix and split into words
        line = line[_CF_STRING_ARRAY_PREFIX_LEN:-_CF_STRING_ARRAY_SUFFIX_LEN].split()
        i = 0

        region_type = line[i]
        i += 1

        while "-" not in line[i]:
            # skip till address range
            i += 1

        address_range = line[i]
        i += 1
        if not address_range.startswith("0x"):
            continue
        start, end = address_range.split("-")

        start = int(start, 16)
        end = int(end, 16)
        vsize = None
        if "V=" in line[i]:
            vsize = line[i].split("V=", 1)[1].split("]", 1)[0]

        while "/" not in line[i]:
            i += 1

        protection = line[i].split("/")
        i += 1

        region_detail = None
        if len(line) >= i + 1:
            region_detail = line[i]

        result.append(
            Region(
                region_type=region_type,
                start=self.get_process_symbol(start),
                end=end,
                vsize=vsize,
                protection=protection[0],
                protection_max=protection[1],
                region_detail=region_detail,
            )
        )

    return result
```

#### regions

```
regions() -> list[Region[DarwinSymbolT_co]]
```

Return the list of VM regions for the process.

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/processes.py`

```
async def regions(self) -> list[Region[DarwinSymbolT_co]]:
    """Return the list of VM regions for the process."""
    return await self.get_regions()
```

#### cdhash

```
cdhash() -> bytes
```

Return the code directory hash for the process.

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/processes.py`

```
async def cdhash(self) -> bytes:
    """Return the code directory hash for the process."""
    async with self._client.safe_malloc(CDHASH_SIZE) as cdhash:
        # by reversing online-auth-agent
        if await self._client.symbols.csops(self.pid, 5, cdhash, CDHASH_SIZE) != 0:
            raise BadReturnValueError(f"failed to get cdhash for {self.pid}")
        return await cdhash.peek(CDHASH_SIZE)
```

#### get_process_symbol

```
get_process_symbol(address: int) -> ProcessSymbol[DarwinSymbolT_co]
```

Create a process symbol for the given address.

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/processes.py`

```
def get_process_symbol(self, address: int) -> ProcessSymbol[DarwinSymbolT_co]:
    """Create a process symbol for the given address."""
    return ProcessSymbol(address, self)
```

#### vm_allocate

```
vm_allocate(size: int) -> ProcessSymbol[DarwinSymbolT_co]
```

Allocate memory in the target task and return its address.

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/processes.py`

```
async def vm_allocate(self, size: int) -> ProcessSymbol[DarwinSymbolT_co]:
    """Allocate memory in the target task and return its address."""
    async with self._client.safe_malloc(8) as out_address:
        if await self._client.symbols.vm_allocate(
            await type(self).task(self), out_address, size, VM_FLAGS_ANYWHERE
        ):
            raise BadReturnValueError("vm_allocate() failed")
        return self.get_process_symbol(await out_address.getindex(0))
```

#### dump_app

```
dump_app(output_dir: str | PurePath, chunk_size: int = CHUNK_SIZE) -> None
```

Based on: https://github.com/AloneMonkey/frida-ios-dump/blob/master/dump.js

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/processes.py`

```
async def dump_app(self, output_dir: str | PurePath, chunk_size: int = CHUNK_SIZE) -> None:
    """
    Based on:
    https://github.com/AloneMonkey/frida-ios-dump/blob/master/dump.js
    """
    for image in await type(self).app_images(self):
        relative_name = image.path.split(APP_SUFFIX, 1)[1]
        output_file = Path(output_dir).expanduser() / relative_name
        output_file.parent.mkdir(exist_ok=True, parents=True)
        logger.debug(f"dumping: {output_file}")

        with open(output_file, "wb") as output_file:
            # Symbol reads are async, so fetch the header + load commands first and parse locally.
            # Offsets captured by `Tell` are then relative to the image start.
            header = await image.address.peek(MACH_HEADER_64_SIZE)
            sizeofcmds = Int32ul.parse(header[MACH_HEADER_SIZEOFCMDS_OFFSET:][:4])
            macho_in_memory = mach_header_t.parse(await image.address.peek(MACH_HEADER_64_SIZE + sizeofcmds))

            async with await self._client.fs.open(image.path, "r") as fat_file:
                # locating the correct MachO offset within the FAT image (if FAT)
                magic_in_fs = await fat_file.parse(Int32ul)
                await fat_file.seek(0, SEEK_SET)
                if magic_in_fs in (FAT_CIGAM, FAT_MAGIC):
                    parsed_fat = await fat_file.parse(fat_header)
                    for arch in parsed_fat.archs:
                        if (
                            arch.cputype == macho_in_memory.cputype
                            and arch.cpusubtype == macho_in_memory.cpusubtype
                        ):
                            # correct MachO offset found
                            file_offset = arch.offset
                            break
                    else:
                        raise RuntimeError("Failed to find file offset.")

                    await fat_file.seek(file_offset, SEEK_SET)

                # perform actual MachO dump
                output_file.seek(0, SEEK_SET)
                while True:
                    chunk = await fat_file.read(chunk_size)
                    if len(chunk) == 0:
                        break
                    output_file.write(chunk)

                offset_cryptid = None

                # if image is encrypted, patch its encryption loader command
                for load_command in macho_in_memory.load_commands:
                    if load_command.cmd in (
                        LOAD_COMMAND_TYPE.LC_ENCRYPTION_INFO_64,
                        LOAD_COMMAND_TYPE.LC_ENCRYPTION_INFO,
                    ):
                        # cryptid follows cryptoff and cryptsize in both command variants
                        offset_cryptid = load_command._data_offset + 8
                        crypt_offset = load_command.data.cryptoff
                        crypt_size = load_command.data.cryptsize
                        break
                else:
                    raise RuntimeError("Failed to find LC_ENCRYPTION_INFO or LC_ENCRYPTION_INFO_64 command.")

                if offset_cryptid is not None:
                    output_file.seek(offset_cryptid, SEEK_SET)
                    output_file.write(b"\x00" * 4)  # cryptid = 0
                    output_file.seek(crypt_offset, SEEK_SET)
                    output_file.flush()
                    output_file.write(await image.address.peek(crypt_size, crypt_offset))
```

#### get_mach_ports

```
get_mach_ports(include_thread_info: bool = False, resolve_kobjects: bool = False) -> AsyncGenerator[MachPortInfo]
```

Enumerate this process's own mach ports, with rights, kobject type and exception handlers.

Parameters:

| Name                  | Type   | Description                                                                                                                                         | Default |
| --------------------- | ------ | --------------------------------------------------------------------------------------------------------------------------------------------------- | ------- |
| `include_thread_info` | `bool` | also collect this task's thread ids.                                                                                                                | `False` |
| `resolve_kobjects`    | `bool` | resolve each port's kernel-object type (IKOT\_\*); one extra RPC per port, so it is off by default (MachPortInfo.kobject stays None when disabled). | `False` |

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/processes.py`

```
async def get_mach_ports(
    self, include_thread_info: bool = False, resolve_kobjects: bool = False
) -> AsyncGenerator[MachPortInfo]:
    """Enumerate this process's own mach ports, with rights, kobject type and exception handlers.

    :param include_thread_info: also collect this task's thread ids.
    :param resolve_kobjects: resolve each port's kernel-object type (IKOT_*); one extra RPC per
        port, so it is off by default (``MachPortInfo.kobject`` stays ``None`` when disabled).
    """
    async for port in self._client.processes.get_pid_mach_ports(
        self.pid, include_thread_info=include_thread_info, resolve_kobjects=resolve_kobjects
    ):
        yield port
```

#### get_mach_port_cross_ref_info

```
get_mach_port_cross_ref_info() -> list[MachPortCrossRefInfo]
```

Get all allocated mach ports and cross-refs to get the recv right owner

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/processes.py`

```
async def get_mach_port_cross_ref_info(self) -> list[MachPortCrossRefInfo]:
    """Get all allocated mach ports and cross-refs to get the recv right owner"""
    own_ports: list[MachPortInfo] = []
    cross_refs_info: dict[int, list[MachPortInfo]] = {}
    async for port in self._client.processes.get_mach_ports():
        if port.pid == self.pid:
            own_ports.append(port)
        if port.ipc_object not in cross_refs_info:
            cross_refs_info[port.ipc_object] = []
        cross_refs_info[port.ipc_object].append(port)

    return [
        MachPortCrossRefInfo(
            name=port.name,
            ipc_object=port.ipc_object,
            rights=port.rights,
            recv_right_pid=cross_ref_port_info.pid,
            recv_right_proc_name=cross_ref_port_info.proc_name,
        )
        for port in own_ports
        for cross_ref_port_info in cross_refs_info[port.ipc_object]
        if cross_ref_port_info.has_recv_right
    ]
```

#### get_memgraph_snapshot

```
get_memgraph_snapshot() -> bytes
```

Return a memory graph snapshot as plist bytes.

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/processes.py`

```
async def get_memgraph_snapshot(self) -> bytes:
    """Return a memory graph snapshot as plist bytes."""
    scanner = None
    try:
        # first attempt via new API
        scanner = await (await self._client.symbols.objc_getClass("VMUProcessObjectGraph")).objc_call(
            "createWithTask:", await type(self).task_read(self)
        )
        snapshot_graph = await (await scanner.objc_call("plistRepresentationWithOptions:", 0)).py(bytes)
    except UnrecognizedSelectorError:
        # if failed, attempt with old API
        scanner = await (
            await (await self._client.symbols.objc_getClass("VMUTaskMemoryScanner")).objc_call("alloc")
        ).objc_call("initWithTask:", await type(self).task_read(self))
        await scanner.objc_call("addRootNodesFromTask")
        await scanner.objc_call("addMallocNodesFromTask")
        snapshot_graph = await (
            await (await scanner.objc_call("processSnapshotGraph")).objc_call("plistRepresentationWithOptions:", 0)
        ).py(bytes)
    finally:
        if scanner is not None:
            # free object scanner so process can resume
            await scanner.objc_call("release")
    return snapshot_graph
```

### DarwinProcesses

Bases: `Processes['DarwinClient[DarwinSymbolT_co]']`, `Generic[DarwinSymbolT_co]`

manage processes

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/processes.py`

```
class DarwinProcesses(Processes["DarwinClient[DarwinSymbolT_co]"], Generic[DarwinSymbolT_co]):
    """manage processes"""

    def __init__(self, client: "DarwinClient[DarwinSymbolT_co]") -> None:
        """Initialize the Darwin process subsystem."""
        super().__init__(client)
        client.load_framework_lazy("Symbolication")

    _self_process: Process[DarwinSymbolT_co] | None = None

    async def get_self(self) -> Process[DarwinSymbolT_co]:
        """get self process"""
        if self._self_process is None:
            self._self_process = Process(self._client, await self._client.get_pid())

        return self._self_process

    async def get_by_pid(self, pid: int) -> Process[DarwinSymbolT_co]:
        """get process object by pid"""
        proc_list = await self.list()
        for p in proc_list:
            if p.pid == pid:
                return p
        raise ArgumentError(f"failed to locate process with pid: {pid}")

    async def get_by_basename(self, name: str) -> Process[DarwinSymbolT_co]:
        """get process object by basename"""
        proc_list = await self.list()
        for p in proc_list:
            if await type(p).basename(p) == name:
                return p
        raise ArgumentError(f"failed to locate process with name: {name}")

    async def get_by_name(self, name: str) -> Process[DarwinSymbolT_co]:
        """get process object by name"""
        proc_list = await self.list()
        for p in proc_list:
            if await type(p).name(p) == name:
                return p
        raise ArgumentError(f"failed to locate process with name: {name}")

    async def grep(self, name: str) -> list[Process[DarwinSymbolT_co]]:
        """get process list by basename filter"""
        result = []
        proc_list = await self.list()
        for p in proc_list:
            basename = await type(p).basename(p)
            if basename and name in basename:
                result.append(p)
        return result

    async def get_processes_by_listening_port(self, port: int) -> list[Process[DarwinSymbolT_co]]:
        """get a process object listening on the specified port"""
        listening_processes = []
        for process in await self.list():
            try:
                fds = await type(process).fds(process)
            except BadReturnValueError:
                # it's possible to get error if new processes have since died or the rpcserver
                # doesn't have the required permissions to access all the processes
                continue

            for fd in fds:
                if (isinstance(fd, (Ipv4SocketFd, Ipv6SocketFd))) and fd.local_port == port and fd.remote_port == 0:
                    listening_processes.append(process)
        return listening_processes

    async def lsof(self) -> dict[int, list[Fd]]:
        """get dictionary of pid to its opened fds"""
        result = {}
        for process in await self.list():
            try:
                fds = await type(process).fds(process)
            except BadReturnValueError:
                # it's possible to get error if new processes have since died or the rpcserver
                # doesn't have the required permissions to access all the processes
                continue

            result[process.pid] = fds
        return result

    async def fuser(self, path: str | PurePath) -> list[Process[DarwinSymbolT_co]]:
        """get a list of all processes have an open hande to the specified path"""
        result = []
        proc_list = await self.list()
        for process in proc_list:
            try:
                fds = await type(process).fds(process)
            except BadReturnValueError:
                # it's possible to get error if new processes have since died or the rpcserver
                # doesn't have the required permissions to access all the processes
                continue

            for fd in fds:
                if isinstance(fd, FileFd) and (str(Path(fd.path).absolute()) == str(Path(path).absolute())):
                    result.append(process)

        return result

    async def list(self) -> list[Process[DarwinSymbolT_co]]:
        """list all currently running processes"""
        n = await self._client.symbols.proc_listallpids(0, 0)
        pid_buf_size = pid_t.sizeof() * n
        async with self._client.safe_malloc(pid_buf_size) as pid_buf:
            pid_buf.item_size = pid_t.sizeof()
            n = await self._client.symbols.proc_listallpids(pid_buf, pid_buf_size)

            result = []
            for i in range(n):
                pid = int(await pid_buf.getindex(i))
                result.append(Process(self._client, pid))
            return result

    async def disable_watchdog(self) -> None:
        """Continuously kill watchdogd to keep it disabled."""
        while True:
            with contextlib.suppress(ArgumentError):
                await (await self.get_by_basename("watchdogd")).kill(SIGKILL)

            await asyncio.sleep(1)

    async def get_mach_ports(
        self, include_thread_info: bool = False, resolve_kobjects: bool = False
    ) -> AsyncGenerator[MachPortInfo]:
        """Enumerate all mach ports (heavily inspired by lsmp).

        :param include_thread_info: also collect each task's thread ids (costs extra RPCs per thread).
        :param resolve_kobjects: resolve every port's kernel-object type (IKOT_*, e.g. TASK_CONTROL /
            THREAD / HOST / CLOCK / IOKIT_CONNECT). This issues one extra RPC per port, so it is off
            by default; when disabled ``MachPortInfo.kobject`` stays ``None``.
        """
        mach_task_self = await self._client.symbols.mach_task_self()
        for task in await self._list_task_read_ports(mach_task_self):
            async for port in self._dump_task_ipc_space(mach_task_self, task, include_thread_info, resolve_kobjects):
                yield port

    async def get_pid_mach_ports(
        self, pid: int, include_thread_info: bool = False, resolve_kobjects: bool = False
    ) -> AsyncGenerator[MachPortInfo]:
        """Enumerate the mach ports of a single task, addressed by pid.

        Unlike :meth:`get_mach_ports` this reads only the target's own IPC space (no processor-set
        walk), so it needs privilege only to read that one task. See :meth:`get_mach_ports` for the
        meaning of ``include_thread_info`` / ``resolve_kobjects``.
        """
        mach_task_self = await self._client.symbols.mach_task_self()
        async with self._client.safe_malloc(8) as p_task:
            if await self._client.symbols.task_read_for_pid(mach_task_self, pid, p_task) != 0:
                raise BadReturnValueError(f"task_read_for_pid({pid}) failed")
            task = int(await p_task.getindex(0))
        async for port in self._dump_task_ipc_space(mach_task_self, task, include_thread_info, resolve_kobjects):
            yield port

    async def _list_task_read_ports(self, mach_task_self: int) -> Sequence[int]:
        """Return the task read ports to enumerate: every task when privileged, else just our own."""
        if await self._client.symbols.getuid() != 0:
            logger.warning("should run as root for best output (cross-ref to other tasks' ports)")
            async with self._client.safe_malloc(8) as p_task:
                if await self._client.symbols.task_read_for_pid(mach_task_self, (await self.get_self()).pid, p_task):
                    raise BadReturnValueError("task_read_for_pid() failed")
                return [int(await p_task.getindex(0))]

        # privileged: convert the processor set to the full list of task read ports so ports held in
        # other tasks can be cross-referenced
        async with (
            self._client.safe_malloc(8) as p_psets,
            self._client.safe_malloc(8) as p_pset_count,
            self._client.safe_malloc(8) as p_pset_priv,
            self._client.safe_malloc(8) as p_tasks,
            self._client.safe_malloc(8) as p_task_count,
        ):
            host = await self._client.symbols.mach_host_self()
            if await self._client.symbols.host_processor_sets(host, p_psets, p_pset_count) != 0:
                raise BadReturnValueError("host_processor_sets() failed")
            if await p_pset_count.getindex(0) != 1:
                raise BadReturnValueError("Assertion Failure: pset count greater than one")
            if await self._client.symbols.host_processor_set_priv(host, await p_psets.getindex(0, 0), p_pset_priv) != 0:
                raise BadReturnValueError("host_processor_set_priv() failed")

            await self._client.symbols.mach_port_deallocate(mach_task_self, await p_psets.getindex(0, 0))
            await self._client.symbols.vm_deallocate(
                mach_task_self, await p_psets.getindex(0), await p_pset_count.getindex(0) * mach_port_t.sizeof()
            )

            if (
                await self._client.symbols.processor_set_tasks_with_flavor(
                    await p_pset_priv.getindex(0), TASK_FLAVOR_READ, p_tasks, p_task_count
                )
                != 0
            ):
                raise BadReturnValueError("processor_set_tasks_with_flavor() failed")
            await self._client.symbols.vm_deallocate(mach_task_self, await p_pset_priv.getindex(0))

            task_count = int(await p_task_count.getindex(0))
            tasks_ptr = await p_tasks.getindex(0)
            tasks = list(struct.unpack(f"<{task_count}I", await tasks_ptr.peek(task_count * 4))) if task_count else []
            await self._client.symbols.vm_deallocate(mach_task_self, tasks_ptr, task_count * mach_port_t.sizeof())

        # move our own task to the end so its (self-referential) ports come last, matching lsmp
        for i, task in enumerate(tasks):
            if await self._client.symbols.mach_task_is_self(task):
                tasks[i], tasks[-1] = tasks[-1], tasks[i]
                break
        return tasks

    async def _dump_task_ipc_space(
        self, mach_task_self: int, task: int, include_thread_info: bool, resolve_kobjects: bool
    ) -> AsyncGenerator[MachPortInfo]:
        """Yield a ``MachPortInfo`` for every named right in a single task's IPC space.

        If the task dies mid-enumeration one of the mach calls fails; we log and stop for that task
        (its port is now dead) instead of aborting the whole walk. The task read port is always
        released via the ``finally``, so repeated calls don't leak a port per task.
        """
        try:
            pid = await self._pid_for_task(task)

            exception_ports = await self._read_exception_ports(self._client.symbols.task_get_exception_ports_info, task)
            if exception_ports is None:
                logger.debug("skipping pid %s: task_get_exception_ports_info() failed (task likely died)", pid)
                return

            thread_info = None
            if include_thread_info:
                thread_info = await self._collect_thread_info(mach_task_self, task, exception_ports)
                if thread_info is None:
                    logger.debug("skipping pid %s: task_threads() failed (task likely died)", pid)
                    return

            entries = await self._read_port_space(mach_task_self, task)
            if entries is None:
                logger.debug("skipping pid %s: mach_port_space_info() failed (task likely died)", pid)
                return

            proc_name = await self._task_proc_name(pid)
            for entry in entries:
                port = await self._classify_port_entry(
                    task, pid, entry, proc_name, thread_info, exception_ports, resolve_kobjects
                )
                if port is not None:
                    yield port
        finally:
            await self._client.symbols.mach_port_deallocate(mach_task_self, task)

    async def _pid_for_task(self, task: int) -> int:
        """Resolve the pid owning a task port."""
        async with self._client.safe_malloc(4) as p_pid:
            p_pid.item_size = 4
            await self._client.symbols.pid_for_task(task, p_pid)
            return int((await p_pid.getindex(0)).c_uint32)

    async def _task_proc_name(self, pid: int) -> str | None:
        """Return the executable name for a pid, or None if it can't be resolved."""
        async with self._client.safe_malloc(100) as proc_name:
            if await self._client.symbols.proc_name(pid, proc_name, 100) == 0:
                return None
            return await proc_name.peek_str()

    async def _read_exception_ports(self, getter, port: int) -> dict[int, MachPortExceptionInfo] | None:
        """Read the exception handler ports of a task or thread via ``getter`` (the ``*_info`` variant).

        Returns a map of ``ipc_object`` -> :class:`MachPortExceptionInfo` so port-table entries can be
        matched to the handler they implement. Returns None if the call fails (port likely died).
        """
        async with (
            self._client.safe_malloc(4) as p_count,
            self._client.safe_malloc(ipc_info_port_t.sizeof() * EXC_TYPES_COUNT) as ports_info,
            self._client.safe_malloc(4 * EXC_TYPES_COUNT) as masks,
            self._client.safe_malloc(4 * EXC_TYPES_COUNT) as behaviors,
            self._client.safe_malloc(4 * EXC_TYPES_COUNT) as flavors,
        ):
            p_count.item_size = 4
            if await getter(port, EXC_MASK_ALL, masks, p_count, ports_info, behaviors, flavors) != 0:
                return None

            count = int((await p_count.getindex(0)).c_uint32)
            if not count:
                return {}
            mask_vals = struct.unpack(f"<{count}I", await masks.peek(4 * count))
            behavior_vals = struct.unpack(f"<{count}I", await behaviors.peek(4 * count))
            flavor_vals = struct.unpack(f"<{count}I", await flavors.peek(4 * count))
            port_infos = await ports_info.parse(Array(count, ipc_info_port_t))

            result: dict[int, MachPortExceptionInfo] = {}
            for i in range(count):
                obj = port_infos[i].iip_port_object
                if not obj:
                    continue  # no handler registered for this exception slot
                result[obj] = MachPortExceptionInfo(
                    masks=exc_mask_names(mask_vals[i]), behavior=behavior_vals[i], flavor=flavor_vals[i]
                )
            return result

    async def _collect_thread_info(
        self, mach_task_self: int, task: int, exception_ports: dict[int, MachPortExceptionInfo]
    ) -> MachPortThreadInfo | None:
        """Collect a task's thread ids and fold each thread's exception handlers into ``exception_ports``."""
        async with (
            self._client.safe_malloc(8) as p_thread_ports,
            self._client.safe_malloc(4) as p_thread_count,
        ):
            p_thread_count.item_size = 4
            if await self._client.symbols.task_threads(task, p_thread_ports, p_thread_count) != 0:
                return None
            thread_count = int((await p_thread_count.getindex(0)).c_uint32)
            thread_ports = (
                struct.unpack(f"<{thread_count}I", await (await p_thread_ports.getindex(0)).peek(4 * thread_count))
                if thread_count
                else ()
            )

        thread_ids = []
        for thread_port in thread_ports:
            thread_exceptions = await self._read_exception_ports(
                self._client.symbols.thread_get_exception_ports_info, thread_port
            )
            for obj, info in (thread_exceptions or {}).items():
                exception_ports.setdefault(obj, info)

            thread_id = await self._resolve_thread_id(mach_task_self, thread_port)
            if thread_id is not None:
                thread_ids.append(thread_id)
            await self._client.symbols.mach_port_deallocate(mach_task_self, thread_port)
        return MachPortThreadInfo(thread_ids=thread_ids)

    async def _resolve_thread_id(self, mach_task_self: int, thread_port: int) -> int | None:
        """Resolve the kernel thread id behind a thread port, or None if unavailable."""
        async with (
            self._client.safe_malloc(4) as p_kotype,
            self._client.safe_malloc(4) as p_kobject,
            self._client.safe_malloc(thread_identifier_info.sizeof()) as th_info,
            self._client.safe_malloc(4) as p_info_count,
        ):
            p_kotype.item_size = 4
            p_info_count.item_size = 4
            await p_info_count.setindex(0, THREAD_IDENTIFIER_INFO_COUNT)
            if (
                await self._client.symbols.mach_port_kernel_object(mach_task_self, thread_port, p_kotype, p_kobject)
                == 0
                and await self._client.symbols.thread_info(thread_port, THREAD_IDENTIFIER_INFO, th_info, p_info_count)
                == 0
            ):
                return (await th_info.parse(thread_identifier_info)).thread_id
        return None

    async def _read_port_space(self, mach_task_self: int, task: int) -> Sequence | None:
        """Parse a task's IPC name table, freeing the kernel-allocated arrays. None if the task died."""
        async with (
            self._client.safe_malloc(200) as space_info,
            self._client.safe_malloc(8) as p_table,
            self._client.safe_malloc(4) as p_table_count,
            self._client.safe_malloc(8) as p_tree,
            self._client.safe_malloc(4) as p_tree_count,
        ):
            p_table_count.item_size = 4
            p_tree_count.item_size = 4
            if (
                await self._client.symbols.mach_port_space_info(
                    task, space_info, p_table, p_table_count, p_tree, p_tree_count
                )
                != 0
            ):
                return None

            table_count = int((await p_table_count.getindex(0)).c_uint32)
            table_ptr = await p_table.getindex(0)
            entries = list(await table_ptr.parse(Array(table_count, ipc_info_name_t))) if table_count else []
            if table_ptr:
                await self._client.symbols.vm_deallocate(
                    mach_task_self, table_ptr, table_count * ipc_info_name_t.sizeof()
                )

            tree_ptr = await p_tree.getindex(0)
            tree_count = int((await p_tree_count.getindex(0)).c_uint32)
            if tree_ptr and tree_count:
                await self._client.symbols.vm_deallocate(
                    mach_task_self, tree_ptr, tree_count * ipc_info_name_t.sizeof()
                )
            return entries

    async def _classify_port_entry(
        self,
        task: int,
        pid: int,
        entry,
        proc_name: str | None,
        thread_info: MachPortThreadInfo | None,
        exception_ports: dict[int, MachPortExceptionInfo],
        resolve_kobjects: bool,
    ) -> MachPortInfo | None:
        """Turn one raw IPC table entry into a :class:`MachPortInfo`, or None for slots to skip."""
        if entry.iin_type & MACH_PORT_TYPE_ALL_RIGHTS == 0:
            return None  # empty table slot
        if entry.iin_type == MACH_PORT_TYPE_PORT_SET:
            return None

        rights = []
        if entry.iin_type & MACH_PORT_TYPE_SEND:
            rights.append("send")
        dead = bool(entry.iin_type & MACH_PORT_TYPE_DNREQUEST)
        if entry.iin_type & MACH_PORT_TYPE_RECEIVE:
            rights.append("recv")
        elif entry.iin_type == MACH_PORT_TYPE_DEAD_NAME:
            return None
        if entry.iin_type & MACH_PORT_TYPE_SEND_ONCE:
            rights.append("send-once")

        kobject = await self._resolve_kobject(task, entry.iin_name) if resolve_kobjects else None
        return MachPortInfo(
            task=task,
            pid=pid,
            name=entry.iin_name,
            rights=rights,
            ipc_object=entry.iin_object,
            dead=dead,
            proc_name=proc_name,
            thread_info=thread_info,
            kobject=kobject,
            exception=exception_ports.get(entry.iin_object),
        )

    async def _resolve_kobject(self, task: int, name: int) -> MachPortKobjectInfo | None:
        """Resolve the kernel-object identity (IKOT_*) a port names, or None if it isn't one.

        Regular (non-kernel) ports report ``IKOT_NONE``; ports the kernel declines to disclose report
        the all-ones sentinel. Both mean "not an identifiable kernel object", so both yield None.
        """
        async with (
            self._client.safe_calloc(4) as p_kotype,
            self._client.safe_calloc(4) as p_kobject,
        ):
            p_kotype.item_size = 4
            p_kobject.item_size = 4
            if await self._client.symbols.mach_port_kernel_object(task, name, p_kotype, p_kobject) != 0:
                return None
            kotype = int((await p_kotype.getindex(0)).c_uint32)
            if kotype in (IKOT_NONE, _IKOT_UNDISCLOSED):
                return None
            addr = int((await p_kobject.getindex(0)).c_uint32)
            return MachPortKobjectInfo(type_id=kotype, type=ikot_name(kotype), addr=addr)
```

#### get_self

```
get_self() -> Process[DarwinSymbolT_co]
```

get self process

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/processes.py`

```
async def get_self(self) -> Process[DarwinSymbolT_co]:
    """get self process"""
    if self._self_process is None:
        self._self_process = Process(self._client, await self._client.get_pid())

    return self._self_process
```

#### get_by_pid

```
get_by_pid(pid: int) -> Process[DarwinSymbolT_co]
```

get process object by pid

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/processes.py`

```
async def get_by_pid(self, pid: int) -> Process[DarwinSymbolT_co]:
    """get process object by pid"""
    proc_list = await self.list()
    for p in proc_list:
        if p.pid == pid:
            return p
    raise ArgumentError(f"failed to locate process with pid: {pid}")
```

#### get_by_basename

```
get_by_basename(name: str) -> Process[DarwinSymbolT_co]
```

get process object by basename

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/processes.py`

```
async def get_by_basename(self, name: str) -> Process[DarwinSymbolT_co]:
    """get process object by basename"""
    proc_list = await self.list()
    for p in proc_list:
        if await type(p).basename(p) == name:
            return p
    raise ArgumentError(f"failed to locate process with name: {name}")
```

#### get_by_name

```
get_by_name(name: str) -> Process[DarwinSymbolT_co]
```

get process object by name

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/processes.py`

```
async def get_by_name(self, name: str) -> Process[DarwinSymbolT_co]:
    """get process object by name"""
    proc_list = await self.list()
    for p in proc_list:
        if await type(p).name(p) == name:
            return p
    raise ArgumentError(f"failed to locate process with name: {name}")
```

#### grep

```
grep(name: str) -> list[Process[DarwinSymbolT_co]]
```

get process list by basename filter

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/processes.py`

```
async def grep(self, name: str) -> list[Process[DarwinSymbolT_co]]:
    """get process list by basename filter"""
    result = []
    proc_list = await self.list()
    for p in proc_list:
        basename = await type(p).basename(p)
        if basename and name in basename:
            result.append(p)
    return result
```

#### get_processes_by_listening_port

```
get_processes_by_listening_port(port: int) -> list[Process[DarwinSymbolT_co]]
```

get a process object listening on the specified port

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/processes.py`

```
async def get_processes_by_listening_port(self, port: int) -> list[Process[DarwinSymbolT_co]]:
    """get a process object listening on the specified port"""
    listening_processes = []
    for process in await self.list():
        try:
            fds = await type(process).fds(process)
        except BadReturnValueError:
            # it's possible to get error if new processes have since died or the rpcserver
            # doesn't have the required permissions to access all the processes
            continue

        for fd in fds:
            if (isinstance(fd, (Ipv4SocketFd, Ipv6SocketFd))) and fd.local_port == port and fd.remote_port == 0:
                listening_processes.append(process)
    return listening_processes
```

#### lsof

```
lsof() -> dict[int, list[Fd]]
```

get dictionary of pid to its opened fds

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/processes.py`

```
async def lsof(self) -> dict[int, list[Fd]]:
    """get dictionary of pid to its opened fds"""
    result = {}
    for process in await self.list():
        try:
            fds = await type(process).fds(process)
        except BadReturnValueError:
            # it's possible to get error if new processes have since died or the rpcserver
            # doesn't have the required permissions to access all the processes
            continue

        result[process.pid] = fds
    return result
```

#### fuser

```
fuser(path: str | PurePath) -> list[Process[DarwinSymbolT_co]]
```

get a list of all processes have an open hande to the specified path

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/processes.py`

```
async def fuser(self, path: str | PurePath) -> list[Process[DarwinSymbolT_co]]:
    """get a list of all processes have an open hande to the specified path"""
    result = []
    proc_list = await self.list()
    for process in proc_list:
        try:
            fds = await type(process).fds(process)
        except BadReturnValueError:
            # it's possible to get error if new processes have since died or the rpcserver
            # doesn't have the required permissions to access all the processes
            continue

        for fd in fds:
            if isinstance(fd, FileFd) and (str(Path(fd.path).absolute()) == str(Path(path).absolute())):
                result.append(process)

    return result
```

#### list

```
list() -> list[Process[DarwinSymbolT_co]]
```

list all currently running processes

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/processes.py`

```
async def list(self) -> list[Process[DarwinSymbolT_co]]:
    """list all currently running processes"""
    n = await self._client.symbols.proc_listallpids(0, 0)
    pid_buf_size = pid_t.sizeof() * n
    async with self._client.safe_malloc(pid_buf_size) as pid_buf:
        pid_buf.item_size = pid_t.sizeof()
        n = await self._client.symbols.proc_listallpids(pid_buf, pid_buf_size)

        result = []
        for i in range(n):
            pid = int(await pid_buf.getindex(i))
            result.append(Process(self._client, pid))
        return result
```

#### disable_watchdog

```
disable_watchdog() -> None
```

Continuously kill watchdogd to keep it disabled.

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/processes.py`

```
async def disable_watchdog(self) -> None:
    """Continuously kill watchdogd to keep it disabled."""
    while True:
        with contextlib.suppress(ArgumentError):
            await (await self.get_by_basename("watchdogd")).kill(SIGKILL)

        await asyncio.sleep(1)
```

#### get_mach_ports

```
get_mach_ports(include_thread_info: bool = False, resolve_kobjects: bool = False) -> AsyncGenerator[MachPortInfo]
```

Enumerate all mach ports (heavily inspired by lsmp).

Parameters:

| Name                  | Type   | Description                                                                                                                                                                                                                | Default |
| --------------------- | ------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------- |
| `include_thread_info` | `bool` | also collect each task's thread ids (costs extra RPCs per thread).                                                                                                                                                         | `False` |
| `resolve_kobjects`    | `bool` | resolve every port's kernel-object type (IKOT\_\*, e.g. TASK_CONTROL / THREAD / HOST / CLOCK / IOKIT_CONNECT). This issues one extra RPC per port, so it is off by default; when disabled MachPortInfo.kobject stays None. | `False` |

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/processes.py`

```
async def get_mach_ports(
    self, include_thread_info: bool = False, resolve_kobjects: bool = False
) -> AsyncGenerator[MachPortInfo]:
    """Enumerate all mach ports (heavily inspired by lsmp).

    :param include_thread_info: also collect each task's thread ids (costs extra RPCs per thread).
    :param resolve_kobjects: resolve every port's kernel-object type (IKOT_*, e.g. TASK_CONTROL /
        THREAD / HOST / CLOCK / IOKIT_CONNECT). This issues one extra RPC per port, so it is off
        by default; when disabled ``MachPortInfo.kobject`` stays ``None``.
    """
    mach_task_self = await self._client.symbols.mach_task_self()
    for task in await self._list_task_read_ports(mach_task_self):
        async for port in self._dump_task_ipc_space(mach_task_self, task, include_thread_info, resolve_kobjects):
            yield port
```

#### get_pid_mach_ports

```
get_pid_mach_ports(pid: int, include_thread_info: bool = False, resolve_kobjects: bool = False) -> AsyncGenerator[MachPortInfo]
```

Enumerate the mach ports of a single task, addressed by pid.

Unlike :meth:`get_mach_ports` this reads only the target's own IPC space (no processor-set walk), so it needs privilege only to read that one task. See :meth:`get_mach_ports` for the meaning of `include_thread_info` / `resolve_kobjects`.

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/processes.py`

```
async def get_pid_mach_ports(
    self, pid: int, include_thread_info: bool = False, resolve_kobjects: bool = False
) -> AsyncGenerator[MachPortInfo]:
    """Enumerate the mach ports of a single task, addressed by pid.

    Unlike :meth:`get_mach_ports` this reads only the target's own IPC space (no processor-set
    walk), so it needs privilege only to read that one task. See :meth:`get_mach_ports` for the
    meaning of ``include_thread_info`` / ``resolve_kobjects``.
    """
    mach_task_self = await self._client.symbols.mach_task_self()
    async with self._client.safe_malloc(8) as p_task:
        if await self._client.symbols.task_read_for_pid(mach_task_self, pid, p_task) != 0:
            raise BadReturnValueError(f"task_read_for_pid({pid}) failed")
        task = int(await p_task.getindex(0))
    async for port in self._dump_task_ipc_space(mach_task_self, task, include_thread_info, resolve_kobjects):
        yield port
```

## HID

## rpcclient.clients.darwin.subsystems.hid

### Hid

Bases: `ClientBound['DarwinClient[DarwinSymbolT_co]']`, `Generic[DarwinSymbolT_co]`

Control HID devices and simulate events

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/hid.py`

```
class Hid(ClientBound["DarwinClient[DarwinSymbolT_co]"], Generic[DarwinSymbolT_co]):
    """Control HID devices and simulate events"""

    def __init__(self, client: "DarwinClient[DarwinSymbolT_co]") -> None:
        self._client = client

    async def send_double_home_button_press(self) -> None:
        await self.send_home_button_press()
        await self.send_home_button_press()

    async def send_rewind_button_press(self) -> None:
        await self.send_key_press(kHIDPage_Consumer, kHIDUsage_Csmr_Rewind)

    async def send_random_play_button_press(self) -> None:
        await self.send_key_press(kHIDPage_Consumer, kHIDUsage_Csmr_RandomPlay)

    async def send_repeat_button_press(self) -> None:
        await self.send_key_press(kHIDPage_Consumer, kHIDUsage_Csmr_Repeat)

    async def send_fast_forward_button_press(self) -> None:
        await self.send_key_press(kHIDPage_Consumer, kHIDUsage_Csmr_FastForward)

    async def send_play_button_press(self) -> None:
        await self.send_key_press(kHIDPage_Consumer, kHIDUsage_Csmr_Play)

    async def send_pause_button_press(self) -> None:
        await self.send_key_press(kHIDPage_Consumer, kHIDUsage_Csmr_Pause)

    async def send_play_pause_button_press(self) -> None:
        await self.send_key_press(kHIDPage_Consumer, kHIDUsage_Csmr_PlayOrPause)

    async def send_search_button_press(self) -> None:
        await self.send_key_press(kHIDPage_Consumer, kHIDUsage_Csmr_ACSearch)

    async def send_mute_button_press(self) -> None:
        await self.send_key_press(kHIDPage_Consumer, kHIDUsage_Csmr_Mute)

    async def send_home_button_press(self) -> None:
        await self.send_key_press(kHIDPage_Consumer, kHIDUsage_Csmr_Menu)

    async def send_power_button_press(self, interval: int = 0) -> None:
        await self.send_key_press(kHIDPage_Consumer, kHIDUsage_Csmr_Power, interval=interval)

    async def send_volume_down_button_press(self, interval: int = 0) -> None:
        await self.send_key_press(kHIDPage_Consumer, kHIDUsage_Csmr_VolumeDecrement, interval=interval)

    async def send_volume_up_button_press(self, interval: int = 0) -> None:
        await self.send_key_press(kHIDPage_Consumer, kHIDUsage_Csmr_VolumeIncrement, interval=interval)

    async def send_key_press(self, page: int, key_code: int, interval: float | int = 0) -> None:
        await self.send_keyboard_event(page, key_code, True)
        if interval:
            await asyncio.sleep(interval)
        await self.send_keyboard_event(page, key_code, False)

    async def send_keyboard_event(self, page: int, key_code: int, down: bool) -> None:
        event = await self._client.symbols.IOHIDEventCreateKeyboardEvent(
            kCFAllocatorDefault, await self._client.symbols.mach_absolute_time(), page, key_code, down, 0
        )
        if not event:
            raise BadReturnValueError("IOHIDEventCreateKeyboardEvent() failed")

        await self.dispatch(event)

    async def send_swipe_right(self) -> None:
        await self.send_swipe(0.5, 0.5, 1.0, 0.5)

    async def send_swipe_left(self) -> None:
        await self.send_swipe(0.5, 0.5, 0.0, 0.5)

    async def send_swipe_up(self) -> None:
        await self.send_swipe(0.5, 1.5, 0.5, 0.5)

    async def send_swipe_down(self) -> None:
        await self.send_swipe(0.5, 0.5, 0.5, 1.5)

    async def send_swipe(self, from_x: float, from_y: float, to_x: float, to_y: float) -> None:
        await self.send_touch_event(TouchEventType.TOUCH_DOWN, from_x, from_y)
        await asyncio.sleep(TOUCH_EVENT_SLEEP)
        await self.send_touch_event(TouchEventType.TOUCH_MOVE, to_x, to_y)
        await self.send_touch_event(TouchEventType.TOUCH_UP, to_x, to_y)

    async def send_touch_event(self, event_type: TouchEventType, x: float, y: float, pressure: float = 0.4) -> None:
        params = EVENT_TYPE_PARAMS[event_type]

        timestamp = await self._client.symbols.mach_absolute_time()

        event_flags = params["event_flags"]
        touch = params["touch"]
        button_mask = params["button_mask"]

        parent = await self.create_digitizer_event(
            IOHIDDigitizerTransducerType.kIOHIDDigitizerTransducerTypeHand,
            0,
            0,
            event_flags,
            0,
            x,
            y,
            0.0,
            0.0,
            0.0,
            touch,
            touch,
            0,
            timestamp=timestamp,
        )

        child = await self.create_digitizer_finger_event(
            2, 2, event_flags, button_mask, x, y, 0.0, pressure, 0.0, touch, touch, 0, timestamp=timestamp
        )
        await self._client.symbols.IOHIDEventAppendEvent(parent, child)
        await self.dispatch(parent)

    async def create_digitizer_event(
        self,
        type_: IOHIDDigitizerTransducerType | int,
        index: int,
        identity: int,
        event_mask: int,
        button_mask: int,
        x: float,
        y: float,
        z: float,
        tip_pressure: float,
        barrel_pressure: float,
        range_: bool,
        touch: bool,
        options: int,
        timestamp=None,
    ):
        if timestamp is None:
            timestamp = await self._client.symbols.mach_absolute_time()

        event = await self._client.symbols.IOHIDEventCreateDigitizerEvent(
            kCFAllocatorDefault,
            timestamp,
            type_,
            index,
            identity,
            event_mask,
            button_mask,
            x,
            y,
            z,
            tip_pressure,
            barrel_pressure,
            range_,
            touch,
            options,
        )

        if not event:
            raise BadReturnValueError("IOHIDEventCreateDigitizerEvent() failed")

        await self._client.symbols.IOHIDEventSetIntegerValue(event, IOHIDEventField.kIOHIDEventFieldIsBuiltIn, 0)
        await self._client.symbols.IOHIDEventSetIntegerValue(
            event, IOHIDEventFieldDigitizer.kIOHIDEventFieldDigitizerIsDisplayIntegrated, 1
        )
        await self._client.symbols.IOHIDEventSetSenderID(event, 0x8000000817319375)

        return event

    async def create_digitizer_finger_event(
        self,
        index: int,
        identity: int,
        event_mask: int,
        button_mask: int,
        x: float,
        y: float,
        z: float,
        tip_pressure: float,
        twist: float,
        range_: bool,
        touch: bool,
        options: int,
        timestamp=None,
    ) -> DarwinSymbolT_co:
        if timestamp is None:
            timestamp = await self._client.symbols.mach_absolute_time()

        event = await self._client.symbols.IOHIDEventCreateDigitizerFingerEvent(
            kCFAllocatorDefault,
            timestamp,
            index,
            identity,
            event_mask,
            button_mask,
            x,
            y,
            z,
            tip_pressure,
            twist,
            range_,
            touch,
            options,
        )

        if not event:
            raise BadReturnValueError("IOHIDEventCreateDigitizerFingerEvent() failed")

        await self._client.symbols.IOHIDEventSetFloatValue(
            event, IOHIDEventFieldDigitizer.kIOHIDEventFieldDigitizerMajorRadius, 0.5
        )
        return event

    @asynccontextmanager
    async def create_hid_client(self) -> AsyncGenerator[DarwinSymbolT_co]:
        client = await self._client.symbols.IOHIDEventSystemClientCreate(0)

        if not client:
            raise BadReturnValueError("IOHIDEventSystemClientCreate() failed")

        try:
            yield client
        finally:
            await self._client.symbols.CFRelease(client)

    async def dispatch(self, event):
        async with self.create_hid_client() as hid_client:
            await self._client.symbols.IOHIDEventSystemClientDispatchEvent(hid_client, event)
```

## Location

## rpcclient.clients.darwin.subsystems.location

### Location

Bases: `ClientBound['DarwinClient[DarwinSymbolT_co]']`, `Generic[DarwinSymbolT_co]`

Wrapper to CLLocationManager https://developer.apple.com/documentation/corelocation/cllocationmanager?language=objc

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/location.py`

```
class Location(ClientBound["DarwinClient[DarwinSymbolT_co]"], Generic[DarwinSymbolT_co]):
    """
    Wrapper to CLLocationManager
    https://developer.apple.com/documentation/corelocation/cllocationmanager?language=objc
    """

    def __init__(self, client: "DarwinClient[DarwinSymbolT_co]") -> None:
        self._client = client
        client.load_framework_lazy("CoreLocation")

    @cached_async_method
    async def _get_CLLocationManager(self) -> DarwinSymbolT_co:
        return await self._client.symbols.objc_getClass("CLLocationManager")

    @cached_async_method
    async def _get_location_manager(self) -> DarwinSymbolT_co:
        return await (await self._get_CLLocationManager()).objc_call("sharedManager")

    async def get_location_services_enabled(self) -> bool:
        """opt-in status for location services"""
        return bool(await (await self._get_location_manager()).objc_call("locationServicesEnabled"))

    async def set_location_services_enabled(self, value: bool) -> None:
        """opt-in status for location services"""
        await (await self._get_CLLocationManager()).objc_call("setLocationServicesEnabled:", value)

    async def authorization_status(self) -> CLAuthorizationStatus:
        """authorization status for current server process of accessing location services"""
        return CLAuthorizationStatus((await self._get_location_manager()).objc_call("authorizationStatus"))

    async def last_sample(self) -> dict | None:
        """last taken location sample (or None if there isn't any)"""
        location = await (await self._get_location_manager()).objc_call("location")
        if not location:
            return None
        return await (await location.objc_call("jsonObject")).py(dict)

    async def request_always_authorization(self) -> None:
        """Request authorization to always query location data"""
        await (await self._get_location_manager()).objc_call("requestAlwaysAuthorization")

    async def start_updating_location(self) -> None:
        """request location updates from CLLocationManager"""
        if (
            await type(self).authorization_status(self)
        ).value < CLAuthorizationStatus.kCLAuthorizationStatusAuthorizedAlways.value:
            raise RpcPermissionError()
        await (await self._get_location_manager()).objc_call("startUpdatingLocation")

    async def stop_updating_location(self) -> None:
        """stop requesting location updates from CLLocationManager"""
        await (await self._get_location_manager()).objc_call("stopUpdatingLocation")

    async def request_oneshot_location(self) -> None:
        """requests the one-time delivery of the user's current location"""
        if (
            await type(self).authorization_status(self)
        ).value < CLAuthorizationStatus.kCLAuthorizationStatusAuthorizedAlways.value:
            raise RpcPermissionError()
        await (await self._get_location_manager()).objc_call("requestLocation")
```

#### get_location_services_enabled

```
get_location_services_enabled() -> bool
```

opt-in status for location services

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/location.py`

```
async def get_location_services_enabled(self) -> bool:
    """opt-in status for location services"""
    return bool(await (await self._get_location_manager()).objc_call("locationServicesEnabled"))
```

#### set_location_services_enabled

```
set_location_services_enabled(value: bool) -> None
```

opt-in status for location services

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/location.py`

```
async def set_location_services_enabled(self, value: bool) -> None:
    """opt-in status for location services"""
    await (await self._get_CLLocationManager()).objc_call("setLocationServicesEnabled:", value)
```

#### authorization_status

```
authorization_status() -> CLAuthorizationStatus
```

authorization status for current server process of accessing location services

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/location.py`

```
async def authorization_status(self) -> CLAuthorizationStatus:
    """authorization status for current server process of accessing location services"""
    return CLAuthorizationStatus((await self._get_location_manager()).objc_call("authorizationStatus"))
```

#### last_sample

```
last_sample() -> dict | None
```

last taken location sample (or None if there isn't any)

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/location.py`

```
async def last_sample(self) -> dict | None:
    """last taken location sample (or None if there isn't any)"""
    location = await (await self._get_location_manager()).objc_call("location")
    if not location:
        return None
    return await (await location.objc_call("jsonObject")).py(dict)
```

#### request_always_authorization

```
request_always_authorization() -> None
```

Request authorization to always query location data

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/location.py`

```
async def request_always_authorization(self) -> None:
    """Request authorization to always query location data"""
    await (await self._get_location_manager()).objc_call("requestAlwaysAuthorization")
```

#### start_updating_location

```
start_updating_location() -> None
```

request location updates from CLLocationManager

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/location.py`

```
async def start_updating_location(self) -> None:
    """request location updates from CLLocationManager"""
    if (
        await type(self).authorization_status(self)
    ).value < CLAuthorizationStatus.kCLAuthorizationStatusAuthorizedAlways.value:
        raise RpcPermissionError()
    await (await self._get_location_manager()).objc_call("startUpdatingLocation")
```

#### stop_updating_location

```
stop_updating_location() -> None
```

stop requesting location updates from CLLocationManager

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/location.py`

```
async def stop_updating_location(self) -> None:
    """stop requesting location updates from CLLocationManager"""
    await (await self._get_location_manager()).objc_call("stopUpdatingLocation")
```

#### request_oneshot_location

```
request_oneshot_location() -> None
```

requests the one-time delivery of the user's current location

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/location.py`

```
async def request_oneshot_location(self) -> None:
    """requests the one-time delivery of the user's current location"""
    if (
        await type(self).authorization_status(self)
    ).value < CLAuthorizationStatus.kCLAuthorizationStatusAuthorizedAlways.value:
        raise RpcPermissionError()
    await (await self._get_location_manager()).objc_call("requestLocation")
```

## Media

## rpcclient.clients.darwin.subsystems.media

### AVAudioSessionCategory

Bases: `Enum`

https://developer.apple.com/documentation/avfaudio/AVAudioSessionCategory?language=objc

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/media.py`

```
class AVAudioSessionCategory(Enum):
    """https://developer.apple.com/documentation/avfaudio/AVAudioSessionCategory?language=objc"""

    PlayAndRecord = "AVAudioSessionCategoryPlayAndRecord"
    Ambient = "AVAudioSessionCategoryAmbient"
    MultiRoute = "AVAudioSessionCategoryMultiRoute"
    Playback = "AVAudioSessionCategoryPlayback"
    Record = "AVAudioSessionCategoryRecord"
    SoloAmbient = "AVAudioSessionCategorySoloAmbient"
    AudioProcessing = "AVAudioSessionCategoryAudioProcessing"
```

### AVAudioSessionMode

Bases: `Enum`

https://developer.apple.com/documentation/avfaudio/avaudiosessionmode?language=objc

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/media.py`

```
class AVAudioSessionMode(Enum):
    """https://developer.apple.com/documentation/avfaudio/avaudiosessionmode?language=objc"""

    Default = "AVAudioSessionModeDefault"
    GameChat = "AVAudioSessionModeGameChat"
    Measurement = "AVAudioSessionModeMeasurement"
    MoviePlayback = "AVAudioSessionModeMoviePlayback"
    SpokenAudio = "AVAudioSessionModeSpokenAudio"
    VideoChat = "AVAudioSessionModeVideoChat"
    VideoRecording = "AVAudioSessionModeVideoRecording"
    VoiceChat = "AVAudioSessionModeVoiceChat"
    VoicePrompt = "AVAudioSessionModeVoicePrompt"
```

### Recorder

Bases: `Allocated['DarwinClient[DarwinSymbolT_co]']`, `Generic[DarwinSymbolT_co]`

Wrapper for AVAudioRecorder https://developer.apple.com/documentation/avfaudio/avaudiorecorder?language=objc

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/media.py`

```
class Recorder(Allocated["DarwinClient[DarwinSymbolT_co]"], Generic[DarwinSymbolT_co]):
    """
    Wrapper for AVAudioRecorder
    https://developer.apple.com/documentation/avfaudio/avaudiorecorder?language=objc
    """

    def __init__(
        self, client: "DarwinClient[DarwinSymbolT_co]", session: "AudioSession", recorder: DarwinSymbolT_co
    ) -> None:
        super().__init__()
        self._client = client
        self._session = session
        self._recorder = recorder

    async def _deallocate(self) -> None:
        await self._recorder.objc_call("release")

    async def record(self) -> None:
        await self._session.set_category(AVAudioSessionCategory.PlayAndRecord)
        await self._session.set_active(True)
        await self._recorder.objc_call("record")
        if not await type(self).recording(self):
            raise RpcFailedToRecordError()

    async def pause(self) -> None:
        await self._recorder.objc_call("pause")
        await self._session.set_active(False)

    async def stop(self) -> None:
        await self._recorder.objc_call("stop")
        await self._session.set_active(False)

    async def delete_recording(self) -> None:
        if not await self._recorder.objc_call("deleteRecording"):
            raise BadReturnValueError("deleteRecording failed")

    async def recording(self) -> bool:
        return bool(await self._recorder.objc_call("isRecording"))
```

### Player

Bases: `Allocated['DarwinClient[DarwinSymbolT_co]']`, `Generic[DarwinSymbolT_co]`

Wrapper for AVAudioPlayer https://developer.apple.com/documentation/avfaudio/avaudioplayer?language=objc

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/media.py`

```
class Player(Allocated["DarwinClient[DarwinSymbolT_co]"], Generic[DarwinSymbolT_co]):
    """
    Wrapper for AVAudioPlayer
    https://developer.apple.com/documentation/avfaudio/avaudioplayer?language=objc
    """

    def __init__(
        self,
        client: "DarwinClient[DarwinSymbolT_co]",
        session: "AudioSession[DarwinSymbolT_co]",
        player: DarwinSymbolT_co,
    ) -> None:
        self._client = client
        self._session: AudioSession[DarwinSymbolT_co] = session
        self._player: DarwinSymbolT_co = player

    async def _deallocate(self) -> None:
        await self._player.objc_call("release")

    async def play(self) -> None:
        await self._session.set_category(AVAudioSessionCategory.PlayAndRecord)
        await self._session.set_active(True)
        await self._player.objc_call("play")
        if not await type(self).playing(self):
            raise RpcFailedToPlayError()

    async def pause(self) -> None:
        await self._player.objc_call("pause")

    async def stop(self) -> None:
        await self._player.objc_call("stop")
        await self._session.set_active(False)

    async def set_volume(self, value: float) -> None:
        await self._player.objc_call("setVolume:", struct.pack("<f", value))

    async def playing(self) -> bool:
        return bool(await self._player.objc_call("isPlaying"))

    async def get_loops(self) -> int:
        return await self._player.objc_call("numberOfLoops")

    async def set_loops(self, value: int) -> None:
        await self._player.objc_call("setNumberOfLoops:", value)
```

### AudioSession

Bases: `ClientBound['DarwinClient[DarwinSymbolT_co]']`, `Generic[DarwinSymbolT_co]`

wrapper for AVAudioSession https://developer.apple.com/documentation/avfaudio/avaudiosession?language=objc

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/media.py`

```
class AudioSession(ClientBound["DarwinClient[DarwinSymbolT_co]"], Generic[DarwinSymbolT_co]):
    """
    wrapper for AVAudioSession
    https://developer.apple.com/documentation/avfaudio/avaudiosession?language=objc
    """

    def __init__(self, client: "DarwinClient[DarwinSymbolT_co]", session: DarwinSymbolT_co) -> None:
        self._client = client
        self._session: DarwinSymbolT_co = session

    @classmethod
    async def create(cls, client: "DarwinClient[DarwinSymbolT_co]") -> Self:
        session = await (await client.symbols.objc_getClass("AVAudioSession")).objc_call("sharedInstance")
        return cls(client, session)

    async def set_active(self, is_active: bool) -> None:
        await self._session.objc_call("setActive:error:", is_active, 0)

    async def set_mode(self, mode: AVAudioSessionMode) -> None:
        await self._session.objc_call(
            "setMode:error:",
            await self._client.symbols[mode.value].getindex(0),
            0,
        )

    async def set_category(
        self,
        category: AVAudioSessionCategory,
        mode: AVAudioSessionMode = AVAudioSessionMode.Default,
        route_sharing_policy: AVAudioSessionRouteSharingPolicy = AVAudioSessionRouteSharingPolicy.Default,
        options: AVAudioSessionCategoryOptions = AVAudioSessionCategoryOptions.DefaultToSpeaker,
    ) -> None:
        await self._session.objc_call(
            "setCategory:mode:routeSharingPolicy:options:error:",
            await self._client.symbols[category.value].getindex(0),
            await self._client.symbols[mode.value].getindex(0),
            route_sharing_policy,
            options,
            0,
        )

    async def set_interruption_priority(self, priority: InterruptionPriority) -> None:
        await self._session.objc_call("setInterruptionPriority:error:", priority, 0)

    async def override_output_audio_port(self, port: int) -> None:
        await self._session.objc_call("overrideOutputAudioPort:error:", port, 0)

    async def other_audio_playing(self) -> bool:
        return bool(await self._session.objc_call("isOtherAudioPlaying"))

    async def record_permission(self) -> str:
        return struct.pack("<I", await self._session.objc_call("recordPermission"))[::-1].decode()

    async def available_categories(self) -> list[str]:
        return await (await self._session.objc_call("availableCategories")).py(list)

    async def available_modes(self) -> list[str]:
        return await (await self._session.objc_call("availableModes")).py(list)

    async def is_active(self) -> bool:
        return bool(await self._session.objc_call("isActive"))
```

### DarwinMedia

Bases: `ClientBound['DarwinClient[DarwinSymbolT_co]']`, `Generic[DarwinSymbolT_co]`

Media utils

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/media.py`

```
class DarwinMedia(ClientBound["DarwinClient[DarwinSymbolT_co]"], Generic[DarwinSymbolT_co]):
    """Media utils"""

    def __init__(self, client: "DarwinClient[DarwinSymbolT_co]") -> None:
        """
        :param rpcclient.darwin.client.DarwinClient client:
        """
        self._client = client
        client.load_framework_lazy("AVFoundation")

    @cached_async_method
    async def session(self) -> AudioSession[DarwinSymbolT_co]:
        return await AudioSession.create(self._client)

    async def get_recorder(self, filename: str | PurePath) -> Recorder[DarwinSymbolT_co]:
        url = await (await self._client.symbols.objc_getClass("NSURL")).objc_call(
            "fileURLWithPath:", await self._client.cf(str(filename))
        )
        settings = await self._client.cf({
            "AVEncoderQualityKey": 100,
            "AVEncoderBitRateKey": 16,
            "AVNumberOfChannelsKey": 1,
            "AVSampleRateKey": 8000.0,
        })
        AVAudioRecorder = await self._client.symbols.objc_getClass("AVAudioRecorder")
        recorder = await (await AVAudioRecorder.objc_call("alloc")).objc_call(
            "initWithURL:settings:error:", url, settings, 0
        )

        return Recorder(self._client, await type(self).session(self), recorder)

    async def get_player(self, filename: str | PurePath) -> Player[DarwinSymbolT_co]:
        NSURL = await self._client.symbols.objc_getClass("NSURL")
        url = await NSURL.objc_call("fileURLWithPath:", await self._client.cf(str(filename)))

        AVAudioPlayer = await self._client.symbols.objc_getClass("AVAudioPlayer")
        player = await (await AVAudioPlayer.objc_call("alloc")).objc_call("initWithContentsOfURL:error:", url, 0)

        return Player(self._client, await type(self).session(self), player)
```

## Preferences

## rpcclient.clients.darwin.subsystems.preferences

### Preferences

Bases: `ClientBound['DarwinClient[DarwinSymbolT_co]']`, `Generic[DarwinSymbolT_co]`

Preferences utils

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/preferences.py`

```
class Preferences(ClientBound["DarwinClient[DarwinSymbolT_co]"], Generic[DarwinSymbolT_co]):
    """Preferences utils"""

    def __init__(self, client: "DarwinClient[DarwinSymbolT_co]") -> None:
        """
        :param rpcclient.darwin.client.DarwinClient client:
        """
        self.cf: CFPreferences[DarwinSymbolT_co] = CFPreferences(client)
        self.sc: SCPreferences[DarwinSymbolT_co] = SCPreferences(client)
```

## IORegistry

## rpcclient.clients.darwin.subsystems.ioregistry

### IOService

Bases: `Allocated['DarwinClient[DarwinSymbolT_co]']`, `Generic[DarwinSymbolT_co]`

representation of a remote IOService

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/ioregistry.py`

```
class IOService(Allocated["DarwinClient[DarwinSymbolT_co]"], Generic[DarwinSymbolT_co]):
    """representation of a remote IOService"""

    def __init__(self, client: "DarwinClient[DarwinSymbolT_co]", service: DarwinSymbolT_co, name: str) -> None:
        super().__init__()
        self._client = client
        self._service: DarwinSymbolT_co = service
        self.name: str = name

    @classmethod
    async def create(cls, client: "DarwinClient[DarwinSymbolT_co]", service: int) -> Self:
        async with client.safe_malloc(io_name_t.sizeof()) as name:
            if await client.symbols.IORegistryEntryGetName(service, name):
                raise BadReturnValueError("IORegistryEntryGetName failed")
            name = await name.peek_str()

        return cls(client, client.symbol(service), name)

    async def properties(self) -> dict:
        async with self._client.safe_malloc(8) as p_properties:
            if await self._client.symbols.IORegistryEntryCreateCFProperties(
                self._service, p_properties, kCFAllocatorDefault, 0
            ):
                raise BadReturnValueError("IORegistryEntryCreateCFProperties failed")
            return await (await p_properties.getindex(0)).py(dict)

    async def _iter(self) -> "AsyncGenerator[IOService[DarwinSymbolT_co]]":
        async with self._client.safe_malloc(io_object_t.sizeof()) as p_child_iter:
            if await self._client.symbols.IORegistryEntryGetChildIterator(self._service, kIOServicePlane, p_child_iter):
                raise BadReturnValueError("IORegistryEntryGetChildIterator failed")
            child_iter = await p_child_iter.getindex(0)

        while child := await self._client.symbols.IOIteratorNext(child_iter):
            yield await IOService.create(self._client, child)

    def __aiter__(self) -> "AsyncGenerator[IOService[DarwinSymbolT_co]]":
        return self._iter()

    async def set(self, properties: dict) -> None:
        await self._client.symbols.IORegistryEntrySetCFProperties(self._service, await self._client.cf(properties))

    async def get(
        self, key: str, typ: type[CfSerializableT] | tuple[type[CfSerializableT], ...] = _CfSerializableAny
    ) -> CfSerializableT:
        return await (
            await self._client.symbols.IORegistryEntryCreateCFProperty(
                self._service, await self._client.cf(key), kCFAllocatorDefault, 0
            )
        ).py(typ)

    async def _deallocate(self) -> None:
        await self._client.symbols.IOObjectRelease(self._service)

    def __repr__(self):
        return f"<{self.__class__.__name__} NAME:{self.name}>"
```

### IORegistry

Bases: `ClientBound['DarwinClient[DarwinSymbolT_co]']`, `Generic[DarwinSymbolT_co]`

IORegistry utils https://developer.apple.com/library/archive/documentation/DeviceDrivers/Conceptual/IOKitFundamentals/TheRegistry/TheRegistry.html

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/ioregistry.py`

```
class IORegistry(ClientBound["DarwinClient[DarwinSymbolT_co]"], Generic[DarwinSymbolT_co]):
    """
    IORegistry utils
    https://developer.apple.com/library/archive/documentation/DeviceDrivers/Conceptual/IOKitFundamentals/TheRegistry/TheRegistry.html
    """

    def __init__(self, client: "DarwinClient[DarwinSymbolT_co]") -> None:
        """
        :param rpcclient.darwin.client.DarwinClient client:
        """
        self._client = client

    async def backlight_control(self) -> BacklightControlService[DarwinSymbolT_co]:
        service = await self._client.symbols.IOServiceGetMatchingService(
            0, await self._client.cf({"IOPropertyMatch": {"backlight-control": True}})
        )
        if not service:
            raise RpcClientException("IOServiceGetMatchingService failed")
        return await BacklightControlService.create(self._client, service)

    async def power_source(self) -> PowerSourceService[DarwinSymbolT_co]:
        service = await self._client.symbols.IOServiceGetMatchingService(
            0, await self._client.symbols.IOServiceMatching("IOPMPowerSource")
        )
        if not service:
            raise RpcClientException("IOServiceGetMatchingService failed")
        return await PowerSourceService.create(self._client, service)

    async def root(self) -> IOService[DarwinSymbolT_co]:
        async with self._client.safe_malloc(mach_port_t.sizeof()) as p_master_port:
            await self._client.symbols.IOMasterPort(MACH_PORT_NULL, p_master_port)
            return await IOService.create(
                self._client, await self._client.symbols.IORegistryGetRootEntry(await p_master_port.getindex(0))
            )
```

## Reports

## rpcclient.clients.darwin.subsystems.reports

### Reports

Bases: `ClientBound['DarwinClient[DarwinSymbolT_co]']`, `Generic[DarwinSymbolT_co]`

equivalent to the data that can be found using the Console app inside the Reports section

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/reports.py`

```
class Reports(ClientBound["DarwinClient[DarwinSymbolT_co]"], Generic[DarwinSymbolT_co]):
    """equivalent to the data that can be found using the Console app inside the Reports section"""

    def __init__(self, client: "DarwinClient[DarwinSymbolT_co]", crash_reports_dir: str) -> None:
        self._client = client
        self.crash_reports: CrashReports[DarwinSymbolT_co] = CrashReports(client, crash_reports_dir)

    async def get_logs(self, prefix: str = "") -> list[Path]:
        result = []
        sub_paths = ["var/log", "Library/Logs"]
        for sub_path in sub_paths:
            for path in await self._client.roots():
                path = Path(path) / sub_path
                if not await self._client.fs.accessible(path):
                    continue

                async for root, _dirs, files in self._client.fs.walk(path, onerror=lambda x: None):
                    for name in files:
                        if not await self._client.fs.accessible(path):
                            continue

                        if name.endswith(".log") and name.startswith(prefix):
                            result.append(Path(root) / name)
        return result

    async def system_log(self) -> str:
        async with await self._client.fs.open("/var/log/system.log", "r") as f:
            return (await f.read()).decode()
```

## Bluetooth

## rpcclient.clients.darwin.subsystems.bluetooth

### Bluetooth

Bases: `ClientBound['DarwinClient[DarwinSymbolT_co]']`, `Generic[DarwinSymbolT_co]`

bluetooth utils

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/bluetooth.py`

```
class Bluetooth(ClientBound["DarwinClient[DarwinSymbolT_co]"], Generic[DarwinSymbolT_co]):
    """bluetooth utils"""

    # bugfix: +[BluetoothManager.setSharedInstanceQueue:] cannot be called twice in the same process,
    # so we use this global to tell if it was already called
    _ENV_QUEUE_SET = "_rpc_server_bluetooth_manager_dispatch_queue_set"

    def __init__(self, client: "DarwinClient[DarwinSymbolT_co]") -> None:
        self._client = client
        client.load_framework_lazy("BluetoothManager")

    _bluetooth_manager: DarwinSymbolT_co | None = None

    async def _get_bluetooth_manager(self) -> DarwinSymbolT_co:
        if self._bluetooth_manager is None:
            bluetooth_manager_class = await self._client.symbols.objc_getClass("BluetoothManager")
            if not await self._client.getenv(self._ENV_QUEUE_SET):
                await bluetooth_manager_class.objc_call(
                    "setSharedInstanceQueue:", await self._client.symbols.dispatch_queue_create(0, 0)
                )
                await self._client.setenv(self._ENV_QUEUE_SET, "1")
            self._bluetooth_manager = await bluetooth_manager_class.objc_call("sharedInstance")

        return self._bluetooth_manager

    async def is_on(self) -> bool:
        return await (await self._get_bluetooth_manager()).objc_call("enabled") == 1

    async def turn_on(self) -> None:
        await self._set(is_on=1)

    async def turn_off(self) -> None:
        await self._set(is_on=0)

    async def address(self) -> str | None:
        addr = await (await (await self._get_bluetooth_manager()).objc_call("localAddress")).py()
        assert addr is None or isinstance(addr, str)

    async def connected(self) -> bool:
        return bool(await (await self._get_bluetooth_manager()).objc_call("connected"))

    async def get_discoverable(self) -> bool:
        return bool(await (await self._get_bluetooth_manager()).objc_call("isDiscoverable"))

    async def set_discoverable(self, value: bool) -> None:
        await (await self._get_bluetooth_manager()).objc_call("setDiscoverable:", value)

    async def _set(self, is_on) -> None:
        await (await self._get_bluetooth_manager()).objc_call("setPowered:", is_on)
        await (await self._get_bluetooth_manager()).objc_call("setEnabled:", is_on)

    def __repr__(self):
        return f"<{type(self).__name__} (async)>"
```

## XPC

## rpcclient.clients.darwin.subsystems.xpc

### XPCObject

Bases: `AbstractDarwinSymbol`, `Generic[DarwinSymbolT_co]`

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/xpc.py`

```
class XPCObject(AbstractDarwinSymbol, Generic[DarwinSymbolT_co]):
    @readonly
    def _client(self) -> "DarwinClient[DarwinSymbolT_co]": ...

    def __init__(self, value: int, client: "DarwinClient[DarwinSymbolT_co]") -> None:
        XPCObject._client.set(self, client)
        self._sym: DarwinSymbolT_co = client.symbol(value)

    def _symbol_from_value(self, value: int) -> DarwinSymbolT_co:
        return self._client.symbol(value)

    async def peek(self, count: int, offset: int = 0) -> bytes:
        return await self._sym.peek(count, offset)

    async def poke(self, buf: bytes, offset: int = 0) -> Any:
        return await self._sym.poke(buf, offset)

    async def peek_str(self, encoding="utf-8") -> str:
        """peek string at given address"""
        return await self._sym.peek_str(encoding=encoding)

    @property
    def arch(self) -> object:
        return self._client.arch

    @property
    def endianness(self) -> str:
        return self._client._endianness

    async def get_dl_info(self) -> Container:
        return await self._sym.get_dl_info()

    async def type(self) -> int:
        return await self._client.symbols.xpc_get_type(self)

    async def release(self) -> None:
        """
        See https://developer.apple.com/documentation/xpc/xpc_release(_:)?language=objc
        """
        await self._client.symbols.xpc_release(self)
```

#### peek_str

```
peek_str(encoding='utf-8') -> str
```

peek string at given address

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/xpc.py`

```
async def peek_str(self, encoding="utf-8") -> str:
    """peek string at given address"""
    return await self._sym.peek_str(encoding=encoding)
```

#### release

```
release() -> None
```

See https://developer.apple.com/documentation/xpc/xpc_release(\_:)?language=objc

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/xpc.py`

```
async def release(self) -> None:
    """
    See https://developer.apple.com/documentation/xpc/xpc_release(_:)?language=objc
    """
    await self._client.symbols.xpc_release(self)
```

### XPCArray

Bases: `XPCObject[DarwinSymbolT_co]`

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/xpc.py`

```
class XPCArray(XPCObject[DarwinSymbolT_co]):
    async def set_data(self, buf: bytes, index: int = XPC_ARRAY_APPEND) -> None:
        """
        See https://developer.apple.com/documentation/xpc/1505937-xpc_array_set_data?language=objc
        """
        await self._client.symbols.xpc_array_set_data(self, index, buf, len(buf))
```

#### set_data

```
set_data(buf: bytes, index: int = XPC_ARRAY_APPEND) -> None
```

See https://developer.apple.com/documentation/xpc/1505937-xpc_array_set_data?language=objc

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/xpc.py`

```
async def set_data(self, buf: bytes, index: int = XPC_ARRAY_APPEND) -> None:
    """
    See https://developer.apple.com/documentation/xpc/1505937-xpc_array_set_data?language=objc
    """
    await self._client.symbols.xpc_array_set_data(self, index, buf, len(buf))
```

### Xpc

Bases: `ClientBound['DarwinClient[DarwinSymbolT_co]']`, `Generic[DarwinSymbolT_co]`

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/xpc.py`

```
class Xpc(ClientBound["DarwinClient[DarwinSymbolT_co]"], Generic[DarwinSymbolT_co]):
    def __init__(self, client: "DarwinClient[DarwinSymbolT_co]") -> None:
        """
        :param rpcclient.darwin.client.DarwinClient client:
        """
        self._client = client
        self._client.load_framework_lazy("DuetActivityScheduler")
        self._service_cache: dict[str, DarwinSymbolT_co] = {}

    async def sharedScheduler(self) -> DarwinSymbolT_co:
        return await (await self._client.symbols.objc_getClass("_DASScheduler")).objc_call("sharedScheduler")

    async def create_xpc_dictionary(self) -> XPCDictionary:
        return XPCDictionary(await self._client.symbols.xpc_dictionary_create(0, 0, 0), self._client)

    async def create_xpc_array(self) -> XPCArray:
        return XPCArray(await self._client.symbols.xpc_array_create_empty(), self._client)

    async def send_xpc_dictionary(self, service_name: str, message: XPCDictionary) -> XPCDictionary:
        """
        Send a native XPC dictionary to a XPC service synchronously and return result.

        :param service_name: mach service name
        :param message: xpc message to send
        :return: received response
        """
        return XPCDictionary(await self.send_message_raw(service_name, message), self._client)

    async def send_message_using_cf_serialization(
        self, service_name: str, message: CfSerializable, decode_cf: bool = True
    ) -> CfSerializable:
        """
        Send a CFObject serialized over an XPC object to a XPC service synchronously and return reply.

        :param service_name: mach service name
        :param message: xpc message to send
        :param decode_cf: should response be decoded as CFObject-over-XPCObject or a native XPC object
        :return: received response
        """
        message_raw = await self.encode_xpc_message_using_cf_serialization(message)
        if message_raw == 0:
            raise RpcXpcSerializationError
        response = await self.send_message_raw(service_name, message_raw)
        if response == 0:
            raise RpcXpcSerializationError
        return (
            await self.decode_xpc_message_using_cf_serialization(response)
            if decode_cf
            else await self.decode_xpc_object_using_cf_serialization(response)
        )

    async def send_object_using_cf_serialization(self, service_name: str, message: CfSerializable) -> CfSerializable:
        """
        Send a native XPC object serialized over a CFObject to a XPC service synchronously and return reply.

        :param service_name: mach service name
        :param message: xpc message to send
        :return: received response
        """
        message_raw = await self.encode_xpc_object_using_cf_serialization(message)
        if message_raw == 0:
            raise RpcXpcSerializationError()
        response = await self.send_message_raw(service_name, message_raw)
        if response == 0:
            raise RpcXpcSerializationError()
        return await self.decode_xpc_object_using_cf_serialization(response)

    async def decode_xpc_object_using_cf_serialization(self, address: int) -> CfSerializable:
        """
        Convert XPC object to python object using CF serialization.
        """
        return await (await self._client.symbols._CFXPCCreateCFObjectFromXPCObject(address)).py()

    async def encode_xpc_object_using_cf_serialization(self, obj: CfSerializable) -> DarwinSymbolT_co:
        """
        Convert python object to XPC object using CF conversion.
        """
        return await self._client.symbols._CFXPCCreateXPCObjectFromCFObject(await self._client.cf(obj))

    async def decode_xpc_message_using_cf_serialization(self, address: int) -> CfSerializable:
        """
        Convert a CFObject serialized over an XPCObject to python object
        """
        return await (await self._client.symbols._CFXPCCreateCFObjectFromXPCMessage(address)).py()

    async def encode_xpc_message_using_cf_serialization(self, obj: CfSerializable) -> DarwinSymbolT_co:
        """
        Convert python object to a CFObject serialized over an XPCObject
        """
        return await self._client.symbols._CFXPCCreateXPCMessageWithCFObject(await self._client.cf(obj))

    async def send_message_raw(self, service_name: str, message_raw: int) -> DarwinSymbolT_co:
        """Send a RAW xpc object to given service_name and wait reply."""
        conn = await self._connect_to_mach_service(service_name)
        return await self._client.symbols.xpc_connection_send_message_with_reply_sync(conn, message_raw)

    async def force_run_activities(self, activities: list[str]) -> None:
        await (await type(self).sharedScheduler(self)).objc_call(
            "forceRunActivities:", await self._client.cf(activities)
        )

    async def loaded_activities(self) -> dict:
        return await self._client.preferences.cf.get_dict("com.apple.xpc.activity2", "root")

    async def set_activity_base_date(self, name: str, date: datetime) -> None:
        activity_base_dates = (await type(self).loaded_activities(self))["ActivityBaseDates"]
        activity_base_dates[name] = date
        await self._client.preferences.cf.set(
            "ActivityBaseDates", activity_base_dates, "com.apple.xpc.activity2", "root"
        )

    async def _connect_to_mach_service(self, service_name: str) -> DarwinSymbolT_co:
        if service_name not in self._service_cache:
            conn = await self._client.symbols.xpc_connection_create_mach_service(service_name, 0, 0)
            if conn == 0:
                raise BadReturnValueError("failed to create xpc connection")
            await self._client.symbols.xpc_connection_set_event_handler(conn, await self._client.get_dummy_block())
            await self._client.symbols.xpc_connection_resume(conn)
            self._service_cache[service_name] = conn

        return self._service_cache[service_name]
```

#### send_xpc_dictionary

```
send_xpc_dictionary(service_name: str, message: XPCDictionary) -> XPCDictionary
```

Send a native XPC dictionary to a XPC service synchronously and return result.

Parameters:

| Name           | Type            | Description         | Default    |
| -------------- | --------------- | ------------------- | ---------- |
| `service_name` | `str`           | mach service name   | *required* |
| `message`      | `XPCDictionary` | xpc message to send | *required* |

Returns:

| Type            | Description       |
| --------------- | ----------------- |
| `XPCDictionary` | received response |

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/xpc.py`

```
async def send_xpc_dictionary(self, service_name: str, message: XPCDictionary) -> XPCDictionary:
    """
    Send a native XPC dictionary to a XPC service synchronously and return result.

    :param service_name: mach service name
    :param message: xpc message to send
    :return: received response
    """
    return XPCDictionary(await self.send_message_raw(service_name, message), self._client)
```

#### send_message_using_cf_serialization

```
send_message_using_cf_serialization(service_name: str, message: CfSerializable, decode_cf: bool = True) -> CfSerializable
```

Send a CFObject serialized over an XPC object to a XPC service synchronously and return reply.

Parameters:

| Name           | Type             | Description                                                                  | Default    |
| -------------- | ---------------- | ---------------------------------------------------------------------------- | ---------- |
| `service_name` | `str`            | mach service name                                                            | *required* |
| `message`      | `CfSerializable` | xpc message to send                                                          | *required* |
| `decode_cf`    | `bool`           | should response be decoded as CFObject-over-XPCObject or a native XPC object | `True`     |

Returns:

| Type             | Description       |
| ---------------- | ----------------- |
| `CfSerializable` | received response |

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/xpc.py`

```
async def send_message_using_cf_serialization(
    self, service_name: str, message: CfSerializable, decode_cf: bool = True
) -> CfSerializable:
    """
    Send a CFObject serialized over an XPC object to a XPC service synchronously and return reply.

    :param service_name: mach service name
    :param message: xpc message to send
    :param decode_cf: should response be decoded as CFObject-over-XPCObject or a native XPC object
    :return: received response
    """
    message_raw = await self.encode_xpc_message_using_cf_serialization(message)
    if message_raw == 0:
        raise RpcXpcSerializationError
    response = await self.send_message_raw(service_name, message_raw)
    if response == 0:
        raise RpcXpcSerializationError
    return (
        await self.decode_xpc_message_using_cf_serialization(response)
        if decode_cf
        else await self.decode_xpc_object_using_cf_serialization(response)
    )
```

#### send_object_using_cf_serialization

```
send_object_using_cf_serialization(service_name: str, message: CfSerializable) -> CfSerializable
```

Send a native XPC object serialized over a CFObject to a XPC service synchronously and return reply.

Parameters:

| Name           | Type             | Description         | Default    |
| -------------- | ---------------- | ------------------- | ---------- |
| `service_name` | `str`            | mach service name   | *required* |
| `message`      | `CfSerializable` | xpc message to send | *required* |

Returns:

| Type             | Description       |
| ---------------- | ----------------- |
| `CfSerializable` | received response |

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/xpc.py`

```
async def send_object_using_cf_serialization(self, service_name: str, message: CfSerializable) -> CfSerializable:
    """
    Send a native XPC object serialized over a CFObject to a XPC service synchronously and return reply.

    :param service_name: mach service name
    :param message: xpc message to send
    :return: received response
    """
    message_raw = await self.encode_xpc_object_using_cf_serialization(message)
    if message_raw == 0:
        raise RpcXpcSerializationError()
    response = await self.send_message_raw(service_name, message_raw)
    if response == 0:
        raise RpcXpcSerializationError()
    return await self.decode_xpc_object_using_cf_serialization(response)
```

#### decode_xpc_object_using_cf_serialization

```
decode_xpc_object_using_cf_serialization(address: int) -> CfSerializable
```

Convert XPC object to python object using CF serialization.

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/xpc.py`

```
async def decode_xpc_object_using_cf_serialization(self, address: int) -> CfSerializable:
    """
    Convert XPC object to python object using CF serialization.
    """
    return await (await self._client.symbols._CFXPCCreateCFObjectFromXPCObject(address)).py()
```

#### encode_xpc_object_using_cf_serialization

```
encode_xpc_object_using_cf_serialization(obj: CfSerializable) -> DarwinSymbolT_co
```

Convert python object to XPC object using CF conversion.

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/xpc.py`

```
async def encode_xpc_object_using_cf_serialization(self, obj: CfSerializable) -> DarwinSymbolT_co:
    """
    Convert python object to XPC object using CF conversion.
    """
    return await self._client.symbols._CFXPCCreateXPCObjectFromCFObject(await self._client.cf(obj))
```

#### decode_xpc_message_using_cf_serialization

```
decode_xpc_message_using_cf_serialization(address: int) -> CfSerializable
```

Convert a CFObject serialized over an XPCObject to python object

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/xpc.py`

```
async def decode_xpc_message_using_cf_serialization(self, address: int) -> CfSerializable:
    """
    Convert a CFObject serialized over an XPCObject to python object
    """
    return await (await self._client.symbols._CFXPCCreateCFObjectFromXPCMessage(address)).py()
```

#### encode_xpc_message_using_cf_serialization

```
encode_xpc_message_using_cf_serialization(obj: CfSerializable) -> DarwinSymbolT_co
```

Convert python object to a CFObject serialized over an XPCObject

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/xpc.py`

```
async def encode_xpc_message_using_cf_serialization(self, obj: CfSerializable) -> DarwinSymbolT_co:
    """
    Convert python object to a CFObject serialized over an XPCObject
    """
    return await self._client.symbols._CFXPCCreateXPCMessageWithCFObject(await self._client.cf(obj))
```

#### send_message_raw

```
send_message_raw(service_name: str, message_raw: int) -> DarwinSymbolT_co
```

Send a RAW xpc object to given service_name and wait reply.

Source code in `src/rpcclient/rpcclient/clients/darwin/subsystems/xpc.py`

```
async def send_message_raw(self, service_name: str, message_raw: int) -> DarwinSymbolT_co:
    """Send a RAW xpc object to given service_name and wait reply."""
    conn = await self._connect_to_mach_service(service_name)
    return await self._client.symbols.xpc_connection_send_message_with_reply_sync(conn, message_raw)
```

## Objective-C

## rpcclient.clients.darwin.objective_c.objc

### Method

Bases: `Generic[DarwinSymbolT_co]`

Source code in `src/rpcclient/rpcclient/clients/darwin/objective_c/objc.py`

```
@dataclass
class Method(Generic[DarwinSymbolT_co]):
    name: str
    client: "DarwinClient[DarwinSymbolT_co]" = field(compare=False)
    address: int = field(compare=False)
    imp: int = field(compare=False)
    type_: str = field(compare=False)
    return_type: str = field(compare=False)
    is_class: bool = field(compare=False)
    args_types: list = field(compare=False)

    @staticmethod
    def from_data(data: dict, client: "DarwinClient[DarwinSymbolT]") -> "Method[DarwinSymbolT]":
        """
        Create Method object from raw data.
        :param data: Data as loaded from get_objectivec_symbol_data.m.
        :param rpcclient.darwin.client.DarwinClient client: Darwin client.
        """
        return Method(
            name=data["name"],
            client=client,
            address=client.symbol(data["address"]),
            imp=client.symbol(data["imp"]),
            type_=data["type"],
            return_type=decode_type(data["return_type"]),
            is_class=data["is_class"],
            args_types=list(map(decode_type, data["args_types"])),
        )

    async def set_implementation(self, new_imp: int) -> None:
        await self.client.symbols.method_setImplementation(self.address, new_imp)
        self.imp = self.client.symbol(new_imp)

    async def always_return(self, value: bool) -> None:
        """
        Patch the method to always return the given value.
        """
        # Exported from rpcserver binary
        ret_val = await self.client.symbols["get_true" if value else "get_false"].resolve()
        await self.set_implementation(ret_val)

    def __str__(self) -> str:
        if ":" in self.name:
            args_names = self.name.split(":")
            name = " ".join(["{}:({})".format(*arg) for arg in zip(args_names, self.args_types[2:], strict=False)])
        else:
            name = self.name
        prefix = "+" if self.is_class else "-"
        return f"{prefix} {name}; // 0x{self.address:x} (returns: {self.return_type})\n"
```

#### from_data

```
from_data(data: dict, client: DarwinClient[DarwinSymbolT]) -> Method[DarwinSymbolT]
```

Create Method object from raw data.

Parameters:

| Name     | Type           | Description                                       | Default    |
| -------- | -------------- | ------------------------------------------------- | ---------- |
| `data`   | `dict`         | Data as loaded from get_objectivec_symbol_data.m. | *required* |
| `client` | `DarwinClient` | Darwin client.                                    | *required* |

Source code in `src/rpcclient/rpcclient/clients/darwin/objective_c/objc.py`

```
@staticmethod
def from_data(data: dict, client: "DarwinClient[DarwinSymbolT]") -> "Method[DarwinSymbolT]":
    """
    Create Method object from raw data.
    :param data: Data as loaded from get_objectivec_symbol_data.m.
    :param rpcclient.darwin.client.DarwinClient client: Darwin client.
    """
    return Method(
        name=data["name"],
        client=client,
        address=client.symbol(data["address"]),
        imp=client.symbol(data["imp"]),
        type_=data["type"],
        return_type=decode_type(data["return_type"]),
        is_class=data["is_class"],
        args_types=list(map(decode_type, data["args_types"])),
    )
```

#### always_return

```
always_return(value: bool) -> None
```

Patch the method to always return the given value.

Source code in `src/rpcclient/rpcclient/clients/darwin/objective_c/objc.py`

```
async def always_return(self, value: bool) -> None:
    """
    Patch the method to always return the given value.
    """
    # Exported from rpcserver binary
    ret_val = await self.client.symbols["get_true" if value else "get_false"].resolve()
    await self.set_implementation(ret_val)
```
