# Using rpcclient from your own scripts

The `rpcclient` API is asynchronous: every call that talks to the server is a coroutine. The
interactive console hides this (see [How the console differs](#how-the-console-differs)), which is
why most examples in these guides have no `await`. In a normal Python program you run an event loop
yourself and `await` each call.

## Connect to a server

Create clients through a `ClientManager`. It picks the right client class for the target (macOS,
iOS, Linux) and keeps track of every client it created. The default transport is TCP:

```python
from rpcclient.client_manager import ClientManager

manager = ClientManager()
client = await manager.create(hostname="127.0.0.1", port=5910)
```

`port` defaults to `5910`, and an optional `timeout` (in seconds) limits how long the connection
attempt may take. A refused connection raises `rpcclient.exceptions.FailedToConnectError`.

To control the local machine without starting a server yourself, use the `local` transport. This is
what `rpclocal` does:

```python
client = await manager.create(mode="local")
```

It downloads the latest `rpcserver_macosx` release from GitHub into the current working directory,
starts it on a free port and connects to it. Closing the client also stops that server process.

## A minimal script

```python
import asyncio

from rpcclient.client_manager import ClientManager


async def main() -> None:
    client = await ClientManager().create(hostname="127.0.0.1")
    async with client:
        print(client)
        print("pid:", await client.get_pid())
        print("sysname:", (await client.get_uname()).sysname)
        print(await client.fs.listdir("/"))


asyncio.run(main())
```

Every method that reaches the server needs `await`, including subscript reads on symbols
(`await s.getindex(0)` rather than `s[0]`) and context managers such as `async with
client.safe_malloc(8) as buf:`.

## Closing the client

`await client.close()` tells the server to end the session and closes the socket. Clients are
async context managers, so `async with client:` closes it for you, even when an exception is
raised. This is the pattern the test suite uses:

```python
async with await ClientManager().create(hostname="127.0.0.1") as client:
    ...
```

If you created several clients through one manager, `await manager.close_all()` closes all of them
and empties `manager.clients`. Put it in a `finally` block:

```python
manager = ClientManager()
try:
    client = await manager.create(hostname="127.0.0.1")
    ...
finally:
    await manager.close_all()
```

## Concurrent calls

A client can be shared between tasks. You can pass several of its calls to `asyncio.gather`:

```python
pid, cwd, home = await asyncio.gather(
    client.symbols.getpid(),
    client.fs.pwd(),
    client.getenv("HOME"),
)
```

Requests on one client go over one socket, one at a time, so this is safe but does not make the
server do the work in parallel. For real parallelism, open more clients. Each connection is served
by its own server process:

```python
a, b = await asyncio.gather(
    manager.create(hostname="127.0.0.1"),
    manager.create(hostname="127.0.0.1"),
)
listing_a, listing_b = await asyncio.gather(a.fs.listdir("/"), b.fs.listdir("/"))
```

## How the console differs

`rpcclient` and `rpclocal` start IPython with `autoawait` turned on, so top-level `await` works.
They also load the `smart_await` extension, which rewrites each cell before it runs:

- a call that returns an awaitable is awaited: `p.get_pid()` gives an `int`
- a subscript read that returns an awaitable is awaited: `s[0]`
- a subscript assignment `s[0] = 7` becomes `await s.setindex(0, 7)` when `s` has an async
  `setindex`

To get the coroutine itself instead of its result, wrap the call in `...( )`, for example
`task = ...(p.fs.listdir("/"))`.

`smart_await` leaves a cell untouched if the cell already uses `await` or another `async`
construct. In a cell with `async with` or `async for`, which the console cannot add for you, write
`await` on every call in that cell yourself.

## Startup files

`rpcclient -f FILE` (and `rpclocal -f FILE`) runs files in the console before the prompt appears,
with `p`, `mgr` and `console` already defined. This is useful for setup that you then continue by
hand. How the file runs depends on its extension:

- A `.ipy` file runs like typed console input, so console-style code without `await` works.
- A `.py` file runs as plain Python. Calls return coroutines, and top-level `await` is a syntax
  error. Run coroutines on the console's event loop with `run_in_loop`:

```python
from rpcclient.utils import run_in_loop

pid = run_in_loop(p.get_pid())
```

!!! note
    Use `run_in_loop` only in startup files and other synchronous code that shares the console's
    loop. In a standalone script, use `asyncio.run` and `await`.

See also: [Quick start](quickstart.md), [Core API](../api/core.md).
