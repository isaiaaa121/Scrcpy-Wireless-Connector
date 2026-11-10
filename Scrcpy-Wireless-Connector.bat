@echo off
title Scrcpy Wireless Connector
color 07
chcp 65001 >nul
mode con: cols=100 lines=55

cd /d "%~dp0"

py -3 qr_adb.py

pause