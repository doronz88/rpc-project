#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <string.h>
#include <fcntl.h>
#include <errno.h>

#include "exec.h"
#include "builtin_cmds.h"
#include "common.h"
#include "shell.h"

extern char **environ;

#define MAX_READ_CHUNK (0x1000)

typedef int (*builtin_handle_t)(process *p, int infile, int outfile, int errfile);

int handle_builtin_help(process *p, int infile, int outfile, int errfile);
int handle_builtin_source(process *p, int infile, int outfile, int errfile);
int handle_builtin_cat(process *p, int infile, int outfile, int errfile);
int handle_builtin_echo(process *p, int infile, int outfile, int errfile);
int handle_builtin_pwd(process *p, int infile, int outfile, int errfile);
int handle_builtin_lasterror(process *p, int infile, int outfile, int errfile);
int handle_builtin_which(process *p, int infile, int outfile, int errfile);
int handle_builtin_cd(process *p, int infile, int outfile, int errfile);
int handle_builtin_exit(process *p, int infile, int outfile, int errfile);
int handle_builtin_jobs(process *p, int infile, int outfile, int errfile);
int handle_builtin_fg(process *p, int infile, int outfile, int errfile);
int handle_builtin_bg(process *p, int infile, int outfile, int errfile);
int handle_builtin_set(process *p, int infile, int outfile, int errfile);
int handle_builtin_export(process *p, int infile, int outfile, int errfile);

typedef struct
{
    char name[256];
    builtin_handle_t handler;
} builtin_cmd_t;

builtin_cmd_t builtin_cmds_list[] = {
    {"help", handle_builtin_help},
    {"source", handle_builtin_source},
    {"cat", handle_builtin_cat},
    {"echo", handle_builtin_echo},
    {"pwd", handle_builtin_pwd},
    {"lasterror", handle_builtin_lasterror},
    {"which", handle_builtin_which},
    {"cd", handle_builtin_cd},
    {"exit", handle_builtin_exit},
    {"jobs", handle_builtin_jobs},
    {"fg", handle_builtin_fg},
    {"bg", handle_builtin_bg},
    {"set", handle_builtin_set},
    {"export", handle_builtin_export}};

int builtin_cmds_launch(process *p, int infile, int outfile, int errfile)
{
    for (size_t i = 0; i < sizeof(builtin_cmds_list) / sizeof(builtin_cmds_list[0]); ++i)
    {
        if (0 == strcmp(p->argv[0], builtin_cmds_list[i].name))
        {
            return builtin_cmds_list[i].handler(p, infile, outfile, errfile);
        }
    }
    return EINVAL;
}

bool builtin_cmds_is_builtin(const char *executable)
{
    for (size_t i = 0; i < sizeof(builtin_cmds_list) / sizeof(builtin_cmds_list[0]); ++i)
    {
        if (0 == strcmp(builtin_cmds_list[i].name, executable))
        {
            return true;
        }
    }
    return false;
}

int handle_builtin_help(process *p, int infile, int outfile, int errfile)
{
    dprintf(outfile, "Builtin commands:\n");
    for (size_t i = 0; i < sizeof(builtin_cmds_list) / sizeof(builtin_cmds_list[0]); ++i)
    {
        dprintf(outfile, "- %s\n", builtin_cmds_list[i].name);
    }
    return 0;
}

int handle_builtin_source(process *p, int infile, int outfile, int errfile)
{
    FILE *f = NULL;
    
    f = fopen(p->argv[1], "rb");
    CHECK(NULL != f);
    
    shell_execute(f, false);

error:
    if (f)
    {
        fclose(f);
    }

    return errno;
}

int handle_builtin_cat(process *p, int infile, int outfile, int errfile)
{
    if (p->argv[1])
    {
        infile = open(p->argv[1], O_RDONLY);
        CHECK(infile >= 0);
    }
    char buf[MAX_READ_CHUNK];
    int result;
    do
    {
        result = read(infile, buf, sizeof(buf));
        if (result > 0)
        {
            write(outfile, buf, result);
        }
    } while (result > 0);
    return 0;

error:
    dprintf(errfile, "cat: failed to read\n");
    return errno;
}

int handle_builtin_echo(process *p, int infile, int outfile, int errfile)
{
    for (size_t i = 1; p->argv[i]; ++i)
    {
        dprintf(outfile, "%s ", p->argv[i]);
    }
    dprintf(outfile, "\n");
    return 0;
}

int handle_builtin_pwd(process *p, int infile, int outfile, int errfile)
{
    char curpath[PATH_MAX_LEN];
    getcwd(curpath, PATH_MAX_LEN);
    dprintf(outfile, "%s\n", curpath);
    return 0;
}

int handle_builtin_lasterror(process *p, int infile, int outfile, int errfile)
{
    int lasterror = exec_get_last_error();
    dprintf(outfile, "%d (%s)\n", lasterror, strerror(lasterror));
    return 0;
}

int handle_builtin_which(process *p, int infile, int outfile, int errfile)
{
    if (builtin_cmds_is_builtin(p->argv[1]))
    {
        dprintf(outfile, "%s: shell built-in command\n", p->argv[1]);
        return 0;
    }

    char *result = exec_which(p->argv[1]);
    if (result)
    {
        dprintf(outfile, "%s\n", result);
    }
    free(result);

    return 0;
}

