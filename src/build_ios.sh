#!/bin/sh

ARCH="arm64"
SDK="iphoneos"
SYSROOT="$(xcrun --sdk iphoneos --show-sdk-path)"
CC="$(xcrun -f --sdk $SDK clang)"
CFLAGS="-arch $ARCH --sysroot=$SYSROOT"

cd remote_server
make clean
make all SERVER_CC="$CC" SERVER_CFLAGS="$CFLAGS"

cd ..

cd basic_shell
make clean
make all CC="$CC" CFLAGS="$CFLAGS" LEMON_CC="gcc" LEMON_CFLAGS=""

cd ..

cp remote_server/server basic_shell/shell .

for i in server shell; do
    codesign -s - --entitlements ents.plist --generate-entitlement-der $i
done
