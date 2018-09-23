@echo OFF

set CURPATH=%cd%
set BINPATH=%~dp0

cd "%BINPATH%\.."
call env\Scripts\activate
python -m leafytracker %*
cd "%CURPATH%"