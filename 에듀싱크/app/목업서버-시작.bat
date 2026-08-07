@echo off
rem 앱 목업 서버 (8789) ? 더블클릭으로 언제든 재시작. 창을 닫으면 서버도 꺼짐.
cd /d %~dp0www
"C:\Users\hardb\AppData\Local\Programs\Python\Python39\python.exe" -m http.server 8789
