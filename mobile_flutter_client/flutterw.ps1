param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Args
)

$flutter = "$env:USERPROFILE\.puro\envs\stable\flutter\bin\flutter.bat"
if (-not (Test-Path $flutter)) {
    Write-Error "Flutter not found at: $flutter"
    exit 1
}

& $flutter @Args
exit $LASTEXITCODE
