@echo off
cd /d "%~dp0"

set "WAS_VENV=0"
if defined VIRTUAL_ENV set "WAS_VENV=1"

if "%WAS_VENV%"=="0" (
  call ".\.venv\Scripts\activate.bat"
)

python -m src.simulation %*

if "%WAS_VENV%"=="0" (
  echo.
  echo ================================
  echo You are now in (.venv) shell.
  echo Run again: python -m src.simulation ...
  echo Exit: exit
  echo ================================
  cmd /k
)
