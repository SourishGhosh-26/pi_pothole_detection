@echo off
cd /d "%~dp0"
title BEL URBANSENSE — AI-Powered Mobile Urban Intelligence Platform
color 0b

echo ========================================================================
echo       BEL URBANSENSE - MOBILE URBAN INTELLIGENCE PLATFORM
echo       Bharat Electronics Limited ^| Public Transport Fleet AI
echo ========================================================================
echo.

:: 1. Free ports 8000 and 8443 if occupied by previous runs
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000 "') do taskkill /f /pid %%a >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8443 "') do taskkill /f /pid %%a >nul 2>&1

:: 2. Detect Real Local LAN IP Address
set LOCAL_IP=
for /f "tokens=*" %%i in ('powershell -NoProfile -Command "Get-NetIPAddress -AddressFamily IPv4 | Where-Object IPAddress -notlike '169.254*' | Where-Object IPAddress -notlike '127*' | Select-Object -First 1 -ExpandProperty IPAddress"') do set LOCAL_IP=%%i

if "%LOCAL_IP%"=="" (
    for /f "tokens=*" %%i in ('powershell -NoProfile -Command "(Get-NetIPAddress -InterfaceAlias 'Wi-Fi*' -AddressFamily IPv4).IPAddress"') do set LOCAL_IP=%%i
)
if "%LOCAL_IP%"=="" set LOCAL_IP=192.168.1.8

echo [*] LAPTOP DASHBOARD:          http://localhost:8000/
echo [*] PHONE REAL CAMERA (HTTPS): https://%LOCAL_IP%:8443/camera
echo [*] PHONE DASHBOARD (HTTP):    http://%LOCAL_IP%:8000/
echo.
echo ========================================================================
echo  FEATURES ACTIVATED:
echo   1. Public Transport Bus Fleet Telemetry (Buses #B101, #B104, #B208)
echo   2. Multi-Task Edge AI: Potholes, Waterlogging, Dividers, Signboards
echo   3. Traffic Density & Congestion Heatmap Analytics
echo   4. Pedestrian & School Zone Safety Detection
echo   5. Offending Vehicle ANPR Tracking (Hit-and-Run / Rash Driving)
echo   6. Bandwidth-Optimized Telemetry Ingestion (98.4%% bandwidth saved)
echo ========================================================================
echo.

:: 3. Open Command Center Dashboard in default browser after 2 seconds
start /b cmd /c "timeout /t 2 >nul & start http://localhost:8000/"

:: 4. Start Central Server
set PYTHONIOENCODING=utf-8
chcp 65001 >nul

.\server\venv\Scripts\python.exe server\run_server.py

pause
