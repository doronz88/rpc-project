#!/bin/sh

NC='\033[0m' # No Color
RED='\033[0;31m'
GREEN='\033[0;32m'

for i in iphoneos,arm64 macosx,x86_64 macosx,arm64
do
    IFS=","
    set -- $i;

    echo "${GREEN}Building $1:$2 ${NC}"
    
    SDK="$1"
    ARCH="$2"
    SYSROOT="$(xcrun --sdk $SDK --show-sdk-path)"
    CC="$(xcrun -f --sdk $SDK clang)"
    CFLAGS="-arch $ARCH --sysroot=$SYSROOT -DSAFE_READ_WRITES"

    if test "$SDK" = 'iphoneos'; then
        CFLAGS="$CFLAGS -miphoneos-version-min=5.0"
    fi

    make clean
    make all SERVER_CC="$CC" SERVER_CFLAGS="$CFLAGS"

    server_binary=rpcserver_${SDK}_${ARCH}
    cp rpcserver $server_binary

    if test "$SDK" = 'iphoneos'; then
        codesign -s - --entitlements ents.plist --generate-entitlement-der $server_binary
    fi
done

# clean old binaries
make clean
