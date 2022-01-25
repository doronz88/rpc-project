# zShell

## Description

Inspired by [inSecure-SHell](https://github.com/fffaraz/inSecure-SHell), this shell's goal is to be the tinyest and simplest remote shell.
This project was optimized for macOS and iOS, but should work also for Linux.

## Building

```shell
git clone git@github.com:doronz88/zshell.git
cd c
./build_ios.sh
```

## Running

To execute the server:

```shell
./server [-p port] [-s shell]
```

Connecting via:

```shell
./client HOST
```
