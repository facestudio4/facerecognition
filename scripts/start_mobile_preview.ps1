param(
    [string]$ApiHost = "127.0.0.1",
    [int]$Port = 8787,
    [int]$WebPort = 9090,
    [switch]$SkipBackend,
    [switch]$Web,
    [switch]$InitWindows
)

$ErrorActionPreference = "Continue"
if ($PSVersionTable.PSVersion.Major -ge 7) {
    $PSNativeCommandUseErrorActionPreference = $false
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$mobileRoot = Join-Path $repoRoot "mobile_flutter_client"
$flutterWrapper = Join-Path $mobileRoot "flutterw.bat"
$wrapperFlutterPath = Join-Path $env:USERPROFILE ".puro\envs\stable\flutter\bin\flutter.bat"

function Get-ApiKeyFromDb {
    $dbPath = Join-Path $repoRoot "database\facestudio.db"
    if (-not (Test-Path $dbPath)) {
        return ""
    }

    try {
        $tmpPy = Join-Path $env:TEMP "face_studio_read_apikey_preview.py"
        @"
import sqlite3
import sys

conn = sqlite3.connect(sys.argv[1])
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

function Wait-BackendReady {
    param(
        [string]$Url,
        [int]$TimeoutSeconds = 45
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        try {
            $res = Invoke-WebRequest -Uri "$Url/api/health" -UseBasicParsing -TimeoutSec 3
            if ($res.StatusCode -eq 200) {
                return $true
            }
        } catch {
        }
        Start-Sleep -Milliseconds 800
    }
    return $false
}

if (-not (Test-Path $mobileRoot)) {
    throw "mobile_flutter_client folder not found at $mobileRoot"
}

if (-not $SkipBackend) {
    try {
        $existing = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($existing) {
            Stop-Process -Id $existing.OwningProcess -Force -ErrorAction SilentlyContinue
            Start-Sleep -Milliseconds 600
        }
    } catch {
    }

    $backendCmd = "Set-Location -Path '$repoRoot'; python scripts/app_runner.py api --host $ApiHost --port $Port"
    Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendCmd | Out-Null
}

$baseUrl = "http://${ApiHost}:$Port"
$apiKey = Get-ApiKeyFromDb

if (-not $SkipBackend) {
    Write-Host "Waiting for backend at $baseUrl ..." -ForegroundColor Cyan
    $ready = Wait-BackendReady -Url $baseUrl -TimeoutSeconds 60
    if (-not $ready) {
        throw "Backend did not start in time at $baseUrl. Check backend terminal for errors."
    }
    Write-Host "Backend is ready." -ForegroundColor Green
}

$windowsProjectPath = Join-Path $mobileRoot "windows"
$device = if ($Web) { "chrome" } else { "windows" }

$flutterCmd = "flutter"
if ((Test-Path $flutterWrapper) -and (Test-Path $wrapperFlutterPath)) {
    $flutterCmd = ".\\flutterw.bat"
}

function Invoke-Flutter {
    param(
        [string]$ArgsLine,
        [switch]$AllowFailure
    )

    Push-Location $mobileRoot
    try {
        if ($flutterCmd -eq ".\\flutterw.bat") {
            & cmd /c ".\\flutterw.bat $ArgsLine"
        } else {
            & cmd /c "flutter $ArgsLine"
        }
        if (-not $AllowFailure -and $LASTEXITCODE -ne 0) {
            throw "Flutter command failed: $ArgsLine"
        }
    } finally {
        Pop-Location
    }
}

Push-Location $mobileRoot
try {
    if ($device -eq "chrome") {
        Invoke-Flutter "config --enable-web"
        $webPath = Join-Path $mobileRoot "web"
        if (-not (Test-Path $webPath)) {
            Write-Host "Web platform not found. Creating web support..." -ForegroundColor Yellow
            Invoke-Flutter "create --platforms=web ."
        }
    }
} finally {
    Pop-Location
}

if ($device -eq "windows" -and -not (Test-Path $windowsProjectPath)) {
    if ($InitWindows) {
        Write-Host "Windows desktop support not found. Initializing Windows platform..." -ForegroundColor Yellow
        Invoke-Flutter "create --platforms=windows ."
    }

    if (-not (Test-Path $windowsProjectPath)) {
        Write-Host "Windows desktop support is missing. Falling back to Chrome preview." -ForegroundColor Yellow
        Write-Host "Tip: run with -InitWindows once to generate the Windows folder." -ForegroundColor Cyan
        $device = "chrome"
    }
}

if ($device -eq "chrome") {
    Invoke-Flutter "clean"
    Invoke-Flutter "pub get" -AllowFailure
    Invoke-Flutter "build web --release --dart-define=FACE_STUDIO_BASE_URL=$baseUrl"

    $serveDir = Join-Path $mobileRoot "build\web"
    if (-not (Test-Path $serveDir)) {
        throw "Web build output not found at $serveDir"
    }

    $serveCmd = "Set-Location -Path '$serveDir'; python -m http.server $WebPort"
    Start-Process powershell -ArgumentList "-NoExit", "-Command", $serveCmd | Out-Null
    Start-Sleep -Seconds 1

    $url = "http://127.0.0.1:$WebPort"
    Start-Process $url | Out-Null
    Write-Host "Web preview ready at $url" -ForegroundColor Green
    Write-Host "Press Ctrl+C in the server window to stop preview." -ForegroundColor Cyan
    return
}

$runCmd = "Set-Location -Path '$mobileRoot'; $flutterCmd run -d $device --dart-define=FACE_STUDIO_BASE_URL=$baseUrl"

if (-not [string]::IsNullOrWhiteSpace($apiKey)) {
    $runCmd = "$runCmd --dart-define=FACE_STUDIO_API_KEY=$apiKey"
}

powershell -NoExit -Command $runCmd
