@echo off
cd /d "%~dp0.."
powershell -ExecutionPolicy Bypass -File "scripts\start_mobile_preview.ps1"
