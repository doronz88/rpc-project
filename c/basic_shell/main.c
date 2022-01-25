#include <stdio.h>
#include <stdlib.h>
#include "shellparser.h"
#include "shellscanner.h"
#include <sys/types.h>
#include <signal.h>
#include "exec.h"
#include <pwd.h>
#include "termios.h"

#define MAX_NAME_LEN 256
#define MAX_PATH_LEN 1024

pid_t shell_pgid;
struct termios shell_tmodes;
int shell_terminal;
int shell_is_interactive;

char *buildin[256] = {"cd", "quit", "exit", "jobs", "fg", "bg"};

/* The active jobs are linked into a list.  This is its head.   */
job *first_job = NULL;

void *ParseAlloc(void *(*allocProc)(size_t));
void *Parse(void *, int, const char *, job *);
void *ParseFree(void *, void (*freeProc)(void *));

void type_prompt(void)
{
    char path[MAX_PATH_LEN];
    getcwd(path, MAX_PATH_LEN);
    int i, ilast;
    for (i = 0; i < MAX_PATH_LEN && path[i]; ++i)
    {
        if (path[i] == '/')
            ilast = i;
    }
    // printf("%s $shell: ", path + ilast + 1);
    printf("$ ");
}

void handle_signal(int signo)
{
    printf("\n");
    type_prompt();
    fflush(stdout);
}

void init_shell()
{

    /* See if we are running interactively.  */
    shell_terminal = STDIN_FILENO;
    shell_is_interactive = isatty(shell_terminal);
    if (shell_is_interactive)
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
        shell_pgid = getpid();
        if (setpgid(shell_pgid, shell_pgid) < 0)
        {
            perror("Couldn't put the shell in its own process group");
            exit(1);
        }

        /* Grab control of the terminal.  */
        tcsetpgrp(shell_terminal, shell_pgid);

        /* Save default terminal attributes for shell.  */
        tcgetattr(shell_terminal, &shell_tmodes);
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
        type_prompt();
        job *j = create_job();
        flag = parse_commands(scanner, j);
        if (j->valid > 0)
        {
            if (first_job)
            {
                job *t;
                for (t = first_job; t->next; t = t->next)
                    ;
                t->next = j;
            }
            else
                first_job = j;
            launch_job(j, j->foreground, &id);
            do_job_notification();
            // print_job(first_job);
        }
        else if (j->valid < 0)
        {
            do_job_notification();
        }
        else
            (free_job(j));
    } while (flag == 1);

    yylex_destroy(scanner);
    return 0;
}
