@echo off
title Allow phone access to Face Studio AI
net session >nul 2>&1
if %errorlevel% neq 0 (
  echo Requesting administrator permission...
  powershell -Command "Start-Process '%~f0' -Verb RunAs"
  exit /b
)
netsh advfirewall firewall delete rule name="Face Studio AI" >nul 2>&1
netsh advfirewall firewall add rule name="Face Studio AI" dir=in action=allow protocol=TCP localport=7860
echo.
echo Done. Your phone can now reach the Face Studio AI server on this PC (port 7860).
echo You only need to run this once.
echo.
pause
