@echo off
setlocal

set "ROOT_DIR=%~dp0.."
cd /d "%ROOT_DIR%"

set "PYTHON_BIN=python"
if exist ".venv\Scripts\python.exe" set "PYTHON_BIN=.venv\Scripts\python.exe"
if exist "venv\Scripts\python.exe" set "PYTHON_BIN=venv\Scripts\python.exe"

set "PYTHONPATH=%ROOT_DIR%\src;%PYTHONPATH%"
"%PYTHON_BIN%" -m loops_opencode.cli %*

exit /b %ERRORLEVEL%
