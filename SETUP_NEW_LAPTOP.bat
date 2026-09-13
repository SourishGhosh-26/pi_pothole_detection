@echo off
title BEL URBANSENSE - New Laptop Setup and Run
color 0b

echo ========================================================================
echo       BEL URBANSENSE - AUTOMATIC SETUP FOR NEW LAPTOP / PC
echo ========================================================================
echo.

:: 1. Check if Python is installed
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python is not installed or not added to PATH!
    echo Please download and install Python from https://www.python.org/
    echo (IMPORTANT: Check the box "Add Python to PATH" during installation!)
    echo.
    pause
    exit /b 1
)

echo [*] Python detected successfully:
python --version
echo.

:: 2. Create Virtual Environment if missing
if not exist "server\venv\Scripts\python.exe" (
    echo [*] Creating fresh Python virtual environment in server\venv...
    python -m venv server\venv
    if %ERRORLEVEL% NEQ 0 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo [*] Virtual environment created!
    echo.
    echo [*] Installing required AI and backend packages...
    echo     (FastAPI, OpenCV, WebSockets, SQLAlchemy, etc.)
    echo     This may take 1-2 minutes on first run. Please wait...
    .\server\venv\Scripts\python.exe -m pip install --upgrade pip
    .\server\venv\Scripts\pip install -r server\requirements.txt
    if %ERRORLEVEL% NEQ 0 (
        echo [ERROR] Package installation failed. Please check your internet connection.
        pause
        exit /b 1
    )
    echo [*] All packages installed successfully!
    echo.
) else (
    echo [*] Python virtual environment already configured!
    echo.
)

:: 3. Launch BEL UrbanSense Platform
echo [*] Launching Central Server and Dashboard...
call RUN_URBANSENSE.bat
