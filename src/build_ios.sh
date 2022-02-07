#!/bin/sh

ARCH="arm64"
SDK="iphoneos"
SYSROOT="$(xcrun --sdk iphoneos --show-sdk-path)"
CC="$(xcrun -f --sdk $SDK clang)"
CFLAGS="-arch $ARCH --sysroot=$SYSROOT"

cd rpcserver
make clean
make all SERVER_CC="$CC" SERVER_CFLAGS="$CFLAGS"

cd ..

server_binary=rpcserver_${SDK}_${ARCH}
cp rpcserver/rpcserver $server_binary

for i in $server_binary ; do
    codesign -s - --entitlements ents.plist --generate-entitlement-der $i
done
