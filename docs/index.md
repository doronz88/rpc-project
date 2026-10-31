---
template: home.html
hide:
  - navigation
  - toc
---

# rpc-project

`rpc-project` is a simple, powerful **RPC service for controlling every aspect of a remote
machine**. A small C **server** exposes a protocol for calling native functions; a Python
**client** turns that into a rich, scriptable API. Use it for QA automation, for testing your
APIs straight from Python, and for software research: found an interesting OS API? Try it with no
compilation required.

## How it fits together

<div class="rp-flow" markdown>

<div class="rp-flow__side" markdown>
**Your machine**

`rpcclient`, written in Python 3. An IPython shell (or a library) that builds high-level APIs on
top of native calls.
</div>

<div class="rp-flow__wire" aria-hidden="true"><span>call → result</span></div>

<div class="rp-flow__side rp-flow__side--remote" markdown>
**The target**

`rpcserver`, a small binary written in C that exposes a protocol for calling native C functions.
Runs on macOS, iOS and Linux.
</div>

</div>

## What you can reach

Each platform adds to the one around it: everything that works everywhere also works on Darwin,
and everything on Darwin also works on iOS.

<div class="rp-scopes" markdown>

<div class="rp-scope rp-scope--all" markdown>
<p class="rp-scope__name">Every platform</p>

- Remote system commands: `p.spawn()`
- Remote shell: `p.shell()`
- Filesystem: `p.fs.*`
- Network (Wi-Fi scan, TCP connect, …): `p.network.*`
- Sysctl: `p.sysctl.*`

<div class="rp-scope rp-scope--darwin" markdown>
<p class="rp-scope__name">Darwin (macOS and iOS)</p>

- Multimedia record and play: `p.media.*`
- Preferences (CFPreferences, SCPreferences): `p.preferences.*`
- Process management: `p.processes.*`
- Location: `p.location.*`
- HID simulation (touch, keyboard, battery): `p.hid.*`
- IORegistry: `p.ioregistry.*`
- Logs and crash reports: `p.reports.*`
- Time, Bluetooth, XPC: `p.time.*`, `p.bluetooth.*`, `p.xpc.*`

<div class="rp-scope rp-scope--ios" markdown>
<p class="rp-scope__name">iOS only</p>

- MobileGestalt: `p.mobile_gestalt.*`
- Backlight: `p.backlight.*`
- Dump decrypted apps: `p.processes.get_by_basename(name).dump_app('/path')`

</div>
</div>
</div>

</div>

## Where to go next

<div class="rp-next" markdown>

[**Installation**<br>Get the server binary and `pip install rpcclient`.](installation.md)

[**Quick start**<br>Run the server and open the client shell.](guides/quickstart.md)

[**Calling native functions**<br>Symbols, globals, raw memory and ObjC.](guides/calling-native-functions.md)

[**API reference**<br>The generated `rpcclient` reference.](api/index.md)

</div>
