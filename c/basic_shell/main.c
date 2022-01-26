#include <stdio.h>
#include "shell.h"

int main(int argc, char **argv)
{
    printf("1\n");
    shell_init();
    printf("2\n");
    return shell_execute(stdin, true);
}
