@echo off
title BEL UrbanSense — BUS-104 VIP Road Traffic Congestion & Detour Demo
color 0b

echo ========================================================================
echo       BEL URBANSENSE - BUS-104 TRAFFIC CONGESTION ^& ROUTE DIVERSION
echo       Corridor: VIP Road ^& Salt Lake Sector V (Route 18B)
echo       Video: Kolkata City Traffic Bottleneck (YouTube Source)
echo ========================================================================
echo.

:: 1. Check if AI Server is running on port 8000. If not, start it in background!
netstat -ano | findstr ":8000 " | findstr "LISTENING" >nul
if %errorlevel% neq 0 (
    echo [*] Starting BEL UrbanSense Server in background...
    start "BEL UrbanSense Server" cmd /k ".\server\venv\Scripts\python.exe server\run_server.py"
    
    :: Wait until port 8000 is actually listening (up to 10 seconds)
    echo [*] Waiting for AI server to initialize...
    for /l %%k in (1,1,10) do (
        timeout /t 1 >nul
        netstat -ano | findstr ":8000 " | findstr "LISTENING" >nul
        if not errorlevel 1 goto ServerReady
    )
)

:ServerReady
echo [+] Server is active and listening!
echo.

:: 2. Automatically open Dashboard in default browser
echo [*] Opening BEL UrbanSense Fleet Command Dashboard at http://localhost:8000/ ...
start http://localhost:8000/
timeout /t 2 >nul

:: 3. Stream BUS-104 Traffic Congestion Video & Live VIP Road GPS
echo [*] Streaming BUS-104 Traffic Video (Kolkata City Traffic)...
echo [*] Route: Ultadanga - Lake Town - Salt Lake Gate - Karunamoyee - Sector V
echo [*] Watch the dashboard switch to BUS-104, detect bottleneck, and trigger detour!
echo ========================================================================
echo.

set PYTHONIOENCODING=utf-8
chcp 65001 >nul

.\server\venv\Scripts\python.exe -u video_streamer.py --bus BUS-104 --video server\static\bus104_traffic.mp4 %*

pause
