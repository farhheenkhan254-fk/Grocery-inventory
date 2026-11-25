@echo off
setlocal enabledelayedexpansion

echo ======================================================================
echo  Smart Grocery Inventory & Procurement Management System (Agentic AI)
echo ======================================================================
echo.

cd /d "%~dp0"

if not exist .venv (
    echo Creating Python virtual environment .venv...
    python -m venv .venv
)

call .venv\Scripts\activate.bat

echo Upgrading pip and verifying dependencies...
python -m pip install --upgrade pip
pip install -r requirements.txt

echo.
echo Launching Streamlit Presentation Dashboard...
streamlit run app/main.py

pause
