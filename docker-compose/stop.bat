@echo off

REM Stop the containers
docker-compose stop

REM Remove the stopped containers
docker-compose rm -f

echo Containers have been stopped and removed.

REM Maybe cache the processes spawned by start_n_containers.bat and close them here?
@REM rem Get the Process ID (PID) of the current PowerShell instance
@REM for /f "tokens=2" %%I in ('powershell -Command "echo $PID"') do (
@REM     echo Result:
@REM )
@REM
@REM
@REM REM Get the PID of the current PowerShell or cmd.exe process
@REM for /f "tokens=2 delims=," %%a in ('"wmic process where (name='powershell.exe' or name='cmd.exe') get processid, parentprocessid /format:csv 2>nul"') do (
@REM     REM %%a contains the PID, %%b contains the Parent PID
@REM     set "current_pid=%%a"
@REM     set "parent_pid=%%b"
@REM     echo Parent PID: !parent_pid! and Current PID: !current_pid!
@REM )
@REM
@REM echo Current script is running with PID: %current_pid% and the parent process is running with PID: %parent_pid%
@REM
@REM REM List all powershell.exe processes
@REM for /f "tokens=2 delims=," %%a in ('"wmic process where name='powershell.exe' get processid, parentprocessid /format:csv 2>nul"') do (
@REM     REM %%a is PID of PowerShell, %%b is Parent PID
@REM     set "ps_pid=%%a"
@REM     set "ps_parent_pid=%%b"
@REM
@REM     REM If the PowerShell process is not the current script's instance (check Parent PID)
@REM     if not "%%a"=="%current_pid%" if not "%%b"=="%parent_pid%" (
@REM         echo Terminating PowerShell process with PID: %%a
@REM         taskkill /PID %%a /F >nul 2>&1
@REM         if %ERRORLEVEL% == 0 (
@REM             echo Successfully terminated PowerShell process with PID %%a
@REM         ) else (
@REM             echo Failed to terminate PowerShell process with PID %%a
@REM         )
@REM     )
@REM )
@REM
@REM echo All other PowerShell processes have been terminated.
