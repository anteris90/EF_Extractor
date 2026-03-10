@echo off
setlocal
REM Start Browser (Windows)
REM Usage: Start Browser.bat [path\to\eve_universe.db]

set "SCRIPT_DIR=%~dp0"
set "BROWSER_DIR=%SCRIPT_DIR%browser"
set "VENV_PYTHON=%SCRIPT_DIR%.venv\Scripts\python.exe"

REM Change to this script's directory and into the browser folder
pushd "%BROWSER_DIR%" || (
    echo Failed to open browser folder: "%BROWSER_DIR%"
    pause
    exit /b 1
)

REM If an argument is provided, use it as EF_DB_PATH
if "%~1"=="" (
    echo Starting Browser app ^(default DB^)...
) else (
    set "EF_DB_PATH=%~1"
    echo Using EF_DB_PATH=%EF_DB_PATH%
)

REM Prefer the local virtual environment, then py, then python
if exist "%VENV_PYTHON%" (
    "%VENV_PYTHON%" -u app.py
) else (
    where py >nul 2>nul
    if errorlevel 1 (
        python -u app.py
    ) else (
        py -3 -u app.py
    )
)

set "EXIT_CODE=%ERRORLEVEL%"
popd

if not "%EXIT_CODE%"=="0" (
    echo.
    echo Browser exited with code %EXIT_CODE%.
)

pause
exit /b %EXIT_CODE%
