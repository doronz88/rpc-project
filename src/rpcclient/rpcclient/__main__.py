import asyncio
import logging

import click
import coloredlogs

from rpcclient.client_manager import ClientManager
from rpcclient.clients.darwin.client import DarwinClient
from rpcclient.console.console import Console, disable_loggers
from rpcclient.core.client import ClientEvent, CoreClient
from rpcclient.core.webdav_mount import (
    mount_webdav_volume,
    reveal_in_file_manager,
    unmount_webdav_volume,
    webdav_mount_supported,
)
from rpcclient.transports import DEFAULT_PORT
from rpcclient.utils import run_in_loop


coloredlogs.install(level=logging.DEBUG)

disable_loggers()

startup_files_option = click.option(
    "-f",
    "--startup-files",
    type=click.Path(exists=True),
    multiple=True,
    help="File(s) (python) to run on session start. Multiple files can be provided.",
)


@click.command()
@startup_files_option
def rpclocal(startup_files: tuple[str]) -> None:
    """connect to a local machine"""
    manager = ClientManager()

    async def _connect() -> int:
        client = await manager.create(mode="local")
        return client.id

    cid = run_in_loop(_connect())

    Console(manager).interactive(switch_cid=cid, startup_files=startup_files)


async def _connect_client(
    manager: ClientManager, hostname: str, port: int, rebind_symbols: bool, load_all_libraries: bool
):
    client = await manager.create(hostname=hostname, port=port)
    if isinstance(client, DarwinClient):
        if rebind_symbols:
            await client.rebind_symbols()
        if load_all_libraries:
            await client.load_all_libraries()
    return client


@click.group(invoke_without_command=True)
@click.argument("hostname", required=False)
@click.option("-p", "--port", type=click.INT, default=DEFAULT_PORT, help="TCP port to connect to")
@click.option("-r", "--rebind-symbols", is_flag=True, help="reload all symbols upon connection")
@click.option("-l", "--load-all-libraries", is_flag=True, help="load all libraries")
@startup_files_option
@click.pass_context
def rpcclient(
    ctx: click.Context,
    hostname: str | None,
    port: int,
    rebind_symbols: bool,
    load_all_libraries: bool,
    startup_files: tuple[str],
):
    """
    Start the console.
    If HOSTNAME is provided, connect immediately.
    Otherwise, start without a connection.
    You can connect later from the console.
    Provide a subcommand (e.g. `webdav`) to run it against HOSTNAME instead of the console.
    """
    manager = ClientManager()
    ctx.obj = {
        "manager": manager,
        "hostname": hostname,
        "port": port,
        "rebind_symbols": rebind_symbols,
        "load_all_libraries": load_all_libraries,
    }

    if ctx.invoked_subcommand is not None:
        return

    cid = None
    if hostname:
        client = run_in_loop(_connect_client(manager, hostname, port, rebind_symbols, load_all_libraries))
        cid = client.id

    Console(manager).interactive(switch_cid=cid, startup_files=startup_files)


_DISCONNECT_HEARTBEAT_INTERVAL = 5.0


async def _wait_for_disconnect(client: CoreClient) -> None:
    """Block until the RPC connection to the target drops.

    The WebDAV server bridges every request to ``client``; if the target goes away (device
    reboot, cable pull, server killed) the mount would otherwise keep serving errors until the
    user hits Ctrl-C. ``ClientEvent.TERMINATED`` fires the moment an in-flight call fails, and a
    periodic liveness probe catches a disconnect that happens while the mount is idle.
    """
    loop = asyncio.get_running_loop()
    terminated = asyncio.Event()
    client.notifier.register_once(ClientEvent.TERMINATED, lambda *_: loop.call_soon_threadsafe(terminated.set))
    while not terminated.is_set():
        try:
            await asyncio.wait_for(terminated.wait(), timeout=_DISCONNECT_HEARTBEAT_INTERVAL)
        except asyncio.TimeoutError:
            try:
                await client.symbols.getpid()
            except Exception:
                return


def _require_mount_tool(mount: bool) -> None:
    """Fail early if ``--mount`` was requested but no WebDAV mount tool is available on this host."""
    if mount and not webdav_mount_supported():
        raise click.UsageError(
            "--mount is unavailable: no supported WebDAV mount tool found "
            "(mount_webdav on macOS, net on Windows, gio on Linux)"
        )


