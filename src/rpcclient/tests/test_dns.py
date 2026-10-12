from typing import cast

import pytest

from rpcclient.clients.darwin.client import DarwinClient
from rpcclient.clients.darwin.subsystems.dns import (
    Dns,
    DnsRecord,
    DnsStateDump,
    encode_rdata,
    is_local_domain,
    parse_dns_cache,
)
from rpcclient.exceptions import ArgumentError


def _row(active: str, ttl: int, ifname: str, kind: str, rrtype: str, dnssec: str, record: str) -> str:
    # mDNSResponder's "%3d %s%8d %-7s%s %-6s   %-40s%s" cache row format
    return f"{12:3d} {active}{ttl:8d} {ifname:<7s}{kind} {rrtype:<6s}   {dnssec:<40s}{record}"


CACHE_ROWS = [
    _row("*", 287, "-U-", " ", "Addr", "", "   4 www.apple.com. Addr 17.253.144.10"),
    _row(" ", 3599, "-U-", " ", "CNAME", "insecure", "  24 apple.com. CNAME www.apple.com.edgekey.net."),
    _row(" ", 120, "-U-", "-", "AAAA", "", "   0 nx.example.com. AAAA "),
    _row("*", 4500, "bridge100", "+", "PTR", "", "  14 _airplay._tcp.local. PTR Living\\032Room._airplay._tcp.local."),
    _row(" ", 10, "en0", "-", "Addr", "", "     <private record description>"),
]
STATE_DUMP = "\n".join([
    "---- BEGIN STATE LOG ---- mDNSResponder mDNSResponder-2600 (Oct 1 2026 00:00:00) 123",
    "------------ Cache -------------",
    "Slt Q     TTL if     U Type     DNSSEC                                   rdlen",
    *CACHE_ROWS,
    "Cache size 600 entities; 5 in use (4 group, 1 multicast, 4 unicast); 2 referenced by active questions",
    "--------- Auth Records ---------",
    "--- MDNS Statistics ---",
    "Name Conflicts 0",
    "--------------------------------",
    "Sleeps 0",
    "----    DNS Cache Analytics     -----",
    "----    Unicast Requests",
    "Cache Hit: 16",
    "----  END STATE LOG  ---- mDNSResponder",
])


@pytest.fixture
def offline_dns() -> Dns:
    """A Dns whose client must never be used, for checks that have to fail before reaching the target."""
    return Dns(cast(DarwinClient, None))


def test_parse_dns_cache() -> None:
    cache = parse_dns_cache(STATE_DUMP)
    assert (cache.entities, cache.in_use, cache.groups, cache.multicast, cache.unicast) == (600, 5, 4, 1, 4)
    assert cache.referenced_by_questions == 2

    a, cname, negative, ptr, private = cache.records
    assert (a.name, a.type, a.ttl, a.rdata, a.dnssec, a.kind) == (
        "www.apple.com.",
        "Addr",
        287,
        "17.253.144.10",
        "",
        "unique",
    )
    assert a.unicast and a.active_question and a.raw == CACHE_ROWS[0]
    assert (cname.dnssec, cname.rdata, cname.active_question) == ("insecure", "www.apple.com.edgekey.net.", False)
    assert negative.negative and negative.rdata == ""
    assert (ptr.interface, ptr.kind, ptr.ttl, ptr.unicast) == ("bridge100", "shared", 4500, False)
    assert (private.name, private.rdata, private.dnssec, private.interface) == (None, None, "", "en0")


def test_parse_dns_cache_without_summary() -> None:
    cache = parse_dns_cache("\n".join(STATE_DUMP.splitlines()[:5]))
    assert len(cache.records) == 2 and cache.entities is None
    assert str(cache).startswith("DNS cache: 2 records\n")
    assert parse_dns_cache("").records == []


def test_dns_cache_find() -> None:
    cache = parse_dns_cache(STATE_DUMP)
    assert cache.find("WWW.apple.com") == cache.find("www.apple.com.") == [cache.records[0]]
    assert cache.find("") == []  # records with a redacted name never match


def test_dns_cache_str() -> None:
    lines = str(parse_dns_cache(STATE_DUMP)).splitlines()
    assert lines[0] == (
        "DNS cache: 5 records (5/600 entities in use, 4 unicast, 1 multicast, 2 referenced by active questions)"
    )
    assert lines[2].split() == ["NAME", "TYPE", "TTL", "IF", "KIND", "DNSSEC", "DATA"]
    assert lines[3].split() == ["*", "www.apple.com.", "Addr", "287", "unicast", "unique", "17.253.144.10"]
    assert lines[6].endswith("Living Room._airplay._tcp.local.")  # "\032" escapes are decoded
    assert lines[5].endswith("<no such record>") and lines[7].split()[0] == "<private>"
    assert str(parse_dns_cache(STATE_DUMP).records[0]) == "www.apple.com. Addr 17.253.144.10 (ttl=287, unicast, unique)"


