@echo off
title PATCHSENSE — YouTube Road Video & Telemetry Streamer
color 0e

echo ========================================================================
echo          PATCHSENSE - YOUTUBE ROAD VIDEO & GPS STREAMER
echo          Video: Indian Highway Truck & Severe Potholes
echo ========================================================================
echo.

:: 1. Check if AI Server is running on port 8000. If not, start it in background!
netstat -ano | findstr ":8000 " | findstr "LISTENING" >nul
if %errorlevel% neq 0 (
    echo [*] Starting PATCHSENSE AI Inference Server in background...
    start "PATCHSENSE Server" cmd /k ".\server\venv\Scripts\python.exe server\run_server.py"
    
    :: Wait until port 8000 is actually listening (up to 10 seconds)
    echo [*] Waiting for AI server to initialize...
    for /l %%k in (1,1,10) do (
        timeout /t 1 >nul
        netstat -ano | findstr ":8000 " | findstr "LISTENING" >nul
        if not errorlevel 1 goto ServerReady
    )
)

:ServerReady
echo [+] AI Server is active and listening!
echo.

:: 2. Automatically open Dashboard in default browser
echo [*] Opening Dashboard at http://localhost:8000/ ...
start http://localhost:8000/
timeout /t 2 >nul

:: 3. Stream YouTube road video & live GPS
echo [*] Streaming YouTube road video (Heavy Indian Truck in Potholes)...
echo [*] Look at your browser window to see the live road and map!
echo ========================================================================
echo.

set PYTHONIOENCODING=utf-8
chcp 65001 >nul

.\server\venv\Scripts\python.exe -u video_streamer.py --video server\static\youtube_demo.mp4 %*

pause
