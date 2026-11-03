[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)][string]$WorkRoot,
  [ValidateRange(1,64)][int]$Jobs = 8,
  [switch]$PrepareOnly
)
$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent
$lock = Get-Content "$PSScriptRoot/source-lock.json" -Raw | ConvertFrom-Json
function Invoke-Checked {
  param([string]$Program, [string[]]$Arguments)
  & $Program @Arguments
  if ($LASTEXITCODE -ne 0) { throw "$Program exited with $LASTEXITCODE" }
}
if (!(Test-Path "$repo/.git")) { throw 'Use a git checkout of Soulu' }
$branch = (& git -C $repo branch --show-current).Trim()
if ($branch -cne 'chromium-preview') { throw 'Build only the chromium-preview branch' }
Invoke-Checked python @("$PSScriptRoot/check_builder.py", '--work-root', $WorkRoot,
  '--output', "$repo/chromium-environment.json")
New-Item -ItemType Directory -Force $WorkRoot | Out-Null
$WorkRoot = (Resolve-Path $WorkRoot).Path
$depot = Join-Path $WorkRoot 'depot_tools'
$checkout = Join-Path $WorkRoot 'chromium'
$src = Join-Path $checkout 'src'
$env:DEPOT_TOOLS_UPDATE = '0'
$env:DEPOT_TOOLS_WIN_TOOLCHAIN = '0'
if (!(Test-Path "$depot/.git")) {
  Invoke-Checked git @('clone', '--no-checkout', $lock.depot_tools.url, $depot)
  Invoke-Checked git @('-C', $depot, 'checkout', '--detach', $lock.depot_tools.revision)
}
$actualDepot = (& git -C $depot rev-parse HEAD).Trim()
if ($actualDepot -cne $lock.depot_tools.revision) { throw 'Existing depot_tools differs from source lock' }
$env:PATH = "$depot;$env:PATH"
New-Item -ItemType Directory -Force $checkout | Out-Null
if (!(Test-Path "$src/.git")) {
  Invoke-Checked git @('init', $src)
  Invoke-Checked git @('-C', $src, 'remote', 'add', 'origin', $lock.chromium.url)
  Invoke-Checked git @('-C', $src, '-c', 'core.longpaths=true', 'fetch', '--depth=1', 'origin', $lock.chromium.revision)
  Invoke-Checked git @('-C', $src, 'checkout', '--detach', 'FETCH_HEAD')
}
$actual = (& git -C $src rev-parse HEAD).Trim()
if ($actual -cne $lock.chromium.revision) { throw 'Existing Chromium checkout differs from source lock; use a separate work root' }
$gclient = "solutions = [{'name': 'src', 'url': '$($lock.chromium.url)', 'managed': False, 'custom_deps': {}, 'custom_vars': {}}]`ntarget_os = ['win']`n"
$gclientPath = Join-Path $checkout '.gclient'
if (Test-Path $gclientPath) {
  if ((Get-Content $gclientPath -Raw) -cne $gclient) { throw 'Existing .gclient differs; refusing to replace it' }
} else { [IO.File]::WriteAllText($gclientPath, $gclient) }
Push-Location $checkout
try {
  Invoke-Checked gclient.bat @('sync', '--no-history', '--revision', "src@$($lock.chromium.revision)")
} finally { Pop-Location }
Invoke-Checked python @("$PSScriptRoot/prepare_source.py", '--chromium-src', $src)
if ($PrepareOnly) { Write-Host 'Source prepared only; browser not built.'; return }
Push-Location $src
try {
  $out = Join-Path $src 'out/Soulu'
  New-Item -ItemType Directory -Force $out | Out-Null
  Copy-Item "$PSScriptRoot/args.gn" "$out/args.gn" -Force
  Invoke-Checked gn.bat @('gen', 'out/Soulu')
  Invoke-Checked autoninja.bat @('-C', 'out/Soulu', 'chrome', '-j', "$Jobs")
  $result = [ordered]@{
    product = 'Soulu Chromium Preview 1 development build'
    chromium = $lock.chromium
    soulu_commit = (& git -C $repo rev-parse HEAD).Trim()
    native_compilation = 'passed'
    runtime_acceptance = 'NOT RUN'
    mandatory_features_complete = $false
    release_ready = $false
  }
  $result | ConvertTo-Json -Depth 10 | Set-Content "$repo/chromium-build-result.json" -Encoding utf8
  Write-Host "Compiled: $out/chrome.exe. No accepted portable ZIP has been produced."
} finally { Pop-Location }
