@echo off
cd /d "%~dp0"
title BEL URBANSENSE - Network Connection Info
color 0a

echo ========================================================================
echo        BEL URBANSENSE - LOCAL NETWORK AND PHONE ACCESS INFO
echo ========================================================================
echo.

:: 1. Detect Real LAN / Wi-Fi IP (Excluding Loopback 127.0.0.1 and Unconnected 169.254.x.x)
set LOCAL_IP=
for /f "tokens=*" %%i in ('powershell -NoProfile -Command "Get-NetIPAddress -AddressFamily IPv4 | Where-Object IPAddress -notlike '169.254*' | Where-Object IPAddress -notlike '127*' | Select-Object -First 1 -ExpandProperty IPAddress"') do set LOCAL_IP=%%i

:: Fallback if empty
if "%LOCAL_IP%"=="" (
    for /f "tokens=*" %%i in ('powershell -NoProfile -Command "(Get-NetIPAddress -InterfaceAlias 'Wi-Fi*' -AddressFamily IPv4).IPAddress"') do set LOCAL_IP=%%i
)
if "%LOCAL_IP%"=="" set LOCAL_IP=192.168.1.8

echo [*] Your Laptop's Current Wi-Fi IP: %LOCAL_IP%
echo.
echo [1] On your LAPTOP browser:
echo     Dashboard:          http://localhost:8000/
echo.
echo [2] On your PHONE browser (Chrome / Safari):
echo     Real Camera + GPS:  https://%LOCAL_IP%:8443/camera
echo     Live Dashboard:     http://%LOCAL_IP%:8000/
echo.
echo ========================================================================
echo  QUICK SETUP INSTRUCTIONS:
echo  1. Connect your Laptop and Phone to the SAME Mobile Hotspot or College Wi-Fi.
echo  2. On your Phone, open Chrome or Safari and enter:
echo        https://%LOCAL_IP%:8443/camera
echo  3. When the browser warns "Your connection is not private":
echo     Tap 'Advanced' (or 'Show Details') and 'Proceed to %LOCAL_IP% (unsafe)'.
echo  4. Allow Camera and Location permissions when prompted.
echo  5. Your phone will immediately start streaming live video and real GPS!
echo ========================================================================
echo.
pause
