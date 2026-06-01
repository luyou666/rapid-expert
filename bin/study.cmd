@echo off
setlocal
chcp 65001 >nul 2>nul
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
set "STUDY_ROOT=%~dp0.."
python -X utf8 "%STUDY_ROOT%\scripts\study_cli.py" %*
exit /b %ERRORLEVEL%
