import asyncio

import pytest

from rpcclient.clients.darwin.client import DarwinClient


pytestmark = pytest.mark.darwin


async def test_modules(client: DarwinClient) -> None:
    assert "/usr/lib/libSystem.B.dylib" in [module.name for module in await client.images()]


async def test_uname(client: DarwinClient) -> None:
    uname = await client.uname()
    assert uname.sysname == "Darwin"
    assert "machine" in uname


async def test_get_class_list(client: DarwinClient) -> None:
    assert len(await client.get_class_list()) > 0


async def test_load_framework(client: DarwinClient) -> None:
    assert await client.load_framework("Foundation") != 0


async def test_load_all_libraries(client: DarwinClient) -> None:
    original_count = len(await client.images())
    await client.load_all_libraries(
        rebind_symbols=False
    )  # Pytest not running under ipython, so we can't rebind symbols.'
    assert len(await client.images()) > original_count


async def test_autorelease_pool_object_retain_count(client: DarwinClient) -> None:
    obj = await client.cf("tst")
    orig_retain_count = (await obj.objc_call("retainCount")).c_int64
    async with await client.create_autorelease_pool_ctx():
        await obj.objc_call("retain")
        await obj.objc_call("autorelease")
        retain_count = (await obj.objc_call("retainCount")).c_int64
        assert retain_count == orig_retain_count + 1
    retain_count = (await obj.objc_call("retainCount")).c_int64
    assert retain_count == orig_retain_count


async def test_autorelease_pool_object_retrival(client: DarwinClient) -> None:
    async with await client.create_autorelease_pool_ctx():
        obj = await client.cf("tst")
        pool = await client.get_current_autorelease_pool()
        assert obj == pool[0]


async def test_autorelease_pool_object_retrival_from_ctx(client: DarwinClient) -> None:
    async with await client.create_autorelease_pool_ctx() as pool:
        obj = await client.cf("tst")
        pool = await pool.get_autorelease_pool()
        assert pool is not None
        assert obj == pool[0]


async def test_autorelease_pool_object_retrival_refresh(client: DarwinClient) -> None:
    async with await client.create_autorelease_pool_ctx() as pool:
        obj = await client.cf("tst")
        pool = await pool.get_autorelease_pool()
        assert pool is not None
        assert obj in pool
        obj2 = await client.cf("tst2")
        assert obj2 not in pool
        await pool.refresh()
        assert obj2 in pool


async def test_requests_are_served_off_the_main_thread(client: DarwinClient) -> None:
    """The main thread is left to pump its run loop, requests are served on a dedicated thread."""
    assert not await client.symbols.pthread_main_np()


async def test_main_run_loop_is_pumped(client: DarwinClient) -> None:
    """
    The main run loop must actually be running, otherwise nothing driven by it - main queue blocks,
    timers, sources, framework callbacks - ever makes progress while a client is connected.
    """
    main_run_loop = await client.symbols.CFRunLoopGetMain()
    for _ in range(50):
        if await client.symbols.CFRunLoopIsWaiting(main_run_loop):
            return
        await asyncio.sleep(0.1)
    pytest.fail("the main run loop is not being pumped")
