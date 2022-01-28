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
