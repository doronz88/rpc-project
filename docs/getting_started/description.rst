Description
===========

Simple RPC service providing an API for controlling every aspect of the
target machine. Thie swiss army knife can be used for:

-  QA Automation
-  Developement (simply test your APIs through python)
-  Software research (found an interesting OS API? try it out with no
   compilation required!)

This project includes two components:

-  Server binary written in C exposing a protocol to call native C
   functions.
-  Client written in Python3 to communicate with the server

The python client utilizes the ability to call native functions in order
to provide APIs for different aspects:

-  Remote system commands (``p.spawn()``)
-  Remote shell (``p.shell()``)
-  Filesystem management (``p.fs.*``)
-  Network management (WiFi scan, TCP connect, etc…) (``p.network.*``)
-  Sysctl API (``p.sysctl.*``)
-  Darwin only:

   -  Multimedia automation (recording and playing) (``p.media.*``)
   -  Preferences managemnent (remote manage CFPreference and
      SCPreferences) (``p.preferences.*``)
   -  Process management (kill, list, query open FDs, etc…)
      (``p.processes.*``)
   -  Location services (``p.location.*``)
   -  HID simulation (``p.hid.*``)

      -  Control battery properties (current percentage and temperature)
      -  Simulate touch and keyboard events

   -  IORegistry API (``p.ioregistry.*``)
   -  Reports management (Logs and Crash Reports) (``p.reports.*``)
   -  Time settings (``p.time.*``)
   -  Bluetooth management (``p.bluetooth.*``)
   -  Location Services (``p.location.*``)
   -  XPC wrappers (``p.xpc.*``)
   -  iOS Only:

      -  MobileGestalt (``p.mobile_gestalt.*``)
      -  Backlight adjusting (``p.backlight.*``)
      -  Dump decrypted applications
         (``p.processes.get_by_basename(process_name).dump_app('/path/to/output')``)

and much more…
