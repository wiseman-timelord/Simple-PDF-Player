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
echo     2. Run Main Program (debug)
echo.
echo     3. Run Installation
echo.
echo.
echo.
echo.
echo.
echo.
echo.
echo ===============================================================================
set /p choice=Selection; Menu Options = 1-3, Exit Batch = X: 

if /I "%choice%"=="1" goto run_silent
if /I "%choice%"=="2" goto run_debug
if /I "%choice%"=="3" goto install
if /I "%choice%"=="X" exit
goto menu

:run_silent
if not exist "venv\Scripts\pythonw.exe" (
    echo.
    echo [ERROR] Virtual environment not found!
    echo Please select Option 3 to run the installation first.
    echo.
    pause
    goto menu
)
echo ===============================================================================
echo     Simple-PDF-Player: Launcher
echo ===============================================================================
echo.
echo    The console will close in 3 seconds.
echo    The application will continue running.
echo.
timeout /t 3 >nul
REM Use pythonw.exe to run completely detached without opening a python console
start "" "venv\Scripts\pythonw.exe" launcher.py
exit

:run_debug
if not exist "venv\Scripts\python.exe" (
    echo.
    echo [ERROR] Virtual environment not found!
    echo Please select Option 3 to run the installation first.
    echo.
    pause
    goto menu
)
echo ===============================================================================
echo     Simple-PDF-Player: Launcher (Debug)
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