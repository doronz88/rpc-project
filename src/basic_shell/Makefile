CC = gcc
LEMON_CC = $(CC)
LEMON_CFLAGS = 

all: shell

shell: main.c exec.o shellparser.o shellscanner.o common.o builtin_cmds.o shell.o
	$(CC) $(CFLAGS) -o $@ $^

%.o: %.c
	$(CC) $(CFLAGS) -c $< -o $@

shellparser.o: shellparser.h shellparser.c exec.o

shellparser.h shellparser.c: shellparser.y exec.h lemon
	./lemon shellparser.y

shellscanner.o: shellscanner.h

shellscanner.h: shellscanner.l
	flex --outfile=shellscanner.c --header-file=shellscanner.h $<

# Prevent yacc from trying to build parsers.
# http://stackoverflow.com/a/5395195/79202
%.c: %.y

lemon: lemon.c
	$(LEMON_CC) $(LEMON_CFLAGS) -o $@ lemon.c

.PHONY: clean
clean:
	rm -f *.o
	rm -f shellscanner.c shellscanner.h
	rm -f shellparser.c shellparser.h shellparser.out
	rm -f shell lemon
