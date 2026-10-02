@echo off
REM ============================================================================
REM  ClutterCutter - CLI launcher (Windows)
REM
REM  Usage:  cc-cli.bat "C:\Users\me\Downloads" [--apply] [--json] ...
REM
REM  Without --apply this only previews what would happen. Nothing is moved.
REM ============================================================================
setlocal

set "CC_HOME=%~dp0"
if not defined CC_HOME set "CC_HOME=C:\Users\Isreal\ClutterCutter\"
cd /d "%CC_HOME%"

if "%~1"=="" (
    echo Usage: cc-cli.bat ^<folder^> [--apply] [--include-protected] [--recursive] [--json]
    echo.
    echo   Without --apply this only previews what would happen.
    exit /b 2
)

set "PY="
for %%P in (
    "%LOCALAPPDATA%\Programs\Python\Python314\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python310\python.exe"
) do (
    if not defined PY if exist %%P set "PY=%%~P"
)
if not defined PY (
    for /f "delims=" %%L in ('py -3 -c "import sys;print(sys.executable)" 2^>nul') do (
        if not defined PY set "PY=%%L"
    )
)
if not defined PY (
    for /f "delims=" %%L in ('python -c "import sys;print(sys.executable)" 2^>nul') do (
        if not defined PY set "PY=%%L"
    )
)

if not defined PY (
    echo Could not find a Python installation. Install Python 3.10 or newer.
    exit /b 1
)

"%PY%" -m cluttercutter %*
exit /b %errorlevel%