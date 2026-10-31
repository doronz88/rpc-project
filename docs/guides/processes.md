# Processes

`p.spawn()` runs commands on the remote host. The `processes` subsystem (`p.processes`) lists the running
processes and returns `Process` objects that let you inspect another process, read and write its memory, and
signal it. The base client only provides `kill()` and `waitpid()`. Everything else on this page needs a Darwin
(macOS/iOS) client.

!!! note
    The examples use the interactive console, where calls are awaited automatically. In a script, `await`
    each call (`proc = await p.processes.get_by_pid(1)`). See [Scripting](scripting.md).

## Running commands with spawn

`spawn()` runs `argv` with `envp` and forwards the process's stdin and stdout/stderr. By default it runs
`/bin/sh` attached to your terminal, so `p.spawn()` gives you an interactive remote shell:

```python
p.spawn()                                   # interactive /bin/sh
p.spawn(['/bin/ls', '-la', '/'])            # output goes to sys.stdout
```

It returns a `SpawnResult(error, pid, stdout)`. `stdin` takes a file object or a string to feed to the
process, and `stdout` takes any file object that should receive both stdout and stderr:

```python
from io import StringIO

out = StringIO()
result = p.spawn(['/bin/echo', 'hello'], stdin='', stdout=out)
result.error                # 0 on success
out.getvalue()              # 'hello\n'
```

Pass `raw_tty=True` to put your local terminal in raw mode for the session, which helps with full-screen
programs. With `background=True`, `spawn()` returns as soon as the process starts, and `error` and `stdout`
are `None`:

```python
result = p.spawn(['/bin/sleep', '60'], stdout=StringIO(), stdin='', background=True)
p.processes.kill(result.pid)
```

## Finding processes

```python
p.processes.list()                       # every running process, as Process objects
p.processes.get_self()                   # the rpcserver process itself
p.processes.get_by_pid(1)                # raises ArgumentError if no such pid
p.processes.get_by_basename('launchd')   # exact match on the executable's file name
p.processes.get_by_name('launchd')       # exact match on the kernel's process name (pbi_name)
p.processes.grep('Spring')               # every process whose basename contains the string
```

You can also look processes up by what they have open:

```python
p.processes.get_processes_by_listening_port(5910)   # processes with a socket listening on the port
p.processes.fuser('/var/log/system.log')            # processes with the file open
p.processes.lsof()                                  # {pid: [Fd, ...]} for every process you can read
```

## Inspecting a process

Keep the `Process` in a variable. `pid` is a plain property. Everything else is a method, so call it:

```python
proc = p.processes.get_by_basename('launchd')
proc.pid                 # 1
proc.path()              # '/sbin/launchd'
proc.basename()          # 'launchd'
proc.name()
proc.bundle_id()         # code-signing identity, e.g. 'com.apple.Preferences'; None if unsigned
proc.ppid(), proc.uid(), proc.gid(), proc.ruid(), proc.rgid()
proc.parent()            # the parent as a Process
proc.start_time()        # datetime (arm64 only)
proc.arguments()         # ['/sbin/launchd']
proc.environ()           # {'PATH': '...', ...}
proc.cdhash()            # bytes
```

`task_all_info()`, `task_vm_info()` and `procargs2()` return the raw parsed kernel structures.

### File descriptors

`fds()` returns a list of `Fd` dataclasses. The subclass tells you the descriptor type: `FileFd` and
`UnixFd` (with `path`), `SharedMemoryFd`, `PipeFd`, `KQueueFd`, and `Ipv4TcpFd`, `Ipv6TcpFd`, `Ipv4UdpFd`
and `Ipv6UdpFd` (with `local_address`, `local_port`, `remote_address`, `remote_port`):

```python
proc = p.processes.get_self()
proc.fds()
[FileFd(fd=0, path='/dev/ttys000'), FileFd(fd=1, path='/dev/ttys000'), ...]
```

### Images, regions and classes

```python
proc.images()            # [Image(address=..., path='/usr/lib/dyld'), ...]
proc.app_images()        # only the images inside the .app bundle
proc.regions()           # [Region(region_type=..., start=..., end=..., protection='r-x', ...), ...]
```

