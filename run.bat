@echo off
title BABFT Hand Gesture Controller
cd /d "%~dp0"

echo ========================================================
echo   Roblox Build A Boat Hand Gesture Controller
echo ========================================================
echo Starting controller...
echo.

:: Try 64-bit Python launcher first
py -3-64 BabftHandGestures.py 2>nul
if %ERRORLEVEL% equ 0 exit /b

:: Try standard py launcher
py -3 BabftHandGestures.py 2>nul
if %ERRORLEVEL% equ 0 exit /b

:: Try system python on PATH
python BabftHandGestures.py
if %ERRORLEVEL% equ 0 exit /b

echo.
echo ========================================================
echo Launch encountered an issue (Exit Code: %ERRORLEVEL%)
echo Please verify 64-bit Python is installed with dependencies:
echo   pip install -r requirements.txt
echo ========================================================
pause
