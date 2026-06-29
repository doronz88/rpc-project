# API Reference

Generated from the `rpcclient` source. The client is organized as a per-platform `Client` built on
a shared core, exposing subsystems as attributes (`p.fs`, `p.network`, `p.processes`, …).

- **[Core client](core.md)** — the abstract client, symbols, and exceptions.
- **[Platform clients](clients.md)** — Linux / macOS / Darwin / iOS clients.
- **[Darwin subsystems](darwin.md)** — filesystem, network, processes, HID, media, and more.
- **[iOS subsystems](ios.md)** — MobileGestalt, SpringBoard, lockdown, backlight, and more.

New here? Start with the [Quick start](../guides/quickstart.md) and
[Calling native functions](../guides/calling-native-functions.md) guides.
