%include {
#include <stdio.h>
#include <string.h>
#include <assert.h>
#include <stdlib.h>
#include "exec.h"
}

%token_type {char*}

%type argumentList {char**}

%destructor argumentList { free($$); }

%type command {process*}

%destructor command { free($$); }

%type commandList {process*}

%destructor commandList { free($$); }

%type argument {char*}

%extra_argument { job *j }

%syntax_error
{
    j->valid = 0;
    fprintf(stderr, "Error parsing command\n");
}

%stack_overflow 
{
    fprintf(stderr,"Giving up.  Parser stack overflow\n");
}

start ::= in .
in ::= .
{
    j->valid = 0;
}
in ::= EOL .
{
    j->valid = -1;
}
in ::= job EOL .
{
    j->foreground = 1;
}
in ::= job AND EOL .
{
    j->foreground = 0;
}
job ::= commandList(B) .
{
    j->first_process = B;
}

job ::= command(B) LEFT ARGUMENT(C) .
{   
    j->first_process = B;
    j->infile = C;
}

job ::= command(B) RIGHT ARGUMENT(C) .
{   
    j->first_process = B;
    j->outfile = C;
}

job ::= command(B) RIGHT ARGUMENT(C) LEFT ARGUMENT(D) .
{   
    j->first_process = B;
    j->infile = D;
    j->outfile = C;
}

job ::= command(B) LEFT ARGUMENT(C) RIGHT ARGUMENT(D) .
{   
    j->first_process = B;
    j->infile = C;
    j->outfile = D;
}
job ::= command(B) LEFT ARGUMENT(C) PIPE commandList(D) .
{   
    B->next = D;
    j->first_process = B;
    j->infile = C;
}

job ::= command(B) PIPE commandList(C) RIGHT ARGUMENT(D) .
{   
    B->next = C;
    j->first_process = B;
    j->outfile = D;
}


job ::= command(B) LEFT ARGUMENT(C) PIPE commandList(D) RIGHT ARGUMENT(E).
{   
    B->next = D;
    j->first_process = B;
    j->infile = C;
    j->outfile = E;
}


commandList(A) ::= command(B) PIPE commandList(C) .
{
    A = B;
    A->next = C;
}

commandList(A) ::= command(B) .
{
    A = B;
}

command(A) ::= argumentList(B) .
{
    //printf("command ::= FILENAME argumentList .\n");
    A = create_process();
    A->argv = B;
}

argumentList(A) ::= argumentList(C) argument(B) .
{
    //printf("argumentList ::= argument argumentList .\n");
    A = C;
    int i;
    for (i = 1; i < ARG_MAX-1; ++i)
    {
        if (A[i] == NULL)
        {
            A[i] = B;
            A[i+1] = NULL;
            break;
        }
    }
}
argumentList(A) ::= argument(B) .
{
    //printf("argumentList ::= argument .\n");
    A = malloc(ARG_MAX * sizeof(char*));
    A[0] = B;
    A[1] = NULL;
}
argument(A) ::= ARGUMENT(B) .
{
    //printf("argument ::= ARGUMENT .\n");
    A = B;
}


