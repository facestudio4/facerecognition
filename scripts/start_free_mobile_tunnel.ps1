param(
    [int]$Port = 8787,
    [string]$ApiHost = "0.0.0.0",
    [switch]$SkipBackend
)

$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

$cloudflaredCmd = Get-Command cloudflared -ErrorAction SilentlyContinue
if ($cloudflaredCmd) {
    $cloudflaredExe = $cloudflaredCmd.Source
} else {
    $fallback = "C:\Program Files (x86)\cloudflared\cloudflared.exe"
    if (Test-Path $fallback) {
        $cloudflaredExe = $fallback
    } else {
        throw "cloudflared is not installed. Install with: winget install --id Cloudflare.cloudflared -e"
    }
}

if (-not $SkipBackend) {
    $backendCmd = "Set-Location -Path '$repoRoot'; python scripts/app_runner.py api --host $ApiHost --port $Port"
    Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendCmd | Out-Null
}

$healthOk = $false
for ($i = 0; $i -lt 30; $i++) {
    Start-Sleep -Seconds 1
    try {
        $h = Invoke-WebRequest "http://127.0.0.1:$Port/api/health" -UseBasicParsing -TimeoutSec 2
        if ($h.StatusCode -eq 200) {
            $healthOk = $true
            break
        }
    } catch {
    }
}

if (-not $healthOk) {
    Write-Host "Backend health check not ready yet. Tunnel will still start." -ForegroundColor Yellow
}

Write-Host "Starting Cloudflare Tunnel..." -ForegroundColor Cyan
Write-Host "Copy the https://...trycloudflare.com URL shown below and use it as app backend URL." -ForegroundColor Cyan
& $cloudflaredExe tunnel --url "http://127.0.0.1:$Port"
