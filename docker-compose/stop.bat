@echo off
setlocal enabledelayedexpansion

REM Stop the containers
docker-compose stop

REM Remove the stopped containers
docker-compose rm -f

echo Containers have been stopped and removed.

set GENERIC_WINDOW_TITLE=Cluster_Container

echo Stopping all PowerShell processes with the window title: %GENERIC_WINDOW_TITLE%*

for /F "tokens=*" %%A in ('tasklist /FI "IMAGENAME eq powershell.exe" /V /FO LIST ^| findstr /I "!GENERIC_WINDOW_TITLE!"') do (
    echo Task %%A
)

echo Terminating all PowerShell processes with the window title: %GENERIC_WINDOW_TITLE%*
taskkill /FI "WINDOWTITLE eq !GENERIC_WINDOW_TITLE!*" /T /F >nul 2>&1

echo Done.
