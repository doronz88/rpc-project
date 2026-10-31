# Networking

The `network` subsystem (`p.network`) does networking from the target's side: it lists the target's interfaces,
resolves host names with the target's resolver and opens TCP and Unix-domain connections from the target process.
On Darwin clients it also reads and sets the system proxy and can remove certificate pinning. On iOS, `p.wifi`
controls the Wi-Fi radio. The mDNSResponder cache has its own guide: [DNS cache](dns.md).

!!! note
    The examples are written for the interactive console, where calls are awaited for you. In a script, `await`
    each call (see [Scripting with rpcclient](scripting.md)). `async with` is needed in both.

## Listing interfaces

`interfaces()` returns the IPv4 interfaces of the target as `Interface(name, address, netmask, broadcast)` named
tuples. Interfaces without an IPv4 address are left out, and `broadcast` is `None` when there isn't one:

```python
for iface in p.network.interfaces():
    print(iface.name, iface.address, iface.netmask, iface.broadcast)
```

## Resolving host names

`gethostbyname()` resolves a name on the target and returns `Hostentry(name, aliases, addresses)`, or `None` if
the name doesn't resolve. `addresses` holds IPv4 addresses as strings:

```python
entry = p.network.gethostbyname("apple.com")
entry.addresses
p.network.gethostbyname("no-such-host.invalid")   # None
```

## Connecting from the target

`tcp_connect(address, port)` makes the target connect to `address:port` and returns a `Socket`. The address must be
an IPv4 or IPv6 literal (anything containing `:` is treated as IPv6), so resolve names first. `unix_connect(path)`
does the same for a Unix-domain socket on the target. A `Socket` is an async context manager that closes the remote
file descriptor on exit:

```python
async with await p.network.tcp_connect("127.0.0.1", 8080) as sock:
    await sock.sendall(b"GET / HTTP/1.0\r\n\r\n")
    print(await sock.recv(1024))

async with await p.network.unix_connect("/var/run/mDNSResponder") as sock:
    ...
```

Inside an `async with` block the console doesn't await for you, hence the explicit `await`s. Outside one, assign
the socket and close it yourself:

```python
sock = p.network.tcp_connect("127.0.0.1", 8080)
sock.sendall(b"ping")
sock.recvall(4)        # block until exactly 4 bytes arrive
sock.deallocate()      # close the fd
```

A refused connection raises `RpcConnectionRefusedError`, and a missing Unix socket path raises
`RpcFileNotFoundError`.

The `Socket` methods are:

- `send(buf, size=None, flags=0)` sends once and returns the number of bytes sent; `sendall(buf)` keeps sending
  until the whole buffer is written. `MSG_NOSIGNAL` is always added to the flags.
- `recv(size=1024, flags=0)` returns up to `size` bytes; `recvall(size)` waits for exactly `size` bytes. Both raise
  if the peer closes the connection.
- `settimeout(seconds)` sets `SO_RCVTIMEO`/`SO_SNDTIMEO`; a timed-out `recv()` raises
  `RpcResourceTemporarilyUnavailableError`. `gettimeout()` returns the value last set.
- `setblocking(flag)`, `getblocking()`, `setbufsize(size)` and `setsockopt(level, option_name, option_value)` wrap
  `fcntl()` and `setsockopt()`.
- `fd` is the remote file descriptor.

There are no helpers for UDP or for listening. `p.network.socket(family, socktype, proto)` creates a socket and
returns its raw file descriptor, which you can drive with `bind()`, `listen()`, `sendto()` and so on through
`p.symbols` (see [Calling native functions](calling-native-functions.md)).

## Proxies and certificate pinning (Darwin)

```python
p.network.proxy_settings()                    # CFNetworkCopySystemProxySettings() as a dict
p.network.set_http_proxy("192.168.1.10", 8080)
p.network.remove_http_proxy()
```

`set_http_proxy()` writes an HTTP and HTTPS proxy into the managed SystemConfiguration preferences and
`remove_http_proxy()` removes it. Both then kill `configd` so the change takes effect.

`remove_certificate_pinning()` empties trustd's pinning rules database
(`/private/var/protected/trustd/pinningrules.sqlite3`) and restarts trustd. `restore_certificate_pinning()` deletes
the database so trustd reloads the rules from its last MobileAsset on restart. `kill_trustd()` restarts trustd on its
own, and `flush_dns()` restarts mDNSResponder.

These change system state and generally need `rpcserver` to run as root.

## Wi-Fi (iOS)

`p.wifi` turns Wi-Fi on and off, lists saved networks, and scans for and joins networks:

```python
p.wifi.is_on()
p.wifi.turn_off()
p.wifi.turn_on()
p.wifi.interfaces()                 # e.g. ['en0']

for network in p.wifi.saved_networks():
    print(network.ssid(), network.bssid())
# network.forget() removes a saved network
```

Scanning and joining go through an interface handle from `get_interface()`, which uses the first Wi-Fi interface
unless you pass a name. The handle is closed when the `async with` block exits:

```python
async with await p.wifi.get_interface() as iface:
    networks = await iface.scan()
    for n in networks:
        print(n.ssid, n.bssid, n.rssi, n.channel)
    await networks[0].connect("password")   # omit the password for open networks
    await iface.disconnect()
```

Scanned networks expose `ssid` (bytes), `bssid`, `rssi` and `channel` as plain properties, and the raw scan
dictionary as `network`. On saved networks, `ssid()` and `bssid()` are methods, and `get_property(name)` reads any
other WiFiNetwork property.

See also: API reference for [Darwin](../api/darwin.md) and [iOS](../api/ios.md), and the [DNS cache](dns.md)
guide.
