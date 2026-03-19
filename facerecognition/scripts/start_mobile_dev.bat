@echo off
cd /d "%~dp0.."
powershell -ExecutionPolicy Bypass -File "scripts\start_mobile_dev.ps1"
