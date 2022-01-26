#ifndef _EXEC_H
#define _EXEC_H

#include <termios.h>
#include <stdbool.h>

#define MAX_ARG_COUNT (256)

/* A process is a single process.  */
typedef struct process
{
  struct process *next; /* next process in pipeline */
  char **argv;          /* for exec */
  pid_t pid;            /* process ID */
  char completed;       /* true if process has completed */
  char stopped;         /* true if process has stopped */
  int status;           /* reported status value */
} process;

/* A job is a pipeline of processes.  */
typedef struct job
{
  struct job *next; /* next active job */
  int id;           /* id of the process; 0 if is build in */
  int valid;
  process *first_process; /* list of processes in this job */
  pid_t pgid;             /* process group ID */
  char notified;          /* true if user told about stopped job */
  struct termios tmodes;  /* saved terminal modes */
  char *infile;
  char *outfile;
  int stdin, stdout, stderr; /* standard i/o channels */
  int foreground;
} job;

pid_t exec_shell_pgid;
struct termios exec_shell_tmodes;
int exec_shell_terminal;
int exec_shell_is_interactive;

/* The active jobs are linked into a list.  This is its head.   */
job *exec_first_job;
int exec_last_job_status;

process *exec_create_process();
job *exec_create_job();
void exec_free_job(job *);
void exec_launch_job(job *j, int foreground, int *id);
void exec_do_job_notification(void);
void exec_update_status(void);
job *exec_find_job_id(int id);
bool exec_job_is_stopped(job *j);
bool exec_job_is_completed(job *j);
void exec_continue_job(job *j, int foreground);
char *exec_which(char *executable);
int exec_get_last_error();

#endif // _EXEC_H