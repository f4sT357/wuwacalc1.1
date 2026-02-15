@echo off
cd /d %~dp0
echo Starting Wuthering Waves Echo Score Calculator...
.\.venv\Scripts\python.exe wuwacalc17.py
pause
