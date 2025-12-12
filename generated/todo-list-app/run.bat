@echo off
REM Todo List Application Startup Script for Windows
REM This script checks dependencies, sets up environment, and starts the application

echo ======================================
echo   Todo List Application Startup
echo ======================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed
    echo Please install Python 3.8 or higher from python.org
    pause
    exit /b 1
)

echo [OK] Python found

REM Check if virtual environment exists
if not exist "venv\" (
    echo [!] Virtual environment not found. Creating...
    python -m venv venv
    echo [OK] Virtual environment created
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Check if requirements are installed
if not exist "venv\Scripts\flask.exe" (
    echo [!] Dependencies not installed. Installing...
    pip install -r requirements.txt
    echo [OK] Dependencies installed
) else (
    echo [OK] Dependencies already installed
)

REM Check if .env file exists
if not exist ".env" (
    echo [!] .env file not found. Creating from .env.example...
    copy .env.example .env
    echo [OK] .env file created
    echo [!] Please edit .env file and set your SECRET_KEY
)

REM Check if database exists
if not exist "todo.db" (
    echo [!] Database not found. It will be created on first run
)

REM Set environment variables
set FLASK_APP=src.app
set FLASK_ENV=development

echo.
echo ======================================
echo   Starting Application
echo ======================================
echo.
echo [OK] Application will be available at: http://localhost:5000
echo [OK] Press Ctrl+C to stop the server
echo.

REM Start the application
python src\app.py

pause
