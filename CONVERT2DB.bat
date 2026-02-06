@echo off
setlocal

echo ============================================
echo   EVE Frontier JSON to DB Converter
echo ============================================
echo.

echo [INFO] Python version check ...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not defined in PATH.
    pause
    exit /b 1
)

echo [INFO] Run Coverter...
py convert/json_to_sqlite_main.py ^

echo.
echo [DONE] Output ready in: "%OUT%" folder.
echo.
pause
