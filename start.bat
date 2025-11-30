@echo off
echo Starting Telegram Reminder Bot...
echo.

REM Activate virtual environment if it exists
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
    echo Virtual environment activated
    echo.
)

REM Run the bot
python main.py

REM Pause to see any errors
echo.
echo Bot stopped.
pause
