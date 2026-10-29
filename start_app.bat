@echo off
cd /d "%~dp0"
where py >nul 2>nul
if not errorlevel 1 (
    py "%~dp0expense_tracker_app.py"
) else (
    python "%~dp0expense_tracker_app.py"
)
if errorlevel 1 (
    echo.
    echo The app could not start. Check that Python and Tkinter are installed.
    pause
)
