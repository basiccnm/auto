@echo off
rem ASCII only. (Korean in .bat gets mangled by cmd codepage - project CLAUDE.md lesson)
title OpenAI API Key Setup
set PYTHONIOENCODING=utf-8
cd /d "%~dp0"
echo.
echo  ==========================================
echo    OpenAI API Key Setup
echo  ==========================================
echo.
echo  Paste your key below, then press Enter.
echo  (Right-click or Ctrl+V to paste)
echo.
set "KEY="
set /p "KEY=KEY: "
echo.
if not defined KEY goto empty

set "OPENAI_API_KEY=%KEY%"
setx OPENAI_API_KEY "%KEY%" >nul 2>&1
echo  [OK] Saved. Checking...
echo.
python scripts\gen_recipe_openai.py --check
echo.
echo  ==========================================
echo   Show the result above to Claude.
echo  ==========================================
echo.
pause
exit /b

:empty
echo  [!] Nothing entered. Please run again.
echo.
pause
