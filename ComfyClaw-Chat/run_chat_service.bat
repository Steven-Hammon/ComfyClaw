@echo off
python "%~dp0chat_service.py"
if %errorlevel% neq 0 (
    echo.
    echo ERROR: Failed to run chat_service.py
    echo Make sure Python is installed and added to your PATH.
    pause
)
