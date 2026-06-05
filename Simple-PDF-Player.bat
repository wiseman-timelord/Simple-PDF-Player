:: Initialization
@echo off
setlocal EnableDelayedExpansion
color 80
title Simple-PDF-Player
cd /d "%~dp0"

:: Menu
:menu
cls
echo ===============================================================================
echo     Simple-PDF-Player: Batch Menu
echo ===============================================================================
echo.
echo.
echo.
echo.
echo.
echo.
echo.
echo     1. Run Main Program
echo.
echo     2. Run Installation
echo.
echo.
echo.
echo.
echo.
echo.
echo.
echo ===============================================================================
set /p choice=Selection; Menu Options = 1-2, Exit Batch = X: 

if /I "%choice%"=="1" goto run
if /I "%choice%"=="2" goto install
if /I "%choice%"=="X" exit
goto menu

:run
if not exist "venv\Scripts\python.exe" (
    echo.
    echo [ERROR] Virtual environment not found!
    echo Please select Option 2 to run the installation first.
    echo.
    pause
    goto menu
)
echo ===============================================================================
echo     Simple-PDF-Player: Launcher
echo ===============================================================================
"venv\Scripts\python.exe" launcher.py
pause
goto menu

:install
echo.
echo Starting installation setup...
python installer.py
pause
goto menu