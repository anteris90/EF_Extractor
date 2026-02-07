@echo off
setlocal

echo ============================================
echo   EVE Frontier Staticdata Extractor
echo ============================================
echo.

REM --- Set the installation Path to EVE Frontier ---
set GAME_PATH=C:\Program Files\EVE Frontier

REM --- Path of resfileindex.txt  ---
set RESINDEX=%GAME_PATH%\stillness\resfileindex.txt

REM --- Output folder ---
set OUT=output

REM --- Lost of containers ---
REM Define the list to extract:
REM Examples:
REM   types,groups,dogmaattributes
REM   industry_blueprints
REM   solarsystemcontent
set CONTAINERS=locationcache,systems,regions,types,solarsystemcontent


echo [INFO] Python version check ...
python --version >nul 2>&1
if errorlevel 1 (
    echo [HIBA] Python is not installed or not defined in PATH.
    pause
    exit /b 1
)

echo [INFO] Run Extractor...
py -3.12 EF_Extractor.py ^
    -e "%GAME_PATH%" ^
    -i "%RESINDEX%" ^
    -o "%OUT%" ^
    -c "%CONTAINERS%"

echo.
echo [DONE] Output ready in: "%OUT%" folder.
echo.
pause
