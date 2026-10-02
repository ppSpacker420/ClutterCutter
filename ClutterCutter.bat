@echo off
REM ============================================================================
REM  ClutterCutter - GUI launcher (Windows)
REM  Double-click this. No console window appears or remains.
REM
REM  Uses pythonw.exe, the console-less Python, so the GUI is not attached
REM  to a terminal. Python is located by full path because a double-clicked
REM  program does not inherit a shell's PATH.
REM ============================================================================
setlocal

set "CC_HOME=%~dp0"
if not defined CC_HOME set "CC_HOME=C:\Users\Isreal\ClutterCutter\"
cd /d "%CC_HOME%"

REM --- locate pythonw.exe (the GUI Python) -------------------------------------
set "PYW="

REM 1. A Python installed for this user - the usual case.
for %%D in (Python314 Python313 Python312 Python311 Python310) do (
    if not defined PYW if exist "%LOCALAPPDATA%\Programs\Python\%%D\pythonw.exe" (
        set "PYW=%LOCALAPPDATA%\Programs\Python\%%D\pythonw.exe"
    )
)

REM 2. Next to an already-found python.exe.
if not defined PYW (
    for /f "delims=" %%L in ('where.exe pythonw.exe 2^>nul') do (
        if not defined PYW set "PYW=%%L"
    )
)

if not defined PYW (
    echo.
    echo   Could not find pythonw.exe.
    echo.
    echo   Install Python 3.10 or newer from python.org, tick
    echo   "tcl/tk and IDLE" during setup, then run this again.
    echo.
    pause
    exit /b 1
)

REM Start fully detached: no console window flashes or hangs around.
start "" "%PYW%" -m cluttercutter.gui

endlocal