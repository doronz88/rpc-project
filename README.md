[![Server application](https://img.shields.io/github/workflow/status/doronz88/rpc-project/Server%20application?label=python%20package&style=plastic)](https://github.com/doronz88/rpc-project/actions/workflows/server-app.yml "Server application action")
[![Python application](https://img.shields.io/github/workflow/status/doronz88/rpc-project/Python%20application?label=server%20build&style=plastic)](https://github.com/doronz88/rpc-project/actions/workflows/python-app.yml "Python application action")
[![Language grade: Python](https://img.shields.io/lgtm/grade/python/g/doronz88/rpc-project.svg?logo=lgtm&logoWidth=18)](https://lgtm.com/projects/g/doronz88/rpc-project/context:python)

- [rpc-project](#rpc-project)
  - [Description](#description)
  - [Building C Server](#building-c-server)
  - [Installing python client](#installing-python-client)
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

and much more...

## Building C Server

macOS & Linux:

```shell
git clone git@github.com:doronz88/rpc-project.git
cd src/rpcserver
make
```

On iOS (Make sure to have XCode installed):

```shell
git clone git@github.com:doronz88/rpc-project.git
cd src/rpcserver
./build_darwin.sh
```

## Installing python client

```shell
git clone git@github.com:doronz88/rpc-project.git
cd src/rpcclient
python3 -m pip install --user -U .
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
python3 -m rpcclient <HOST> [-p port]
```

> **_NOTE:_** If you are attempting to connect to a **jailbroken iOS device**, you will be required to also create a TCP tunnel to your device. For example, using: [`pymobiledevice3`](https://github.com/doronz88/pymobiledevice3): ```python3 -m pymobiledevice3 lockdown forward 5910 5910 -vvv```

You should now get a nice iPython shell looking like this:

```
➜  rpc-project git:(master) python3 -m rpcclient 127.0.0.1
2022-03-29 23:42:31 Cyber root[24947] INFO connection uname.sysname: Darwin

Welcome to the rpcclient interactive shell! You interactive shell for controlling the remote rpcserver.
Feel free to use the following globals:

🌍 p - the injected process
🌍 symbols - process global symbols

Have a nice flight ✈️!
Starting an IPython shell... 🐍

Python 3.9.10 (main, Jan 15 2022, 11:48:04)
Type 'copyright', 'credits' or 'license' for more information
IPython 7.25.0 -- An enhanced Interactive Python. Type '?' for help.

In [1]:
```

And... Congrats! You are now ready to go! 😎 

Try accessing the different features using the global `p` variable.
For example (Just a tiny sample of the many things you can now do. Feel free to explore much more!):

```
In [2]: p.spawn(['sleep', '1'])
2022-03-29 23:45:51 Cyber root[24947] INFO shell process started as pid: 25047
Out[2]: SpawnResult(error=0, pid=25047, stdout=<_io.TextIOWrapper name='<stdout>' mode='w' encoding='utf-8'>)

In [3]: p.fs.listdir('.')
Out[3]:
['common.c',
 '.pytest_cache',
 'Makefile',
 'rpcserver_iphoneos_arm64',
 'rpcserver.c',
 'common.h',
 'rpcserver_macosx_x86_64',
 'ents.plist',
 'build_darwin.sh']

In [4]: p.processes.get_by_pid(p.pid).fds
Out[4]:
[FileFd(fd=0, path='/dev/ttys000'),
 FileFd(fd=1, path='/dev/ttys000'),
 FileFd(fd=2, path='/dev/ttys000'),
 Ipv6TcpFd(fd=3, local_address='0.0.0.0', local_port=5910, remote_address='0.0.0.0', remote_port=0),
 Ipv6TcpFd(fd=4, local_address='127.0.0.1', local_port=5910, remote_address='127.0.0.1', remote_port=53217),
 Ipv6TcpFd(fd=5, local_address='127.0.0.1', local_port=5910, remote_address='127.0.0.1', remote_port=53229),
 Ipv6TcpFd(fd=6, local_address='127.0.0.1', local_port=5910, remote_address='127.0.0.1', remote_port=53530)]

In [5]: p.processes.get_by_pid(p.pid).regions[:3]
Out[5]:
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
s[0] = symbol(0x11223344)()  # calling symbols also returns symbols 
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
```
