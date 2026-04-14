@echo off
cd /d "%~dp0"
title NewsLet Pro
echo Starting NewsLet Pro...
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
pause
