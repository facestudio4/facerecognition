@echo off
set "FLUTTER=%USERPROFILE%\.puro\envs\stable\flutter\bin\flutter.bat"
if not exist "%FLUTTER%" (
  echo Flutter not found at %FLUTTER%
  exit /b 1
)
"%FLUTTER%" %*
