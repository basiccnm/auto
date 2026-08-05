@echo off
rem ASCII only. (Korean in .bat gets mangled by cmd codepage - project CLAUDE.md lesson)
title Coupang Partners API Key Setup
cd /d "%~dp0"
echo.
echo  ==========================================
echo    Coupang Partners API Key Setup
echo  ==========================================
echo.
echo  Where to get the keys:
echo    Coupang Partners - login - [My Info] - [API Management]
echo    You need TWO values: ACCESS KEY and SECRET KEY
echo.
echo  Saved to .env in this folder only.
echo  Not sent to chat or Drive.
echo.

set "AK="
set "SK="
set /p "AK=ACCESS KEY: "
set /p "SK=SECRET KEY: "
echo.

if not defined AK goto empty
if not defined SK goto empty

if exist ".env" copy /y ".env" ".env.bak" >nul

> ".env" echo COUPANG_ACCESS_KEY=%AK%
>> ".env" echo COUPANG_SECRET_KEY=%SK%

echo  [OK] Saved to .env
echo.
echo  Verifying connection...
echo.
python scripts\coupang_check.py
echo.
echo  ==========================================
echo   Show the result above to Claude.
echo  ==========================================
echo.
pause
exit /b

:empty
echo  [!] Both keys are required. Please run again.
echo.
pause
