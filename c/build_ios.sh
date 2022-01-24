#!/bin/sh

ARCH="arm64"
SDK="iphoneos"
SYSROOT="$(xcrun --sdk iphoneos --show-sdk-path)"
CC="$(xcrun -f --sdk $SDK clang)"
CFLAGS="-arch $ARCH --sysroot=$SYSROOT"

export CC CFLAGS

make clean
make all CC="$CC" CFLAGS="$CFLAGS"

for i in client server; do
    codesign -s - --generate-entitlement-der $i
done
