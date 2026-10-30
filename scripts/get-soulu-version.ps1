$ErrorActionPreference='Stop'
$repo=(Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$header=Get-Content (Join-Path $repo 'cef/soulu/app_version.h') -Raw
$matches=[regex]::Matches($header,'kSouluVersion\s*=\s*"([^"]+)"')
if($matches.Count -ne 1){throw 'Exactly one canonical Soulu version is required'}
$version=$matches[0].Groups[1].Value
$parts=[regex]::Match($version,'^(\d+)\.(\d+)\.(\d+)(?:-[0-9A-Za-z.-]+)?$')
if(!$parts.Success){throw 'Invalid canonical Soulu version'}
if($env:BETA_VERSION -and $env:BETA_VERSION -cne $version){throw 'BETA_VERSION must match the canonical Soulu version'}
if($env:BETA_NUMBER -and $env:BETA_NUMBER -cne $parts.Groups[3].Value){throw 'BETA_NUMBER must match the canonical Soulu patch version'}
$version
