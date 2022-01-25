#include <fcntl.h>
#include <unistd.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <errno.h>
#include <sys/types.h>
#include <signal.h>
#include <sys/wait.h>
#include <spawn.h>

#include "common.h"
#include "exec.h"

extern pid_t shell_pgid;
extern struct termios shell_tmodes;
extern int shell_terminal;
extern int shell_is_interactive;
extern char *buildin[];
extern job *first_job;

struct passwd *pwd;

void print_process(process *p)
{
	int i;
	for (i = 0; p->argv[i]; ++i)
	{
		printf("argv%d: %s\n", i, p->argv[i]);
	}
}

process *create_process(void)
{
	process *p = malloc(sizeof(process));
	if (!p)
	{
		perror("malloc");
		return NULL;
	}
	p->next = NULL;
	p->argv = NULL;
	p->completed = 0;
	p->stopped = 0;
	return p;
}

job *create_job()
{
	job *j = malloc(sizeof(job));
	if (!j)
	{
		perror("malloc");
		return NULL;
	}
	j->first_process = NULL;
	j->valid = 1;
	j->id = 0;
	j->infile = NULL;
	j->outfile = NULL;
	j->stdin = STDIN_FILENO;
	j->stdout = STDOUT_FILENO;
	j->stderr = STDERR_FILENO;
	j->foreground = 1;
	j->notified = 0;
	j->pgid = 0;
	return j;
}

void free_process(process *p)
{
	if (!p->argv)
		return;
	for (int i = 0; p->argv[i] && i < ARG_MAX; ++i)
	{
		free(p->argv[i]);
	}
	free(p->argv);
}

void free_job(job *j)
{
	if (!j)
		return;
	process *p = j->first_process;
	while (p)
	{
		process *tmp = p->next;
		free_process(p);
		p = tmp;
	}
	free(j->infile);
	free(j->outfile);
}

/* Find the active job with the indicated pgid.  */
job *find_job(pid_t pgid)
{
	job *j;

	for (j = first_job; j; j = j->next)
		if (j->pgid == pgid)
			return j;
	return NULL;
}

job *find_job_id(int id)
{
	if (id < 1)
		return NULL;
	job *j;
	for (j = first_job; j; j = j->next)
		if (j->id == id)
			return j;
	return NULL;
}

/* Return true if all processes in the job have stopped or completed.  */
int job_is_stopped(job *j)
{
	process *p;

	for (p = j->first_process; p; p = p->next)
		if (!p->completed && !p->stopped)
			return 0;
	return 1;
}

/* Return true if all processes in the job have completed.  */
int job_is_completed(job *j)
{
	process *p;

	for (p = j->first_process; p; p = p->next)
		if (!p->completed)
			return 0;
	return 1;
}

void print_job(job *j)
{
	if (!j->id)
	{
		fprintf(stderr, "parsing failed\n");
		return;
	}
	process *p;
	int i = 0;
	if (j->infile)
		printf("infile: %s\n", j->infile);
	if (j->outfile)
		printf("outfile: %s\n", j->outfile);
	for (p = j->first_process; p; p = p->next)
	{
		printf("pro%d\n", i);
		print_process(p);
		i = i + 1;
	}
}

int is_buildin(process *p)
{
	int i;
	for (i = 0; buildin[i]; ++i)
		if (strcmp(buildin[i], p->argv[0]) == 0)
			return 1;
	return 0;
}

/* Store the status of the process pid that was returned by waitpid.
   Return 0 if all went well, nonzero otherwise.  */

int mark_process_status(pid_t pid, int status)
{
	job *j;
	process *p;
	if (pid > 0)
	{
		/* Update the record for the process.  */
		for (j = first_job; j; j = j->next)
			for (p = j->first_process; p; p = p->next)
				if (p->pid == pid)
				{
					p->status = status;
					if (WIFSTOPPED(status))
						p->stopped = 1;
					else
					{
						p->completed = 1;
						if (WIFSIGNALED(status))
							fprintf(stderr, "%d: Terminated by signal %d.\n",
									(int)pid, WTERMSIG(p->status));
					}
					return 0;
				}
		fprintf(stderr, "No child process %d.\n", pid);
		return -1;
	}
	else if (pid == 0 || errno == ECHILD)
		/* No processes ready to report.  */
		return -1;
	else
	{
		/* Other weird errors.  */
		perror("waitpid");
		return -1;
	}
}

