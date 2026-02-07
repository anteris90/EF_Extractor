@echo off
REM Start Browser (Windows)
REM Usage: Start Browser.bat [path\to\eve_universe.db]

REM Change to this script's directory and into the browser folder
pushd "%~dp0browser"

REM If an argument is provided, use it as EF_DB_PATH
if "%~1"=="" (
    echo Starting Browser app (default DB)...
) else (
    set "EF_DB_PATH=%~1"
    echo Using EF_DB_PATH=%EF_DB_PATH%
)

REM Prefer the Python launcher; fall back to python
where py >nul 2>nul
if %errorlevel%==0 (
    py -3 -u app.py
) else (
    python -u app.py
)

REM Keep console open after exit
popd
pause
