#!/bin/bash

# Todo List Application Startup Script
# This script checks dependencies, sets up environment, and starts the application

set -e  # Exit on error

echo "======================================"
echo "  Todo List Application Startup"
echo "======================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 is not installed${NC}"
    echo "Please install Python 3.8 or higher"
    exit 1
fi

# Check Python version
PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo -e "${GREEN}✓${NC} Python $PYTHON_VERSION found"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}⚠${NC} Virtual environment not found. Creating..."
    python3 -m venv venv
    echo -e "${GREEN}✓${NC} Virtual environment created"
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Check if requirements are installed
if [ ! -f "venv/bin/flask" ]; then
    echo -e "${YELLOW}⚠${NC} Dependencies not installed. Installing..."
    pip install -r requirements.txt
    echo -e "${GREEN}✓${NC} Dependencies installed"
else
    echo -e "${GREEN}✓${NC} Dependencies already installed"
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠${NC} .env file not found. Creating from .env.example..."
    cp .env.example .env
    echo -e "${GREEN}✓${NC} .env file created"
    echo -e "${YELLOW}⚠${NC} Please edit .env file and set your SECRET_KEY"
fi

# Check if database exists
if [ ! -f "todo.db" ]; then
    echo -e "${YELLOW}⚠${NC} Database not found. It will be created on first run"
fi

# Set environment variables
export FLASK_APP=src.app
export FLASK_ENV=development

echo ""
echo "======================================"
echo "  Starting Application"
echo "======================================"
echo ""
echo -e "${GREEN}✓${NC} Application will be available at: http://localhost:5000"
echo -e "${GREEN}✓${NC} Press Ctrl+C to stop the server"
echo ""

# Start the application
python src/app.py
