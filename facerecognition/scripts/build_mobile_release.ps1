param(
    [Parameter(Mandatory = $true)]
    [string]$BackendUrl,

    [string]$ApiKey = ""
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path $PSScriptRoot -Parent
$mobileDir = Join-Path $projectRoot "mobile_flutter_client"

Set-Location $mobileDir

if ($ApiKey -and $ApiKey.Trim().Length -gt 0) {
    .\flutterw.ps1 build apk --release --dart-define=FACE_STUDIO_BASE_URL=$BackendUrl --dart-define=FACE_STUDIO_API_KEY=$ApiKey
} else {
    .\flutterw.ps1 build apk --release --dart-define=FACE_STUDIO_BASE_URL=$BackendUrl
}

Write-Host "APK generated at: $mobileDir\build\app\outputs\flutter-apk\app-release.apk"
