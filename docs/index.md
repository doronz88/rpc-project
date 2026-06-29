# rpc-project

`rpc-project` is a simple, powerful **RPC service for controlling every aspect of a remote
machine**. A small C **server** exposes a protocol for calling native functions; a Python
**client** turns that into a rich, scriptable API. Think of it as a swiss-army knife for:

- QA automation
- Development — test your APIs straight from Python
- Software research — found an interesting OS API? Try it with no compilation required

[Get started :material-arrow-right:](installation.md){ .md-button .md-button--primary }
[Quick start](guides/quickstart.md){ .md-button }

## Two components

- **Server** — a binary written in C that exposes a protocol to call native C functions.
- **Client** — `rpcclient`, written in Python 3, that talks to the server and builds high-level
  APIs on top of native calls.

## What the client gives you

Cross-platform:

- Remote system commands — `p.spawn()`
- Remote shell — `p.shell()`
- Filesystem — `p.fs.*`
- Network (Wi-Fi scan, TCP connect, …) — `p.network.*`
- Sysctl — `p.sysctl.*`

Darwin (macOS/iOS):

- Multimedia record/play — `p.media.*`
- Preferences (CFPreferences / SCPreferences) — `p.preferences.*`
- Process management — `p.processes.*`
- Location — `p.location.*`
- HID simulation (touch, keyboard, battery) — `p.hid.*`
- IORegistry — `p.ioregistry.*`
- Logs & crash reports — `p.reports.*`
- Time, Bluetooth, XPC — `p.time.*`, `p.bluetooth.*`, `p.xpc.*`

iOS only:

- MobileGestalt — `p.mobile_gestalt.*`
- Backlight — `p.backlight.*`
- Dump decrypted apps — `p.processes.get_by_basename(name).dump_app('/path')`

…and much more.

## Where to go next

<div class="grid cards" markdown>

- :material-download: **[Installation](installation.md)** — get the server and `pip install rpcclient`.
- :material-rocket-launch: **[Quick start](guides/quickstart.md)** — run the server and open the client shell.
- :material-function-variant: **[Calling native functions](guides/calling-native-functions.md)** — symbols, globals, ObjC.
- :material-book-open-variant: **[API reference](api/index.md)** — the generated `rpcclient` reference.

</div>
