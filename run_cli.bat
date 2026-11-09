@echo off
title YouTube to MP3 Downloader (320kbps) - Interactive CLI
echo ========================================================
echo   Launching YouTube to MP3 Interactive Downloader...
echo ========================================================
python downloader.py
if errorlevel 1 (
    echo.
    echo An error occurred while running the script.
    pause
)
