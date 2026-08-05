@echo off
rem ASCII only. (Korean in .bat gets mangled by cmd codepage - project CLAUDE.md lesson)
title olmanama daily update
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
echo.
echo  ==========================================
echo    olmanama - daily update
echo    collect - history - recalc - build - deploy
echo  ==========================================
echo.
python scripts\daily_update.py
echo.
echo  Log: data\daily_update.log
echo.
if "%1"=="/auto" exit /b
pause