int handle_builtin_cd(process *p, int infile, int outfile, int errfile)
{
    int err = 0;
    char *cd_path = NULL;
    if (!p->argv[1])
    {
        cd_path = strdup(getenv("HOME"));
    }
    else if (p->argv[1][0] == '~')
    {
        cd_path = malloc(strlen(getenv("HOME")) + strlen(p->argv[1]));
        strcpy(cd_path, getenv("HOME"));
        strncpy(cd_path + strlen(getenv("HOME")), p->argv[1] + 1, strlen(p->argv[1]));
    }
    else
    {
        cd_path = strdup(p->argv[1]);
    }
    err = chdir(cd_path);
    if (err < 0)
    {
        perror("cd");
    }
    free(cd_path);
    return err;
}

int handle_builtin_set(process *p, int infile, int outfile, int errfile)
{
    for (char **env = environ; *env != NULL; env++)
    {
        printf("%s\n", *env);
    }
    return 0;
}

int handle_builtin_export(process *p, int infile, int outfile, int errfile)
{
    if (setenv(p->argv[1], p->argv[2], 1))
    {
        fprintf(stderr, "setenv failed\n");
    }
    return 0;
}

int handle_builtin_exit(process *p, int infile, int outfile, int errfile)
{
    exec_update_status();
    exit(0);
}

int handle_builtin_jobs(process *p, int infile, int outfile, int errfile)
{
    if (p->argv[1])
    {
        int i;
        int id;
        job *j;
        for (i = 1; p->argv[i]; ++i)
        {
            id = atoi(p->argv[i]);
            j = exec_find_job_id(id);
            if (j)
            {
                if (!exec_job_is_completed(j))
                {
                    if (exec_job_is_stopped(j))
                    {
                        dprintf(outfile, "[%d] %ld Stopped\n", j->id, (long)j->pgid);
                    }
                    else
                    {
                        dprintf(outfile, "[%d] %ld Running\n", j->id, (long)j->pgid);
                    }
                }
                else
                    dprintf(errfile, "jobs: %s : no such job\n", p->argv[i]);
            }
            else
                dprintf(errfile, "jobs: %s : no such job\n", p->argv[i]);
        }
        return 0;
    }
    job *j;
    /* Update status information for child processes.  */
    exec_update_status();

    for (j = exec_first_job; j; j = j->next)
    {
        if (!exec_job_is_completed(j) && j->id)
        {
            if (exec_job_is_stopped(j))
            {
                dprintf(outfile, "[%d] %ld Stopped\n", j->id, (long)j->pgid);
            }
            else
            {
                dprintf(outfile, "[%d] %ld Running\n", j->id, (long)j->pgid);
            }
        }
    }

    return 0;
}

int handle_builtin_fg(process *p, int infile, int outfile, int errfile)
{
    if (p->argv[1])
    {
        int i;
        int id;
        job *j;
        for (i = 1; p->argv[i]; ++i)
        {
            id = atoi(p->argv[i]);
            j = exec_find_job_id(id);
            if (j)
            {
                if (!exec_job_is_completed(j) && exec_job_is_stopped(j))
                    exec_continue_job(j, 1);
                else
                    dprintf(errfile, "fg: %s : no such job\n", p->argv[i]);
            }
            else
                dprintf(errfile, "fg: %s : no such job\n", p->argv[i]);
        }
        return 0;
    }
    job *j;
    job *jlast = NULL;
    /* Update status information for child processes.  */
    exec_update_status();

    for (j = exec_first_job; j; j = j->next)
    {
        if (!exec_job_is_completed(j) && j->id)
        {
            if (exec_job_is_stopped(j))
            {
                jlast = j;
            }
        }
    }

    if (jlast)
    {
        exec_continue_job(jlast, 1);
    }
    else
    {
        dprintf(errfile, "fg: current: no such job\n");
    }

    return 0;
}

int handle_builtin_bg(process *p, int infile, int outfile, int errfile)
{
    if (p->argv[1])
    {
        int i;
        int id;
        job *j;
        for (i = 1; p->argv[i]; ++i)
        {
            id = atoi(p->argv[i]);
            j = exec_find_job_id(id);
            if (j)
            {
                if (!exec_job_is_completed(j) && exec_job_is_stopped(j))
                    exec_continue_job(j, 0);
                else
                    dprintf(errfile, "bg: %s : no such job\n", p->argv[i]);
            }
            else
                dprintf(errfile, "bg: %s : no such job\n", p->argv[i]);
        }
        return 0;
    }
    job *j;
    job *jlast = NULL;
    /* Update status information for child processes.  */
    exec_update_status();

    for (j = exec_first_job; j; j = j->next)
    {
        if (!exec_job_is_completed(j) && j->id)
        {
            if (exec_job_is_stopped(j))
            {
                jlast = j;
            }
        }
    }

    if (jlast)
    {
        exec_continue_job(jlast, 0);
    }
    else
    {
        dprintf(errfile, "bg: current: no such job\n");
    }

    return 0;
}
