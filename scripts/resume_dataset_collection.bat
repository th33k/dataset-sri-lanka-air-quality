@echo off
cd /d "%~dp0\.."
echo ======================================================================
echo Resuming Sri Lanka DSD Air Quality Dataset Collection
echo ======================================================================
echo Current working directory: %CD%
echo.
python scripts\collect_srilanka_dsd_air_quality.py --start 2023-01-01
echo.
echo ======================================================================
echo Execution finished. Press any key to exit.
echo ======================================================================
pause
