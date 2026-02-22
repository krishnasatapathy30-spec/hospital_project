@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

REM Create virtual environment if it doesn't exist
if not exist "venv\" (
  echo Creating virtual environment...
  python -m venv venv
  if errorlevel 1 (
    echo Failed to create virtual environment
    exit /b 1
  )
)

REM Activate virtual environment
call venv\Scripts\activate.bat
if errorlevel 1 (
  echo Failed to activate virtual environment
  exit /b 1
)

REM Install requirements
echo Installing requirements...
pip install -r requirements.txt
if errorlevel 1 (
  echo Failed to install requirements
  exit /b 1
)

REM Run the Flask app from main folder
echo Starting Hospital Project...
python "main folder\app.py"