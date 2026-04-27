@echo off

setlocal

set CURRENT_TRACE_DIR=%1
set SCRIPTS_DIR=%2%

if exist "ParseTraceFiles" copy ParseTraceFiles\*.* /y %CURRENT_TRACE_DIR%

call %SCRIPTS_DIR%\GetVersions.bat %CURRENT_TRACE_DIR% %SCRIPTS_DIR%