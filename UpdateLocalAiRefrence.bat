@echo off
title Update Ormophine AI References
echo ==========================================
echo   Updating AI Reference Files (Local)
echo ==========================================
echo.

:: Check if Python is available
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not added to PATH.
    echo Please install Python 3 and try again.
    goto :end
)

:: Run the Python script
echo Running script...
python scripts/update_ai_references.py

:: Check if the script ran successfully
if %errorlevel% equ 0 (
    echo.
    echo [SUCCESS] AI Reference files updated successfully!
) else (
    echo.
    echo [ERROR] Something went wrong while running the script.
)

:end
echo.
pause