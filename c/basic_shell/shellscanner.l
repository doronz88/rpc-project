%{
    #include "shellparser.h"
    #include "string.h"
%}

%option reentrant
%option noyywrap

%x SINGLE_QUOTED
%x SINGLE_QUOTED_END
%x DOUBLE_QUOTED
%x DOUBLE_QUOTED_END

%%

"|"                     { return PIPE; }
"\<"						{ return LEFT; }
"\>"						{ return RIGHT; }
"&"						{ return AND; }

[ \t\r]                 { }
[\n]                    { return EOL; }

[^ \t\r\n|\<\>'"&]+       { return ARGUMENT; }

[']                     { BEGIN(SINGLE_QUOTED); }
<SINGLE_QUOTED>[^']+    { yymore(); }
<SINGLE_QUOTED>[']      { BEGIN(SINGLE_QUOTED_END); yyless(yyleng-1); return ARGUMENT;}
<SINGLE_QUOTED_END>[']  { BEGIN(INITIAL);}
<SINGLE_QUOTED><<EOF>>  { return -1; }

["]                     { BEGIN(DOUBLE_QUOTED); }
<DOUBLE_QUOTED>[^"]+    { yymore(); }
<DOUBLE_QUOTED>["]      { BEGIN(DOUBLE_QUOTED_END); yyless(yyleng-1); return ARGUMENT; }
<DOUBLE_QUOTED_END>["]  { BEGIN(INITIAL);}
<DOUBLE_QUOTED><<EOF>>  { return -1; }

%%
