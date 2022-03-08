[![Server application](https://img.shields.io/github/workflow/status/doronz88/rpc-project/Server%20application?label=python%20package&style=plastic)](https://github.com/doronz88/rpc-project/actions/workflows/server-app.yml "Server application action")
[![Python application](https://img.shields.io/github/workflow/status/doronz88/rpc-project/Python%20application?label=server%20build&style=plastic)](https://github.com/doronz88/rpc-project/actions/workflows/python-app.yml "Python application action")

# rpc-project

## Description

Simple RPC service providing an API for controlling every aspect of the target machine for automation purposes.

This project includes two components:

* Server binary written in C exposing a protocol to call native C functions.
* Client written in Python3 to communicate with the server

The python client utilizes the ability to call native functions in order to provide APIs for different aspects:

* Remote shell commands (`p.spawn()`)
* Filesystem management (`p.fs.*`)
* Network management (WiFi scan, TCP connect, etc...) (`p.network.*`)
* Darwin only:
  * Multimedia automation (recording and playing) (`p.media.*`)
  * Preferences managemnent (remote manage CFPreference and SCPreferences) (`p.preferences.*`)
  * Process management (kill, list, query open FDs, etc...) (`p.processes`)
  * Location services (`p.location.*`)
  * HID simulation (`p.hid.*`)
  * IORegistry API (`p.ioregistry.*`)
  * Reports management (Logs and Crash Reports) (`p.reports.*`)
  * Time settings (`p.time.*`)
  * iOS Only:
    * MobileGestalt (`p.mobile_gestalt.*`)
    * Backlight adjusting (`p.backlight.*`)

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

## Running

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
