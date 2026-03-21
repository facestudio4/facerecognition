@echo off
setlocal
cd /d %~dp0..
if not exist ".venv-kivy\Scripts\python.exe" (
  echo Kivy environment not found. Please create it first.
  pause
  exit /b 1
)
".venv-kivy\Scripts\python.exe" "frontend\kivy_laptop_app.py"
