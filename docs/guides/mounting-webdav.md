# Mounting a remote path in Finder (WebDAV)

`rpcclient` can expose any path on the remote target as a local **WebDAV** volume, so macOS
Finder (or any WebDAV client) can browse and edit the remote filesystem read-write as if it were
mounted.

A small async WebDAV server runs **inside the `rpcclient` process**; every WebDAV request is
translated into `client.fs` calls against the target. Nothing runs on the target and there are no
server-side changes, so it works the same for iOS, macOS, and Linux targets.

WebDAV is used rather than FTP because macOS Finder mounts FTP **read-only** — it only allows
writes to servers that implement WebDAV locking, which this server does.

## Quick start

Serve the target's root and mount it in your file manager in one step:

```shell
rpcdav HOSTNAME --mount
```

`--mount` uses the host's native WebDAV mechanism — `mount_webdav` on macOS, `net use` on
Windows, `gio mount` on Linux — and reveals the volume in the file manager. If none is
available, it falls back to printing the URL to open manually.

Serve a specific path instead of `/`:

```shell
rpcdav HOSTNAME /var/mobile/Containers --mount
```

The same is available as a subcommand of `rpcclient`:

```shell
rpcclient HOSTNAME webdav [PATH] [--mount]
```

Press `Ctrl-C` to unmount and stop the server.

## Mounting manually

Without `--mount`, the server prints its local URL:

```
WebDAV server serving '/' at http://127.0.0.1:52314/
In Finder: Go → Connect to Server → http://127.0.0.1:52314/
```

In Finder, choose **Go → Connect to Server** (`⌘K`) and enter that URL (on Linux/Windows, open
it in your file manager's "connect to server" equivalent, or use any WebDAV client).

## Usage

```none
Usage: rpcdav [OPTIONS] HOSTNAME [PATH]

  Serve a remote HOSTNAME's PATH (default: /) over WebDAV for local mounting.

Options:
  -p, --port INTEGER        TCP port to connect to
  -r, --rebind-symbols      reload all symbols upon connection
  -l, --load-all-libraries  load all libraries
  --mount                   mount the served path locally and reveal it in your file manager
  --host TEXT               local interface to bind
  --bind-port INTEGER       local TCP port (0 picks a free port)
  --readonly                expose the path read-only
```

## From a script

The `webdav` subsystem is available on every client:

```python
server = await client.webdav.serve("/var/mobile", host="127.0.0.1", port=0)
print(server.url)  # http://127.0.0.1:<port>/
# ... use the mount ...
await server.stop()
```

## Notes and limitations

- **Freshness / stale views.** A mounted WebDAV volume is a *client-cached network filesystem*.
  Changes you make through the mount are immediate, but changes made on the target out-of-band may
  appear stale until the client revalidates. WebDAV has no live-reload mechanism, and macOS's
  WebDAV client caches directory listings and attributes at the kernel level regardless of server
  hints. To force a refresh, navigate out of the folder and back (or reopen the window).
- **Read-write** browse, read, create, edit, `mkdir`, rename/move, and delete all propagate to the
  target.
- **Finder metadata** (`.DS_Store`, AppleDouble `._*`, …) writes are swallowed — reported as
  success but never written to the target, so they don't clutter it or fail on read-only roots.
- **`chmod` / `chown` do not propagate.** WebDAV has no representation for POSIX permissions or
  ownership, and macOS's WebDAV client never sends them — such changes on the mount are local
  no-ops. Use `client.fs.chmod(...)` / `client.fs.chown(...)` for real remote permission changes.
- **New files and directories** are created by the process the `rpcserver` runs as, so they are
  owned by that user (e.g. `root` when the server runs as root), with the server's default
  permissions — not your local user.
