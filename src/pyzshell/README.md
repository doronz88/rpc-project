# zShell

## Description

Simple C server for achieving a nice remote shell allowing:
* Remote C function calls
* Remote shell commands
* Remote filesystem management

## Building C Server

macOS & Linux:
```shell
git clone git@github.com:doronz88/zshell.git
cd src/remote_server
make
```

On iOS:
```shell
git clone git@github.com:doronz88/zshell.git
cd src
./build_ios.sh
```

## Installing python client

```shell
git clone git@github.com:doronz88/zshell.git
cd src/pyzshell
python3 -m pip install --user -U .
```

## Running

To execute the server:

```shell
./server [-p port]
```

Connecting via:

```shell
python3 -m pyzshell ishell <HOST>
```

Here are some examples of things you may do:

```
z@DoronZ ~/d/z/s/pyzshell (master)> pyzshell 127.0.0.1 ishell
2022-01-30 13:45:26 DoronZ.local root[75935] INFO connected system uname.version: Darwin Kernel Version 21.2.0: Sun Nov 28 20:28:54 PST 2021; root:xnu-8019.61.5~1/RELEASE_X86_64

Welcome to iShell! You interactive shell for controlling the remote zShell server.
Feel free to use the following globals:

🌍 p - the injected process
🌍 symbols - process global symbols

Have a nice flight ✈️!
Starting an IPython shell... 🐍

Python 3.9.10 (main, Jan 15 2022, 11:48:04)
Type 'copyright', 'credits' or 'license' for more information
IPython 7.29.0 -- An enhanced Interactive Python. Type '?' for help.

In [1]: x = malloc(20)

In [2]: x.poke(b'abc\0')

In [3]: strlen(x)
Out[3]: <DarwinSymbol: 0x3>

In [4]: p.fs.dirlist('.')
Out[4]:
[Container(d_ino=42477240, d_offset=12, d_reclen=4, d_namelen=1, d_name=u'.'),
 Container(d_ino=42065420, d_offset=12, d_reclen=4, d_namelen=2, d_name=u'..'),
 Container(d_ino=42067893, d_offset=20, d_reclen=8, d_namelen=8, d_name=u'common.c'),
 Container(d_ino=42477250, d_offset=20, d_reclen=8, d_namelen=9, d_name=u'.DS_Store'),
 Container(d_ino=42905463, d_offset=20, d_reclen=8, d_namelen=8, d_name=u'Makefile'),
 Container(d_ino=42915018, d_offset=16, d_reclen=8, d_namelen=6, d_name=u'server'),
 Container(d_ino=42905464, d_offset=20, d_reclen=8, d_namelen=8, d_name=u'server.c'),
 Container(d_ino=42067833, d_offset=20, d_reclen=8, d_namelen=8, d_name=u'common.h'),
 Container(d_ino=42915015, d_offset=24, d_reclen=8, d_namelen=15, d_name=u'common_server.o')]

In [5]:
```