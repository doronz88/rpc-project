#ifndef _SHELL_H
#define _SHELL_H

#include <stdio.h>
#include <stdbool.h>

void shell_init();
int shell_execute(FILE *in, bool interactive);

#endif // _SHELL_H