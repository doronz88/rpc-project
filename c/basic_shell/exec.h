#include <termios.h>

#define ARG_MAX 256


/* A process is a single process.  */
typedef struct process
{
  struct process *next;       /* next process in pipeline */
  char **argv;                /* for exec */
  pid_t pid;                  /* process ID */
  char completed;             /* true if process has completed */
  char stopped;               /* true if process has stopped */
  int status;                 /* reported status value */
} process;
/* A job is a pipeline of processes.  */
typedef struct job
{
  struct job *next;           /* next active job */
  int id;				  	  /* id of the process; 0 if is build in */
  int valid;
  process *first_process;     /* list of processes in this job */
  pid_t pgid;                 /* process group ID */
  char notified;              /* true if user told about stopped job */
  struct termios tmodes;      /* saved terminal modes */
  char* infile;
  char* outfile;
  int stdin, stdout, stderr;  /* standard i/o channels */
  int foreground;
} job;

void print_process (process*);

process* create_process ();

job* create_job ();

void free_job (job*);

void free_process (process*);

void print_job (job*);

pid_t launch_process (process *p, pid_t pgid,
                int infile, int outfile, int errfile,
                int foreground);


void launch_job (job *j, int foreground, int* id);

void do_job_notification (void);