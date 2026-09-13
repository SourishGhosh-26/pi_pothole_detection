@echo off
title BEL URBANSENSE - Share Prototype Online Across Any Location
color 0e

echo ========================================================================
echo       BEL URBANSENSE - SHARE ONLINE ANYWHERE IN THE WORLD
echo ========================================================================
echo.
echo [*] This creates a public internet tunnel for your project.
echo [*] Anyone on ANY laptop or phone in ANY city can view your live dashboard!
echo.
echo [!] NOTE: Make sure RUN_URBANSENSE.bat is already running on your laptop!
echo [*] Generating public internet URL...
echo.

cmd /c "npx -y localtunnel --port 8000"

pause
