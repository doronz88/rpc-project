import pytest

from rpcclient.clients.darwin.client import DarwinClient


pytestmark = pytest.mark.darwin

SCRATCH_DOMAIN = "com.rpcclient.process_preferences_test"


async def test_bundle_id(client: DarwinClient) -> None:
    """Process.bundle_id() (csops CS_OPS_IDENTITY) returns the process's code-signing identity."""
    process = await client.processes.get_by_pid(await client.get_pid())
    bundle_id = await process.bundle_id()
    assert isinstance(bundle_id, str) and bundle_id


async def test_environ_is_mapping(client: DarwinClient) -> None:
    process = await client.processes.get_by_pid(await client.get_pid())
    assert isinstance(await process.environ(), dict)


async def test_preferences_own_domain(client: DarwinClient) -> None:
    """preferences() with no argument resolves to the process's own bundle-id domain."""
    process = await client.processes.get_by_pid(await client.get_pid())
    prefs = process.preferences()
    assert await prefs.application_id() == await process.bundle_id()


async def test_preferences_path_matches_container(client: DarwinClient) -> None:
    """path() is <container>/Library/Preferences/<domain>.plist for the target."""
    process = await client.processes.get_by_pid(await client.get_pid())
    prefs = process.preferences(SCRATCH_DOMAIN)
    assert await prefs.path() == f"{await prefs.container()}/Library/Preferences/{SCRATCH_DOMAIN}.plist"


async def test_preferences_roundtrip(client: DarwinClient) -> None:
    """set / get / set_dict / remove / clear on a scratch domain, resolved as the process; path() exists."""
    process = await client.processes.get_by_pid(await client.get_pid())
    prefs = process.preferences(SCRATCH_DOMAIN)
    try:
        await prefs.set("key", 42)
        assert await prefs.get("key") == 42

        await prefs.set_dict({"a": 1, "b": [1, 2, 3]})
        assert await prefs.get_dict() == {"a": 1, "b": [1, 2, 3]}

        # the value physically lands at the fully-resolved path()
        assert await client.fs.read_file(await prefs.path())

        await prefs.remove("a")
        assert await prefs.get_dict() == {"b": [1, 2, 3]}
    finally:
        await prefs.clear()
    assert await prefs.get_dict() == {}
