import asyncio
import time
from threading import Thread

import pytest

from tests._types import AsyncClient, SyncClient


def test_same_socket_different_threads(client: SyncClient) -> None:
    # get an expected result once on main thread
    expected_result = client.fs.listdir("/")

    # global to tell threads when to exit
    should_exit = False

    def listdir_thread(client):
        while not should_exit:
            assert client.fs.listdir("/") == expected_result
        return 0

    # launch the two threads
    t1 = Thread(target=listdir_thread, args=(client,))
    t2 = Thread(target=listdir_thread, args=(client,))

    t1.start()
    t2.start()

    # wait 10 seconds
    time.sleep(10)

    # tell threads they
    should_exit = True

    t1.join()
    t2.join()


@pytest.mark.asyncio
async def test_same_socket_different_tasks(async_client: AsyncClient) -> None:
    # get an expected result once on main thread
    expected_result = await async_client.fs.listdir("/")

    # global to tell threads when to exit
    should_exit = False

    async def listdir_thread(client: AsyncClient) -> int:
        while not should_exit:
            assert await client.fs.listdir("/") == expected_result
        return 0

    # launch the two threads
    tasks = [
        asyncio.create_task(listdir_thread(async_client)),
        asyncio.create_task(listdir_thread(async_client)),
    ]

    # wait 10 seconds
    await asyncio.sleep(10)

    # tell threads they
    should_exit = True

    asyncio.gather(*tasks)
