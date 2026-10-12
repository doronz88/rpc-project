# DNS cache

The `dns` subsystem (`p.dns`) works with mDNSResponder, the daemon behind all name resolution on macOS and
iOS. It reads its DNS cache, injects records into it and flushes records out of it.

`rpcserver` must run as **root**, and `delete()` also needs it signed with the
`com.apple.private.mDNSResponder.record-cache.flush` entitlement (included in `ents.plist`).

## Reading the cache

mDNSResponder only hands out its cache through a state dump, which recent OS versions disable for privacy. Enable it
once per device (this persists across reboots and restarts mDNSResponder):

```python
p.dns.enable_state_dump()
```

Then:

```python
cache = p.dns.cache()
cache                        # prints as a table
cache.find("apple.com")      # the records of one name
for record in cache.records:
    print(record.name, record.type, record.ttl, record.rdata)
```

```text
DNS cache: 57 records (77/146 entities in use, 9 unicast, 48 multicast, 4 referenced by active questions)

  NAME                         TYPE  TTL  IF      KIND     DNSSEC DATA
* _companion-link._tcp.local.  PTR   4270 en0     shared          user’s Mac mini._companion-link._tcp.local.
  time.apple.com.              CNAME 4367 unicast unique          time.g.aaplimg.com.
  dns.google.                  HTTPS 172  en0     negative        <no such record>
```

The full state dump (questions, resolvers, interfaces, statistics, ...) is available too:

```python
dump = p.dns.state_dump()
dump.sections().keys()
print(dump.section("DNS Services"))
```

`p.dns.disable_state_dump()` turns it off again.

## Injecting records

`add()` registers a record that mDNSResponder answers with before consulting its cache or the network:

```python
record = p.dns.add("printer.local", "192.168.1.50")          # A
p.dns.add("printer.local", "fe80::1", rrtype="AAAA", ttl=60)
p.dns.add("_http._tcp.example.com", ["path=/"], rrtype="TXT")
p.dns.update("printer.local", "192.168.1.51")                 # replace the A record
p.dns.records()                                                     # what this client injected
p.dns.remove(record)
p.dns.remove_all()
```

!!! warning "Address records are limited to local domains"
    mDNSResponder only accepts A, AAAA and CNAME records for names in the link-local domains: `local.`,
    `254.169.in-addr.arpa.` and `{8,9,a,b}.e.f.ip6.arpa.`. It refuses them for any other name, regardless of root or
    entitlements, so that a process can't redirect e.g. `www.bigbank.com`. `add()` raises `ArgumentError` for those.
    Other record types can be added for any name.

Injected records live as long as their connection to mDNSResponder: until they are removed, or until rpcserver or
mDNSResponder exits.

## Flushing

```python
p.dns.delete("example.com")   # injected and cached records of one name
p.dns.clear()                 # the whole cache, by restarting mDNSResponder
```

Records an active question references are re-resolved right away and may reappear, and Bonjour records are
relearned as soon as mDNSResponder restarts.
