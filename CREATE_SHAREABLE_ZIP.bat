@echo off
cd /d "%~dp0"
title BEL URBANSENSE - Create Clean Shareable Zip
color 0a

echo ========================================================================
echo       BEL URBANSENSE - AUTOMATIC PROJECT PACKAGER
echo ========================================================================
echo.

set PYTHON_EXE=
if exist "server\venv\Scripts\python.exe" (
    set "PYTHON_EXE=.\server\venv\Scripts\python.exe"
) else (
    set "PYTHON_EXE=python"
)

%PYTHON_EXE% tools\create_share_zip.py

echo.
pause
