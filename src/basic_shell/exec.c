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
#include "builtin_cmds.h"

#define ENV_VAR_PREFIX ('$')

extern char **environ;

int exec_last_job_status = 0;
job *exec_first_job = NULL;

pid_t launch_process(process *p, pid_t pgid,
					 int infile, int outfile, int errfile,
					 int foreground);

void print_job(job *);
void free_process(process *);
void print_process(process *);

void print_process(process *p)
{
	int i;
	for (i = 0; p->argv[i]; ++i)
	{
		printf("argv%d: %s\n", i, p->argv[i]);
	}
}

process *exec_create_process(void)
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

job *exec_create_job()
{
	job *j = malloc(sizeof(job));
	if (!j)
	{
		perror("malloc");
		return NULL;
	}
	j->next = NULL;
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
	for (int i = 0; p->argv[i] && i < MAX_ARG_COUNT; ++i)
	{
		free(p->argv[i]);
	}
	free(p->argv);
}

void exec_free_job(job *j)
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

	for (j = exec_first_job; j; j = j->next)
		if (j->pgid == pgid)
			return j;
	return NULL;
}

job *exec_find_job_id(int id)
{
	if (id < 1)
		return NULL;
	job *j;
	for (j = exec_first_job; j; j = j->next)
		if (j->id == id)
			return j;
	return NULL;
}

/* Return true if all processes in the job have stopped or completed.  */
bool exec_job_is_stopped(job *j)
{
	process *p;

	for (p = j->first_process; p; p = p->next)
	{
		if (!p->completed && !p->stopped)
		{
			return false;
		}
	}
	return true;
}