Each `Region` has `start`, `end`, `size`, `protection`, `protection_max`, `region_type` and
`region_detail`. `loaded_classes()` is an async generator over the Objective-C classes realized in the
process, so loop over it with `async for`. A cell that contains `async for` is not rewritten by the
console, so `await` any calls inside it yourself:

```python
async for cls in proc.loaded_classes():
    print(cls.name, cls.binary_path)
```

### Threads and backtraces

```python
threads = proc.threads()         # [ArmThread64 / IntelThread64, ...]
t = threads[0]
t.thread_id
t.get_state()                    # parsed register state
t.suspend()
t.resume()
proc.backtraces()                # one Backtrace (with frames) per thread
```

`t.set_state(state)` writes a register state built from a dict that has the same fields as `get_state()`.

### Symbols, Mach ports and memory graphs

```python
proc.get_symbol_address('malloc', 'libsystem_malloc.dylib')
proc.get_symbol_image('malloc')  # the Image that exports it
proc.get_memgraph_snapshot()     # memory graph as plist bytes
```

`get_mach_ports()` is an async generator of `MachPortInfo` entries (`name`, `rights`, `kobject`,
`exception`, ...). `get_mach_port_cross_ref_info()` shows which process holds the receive right for each
of this process's ports. It only sees other tasks' ports when `rpcserver` runs as root.

```python
async for port in proc.get_mach_ports(resolve_kobjects=True):
    print(port.name, port.rights, port.kobject)
```

`proc.preferences()` reads and writes the preference domain the way this process resolves it (its own
container and uid), for example `proc.preferences().get_dict()`.

## Reading and writing another process's memory

`peek()`, `peek_str()` and `poke()` take an address in the target process. Addresses that come back from
`images()`, `regions()` and `vm_allocate()` are `ProcessSymbol` objects. A `ProcessSymbol` is an `int` bound to
its process, so you can do arithmetic on it and call `peek()`/`poke()` on it directly:

```python
proc = p.processes.get_by_basename('Finder')
base = proc.images()[0].address
proc.peek(base, 4)               # b'\xcf\xfa\xed\xfe'
base.peek(4)                     # the same, through the ProcessSymbol
(base + 0x10).peek(8)

buf = proc.vm_allocate(0x1000)   # allocate memory in the target
buf.poke(b'hello\x00')
buf.peek_str()                   # 'hello'
proc.get_process_symbol(0x100000000)   # wrap any address of the target
```

A `ProcessSymbol` cannot be called. To run code, use a client connected to that process.

!!! note
    Reads use `task_read_for_pid()`, while writes and `vm_allocate()` use `task_for_pid()`. To work on
    other processes, `rpcserver` must run as root and carry the `task_for_pid-allow` entitlement (included in
    `ents.plist`). Hardened or platform processes may still refuse.

## Signals and waiting

```python
from rpcclient.core.structs.consts import SIGKILL

proc.kill()                      # SIGTERM by default
proc.kill(SIGKILL)
p.processes.kill(1234, SIGKILL)  # by pid
p.processes.waitpid(result.pid)  # exit status; only for children of rpcserver, such as spawned ones
```

`p.processes.disable_watchdog()` kills `watchdogd` once a second in a loop that never returns.

## iOS: launching and dumping apps

On iOS, `launch()` starts an app through BackBoardServices and returns its `Process`. By default it kills
any running instance first. It can also disable ASLR, wait for a debugger, or redirect stdout/stderr to a file
on the device. It raises `LaunchError` if the app does not start:

```python
proc = p.processes.launch('com.apple.calculator')
proc = p.processes.launch('com.example.app', disable_aslr=True, wait_for_debugger=True,
                          stdout='/tmp/app.out', stderr='/tmp/app.err')
```

`dump_app(output_dir)` writes each Mach-O in the app bundle to a local directory, keeping its path relative
to the `.app`. For encrypted binaries it copies the decrypted pages from memory and sets `cryptid` to 0,
in the same way as frida-ios-dump. Launch the app first so its images are loaded:

```python
proc = p.processes.launch('com.example.app')
proc.dump_app('~/dumps/example')
```

See also: [Darwin API](../api/darwin.md#processes), [iOS API](../api/ios.md),
[Calling native functions](calling-native-functions.md).
