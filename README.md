# Rpc-Project

<!-- markdownlint-disable MD013 -->
[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/doronz88/rpc-project)
<!-- markdownlint-enable MD013 -->


- [rpc-project](#rpc-project)
  - [Description](#description)
  - [Local installation](#local-installation)
  - [Remote installation](#remote-installation)
  - [Building](#building)
    - [macOS/iOS](#macosios)
    - [Linux](#linux)
  - [Quickstart](#quickstart)
  - [Calling native functions](#calling-native-functions)
    - [Globalized symbols](#globalized-symbols)
    - [ObjC support](#objc-support)

# rpc-project

## Description

Simple RPC service providing an API for controlling every aspect of the target machine. Thie swiss army knife can be used for:

- QA Automation
- Developement (simply test your APIs through python)
- Software research (found an interesting OS API? try it out with no compilation required!)

This project includes two components:

- Server binary written in C exposing a protocol to call native C functions.
- Client written in Python3 to communicate with the server

The python client utilizes the ability to call native functions in order to provide APIs for different aspects:

- Remote system commands (`p.spawn()`)
- Remote shell (`p.shell()`)
- Filesystem management (`p.fs.*`)
- Network management (WiFi scan, TCP connect, etc...) (`p.network.*`)
- Sysctl API (`p.sysctl.*`)
- Darwin only:
  - Multimedia automation (recording and playing) (`p.media.*`)
  - Preferences managemnent (remote manage CFPreference and SCPreferences) (`p.preferences.*`)
  - Process management (kill, list, query open FDs, etc...) (`p.processes.*`)
  - Location services (`p.location.*`)
  - HID simulation (`p.hid.*`)
    - Control battery properties (current percentage and temperature)
    - Simulate touch and keyboard events
  - IORegistry API (`p.ioregistry.*`)
  - Reports management (Logs and Crash Reports) (`p.reports.*`)
  - Time settings (`p.time.*`)
  - Bluetooth management (`p.bluetooth.*`)
  - Location Services (`p.location.*`)
  - XPC wrappers (`p.xpc.*`)
  - iOS Only:
    - MobileGestalt (`p.mobile_gestalt.*`)
    - Backlight adjusting (`p.backlight.*`)
    - Dump decrypted applications (`p.processes.get_by_basename(process_name).dump_app('/path/to/output')`)

and much more...

## Local installation

```shell
# install the package
python3 -m pip install -U rpcclient

# enter shell
rpclocal
```

## Remote installation

Download and execute the latest server artifact, according to your platform and arch from the latest [GitHub action execution](https://github.com/doronz88/rpc-project/actions/workflows/server-publish.yml).

If your specific platform and arch isn't listed, you can also [build it yourself](#building).

Install the latest client from PyPi:

```shell
python3 -m pip install -U rpcclient
```

## Building

**Note:** Cross-platform support is currently not available.

### macOS/iOS
For macOS/iOS (Ensure that Xcode is installed):

```bash
brew install protobuf protobuf-c
python3 -m pip install mypy-protobuf protobuf grpcio-tools
git clone git@github.com:doronz88/rpc-project.git
cd rpc-project
make -C src/protos/ all
cd src/rpcserver
mkdir build
cd build
cmake .. -DTARGET=OSX
make
cmake .. -DTARGET=IOS 
make
```

### Linux

```bash
sudo apt-get install -y protobuf-compiler libprotobuf-dev libprotoc-dev protobuf-c-compiler
python3 -m pip mypy-protobuf protobuf grpcio-tools
git clone git@github.com:doronz88/rpc-project.git --recurse-submodules
cd rpc-project
make -C src/protos/ all
cd src/rpcserver
mkdir build
cd build
cmake .. -DTARGET=LINUX
make
```

## Quickstart

To execute the server:

```
Usage: ./rpcserver [-p port] [-o (stdout|syslog|file:filename)]
-h  show this help message
-o  output. can be all of the following: stdout, syslog and file:filename. can be passed multiple times

Example usage:
./rpcserver -p 5910 -o syslog -o stdout -o file:/tmp/log.txt
```

Connecting via:

```shell
python3 -m rpcclient
```

Full usage:

```
Usage: rpcclient [OPTIONS] [HOSTNAME]

  Start the console. If HOSTNAME is provided, connect immediately. Otherwise,
  start without a connection. You can connect later from the console.

Options:
  -p, --port INTEGER        TCP port to connect to
  -r, --rebind-symbols      reload all symbols upon connection
  -l, --load-all-libraries  load all libraries
  --help                    Show this message and exit.
```

> **_NOTE:_** If you are attempting to connect to a **jailbroken iOS device**, you will be required to also create a TCP tunnel to your device. For example, using: [`pymobiledevice3`](https://github.com/doronz88/pymobiledevice3): ```python3 -m pymobiledevice3 usbmux forward 5910 5910 -vvv```

You should now get a nice iPython shell looking like this:

```
RpcClient has been successfully loaded! 😎
Usage:
mgr     Client manager: create | get | remove | clients | clear
console Console controller: switch
p       Active client (e.g., p.info(), p.pid)
F1      Show this help
F2      Show active contexts
F3      Previous context
F4      Toggle Auto switch on creation
Have a nice flight ✈️! Starting an IPython shell...
Python 3.12.7 (main, Oct  1 2024, 02:05:46) [Clang 16.0.0 (clang-1600.0.26.3)]
Type 'copyright', 'credits' or 'license' for more information
IPython 9.4.0 -- An enhanced Interactive Python. Type '?' for help.

IPython profile: rpcclient
Tip: Use `F2` or %edit with no arguments to open an empty editor with a temporary file.

[Rpc-client]:
```

### Understanding the globals: mgr, console, and p

- mgr — Client manager for creating and tracking RPC clients
    - `mgr.create(hostname="127.0.0.1", port=5910)` → create and connect a new client
    - `mgr.get(pid)` → get a client by PID
    - `mgr.remove(pid)` → disconnect and remove a client
    - `mgr.clients` → list current clients
    - `mgr.clear()` → remove all clients

- console — Console/session controller for switching active client contexts
    - `console.switch(pid)` → switch the active context to a specific PID
    - `console.switch()` → interactively pick a client to switch to

- p — The active client in the current console context
    - Use p to call APIs, e.g., `p.info()`, `p.pid`, `p.fs.listdir(".")`, `p.spawn([...])`
    - When you switch contexts, p is automatically updated to the selected client


Create a new client:
```
[Rpc-client]: mgr.create(hostname="127.0.0.1")
Auto-switched to new client PID: 79669
[osx| (79669) rpcserver_macosx]: <MacosClient: 79669 | rpcserver_macosx>

[osx| (79669) rpcserver_macosx]:
```

Change the console context to another client:
```
[Rpc-client]: console.switch()
[?] Select a client PID: <MacosClient: 78536 | rpcserver_macosx>
   <MacosClient: 78535 | rpcserver_macosx>
 ❯ <MacosClient: 78536 | rpcserver_macosx>
```

Now you can try accessing the different features using the global `p` variable.
For example (Just a tiny sample of the many things you can now do. Feel free to explore much more!):

```
[osx| (78479) rpcserver_macosx]: p.spawn(['sleep', '1'])
[osx| (78479) rpcserver_macosx]: SpawnResult(error=0, pid=25047, stdout=<_io.TextIOWrapper name='<stdout>' mode='w' encoding='utf-8'>)

[osx| (78479) rpcserver_macosx]: p.fs.listdir('.')
[osx| (78479) rpcserver_macosx]:
['common.c',
 '.pytest_cache',
 'Makefile',
 'rpcserver_iphoneos_arm64',
 'rpcserver.c',
 'common.h',
 'rpcserver_macosx_x86_64',
 'ents.plist',
 'build_darwin.sh']

[osx| (78479) rpcserver_macosx]: p.processes.get_by_pid(p.pid).fds
[osx| (78479) rpcserver_macosx]:
[FileFd(fd=0, path='/dev/ttys000'),
 FileFd(fd=1, path='/dev/ttys000'),
 FileFd(fd=2, path='/dev/ttys000'),
 Ipv6TcpFd(fd=3, local_address='0.0.0.0', local_port=5910, remote_address='0.0.0.0', remote_port=0),
 Ipv6TcpFd(fd=4, local_address='127.0.0.1', local_port=5910, remote_address='127.0.0.1', remote_port=53217),
 Ipv6TcpFd(fd=5, local_address='127.0.0.1', local_port=5910, remote_address='127.0.0.1', remote_port=53229),
 Ipv6TcpFd(fd=6, local_address='127.0.0.1', local_port=5910, remote_address='127.0.0.1', remote_port=53530)]

[osx| (78479) rpcserver_macosx]: p.processes.get_by_pid(p.pid).regions[:3]
[osx| (78479) rpcserver_macosx]:
[Region(region_type='__TEXT', start=4501995520, end=4502028288, vsize='32K', protection='r-x', protection_max='r-x', region_detail='/Users/USER/*/rpcserver_macosx_x86_64'),
 Region(region_type='__DATA_CONST', start=4502028288, end=4502044672, vsize='16K', protection='r--', protection_max='rw-', region_detail='/Users/USER/*/rpcserver_macosx_x86_64'),
 Region(region_type='__DATA', start=4502044672, end=4502061056, vsize='16K', protection='rw-', protection_max='rw-', region_detail='/Users/USER/*/rpcserver_macosx_x86_64')]
```

## Calling native functions

In `rpc-project`, almost everything is wrapped using the `Symbol` Object. Symbol is just a nicer way for referring to addresses
encapsulated with an object allowing to deref the memory inside, or use these addresses as functions.

In order to create a symbol from a given address, please use:

```python
s = p.symbol(0x12345678)

# the Symbol object extends `int`
True == isinstance(s, int)

# write into this memory
s.poke(b'abc')

# peek(/read) 20 bytes of memory
print(s.peek(20))

# jump to `s` as a function, passing (1, "string") as its args 
s(1, "string")

# change the size of each item_size inside `s` for derefs
s.item_size = 1

# *(char *)s = 1
s[0] = 1

# *(((char *)s)+1) = 1
s[1] = 1

# symbol inherits from int, so all int operations apply
s += 4

# change s item size back to 8 to store pointers
s.item_size = 8

# *(intptr_t *)s = 1
s[0] = 1

# storing the return value of the function executed at `0x11223344`
# into `*s`
s[0] = p.symbol(0x11223344)()  # calling symbols also returns symbols 

# query in which file 0x11223344 is loaded from
print(p.symbol(0x11223344).filename)
```

### Globalized symbols

Usually you would want/need to use the symbols already mapped into the currently running process. To do so, you can
access them using `symbols.<symbol-name>`. The `symbols` global object is of type `SymbolsJar`, which is a wrapper
to `dict` for accessing all exported symbols. For example, the following will generate a call to the exported
`malloc` function with `20` as its only argument:

```python
x = symbols.malloc(20)
```

You can also just write their name as if they already were in the global scope. The client will check if no name collision
exists, and if so, will perform the following lazily for you:

```python
x = malloc(20)

# is equivalent to:
malloc = symbols.malloc
x = malloc(20)
```

### ObjC support

When working on Darwin based systems, it can be sometimes easier to use the builtin ObjC support.

```python
# creating CF/NSObjets using the builtin cf() method
some_cf_string = p.cf('some string')

# create a new NSMutableDictionary
a = NSMutableDictionary.new()

# tell where this class is loaded from
print(NSMutableDictionary.bundle_path)

# which is a short-hand for objc_get_class(class_name)
a = p.objc_get_class('NSMutableDictionary').new()

# each darwin object is a "DarwinSymbol", instead of a "simple Symbol"
# that mean it has the special method: objc_call("selector", ...)
a.objc_call('setObject:forKey:', p.cf('value'), p.cf('key'))

# we can look at the CFDescription of every DarwinSymbol using the "cfdesc" property
a.cfdesc

# it can be easier to use further ObjC capabilities by converting the current DarwinSymbol into an ObjectiveCSymbol instead
a = a.objc_symbol

# We can now examine the class/objects properties
a.show()

# now we'll have a auto-complete for all of its selectors, ivars, etc.
a.setObject_forKey_(p.cf('value2'), p.cf('key2'))

# and we can easily convert this object to python native using the py() method. please note that this is done behind-the-scene using plistlib, meaning only plist-serializable objects (and None) can be coverted this way.
a = a.py()

# attempt to load all frameworks for auto-completions of all ObjC classes
# (equivalent to running the client with -l -r)
p.load_all_libraries()

# create autorelease pool context where the pool is drained at the end
pool_ctx = p.create_autorelease_pool_ctx()
# ...
# do stuff
# ...
# drain pool
pool_ctx.drain()

# same but in `with` statement
with p.create_autorelease_pool_ctx() as pool_ctx:
    # do stuff

# fetch all currently existing autorelease pools and iterate over all of the objects inside
for pool in p.get_autorelease_pools():
    for obj in pool:
        # do stuff with objects
```
