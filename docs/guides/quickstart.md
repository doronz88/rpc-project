# Quick start

## Run the server

```none
Usage: ./rpcserver [-p port] [-o (stdout|syslog|file:filename)]
-h  show this help message
-o  output. can be all of: stdout, syslog and file:filename. can be passed multiple times

Example:
./rpcserver -p 5910 -o syslog -o stdout -o file:/tmp/log.txt
```

## Connect the client

Connect to a running server (`HOSTNAME` is optional — omit it to start without a connection and
connect later from the console):

```shell
rpcclient [HOSTNAME]
# or: python3 -m rpcclient [HOSTNAME]
```

To control the **local** machine (no remote server needed), use:

```shell
rpclocal
```

Full usage:

```none
Usage: rpcclient [OPTIONS] [HOSTNAME]

  Start the console. If HOSTNAME is provided, connect immediately. Otherwise,
  start without a connection. You can connect later from the console.

Options:
  -p, --port INTEGER        TCP port to connect to
  -r, --rebind-symbols      reload all symbols upon connection
  -l, --load-all-libraries  load all libraries
  -f, --startup-files PATH  File(s) (python) to run on session start. Repeatable.
  --help                    Show this message and exit.
```

!!! note "Connecting to a jailbroken iOS device"
    You'll need a TCP tunnel to the device first, e.g. with
    [pymobiledevice3](https://github.com/doronz88/pymobiledevice3):

    ```shell
    python3 -m pymobiledevice3 usbmux forward 5910 5910 -vvv
    ```

## The console: `mgr`, `console`, `p`

You land in an IPython shell with three globals:

- **`mgr`** — client manager: `mgr.create(hostname="127.0.0.1", port=5910)`, `mgr.get(pid)`,
  `mgr.remove(pid)`, `mgr.clients`, `mgr.clear()`
- **`console`** — context controller: `console.switch(pid)`, or `console.switch()` to pick
  interactively
- **`p`** — the active client; auto-updated when you switch context (`p.info()`, `p.pid`,
  `p.fs.listdir(".")`, `p.spawn([...])`)

`F1` shows help, `F2` shows active contexts, `F3` switches to the previous context, `F4` toggles
auto-switch on creation.

```text
[Rpc-client]: mgr.create(hostname="127.0.0.1")
Auto-switched to new client PID: 79669
[osx| (79669) rpcserver_macosx]: <MacosClient: 79669 | rpcserver_macosx>
```

## Try it

```python
[osx| (78479) rpcserver_macosx]: p.spawn(['sleep', '1'])
SpawnResult(error=0, pid=25047, stdout=<_io.TextIOWrapper ...>)

[osx| (78479) rpcserver_macosx]: p.fs.listdir('.')
['common.c', 'Makefile', 'rpcserver.c', ...]

[osx| (78479) rpcserver_macosx]: p.processes.get_by_pid(p.pid).fds
[FileFd(fd=0, path='/dev/ttys000'), ...]
```

Explore the rest through `p`. Next: [Calling native functions](calling-native-functions.md).