def _serve_webdav(
    manager: ClientManager,
    hostname: str,
    port: int,
    rebind_symbols: bool,
    load_all_libraries: bool,
    path: str,
    mount: bool,
    bind_host: str,
    bind_port: int,
    readonly: bool,
) -> None:
    """Connect to HOSTNAME, serve PATH over WebDAV, optionally mount, and block until interrupted."""
    _require_mount_tool(mount)

    async def _setup():
        client = await _connect_client(manager, hostname, port, rebind_symbols, load_all_libraries)
        server = await client.webdav.serve(path, host=bind_host, port=bind_port, readonly=readonly)
        mounted = await mount_webdav_volume(server.url, label=f"rpc-{hostname}-{path}") if mount else None
        return client, server, mounted

    client, server, mounted = run_in_loop(_setup())
    click.echo(f"WebDAV server serving {path!r} at {server.url}")
    if mounted is not None:
        run_in_loop(reveal_in_file_manager(mounted.reveal_target))
        click.echo(f"Mounted; revealed {mounted.reveal_target}")
    else:
        if mount:
            click.echo("Automatic mount is unavailable on this host; open the URL below in your file manager.")
        click.echo(f"Open this WebDAV URL in your file manager: {server.url}")
    click.echo("Press Ctrl-C to stop.")

    try:
        run_in_loop(_wait_for_disconnect(client))
        click.echo(f"Connection to {hostname} lost; stopping.")
    except KeyboardInterrupt:
        pass
    finally:

        async def _teardown() -> None:
            if mounted is not None:
                await unmount_webdav_volume(mounted)
            await server.stop()
            await client.close()

        run_in_loop(_teardown())
        click.echo("stopped.")


@rpcclient.command()
@click.argument("path", required=False, default="/")
@click.option("--mount", is_flag=True, help="mount the served path locally and reveal it in your file manager")
@click.option("--host", "bind_host", default="127.0.0.1", help="local interface to bind")
@click.option("--port", "bind_port", type=click.INT, default=0, help="local TCP port (0 picks a free port)")
@click.option("--readonly", is_flag=True, help="expose the path read-only")
@click.pass_context
def webdav(ctx: click.Context, path: str, mount: bool, bind_host: str, bind_port: int, readonly: bool) -> None:
    """Serve a remote PATH (default: /) over WebDAV for local mounting."""
    obj = ctx.obj
    if not obj["hostname"]:
        raise click.UsageError("HOSTNAME is required: rpcclient HOSTNAME webdav [--mount]")
    _serve_webdav(
        obj["manager"],
        obj["hostname"],
        obj["port"],
        obj["rebind_symbols"],
        obj["load_all_libraries"],
        path,
        mount,
        bind_host,
        bind_port,
        readonly,
    )


@click.command()
@click.argument("hostname")
@click.argument("path", required=False, default="/")
@click.option("-p", "--port", type=click.INT, default=DEFAULT_PORT, help="TCP port to connect to")
@click.option("-r", "--rebind-symbols", is_flag=True, help="reload all symbols upon connection")
@click.option("-l", "--load-all-libraries", is_flag=True, help="load all libraries")
@click.option("--mount", is_flag=True, help="mount the served path locally and reveal it in your file manager")
@click.option("--host", "bind_host", default="127.0.0.1", help="local interface to bind")
@click.option("--bind-port", "bind_port", type=click.INT, default=0, help="local TCP port (0 picks a free port)")
@click.option("--readonly", is_flag=True, help="expose the path read-only")
def rpcdav(
    hostname: str,
    path: str,
    port: int,
    rebind_symbols: bool,
    load_all_libraries: bool,
    mount: bool,
    bind_host: str,
    bind_port: int,
    readonly: bool,
) -> None:
    """Serve a remote HOSTNAME's PATH (default: /) over WebDAV for local mounting."""
    _serve_webdav(
        ClientManager(),
        hostname,
        port,
        rebind_symbols,
        load_all_libraries,
        path,
        mount,
        bind_host,
        bind_port,
        readonly,
    )


if __name__ == "__main__":
    rpcclient()
