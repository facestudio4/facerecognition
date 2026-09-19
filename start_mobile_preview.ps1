param(
    [string]$ApiHost = "127.0.0.1",
    [int]$Port = 8787,
    [switch]$SkipBackend,
    [switch]$Web,
    [switch]$InitWindows
)

$scriptPath = Join-Path $PSScriptRoot "scripts\start_mobile_preview.ps1"
if (-not (Test-Path $scriptPath)) {
    throw "Missing script: $scriptPath"
}

$args = @(
    "-ExecutionPolicy", "Bypass",
    "-File", $scriptPath,
    "-ApiHost", $ApiHost,
    "-Port", "$Port"
)

if ($SkipBackend.IsPresent) {
    $args += "-SkipBackend"
}
if ($Web.IsPresent) {
    $args += "-Web"
}
if ($InitWindows.IsPresent) {
    $args += "-InitWindows"
}

& powershell @args
