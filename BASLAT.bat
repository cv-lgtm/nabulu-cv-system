@echo off
chcp 65001 > nul
title Nabulu Talent - CV Otomasyon Servisi
cd /d %~dp0

echo ===================================================
echo     NABULU TALENT - CV YONETIM VE RAPORLAMA
echo ===================================================
echo.

py main.py

pause
