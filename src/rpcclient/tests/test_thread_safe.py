import asyncio

from tests._types import Client


async def test_same_socket_different_tasks(client: Client) -> None:
    # get an expected result once before fanning out
    expected_result = await client.fs.listdir("/")

    # flag to tell the concurrent tasks when to exit
    should_exit = False

    async def listdir_task(client: Client) -> int:
        while not should_exit:
            assert await client.fs.listdir("/") == expected_result
        return 0

    # launch two concurrent tasks sharing the same client/socket
    tasks = [
        asyncio.create_task(listdir_task(client)),
        asyncio.create_task(listdir_task(client)),
    ]

    # let them hammer the shared socket for 10 seconds
    await asyncio.sleep(10)

    # tell tasks to exit
    should_exit = True

    await asyncio.gather(*tasks)
