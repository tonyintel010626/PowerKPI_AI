@echo off
setlocal
rem param 1: log name
rem param 2: pdb directory

set ETL_FILE_NAME=%1
set PDB_DIR=%2
set MODE=%3

set OUTPUT_FILE_NAME=%ETL_FILE_NAME%.txt
set CURRENT_DIR=%cd%

pushd %PDB_DIR%
call %CURRENT_DIR%\tracepdb.exe %PDB_DIR%
move /y *.tmf %CURRENT_DIR%
move /y *.mof %CURRENT_DIR%
popd

set TRACE_FORMAT_PREFIX=[%%4!s!][%%!FLAGS!][%%!LEVEL!] 
if '%MODE%'=='detailed' set TRACE_FORMAT_PREFIX=[%%4!s!][%%9!d!:%%8!04X!:%%3!04X!][%%1!s!][%%2!s!][%%!FUNC!][%%!FLAGS!][%%!LEVEL!] 

call tracefmt.exe %ETL_FILE_NAME% -o %OUTPUT_FILE_NAME%
del /q *.tmf
del /q *.mof

endlocal
