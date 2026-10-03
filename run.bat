@echo off
title BABFT Hand Gesture Controller
cd /d "%~dp0"

echo ========================================================
echo   Roblox Build A Boat Hand Gesture Controller
echo ========================================================
echo Starting controller...
python BabftHandGestures.py

if %errorlevel% neq 0 (
    echo.
    echo Script ended with an error code: %errorlevel%
    pause
)