/* Check for processes that have status information available,
   without blocking.  */

void update_status(void)
{
	int status;
	pid_t pid;

	do
		pid = waitpid(WAIT_ANY, &status, WUNTRACED | WNOHANG);
	while (!mark_process_status(pid, status));
}

extern char **environ;

pid_t launch_process(process *p, pid_t pgid,
					 int infile, int outfile, int errfile,
					 int foreground)
{
	pid_t pid = 0;

	posix_spawn_file_actions_t actions;
	CHECK(0 == posix_spawn_file_actions_init(&actions));

	posix_spawnattr_t attr;
	CHECK(0 == posix_spawnattr_init(&attr));

	if (shell_is_interactive)
	{
		/* Put the process into the process group and give the process group
		 the terminal, if appropriate.
		 This has to be done both by the shell and in the individual
		 child processes because of potential race conditions.  */
		if (pgid == 0) 
		{
			pgid = pid;
		}
		
		CHECK(0 == posix_spawnattr_setpgroup(&attr, pgid));
		CHECK(0 == posix_spawnattr_setflags(&attr, POSIX_SPAWN_SETPGROUP));

		/* Set the handling for job control signals back to the default.  */
		sigset_t sigset[] = {SIGINT, SIGQUIT, SIGTSTP, SIGTTIN, SIGTTOU, SIGCHLD, 0};
		CHECK(0 == posix_spawnattr_setsigdefault(&attr, sigset));
	}

	/* Set the standard input/output channels of the new process.  */
	if (infile != STDIN_FILENO)
	{
		CHECK(0 == posix_spawn_file_actions_adddup2(&actions, infile, STDIN_FILENO));
	}
	if (outfile != STDOUT_FILENO)
	{
		CHECK(0 == posix_spawn_file_actions_adddup2(&actions, outfile, STDOUT_FILENO));
	}
	if (errfile != STDERR_FILENO)
	{
		CHECK(0 == posix_spawn_file_actions_adddup2(&actions, errfile, STDERR_FILENO));
	}

	/* Exec the new process.  Make sure we exit.  */
	CHECK(0 == posix_spawnp(&pid, p->argv[0], &actions, &attr, p->argv, environ));

	if (foreground)
	{
		CHECK(0 == tcsetpgrp(shell_terminal, pgid));
	}

error:
	return pid;
}

/* Check for processes that have status information available,
   blocking until all processes in the given job have reported.  */

void wait_for_job(job *j)
{
	int status;
	pid_t pid;

	do
		pid = waitpid(-j->pgid, &status, WUNTRACED);
	while (!mark_process_status(pid, status) && !job_is_stopped(j) && !job_is_completed(j));
}
/* Format information about job status for the user to look at.  */

void format_job_info(job *j, const char *status)
{
	fprintf(stderr, "[%d] %ld %s\n", j->id, (long)j->pgid, status);
}
/* Notify the user about stopped or terminated jobs.
   Delete terminated jobs from the active job list.  */

void do_job_notification(void)
{
	job *j, *jlast, *jnext;

	/* Update status information for child processes.  */
	update_status();

	jlast = NULL;
	for (j = first_job; j; j = jnext)
	{
		jnext = j->next;

		/* If all processes have completed, tell the user the job has
		completed and delete it from the list of active jobs.  */
		if (job_is_completed(j))
		{
			if (!j->foreground)
				format_job_info(j, "Done");
			if (jlast)
				jlast->next = jnext;
			else
				first_job = jnext;
			free_job(j);
		}

		/* Notify the user about stopped jobs,
		marking them so that we won’t do this more than once.  */
		else if (job_is_stopped(j) && !j->notified)
		{
			format_job_info(j, "Stopped");
			j->notified = 1;
			jlast = j;
		}

		/* Don’t say anything about jobs that are still running.  */
		else
			jlast = j;
	}
}

/* Put job j in the foreground.  If cont is nonzero,
   restore the saved terminal modes and send the process group a
   SIGCONT signal to wake it up before we block.  */

