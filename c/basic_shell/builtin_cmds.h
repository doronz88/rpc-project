#ifndef _BUILTIN_CMDS_H
#define _BUILTIN_CMDS_H

#include <stdbool.h>

#include "exec.h"

void builtin_cmds_launch(process *p, int infile, int outfile, int errfile);
bool builtin_cmds_is_builtin(process *p);

#endif // _BUILTIN_CMDS_H