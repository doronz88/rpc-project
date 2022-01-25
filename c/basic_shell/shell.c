#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

int main(int argc, char **argv, char **envp)
{
  char **s = {"echo", "helloworld", NULL};
  execve("/bin/echo", s);
  return 0;
}
