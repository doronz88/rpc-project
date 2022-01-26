#include <stdio.h>
#include <stdlib.h>
#include <sys/types.h>
#include <signal.h>
#include <unistd.h>
#include <limits.h>
#include <libgen.h>

#include "shellparser.h"
#include "shellscanner.h"
#include "exec.h"
#include "termios.h"
#include "common.h"

void *ParseAlloc(void *(*allocProc)(size_t));
void *Parse(void *, int, const char *, job *);
void *ParseFree(void *, void (*freeProc)(void *));

#define DEFAULT_PS1 ("[\\s@\\h \\b]\\$")
#define SHELL_NAME ("zShell")
#define USER_SUFFIX ("$")
#define ROOT_SUFFIX ("#")
#define HOST_NAME_MAX (256)

void print_prompt(void)
{
    char *ps1 = getenv("PS1");
    if (!ps1) {
        ps1 = DEFAULT_PS1;
    }

    char hostname[HOST_NAME_MAX + 1];
    CHECK(0 == gethostname(hostname, HOST_NAME_MAX + 1));

    char curpath[PATH_MAX_LEN];
    getcwd(curpath, PATH_MAX_LEN);

    char *resolved_prompt_old = NULL;
    char *resolved_prompt = NULL;
    
    resolved_prompt = str_replace(ps1, "\\s", SHELL_NAME);
    CHECK(resolved_prompt != NULL);

    resolved_prompt_old = resolved_prompt;
    resolved_prompt = str_replace(resolved_prompt_old, "\\h", hostname);
    free(resolved_prompt_old);
    resolved_prompt_old = NULL;
    CHECK(resolved_prompt != NULL);

    resolved_prompt_old = resolved_prompt;
    resolved_prompt = str_replace(resolved_prompt_old, "\\b", basename(curpath));
    free(resolved_prompt_old);
    resolved_prompt_old = NULL;
    CHECK(resolved_prompt != NULL);

    resolved_prompt_old = resolved_prompt;
    resolved_prompt = str_replace(resolved_prompt_old, "\\$", getuid() == 0 ? ROOT_SUFFIX : USER_SUFFIX);
    free(resolved_prompt_old);
    resolved_prompt_old = NULL;
    CHECK(resolved_prompt != NULL);

    printf("%s ", resolved_prompt);
    free(resolved_prompt);
    return;

error:
    if (resolved_prompt_old)
    {
        free(resolved_prompt_old);
    }
    if (resolved_prompt)
    {
        free(resolved_prompt);
    }
    printf("$ ");
}

void handle_signal(int signo)
{
    printf("\n");
    print_prompt();
    fflush(stdout);
}

void init_shell()
{
    /* See if we are running interactively.  */
    exec_shell_terminal = STDIN_FILENO;
    exec_shell_is_interactive = isatty(exec_shell_terminal);
    if (exec_shell_is_interactive)
    {
        // /* Loop until we are in the foreground.  */
        // while (tcgetpgrp(shell_terminal) != (shell_pgid = getpgrp()))
        //     kill(-shell_pgid, SIGTTIN);

        /* Ignore interactive and job-control signals.  */
        signal(SIGINT, handle_signal);
        signal(SIGQUIT, SIG_IGN);
        signal(SIGTSTP, SIG_IGN);
        signal(SIGTTIN, SIG_IGN);
        signal(SIGTTOU, SIG_IGN);
        // signal (SIGCHLD, SIG_IGN);

        /* Put ourselves in our own process group.  */
        exec_shell_pgid = getpid();
        if (setpgid(exec_shell_pgid, exec_shell_pgid) < 0)
        {
            perror("Couldn't put the shell in its own process group");
            exit(1);
        }

        /* Grab control of the terminal.  */
        tcsetpgrp(exec_shell_terminal, exec_shell_pgid);

        /* Save default terminal attributes for shell.  */
        tcgetattr(exec_shell_terminal, &exec_shell_tmodes);
    }
}

int parse_commands(yyscan_t scanner, job *j)
{
    // Set up the parser
    void *shellParser = ParseAlloc(malloc);

    int lexCode;
    do
    {
        lexCode = yylex(scanner);
        Parse(shellParser, lexCode, strdup(yyget_text(scanner)), j);
        if (lexCode == EOL)
        {
            Parse(shellParser, 0, NULL, j);
            break;
        }
    } while (lexCode > 0);

    // Cleanup the parser
    ParseFree(shellParser, free);

    if (-1 == lexCode)
    {
        fprintf(stderr, "The scanner encountered an error.\n");
        return -1;
    }
    else if (0 == lexCode)
        return 0;
    return 1;
}

int main(int argc, char **argv)
{
    init_shell();

    int flag;

    // Set up the scanner
    yyscan_t scanner;
    yylex_init(&scanner);
    yyset_in(stdin, scanner);

    int id = 1;

    do
    {
        print_prompt();
        job *j = exec_create_job();
        flag = parse_commands(scanner, j);
        if (j->valid > 0)
        {
            if (exec_first_job)
            {
                job *t;
                for (t = exec_first_job; t->next; t = t->next)
                    ;
                t->next = j;
            }
            else
            {
                exec_first_job = j;
            }
            exec_launch_job(j, j->foreground, &id);
            exec_do_job_notification();
        }
        else if (j->valid < 0)
        {
            exec_do_job_notification();
        }
        else
        {
            (exec_free_job(j));
        }
    } while (flag == 1);

    yylex_destroy(scanner);
    return 0;
}