/* Return true if all processes in the job have completed.  */
bool exec_job_is_completed(job *j)
{
	process *p;

	for (p = j->first_process; p; p = p->next)
	{
		if (!p->completed)
		{
			return false;
		}
	}
	return true;
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
	{
		printf("infile: %s\n", j->infile);
	}
	if (j->outfile)
	{
		printf("outfile: %s\n", j->outfile);
	}
	for (p = j->first_process; p; p = p->next)
	{
		printf("pro%d\n", i);
		print_process(p);
		i = i + 1;
	}
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
		for (j = exec_first_job; j; j = j->next)
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

void exec_update_status(void)
{
	int status;
	pid_t pid;

	do
	{
		pid = waitpid(WAIT_ANY, &status, WUNTRACED | WNOHANG);
	} while (!mark_process_status(pid, status));
}

char **get_splitted_path()
{
	size_t i;
	char **result = NULL;
	char *path = getenv("PATH");
	CHECK(path != NULL);

	// count the number of ':' in the PATH env var
	size_t components = 1;
	for (i = 0; i < strlen(path); ++i)
	{
		if (path[i] == ':')
		{
			++components;
		}
	}

	// allocate a place to store all paths (+1 extra for NULL)
	size_t result_size = sizeof(char *) * (components + 1);
	result = (char **)malloc(result_size);
	CHECK(result != NULL);
	memset(result, 0, result_size);

	// store each path
	i = 0;
	char *next;

	for (i = 0; i < components - 1; ++i)
	{
		next = strchr(path, ':');
		if (next == NULL)
		{
			break;
		}

		result[i] = malloc(sizeof(char) * (next - path + 1));
		result[i][next - path] = '\0';
		CHECK(result[i] != NULL);
		strncpy(result[i], path, next - path);
		path = next + 1;
	}

	result[i] = malloc(sizeof(char) * strlen(path));
	strcpy(result[i], path);

	return result;

error:
	if (result)
	{
		while (*result)
		{
			free(*result);
			++result;
		}
		free(result);
	}

	return NULL;
}

char *exec_which(char *executable)
{
	size_t i = 0;
	char *result = NULL;
	char **paths = NULL;

	paths = get_splitted_path();
	CHECK(paths != NULL);

	while (paths[i])
	{
		char fullpath[1024];
		sprintf(fullpath, "%s/%s", paths[i], executable);
		if (0 == access(fullpath, O_RDONLY))
		{
			result = malloc(sizeof(char) * (strlen(fullpath) + 1));
			CHECK(result != NULL);
			strcpy(result, fullpath);
			break;
		}
		++i;
	}

error:
	if (paths)
	{
		i = 0;
		while (paths[i])
		{
			free(paths[i]);
			++i;
		}
		free(paths);
	}

	return result;
}

bool is_path(char *executable)
{
	return strchr(executable, '/') != NULL;
}

int exec_get_last_error()
{
	char *last_error_str = getenv("?");
	if (NULL == last_error_str)
	{
		return 0;
	}
	int lasterror = atoi(last_error_str);
	return lasterror;
}

pid_t launch_process(process *p, pid_t pgid,
					 int infile, int outfile, int errfile,
					 int foreground)
{
	char *fullpath = NULL;
	pid_t pid = 0;

	posix_spawn_file_actions_t actions;
	CHECK(0 == posix_spawn_file_actions_init(&actions));

	posix_spawnattr_t attr;
	CHECK(0 == posix_spawnattr_init(&attr));

	if (exec_shell_is_interactive)
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

	char *executable = p->argv[0];

	if (is_path(executable))
	{
		if (0 != access(executable, O_RDONLY))
		{
			fprintf(stderr, "%s: failed to access\n", executable);
		}
	}
	else
	{
		fullpath = exec_which(executable);
		if (!fullpath)
		{
			fprintf(stderr, "%s: not in path\n", executable);
			goto error;
		}
		executable = fullpath;
	}

	CHECK(0 == posix_spawnp(&pid, executable, &actions, &attr, p->argv, environ));

	if (foreground)
	{
		CHECK(0 == tcsetpgrp(exec_shell_terminal, pgid));
	}

error:
	if (fullpath)
	{
		free(fullpath);
	}

	return pid;
}

void set_last_error(int error)
{
	char status_str[256];
	sprintf(status_str, "%d", error);
	setenv("?", status_str, 1);
}

/* Check for processes that have status information available,
   blocking until all processes in the given job have reported.  */
void wait_for_job(job *j)
{
	int status;
	pid_t pid;

	do
	{
		pid = waitpid(-j->pgid, &status, WUNTRACED);
		set_last_error(status);
	} while (!mark_process_status(pid, status) && !exec_job_is_stopped(j) && !exec_job_is_completed(j));
}

/* Format information about job status for the user to look at.  */
void format_job_info(job *j, const char *status)
{
	fprintf(stderr, "[%d] %ld %s\n", j->id, (long)j->pgid, status);
}

/* Notify the user about stopped or terminated jobs.
   Delete terminated jobs from the active job list.  */
void exec_do_job_notification(void)
{
	job *j = NULL;
	job *jlast = NULL;
	job *jnext = NULL;

	/* Update status information for child processes.  */
	exec_update_status();

	jlast = NULL;
	for (j = exec_first_job; j; j = jnext)
	{
		jnext = j->next;

		/* If all processes have completed, tell the user the job has
		completed and delete it from the list of active jobs.  */
		if (exec_job_is_completed(j))
		{
			if (!j->foreground)
				format_job_info(j, "Done");
			if (jlast)
				jlast->next = jnext;
			else
				exec_first_job = jnext;
			exec_free_job(j);
		}

		/* Notify the user about stopped jobs,
		marking them so that we won’t do this more than once.  */
		else if (exec_job_is_stopped(j) && !j->notified)
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
	tcsetpgrp(exec_shell_terminal, j->pgid);
	/* Send the job a continue signal, if necessary.  */
	if (cont)
	{
		tcsetattr(exec_shell_terminal, TCSADRAIN, &j->tmodes);
		if (kill(-j->pgid, SIGCONT) < 0)
			perror("kill (SIGCONT)");
	}
	/* Wait for it to report.  */
	wait_for_job(j);

	/* Put the shell back in the foreground.  */
	tcsetpgrp(exec_shell_terminal, exec_shell_pgid);

	/* Restore the shell’s terminal modes.  */
	tcgetattr(exec_shell_terminal, &j->tmodes);
	tcsetattr(exec_shell_terminal, TCSADRAIN, &exec_shell_tmodes);
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
void exec_continue_job(job *j, int foreground)
{
	mark_job_as_running(j);
	if (foreground)
		put_job_in_foreground(j, 1);
	else
		put_job_in_background(j, 1);
}

void exec_launch_job(job *j, int foreground, int *id)
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
		{
			outfile = j->stdout;
		}
		if (builtin_cmds_is_builtin(p->argv[0]))
		{
			set_last_error(builtin_cmds_launch(p, infile, outfile, j->stderr));
			p->completed = 1;
		}
		else
		{
			pid = launch_process(p, j->pgid, infile,
								 outfile, j->stderr, foreground);

			if (pid)
			{
				p->pid = pid;
				if (exec_shell_is_interactive)
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

	if (!exec_shell_is_interactive)
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
