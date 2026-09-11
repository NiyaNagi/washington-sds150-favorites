@echo off
rem Update every radio: double-click this file.
rem
rem Opens the wasds150 web UI on the Fleet tab, using this repository's own
rem working home (.wasds150-home), where the refreshed catalog and the
rem RadioReference exports live. Press "Update selected" and answer each
rem checklist step. Close this window (or press Ctrl+C) when you are done.
rem See docs\fleet-updates.md.

cd /d "%~dp0"
if not exist ".venv\Scripts\wasds150.exe" (
    echo The Python environment is missing. From this folder run:
    echo     python -m venv .venv
    echo     .venv\Scripts\python.exe -m pip install -e .
    pause
    exit /b 1
)
".venv\Scripts\wasds150.exe" --home ".wasds150-home" ui --tab fleet
if errorlevel 1 pause