void put_job_in_foreground(job *j, int cont)
{
	j->foreground = 1;
	/* Put the job into the foreground.  */
	tcsetpgrp(shell_terminal, j->pgid);
	/* Send the job a continue signal, if necessary.  */
	if (cont)
	{
		tcsetattr(shell_terminal, TCSADRAIN, &j->tmodes);
		if (kill(-j->pgid, SIGCONT) < 0)
			perror("kill (SIGCONT)");
	}
	/* Wait for it to report.  */
	wait_for_job(j);

	/* Put the shell back in the foreground.  */
	tcsetpgrp(shell_terminal, shell_pgid);

	/* Restore the shell’s terminal modes.  */
	tcgetattr(shell_terminal, &j->tmodes);
	tcsetattr(shell_terminal, TCSADRAIN, &shell_tmodes);
}

/* Put a job in the background.  If the cont argument is true, send
   the process group a SIGCONT signal to wake it up.  */

void put_job_in_background(job *j, int cont)
{
	/* Send the job a continue signal, if necessary.  */
	j->foreground = 0;
	if (cont)
		if (kill(-j->pgid, SIGCONT) < 0)
			perror("kill (SIGCONT)");
}

/* Mark a stopped job J as being running again.  */

void mark_job_as_running(job *j)
{
	process *p;

	for (p = j->first_process; p; p = p->next)
		p->stopped = 0;
	j->notified = 0;
}
/* Continue the job J.  */

void continue_job(job *j, int foreground)
{
	mark_job_as_running(j);
	if (foreground)
		put_job_in_foreground(j, 1);
	else
		put_job_in_background(j, 1);
}

void lauch_buildin(process *p, int infile, int outfile, int errfile)
{
	/* Set the standard input/output channels of the new process.  */
	if (strcmp(p->argv[0], "cd") == 0)
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
	else if (strcmp(p->argv[0], "exit") == 0)
	{
		update_status();
		exit(0);
	}
	else if (strcmp(p->argv[0], "quit") == 0)
	{
		update_status();
		exit(0);
	}
	else if (strcmp(p->argv[0], "jobs") == 0)
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
	else if (strcmp(p->argv[0], "fg") == 0)
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
	else if (strcmp(p->argv[0], "bg") == 0)
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
}

void launch_job(job *j, int foreground, int *id)
{
	process *p;
	pid_t pid;
	int mypipe[2], infile, outfile;
	if (j->infile)
	{
		j->stdin = open(j->infile, O_RDONLY);
		if (j->stdin < 0)
		{
			perror(j->infile);
			exit(1);
		}
	}
	if (j->outfile)
	{
		j->stdout = open(j->outfile, O_WRONLY | O_CREAT | O_TRUNC, 0666);
		if (j->stdout < 0)
		{
			perror(j->outfile);
			exit(1);
		}
	}
	infile = j->stdin;
	for (p = j->first_process; p; p = p->next)
	{
		/* Set up pipes, if necessary.  */
		if (p->next)
		{
			if (pipe(mypipe) < 0)
			{
				perror("pipe");
				exit(1);
			}
			outfile = mypipe[1];
		}
		else
			outfile = j->stdout;
		if (is_buildin(p))
		{
			lauch_buildin(p, infile, outfile, j->stderr);
			p->completed = 1;
		}
		else
		{
			/* Fork the child processes.  */
			pid = launch_process(p, j->pgid, infile,
								 outfile, j->stderr, foreground);
			/* This is the parent process.  */
			p->pid = pid;
			if (shell_is_interactive)
			{
				if (!j->pgid)
				{
					j->pgid = pid;
					j->id = *id;
					*id = *id + 1;
				}
				setpgid(pid, j->pgid);
			}
		}
		/* Clean up after pipes.  */
		if (infile != j->stdin)
		{
			close(infile);
		}
		if (outfile != j->stdout)
		{
			close(outfile);
		}
		infile = mypipe[0];
	}

	if (!shell_is_interactive)
	{
		wait_for_job(j);
	}
	else if (foreground)
	{
		put_job_in_foreground(j, 0);
	}
	else
	{
		put_job_in_background(j, 0);
		format_job_info(j, "backgroud");
	}
}
