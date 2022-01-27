#include <stdio.h>
#include "shell.h"

int main(int argc, char **argv)
{
    shell_init();
    return shell_execute(stdin, true);
}
