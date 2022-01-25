#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <string.h>

#include "exec.h"
#include "builtin_cmds.h"
#include "common.h"

extern char **environ;

extern pid_t shell_pgid;
extern struct termios shell_tmodes;
extern int shell_terminal;
extern int shell_is_interactive;
extern char *builtin[];
extern job *first_job;

typedef void (*builtin_handle_t)(process *p, int infile, int outfile, int errfile);

void handle_builtin_which(process *p, int infile, int outfile, int errfile);
void handle_builtin_cd(process *p, int infile, int outfile, int errfile);
void handle_builtin_exit(process *p, int infile, int outfile, int errfile);
void handle_builtin_jobs(process *p, int infile, int outfile, int errfile);
void handle_builtin_fg(process *p, int infile, int outfile, int errfile);
void handle_builtin_bg(process *p, int infile, int outfile, int errfile);
void handle_builtin_set(process *p, int infile, int outfile, int errfile);
void handle_builtin_export(process *p, int infile, int outfile, int errfile);

typedef struct
{
    char name[256];
    builtin_handle_t handler;
} builtin_cmd_t;

builtin_cmd_t builtin_cmds_list[] = {
    {"which", handle_builtin_which},
    {"cd", handle_builtin_cd},
    {"exit", handle_builtin_exit},
    {"jobs", handle_builtin_jobs},
    {"fg", handle_builtin_fg},
    {"bg", handle_builtin_bg},
    {"set", handle_builtin_set},
    {"export", handle_builtin_export}};

void builtin_cmds_launch(process *p, int infile, int outfile, int errfile)
{
    for (size_t i = 0; i < sizeof(builtin_cmds_list) / sizeof(builtin_cmds_list[0]); ++i)
    {
        if (0 == strcmp(p->argv[0], builtin_cmds_list[i].name))
        {
            builtin_cmds_list[i].handler(p, infile, outfile, errfile);
            break;
        }
    }
}

bool builtin_cmds_is_builtin(process *p)
{
    for (size_t i = 0; i < sizeof(builtin_cmds_list) / sizeof(builtin_cmds_list[0]); ++i)
    {
        if (0 == strcmp(builtin_cmds_list[i].name, p->argv[0]))
        {
            return true;
        }
    }
    return false;
}

void handle_builtin_which(process *p, int infile, int outfile, int errfile)
{
    char *result = exec_which(p->argv[1]);
    if (result)
    {
        puts(result);
    }
}

void handle_builtin_cd(process *p, int infile, int outfile, int errfile)
{
    char *cd_path = NULL;
    if (!p->argv[1])
        cd_path = strdup(getenv("HOME"));
    else if (p->argv[1][0] == '~')
    {
        cd_path = malloc(strlen(getenv("HOME")) + strlen(p->argv[1]));
        strcpy(cd_path, getenv("HOME"));
        strncpy(cd_path + strlen(getenv("HOME")), p->argv[1] + 1, strlen(p->argv[1]));
    }
    else
        cd_path = strdup(p->argv[1]);
    if (chdir(cd_path) < 0)
        perror("cd:");
    free(cd_path);
}

void handle_builtin_set(process *p, int infile, int outfile, int errfile)
{
    for (char **env = environ; *env != NULL; env++)
    {
        printf("%s\n", *env);
    }
}

void handle_builtin_export(process *p, int infile, int outfile, int errfile)
{
    if (setenv(p->argv[1], p->argv[2], 1))
    {
        fprintf(stderr, "setenv failed\n");
    }
}

void handle_builtin_exit(process *p, int infile, int outfile, int errfile)
{
    update_status();
    exit(0);
}

void handle_builtin_jobs(process *p, int infile, int outfile, int errfile)
{
    if (p->argv[1])
    {
        int i;
        int id;
        job *j;
        for (i = 1; p->argv[i]; ++i)
        {
            id = atoi(p->argv[i]);
            j = find_job_id(id);
            if (j)
            {
                if (!job_is_completed(j))
                {
                    if (job_is_stopped(j))
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
        return;
    }
    job *j;
    /* Update status information for child processes.  */
    update_status();

    for (j = first_job; j; j = j->next)
    {
        if (!job_is_completed(j) && j->id)
        {
            if (job_is_stopped(j))
            {
                dprintf(outfile, "[%d] %ld Stopped\n", j->id, (long)j->pgid);
            }
            else
            {
                dprintf(outfile, "[%d] %ld Running\n", j->id, (long)j->pgid);
            }
        }
    }
}

void handle_builtin_fg(process *p, int infile, int outfile, int errfile)
{
    if (p->argv[1])
    {
        int i;
        int id;
        job *j;
        for (i = 1; p->argv[i]; ++i)
        {
            id = atoi(p->argv[i]);
            j = find_job_id(id);
            if (j)
            {
                if (!job_is_completed(j) && job_is_stopped(j))
                    continue_job(j, 1);
                else
                    dprintf(errfile, "fg: %s : no such job\n", p->argv[i]);
            }
            else
                dprintf(errfile, "fg: %s : no such job\n", p->argv[i]);
        }
        return;
    }
    job *j;
    job *jlast = NULL;
    /* Update status information for child processes.  */
    update_status();

    for (j = first_job; j; j = j->next)
    {
        if (!job_is_completed(j) && j->id)
        {
            if (job_is_stopped(j))
            {
                jlast = j;
            }
        }
    }

    if (jlast)
        continue_job(jlast, 1);
    else
        dprintf(errfile, "fg: current: no such job\n");
}

void handle_builtin_bg(process *p, int infile, int outfile, int errfile)
{
    if (p->argv[1])
    {
        int i;
        int id;
        job *j;
        for (i = 1; p->argv[i]; ++i)
        {
            id = atoi(p->argv[i]);
            j = find_job_id(id);
            if (j)
            {
                if (!job_is_completed(j) && job_is_stopped(j))
                    continue_job(j, 0);
                else
                    dprintf(errfile, "bg: %s : no such job\n", p->argv[i]);
            }
            else
                dprintf(errfile, "bg: %s : no such job\n", p->argv[i]);
        }
        return;
    }
    job *j;
    job *jlast = NULL;
    /* Update status information for child processes.  */
    update_status();

    for (j = first_job; j; j = j->next)
    {
        if (!job_is_completed(j) && j->id)
        {
            if (job_is_stopped(j))
            {
                jlast = j;
            }
        }
    }

    if (jlast)
        continue_job(jlast, 0);
    else
        dprintf(errfile, "bg: current: no such job\n");
}
