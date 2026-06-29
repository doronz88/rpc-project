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

```shell
python3 -m rpcclient <HOST>
```

Full usage:

```none
Usage: python -m rpcclient [OPTIONS] HOSTNAME

Options:
  -p, --port INTEGER
  -r, --rebind-symbols      reload all symbols upon connection
  -l, --load-all-libraries  load all libraries
  --help                    Show this message and exit.
```

!!! note "Connecting to a jailbroken iOS device"
    You'll need a TCP tunnel to the device first, e.g. with
    [pymobiledevice3](https://github.com/doronz88/pymobiledevice3):

    ```shell
    python3 -m pymobiledevice3 usbmux forward 5910 5910 -vvv
    ```

You'll land in an IPython shell with two globals ready to use:

- 🌍 `p` — the injected process
- 🌍 `symbols` — process global symbols

## Try it

```python
In [2]: p.spawn(['sleep', '1'])
Out[2]: SpawnResult(error=0, pid=25047, stdout=<_io.TextIOWrapper ...>)

In [3]: p.fs.listdir('.')
Out[3]: ['common.c', 'Makefile', 'rpcserver.c', ...]

In [4]: p.processes.get_by_pid(p.pid).fds
Out[4]: [FileFd(fd=0, path='/dev/ttys000'), ...]

In [5]: p.processes.get_by_pid(p.pid).regions[:3]
Out[5]: [Region(region_type='__TEXT', start=..., protection='r-x', ...), ...]
```

Explore the rest through the global `p`. See
[Calling native functions](calling-native-functions.md) next.