def test_state_dump_sections() -> None:
    dump = DnsStateDump(STATE_DUMP)
    assert list(dump.sections()) == ["Cache", "Auth Records", "MDNS Statistics", "DNS Cache Analytics"]
    # separator lines and "----    Subtitle" lines belong to their section, the log boundaries to none
    assert dump.section("mdns statistics") == "Name Conflicts 0\n--------------------------------\nSleeps 0"
    assert dump.section("DNS Cache Analytics") == "----    Unicast Requests\nCache Hit: 16"
    with pytest.raises(KeyError, match="no such section: Questions"):
        dump.section("Questions")


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("test.local", True),
        ("Test.Local.", True),
        ("83.12.254.169.in-addr.arpa.", True),
        ("1.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.8.e.f.ip6.arpa.", True),
        ("b.e.f.ip6.arpa", True),
        ("test.test.il", False),
        ("local.example.com", False),
        ("1.0.0.127.in-addr.arpa.", False),
        ("c.e.f.ip6.arpa", False),
        ("ab.e.f.ip6.arpa", False),
        ("", False),
    ],
)
def test_is_local_domain(name: str, expected: bool) -> None:
    assert is_local_domain(name) is expected


@pytest.mark.parametrize(
    ("rrtype", "rdata", "expected"),
    [
        (1, "1.2.3.4", bytes([1, 2, 3, 4])),
        (28, "::1", bytes(15) + b"\x01"),
        (5, "www.apple.com.", b"\x03www\x05apple\x03com\x00"),
        (12, "host.local", b"\x04host\x05local\x00"),
        (16, "a=1", b"\x03a=1"),
        (16, ["a=1", "bb"], b"\x03a=1\x02bb"),
        (99, b"raw", b"raw"),
    ],
)
def test_encode_rdata(rrtype: int, rdata: str | bytes | list[str], expected: bytes) -> None:
    assert encode_rdata(rrtype, rdata) == expected


@pytest.mark.parametrize(
    ("rrtype", "rdata", "error"),
    [
        (1, "1.2.3", ValueError),
        (1, ["1.2.3.4"], TypeError),
        (5, "a..b", ValueError),
        (5, "a" * 64 + ".com", ValueError),
        (5, ".".join(["a" * 63] * 4), ValueError),
        (16, "x" * 256, ValueError),
        (99, "text", ValueError),
    ],
)
def test_encode_rdata_rejects(rrtype: int, rdata: str | list[str], error: type[Exception]) -> None:
    with pytest.raises(error):
        encode_rdata(rrtype, rdata)


@pytest.mark.parametrize(("name", "rrtype"), [("test.test.il", "A"), ("test.test.il", "AAAA"), ("test.il", "CNAME")])
async def test_add_rejects_address_records_outside_local_domains(offline_dns: Dns, name: str, rrtype: str) -> None:
    with pytest.raises(ArgumentError, match="local domains"):
        await offline_dns.add(name, "192.168.1.1", rrtype)


async def test_add_rejects_unknown_record_type(offline_dns: Dns) -> None:
    with pytest.raises(ValueError, match="unknown record type"):
        await offline_dns.add("test.local", "x", "BOGUS")


async def test_remove_rejects_unregistered_record(offline_dns: Dns) -> None:
    # a removed record's DNSRecordRef is freed, passing it to dns_sd would be a use-after-free in rpcserver
    stale = DnsRecord("test.local", 1, bytes(4), 60, ref=0x1000)
    with pytest.raises(ArgumentError, match="isn't registered"):
        await offline_dns.remove(stale)


@pytest.mark.darwin
@pytest.mark.local_only
async def test_dns_cache(darwin_client: DarwinClient) -> None:
    await darwin_client.network.gethostbyname("apple.com")
    cache = await darwin_client.dns.cache()
    assert cache.entities is not None
    assert cache.find("apple.com")


@pytest.mark.darwin
@pytest.mark.local_only
async def test_dns_delete(darwin_client: DarwinClient) -> None:
    await darwin_client.network.gethostbyname("example.com")
    assert (await darwin_client.dns.cache()).find("example.com")
    await darwin_client.dns.delete("example.com")
    assert all(record.active_question for record in (await darwin_client.dns.cache()).find("example.com"))


@pytest.mark.darwin
@pytest.mark.local_only
async def test_dns_crud(darwin_client: DarwinClient) -> None:
    dns, name = darwin_client.dns, "rpcclient-test.local"

    async def resolve() -> list[str]:
        host = await darwin_client.network.gethostbyname(name)
        return [] if host is None else host.addresses

    try:
        record = await dns.add(name, "10.0.0.1")
        assert await resolve() == ["10.0.0.1"]
        assert await dns.update(name, "10.0.0.2") is record
        assert dns.records(name) == [record] and record.rdata == bytes([10, 0, 0, 2])
        assert await resolve() == ["10.0.0.2"]
        await dns.remove(record)
        assert not dns.records(name)
        assert await resolve() == []
        with pytest.raises(ArgumentError):
            await dns.remove(record)

        await dns.add(name, "10.0.0.3")
        await dns.remove_all()
        assert not dns.records() and await resolve() == []
    finally:
        await dns.remove_all()
