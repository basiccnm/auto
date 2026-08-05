@echo off
rem ASCII only. (Korean inside .bat gets mangled by cmd codepage - project CLAUDE.md lesson)
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
python admin_server.py
pause
