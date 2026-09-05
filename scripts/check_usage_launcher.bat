@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
cd /d "C:\Users\picot\Desktop\claude\news_to_podcast"
"C:\Users\picot\AppData\Local\Programs\Python\Python36\python.exe" src\check_usage.py
echo.
pause
