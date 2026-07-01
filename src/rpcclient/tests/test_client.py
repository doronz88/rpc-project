from collections.abc import Iterable

import pytest

from rpcclient.clients.darwin.client import DarwinClient
from rpcclient.core.client import RemoteCallArg
from rpcclient.core.subsystems.decorator import SubsystemNotAvailable, subsystem
from rpcclient.core.symbol import Symbol
from rpcclient.core.symbols_jar import LazySymbol
from rpcclient.exceptions import ArgumentError
from tests._types import Client


def _get_subsystems(client) -> list[str]:
    names: set[str] = set()
    for cls in client.__class__.mro():
        for name, attr in vars(cls).items():
            if isinstance(attr, subsystem):
                names.add(name)
    return sorted(names)


async def test_uncached_symbol_is_lazy(client: Client) -> None:
    # An unresolved symbol name yields a LazySymbol placeholder (sync attribute access can't await).
    if "strlen" in client.symbols:
        del client.symbols["strlen"]
    assert isinstance(client.symbols.strlen, LazySymbol)


async def test_lazy_symbol_is_awaitable(client: Client) -> None:
    # `await`-ing an unresolved lazy handle resolves it to a real Symbol (what the REPL relies on).
    if "strlen" in client.symbols:
        del client.symbols["strlen"]
    lazy = client.symbols.strlen
    assert isinstance(lazy, LazySymbol)
    resolved = await lazy
    assert isinstance(resolved, Symbol)
    assert int(resolved) == int(await lazy.resolve())


async def test_peek(client: Client) -> None:
    async with client.safe_malloc(0x100) as peekable:
        await client.peek(peekable, 0x100)


async def test_poke(client: Client) -> None:
    async with client.safe_malloc(0x100) as peekable:
        await client.poke(peekable, b"a" * 0x100)


@pytest.mark.parametrize(
    "params", [([1, 2, 3, 4, 5, 6, 7, 8, 9, 10]), ([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15])]
)
async def test_16args(client: Client, params: list[int]) -> None:
    async with client.safe_malloc(0x100) as peekable:
        await client.symbols.test_16args(peekable, *params)
        for i in range(len(params)):
            assert await peekable.getindex(i) == params[i]


@pytest.mark.parametrize(
    ("va_list_index", "params", "expected"),
    [
        (2, ["%f", 15.5], "15.500000"),
        (2, ["%f %f", 15.5, 7.3], "15.500000 7.300000"),
        (2, ["%f %f %d", 15.5, 7.3, 42], "15.500000 7.300000 42"),
        (2, ["%f %f %d %d", 15.5, 7.3, 1, 2], "15.500000 7.300000 1 2"),
        (2, ["%f %f %d %d %s", 15.5, 7.3, 1, 2, "test"], "15.500000 7.300000 1 2 test"),
        (2, ["%f %f %d %d %s %s", 15.5, 7.3, 1, 2, "test", "test2"], "15.500000 7.300000 1 2 test test2"),
    ],
)
@pytest.mark.arm
async def test_va_list_call(client: Client, va_list_index: int, params: Iterable[RemoteCallArg], expected: str) -> None:
    async with client.safe_malloc(0x100) as peekable:
        await client.symbols.sprintf(peekable, *params, va_list_index=va_list_index)
        assert expected == await peekable.peek_str()


@pytest.mark.arm
async def test_floating_point_call(client: Client) -> None:
    assert await client.symbols.sqrt(16.0, return_float64=True) == 4.0


async def test_peek_invalid_address(client: Client) -> None:
    # Server config: -DSAFE_WRITE raises ArgumentError for invalid address; else, ConnectionError.
    with pytest.raises((ArgumentError, ConnectionError)):
        await client.peek(0, 0x10)


async def test_poke_invalid_address(client: Client) -> None:
    # Server config: -DSAFE_WRITE raises ArgumentError for invalid address; else, ConnectionError.
    with pytest.raises((ArgumentError, ConnectionError)):
        await client.poke(0, b"a")


@pytest.mark.darwin
async def test_get_dummy_block(client: DarwinClient) -> None:
    await (await client.cf([1, 2, 3])).objc_call("enumerateObjectsUsingBlock:", await client.get_dummy_block())


async def test_listdir(client: Client) -> None:
    entries = await client.listdir("/")
    assert entries[0].d_name == "."
    assert entries[1].d_name == ".."


async def test_calloc(client: Client) -> None:
    async with client.safe_calloc(0x100) as zeros:
        assert await client.peek(zeros, 0x100) == b"\x00" * 0x100


async def test_env_get_set(client: Client) -> None:
    await client.setenv("TEST", "test")
    assert await client.getenv("TEST") == "test"


async def test_environ(client: Client) -> None:
    assert len(await client.environ()) > 0
    for e in await client.environ():
        assert "=" in e


async def test_all_subsystems_initialize(client: Client) -> None:
    """Ensure each @subsystem property is initialized and not SubsystemNotAvailable."""
    subsystem_names = _get_subsystems(client)
    failures: dict[str, str] = {}

    for name in subsystem_names:
        value = getattr(client, name)
        if isinstance(value, SubsystemNotAvailable):
            failures[name] = repr(value)

    assert not failures, f"Subsystems failed to initialize: {failures}"
