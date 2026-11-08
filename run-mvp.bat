@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Close this window to stop the server.
python server.py
if errorlevel 1 py server.py
pause
