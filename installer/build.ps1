param([Parameter(Mandatory=$true)][string]$BuildDir,[Parameter(Mandatory=$true)][string]$OutFile,[string]$PayloadZip,[switch]$TestUI)
$ErrorActionPreference='Stop'
$root=(Resolve-Path (Join-Path $PSScriptRoot '..')).Path
& (Join-Path $root 'scripts/verify-cef-engine.ps1') -BuildDir $BuildDir
$version=& (Join-Path $root 'scripts/get-soulu-version.ps1')
$payload=if($PayloadZip){$PayloadZip}else{$BuildDir}
& (Join-Path $root 'scripts/build-connect-installer.ps1') -PayloadPath $payload -Version $version -OutFile $OutFile -TestUI:$TestUI
