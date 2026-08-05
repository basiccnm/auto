@echo off
rem ASCII only. (Korean inside .bat gets mangled by cmd codepage - project CLAUDE.md lesson)
title Kakao REST API Key Setup
cd /d "%~dp0"
echo.
echo  ==========================================
echo    Kakao Login - REST API Key Setup
echo  ==========================================
echo.
echo  Where to get it:
echo    developers.kakao.com - My Application - App Keys
echo    Copy the "REST API Key" value.
echo.
echo  Saved to .env in this folder only.
echo  Existing keys (Coupang etc.) are kept.
echo  Not sent to chat or Drive.
echo.

set "KK="
set /p "KK=REST API KEY: "
echo.

if not defined KK goto empty

rem back up, then rewrite .env keeping every line except an old KAKAO_REST_KEY
if exist ".env" copy /y ".env" ".env.bak" >nul
if exist ".env" (
  > ".env.tmp" (
    for /f "usebackq delims=" %%L in (".env.bak") do (
      echo %%L | findstr /b /c:"KAKAO_REST_KEY=" >nul || echo %%L
    )
  )
  move /y ".env.tmp" ".env" >nul
)
>> ".env" echo KAKAO_REST_KEY=%KK%

echo  [OK] KAKAO_REST_KEY saved to .env
echo.
echo  Current .env keys (values hidden):
for /f "usebackq tokens=1 delims==" %%K in (".env") do echo    - %%K
echo.
echo  ==========================================
echo   Tell Claude it is saved. Do NOT paste the key in chat.
echo  ==========================================
echo.
pause
exit /b

:empty
echo  [!] REST API Key is required. Please run again.
echo.
pause
