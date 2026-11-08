@echo off
rem Atalho do Windows para o lancador (script bash): usa o Git Bash que o Claude Code ja exige.
setlocal
set "BASH_EXE=bash"
where bash >nul 2>nul || set "BASH_EXE=%ProgramFiles%\Git\bin\bash.exe"
set "AQUI=%~dp0"
"%BASH_EXE%" "%AQUI:\=/%vch" %*
exit /b %ERRORLEVEL%
