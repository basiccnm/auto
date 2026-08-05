@echo off
rem ASCII only - Korean text breaks cmd label seeking. Real work is in scripts\update-deploy.ps1
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\update-deploy.ps1"
pause