param(
    [string]$ApiHost = "0.0.0.0",
    [int]$Port = 8787,
    [switch]$SkipGui,
    [switch]$SkipBackend
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

if (-not $SkipBackend) {
    Write-Host "Starting backend API (host=$ApiHost port=$Port)..." -ForegroundColor Cyan
    $backendCmd = "Set-Location -Path '$repoRoot'; python scripts/app_runner.py api --host $ApiHost --port $Port"
    Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendCmd | Out-Null
}

if (-not $SkipGui) {
    Write-Host "Starting desktop GUI (Kivy) in a new window..." -ForegroundColor Cyan
    $guiCmd = "Set-Location -Path '$repoRoot'; python scripts/app_runner.py gui"
    Start-Process powershell -ArgumentList "-NoExit", "-Command", $guiCmd | Out-Null
}

Write-Host "All requested dev processes started. Check the new terminal windows." -ForegroundColor Green
