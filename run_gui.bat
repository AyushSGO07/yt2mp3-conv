@echo off
title YouTube to MP3 Studio (320kbps) - Web App
echo ========================================================
echo   Launching YouTube to MP3 (320kbps) Web Studio...
echo ========================================================
python -m streamlit run app.py
if errorlevel 1 (
    echo.
    echo An error occurred while running the application.
    pause
)
