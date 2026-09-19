param(
  [string]$Message = 'batch face enrollment to reduce render requests',
  [switch]$NoPush
)

$ErrorActionPreference = 'Stop'

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Resolve-Path (Join-Path $scriptDir '..')
Set-Location $repoRoot

$paths = @(
  'backend/phase3_services_pack.py',
  'mobile_flutter_client/lib/main.dart',
  'scripts/pull_faces_from_cloud.py'
)

foreach ($path in $paths) {
  if (-not (Test-Path (Join-Path $repoRoot $path))) {
    throw "Required file not found: $path"
  }
}

$gitArgs = @('add', '--') + $paths
& git -C $repoRoot @gitArgs
if ($LASTEXITCODE -ne 0) {
  throw 'git add failed'
}

$status = & git -C $repoRoot status --short -- $paths
if (-not $status) {
  Write-Host 'No changes to commit.'
  exit 0
}

& git -C $repoRoot commit -m $Message
if ($LASTEXITCODE -ne 0) {
  throw 'git commit failed'
}

if (-not $NoPush) {
  & git -C $repoRoot push
  if ($LASTEXITCODE -ne 0) {
    throw 'git push failed'
  }
}
