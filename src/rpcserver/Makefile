SERVER_CC=gcc
LDFLAGS=
UNAME_S:=$(shell uname -s)
EXTRA_O_FILES=common.o

ifeq ($(UNAME_S),Darwin)
	LDFLAGS += -framework CoreFoundation -framework Foundation
	EXTRA_O_FILES += darwin_class.o darwin_object.o darwin_utils.o darwin_get_class_list.o
endif

all: rpcserver 

common.o: common.c
	$(SERVER_CC) $(SERVER_CFLAGS) -c common.c -o common.o

darwin_utils.o: darwin/darwin_utils.m
	$(SERVER_CC) $(SERVER_CFLAGS) darwin/darwin_utils.m -c -ObjC -o darwin_utils.o

darwin_class.o: darwin/darwin_class.m
	$(SERVER_CC) $(SERVER_CFLAGS) darwin/darwin_class.m -c -ObjC -o darwin_class.o

darwin_object.o: darwin/darwin_object.m
	$(SERVER_CC) $(SERVER_CFLAGS) darwin/darwin_object.m -c -ObjC -o darwin_object.o

darwin_get_class_list.o: darwin/darwin_get_class_list.m
	$(SERVER_CC) $(SERVER_CFLAGS) darwin/darwin_get_class_list.m -c -ObjC -o darwin_get_class_list.o

rpcserver: rpcserver.c $(EXTRA_O_FILES)
	$(SERVER_CC) $(SERVER_CFLAGS) $(LDFLAGS) -Wno-unguarded-availability-new rpcserver.c -lpthread -ldl $(EXTRA_O_FILES) -o rpcserver

clean:
	rm -rf *.o rpcserver
