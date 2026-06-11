@echo off
setlocal

set "ROOT_DIR=%~dp0.."
cd /d "%ROOT_DIR%"

where uv >nul 2>nul
if %ERRORLEVEL%==0 (
  if "%UV_LINK_MODE%"=="" set "UV_LINK_MODE=copy"
  uv run --extra tui loops-opencode-tui %*
  exit /b %ERRORLEVEL%
)

set "PYTHON_BIN=python"
if exist ".venv\Scripts\python.exe" set "PYTHON_BIN=.venv\Scripts\python.exe"
if exist "venv\Scripts\python.exe" set "PYTHON_BIN=venv\Scripts\python.exe"

set "PYTHONPATH=%ROOT_DIR%\src;%PYTHONPATH%"
"%PYTHON_BIN%" -m loops_opencode.tui %*

exit /b %ERRORLEVEL%
