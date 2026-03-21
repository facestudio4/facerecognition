param(
    [string]$ApiHost = "0.0.0.0",
    [int]$Port = 8787,
    [string]$BaseUrl = "",
    [switch]$SkipBackend,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$mobileRoot = Join-Path $repoRoot "mobile_flutter_client"
$flutterWrapper = Join-Path $mobileRoot "flutterw.bat"

function Get-PreferredLanIp {
    try {
        $route = Get-NetRoute -DestinationPrefix "0.0.0.0/0" -ErrorAction Stop |
            Sort-Object RouteMetric |
            Select-Object -First 1
        if ($null -ne $route) {
            $ip = Get-NetIPAddress -InterfaceIndex $route.InterfaceIndex -AddressFamily IPv4 -ErrorAction Stop |
                Where-Object { $_.IPAddress -notlike "169.254.*" -and $_.IPAddress -ne "127.0.0.1" } |
                Select-Object -First 1 -ExpandProperty IPAddress
            if ($ip) { return $ip }
        }
    } catch {
    }

    $fallback = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
        Where-Object {
            $_.IPAddress -notlike "169.254.*" -and
            $_.IPAddress -ne "127.0.0.1" -and
            $_.PrefixOrigin -ne "WellKnown"
        } |
        Select-Object -First 1 -ExpandProperty IPAddress
    return $fallback
}

function Get-ApiKeyFromDb {
    $dbPath = Join-Path $repoRoot "database\facestudio.db"
    if (-not (Test-Path $dbPath)) {
        return ""
    }

    try {
        $tmpPy = Join-Path $env:TEMP "face_studio_read_apikey.py"
        @"
import sqlite3
import sys

db = sys.argv[1]
conn = sqlite3.connect(db)
try:
    row = conn.execute("SELECT meta_value FROM project_meta WHERE meta_key='api_key'").fetchone()
    print((row[0] if row else "").strip())
finally:
    conn.close()
"@ | Set-Content -Path $tmpPy -Encoding ASCII

        $key = (& python $tmpPy $dbPath 2>$null | Select-Object -First 1)
        if ($null -eq $key) { return "" }
        return $key.Trim()
    } catch {
        return ""
    }
}

if (-not (Test-Path $mobileRoot)) {
    throw "mobile_flutter_client folder not found at $mobileRoot"
}

if (-not (Get-Command adb -ErrorAction SilentlyContinue)) {
    throw "adb is not available in PATH. Install Android platform-tools first."
}

if (-not $SkipBackend) {
    $backendCmd = "Set-Location -Path '$repoRoot'; python scripts/app_runner.py api --host $ApiHost --port $Port"
    if ($DryRun) {
        Write-Host "[DryRun] Would start backend: $backendCmd" -ForegroundColor Yellow
    } else {
        Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendCmd | Out-Null
        Start-Sleep -Seconds 2
    }
}

if ([string]::IsNullOrWhiteSpace($BaseUrl)) {
    if ($ApiHost -eq "0.0.0.0") {
        $lanIp = Get-PreferredLanIp
        if ([string]::IsNullOrWhiteSpace($lanIp)) {
            throw "Could not detect LAN IP. Pass -BaseUrl manually, for example: -BaseUrl http://192.168.1.10:$Port"
        }
        $BaseUrl = "http://${lanIp}:$Port"
    } else {
        $BaseUrl = "http://${ApiHost}:$Port"
    }
}

Write-Host "Using mobile Base URL: $BaseUrl" -ForegroundColor Cyan

$apiKey = Get-ApiKeyFromDb
if ([string]::IsNullOrWhiteSpace($apiKey)) {
    Write-Host "Warning: API key not found in database. App will require manual API key entry." -ForegroundColor Yellow
} else {
    Write-Host "Using API key from local database." -ForegroundColor Cyan
}

$deviceLine = (adb devices) | Select-String "\sdevice$" | Select-Object -First 1
if (-not $deviceLine) {
    throw "No authorized Android device found. Connect phone, enable USB debugging, then accept authorization prompt."
}

$deviceId = ($deviceLine.ToString() -split "\s+")[0]
Write-Host "Using device: $deviceId" -ForegroundColor Cyan

if (Test-Path $flutterWrapper) {
    $runCmd = "Set-Location -Path '$mobileRoot'; .\\flutterw.bat run -d $deviceId --dart-define=FACE_STUDIO_BASE_URL=$BaseUrl"
} else {
    $runCmd = "Set-Location -Path '$mobileRoot'; flutter run -d $deviceId --dart-define=FACE_STUDIO_BASE_URL=$BaseUrl"
}

if (-not [string]::IsNullOrWhiteSpace($apiKey)) {
    $runCmd = "$runCmd --dart-define=FACE_STUDIO_API_KEY=$apiKey"
}

if ($DryRun) {
    Write-Host "[DryRun] Would run Flutter: $runCmd" -ForegroundColor Yellow
} else {
    powershell -NoExit -Command $runCmd
}
