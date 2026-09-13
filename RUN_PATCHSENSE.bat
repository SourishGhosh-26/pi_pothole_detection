@echo off
cd /d "%~dp0"
title PATCHSENSE — AI Pothole Detection Platform
color 0b

echo ========================================================================
echo               PATCHSENSE - AI ROAD HAZARD DETECTION SYSTEM
echo ========================================================================
:: Free ports 8000 and 8443 if occupied by any previous run
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000 "') do taskkill /f /pid %%a >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8443 "') do taskkill /f /pid %%a >nul 2>&1

:: Check Python executable
set PYTHON_EXE=
if exist "server\venv\Scripts\python.exe" (
    set "PYTHON_EXE=.\server\venv\Scripts\python.exe"
) else (
    where python >nul 2>&1
    if %ERRORLEVEL% equ 0 (
        set "PYTHON_EXE=python"
    ) else (
        echo [ERROR] Python is not found on this laptop!
        echo Please install Python 3.10+ from https://www.python.org/ (check 'Add to PATH').
        pause
        exit /b 1
    )
)

:: Detect Real Local LAN IP Address
set LOCAL_IP=
for /f "tokens=*" %%i in ('powershell -NoProfile -Command "Get-NetIPAddress -AddressFamily IPv4 | Where-Object IPAddress -notlike '169.254*' | Where-Object IPAddress -notlike '127*' | Select-Object -First 1 -ExpandProperty IPAddress"') do set LOCAL_IP=%%i

if "%LOCAL_IP%"=="" (
    for /f "tokens=*" %%i in ('powershell -NoProfile -Command "(Get-NetIPAddress -InterfaceAlias 'Wi-Fi*' -AddressFamily IPv4).IPAddress"') do set LOCAL_IP=%%i
)
if "%LOCAL_IP%"=="" set LOCAL_IP=192.168.1.8

echo [*] Laptop Dashboard URL:       http://localhost:8000/
echo [*] Mobile Real Camera URL:     https://%LOCAL_IP%:8443/camera
echo.
echo ========================================================================
echo  HOW TO CONNECT YOUR PHONE:
echo  1. Connect Laptop and Phone to the SAME Wi-Fi or Phone Hotspot.
echo  2. On your phone browser (Chrome/Safari), open:
echo        https://%LOCAL_IP%:8443/camera
echo  3. Tap 'Advanced' -^> 'Proceed to %LOCAL_IP% (unsafe)'.
echo  4. Allow Camera and Location permissions to start live streaming!
echo ========================================================================
echo.

:: Open dashboard in default browser after 2 seconds
start /b cmd /c "timeout /t 2 >nul & start http://localhost:8000/"

:: Start dual HTTP (8000) and HTTPS (8443) server
%PYTHON_EXE% server\run_server.py

pause
