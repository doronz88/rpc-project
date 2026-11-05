# rpc-project

`rpc-project` is a simple, powerful **RPC service for controlling every aspect of a remote machine**. A small C **server** exposes a protocol for calling native functions; a Python **client** turns that into a rich, scriptable API. Use it for QA automation, for testing your APIs straight from Python, and for software research: found an interesting OS API? Try it with no compilation required.

## How it fits together

**Your machine**

`rpcclient`, written in Python 3. An IPython shell (or a library) that builds high-level APIs on top of native calls.

call → result

**The target**

`rpcserver`, a small binary written in C that exposes a protocol for calling native C functions. Runs on macOS, iOS and Linux.

## What you can reach

Each platform adds to the one around it: everything that works everywhere also works on Darwin, and everything on Darwin also works on iOS.

Every platform

- Remote system commands: `p.spawn()`
- Remote shell: `p.shell()`
- Filesystem: `p.fs.*`
- Network (Wi-Fi scan, TCP connect, …): `p.network.*`
- Sysctl: `p.sysctl.*`

Darwin (macOS and iOS)

- Multimedia record and play: `p.media.*`
- Preferences (CFPreferences, SCPreferences): `p.preferences.*`
- Process management: `p.processes.*`
- Location: `p.location.*`
- HID simulation (touch, keyboard, battery): `p.hid.*`
- IORegistry: `p.ioregistry.*`
- Logs and crash reports: `p.reports.*`
- Time, Bluetooth, XPC: `p.time.*`, `p.bluetooth.*`, `p.xpc.*`

iOS only

- MobileGestalt: `p.mobile_gestalt.*`
- Backlight: `p.backlight.*`
- Dump decrypted apps: `p.processes.get_by_basename(name).dump_app('/path')`

## Where to go next

[**Installation**\
Get the server binary and `pip install rpcclient`.](https://doronz88.github.io/rpc-project/latest/installation/index.md)

[**Quick start**\
Run the server and open the client shell.](https://doronz88.github.io/rpc-project/latest/guides/quickstart/index.md)

[**Calling native functions**\
Symbols, globals, raw memory and ObjC.](https://doronz88.github.io/rpc-project/latest/guides/calling-native-functions/index.md)

[**API reference**\
The generated `rpcclient` reference.](https://doronz88.github.io/rpc-project/latest/api/index.md)
