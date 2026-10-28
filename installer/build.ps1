param([Parameter(Mandatory=$true)][string]$BuildDir,[Parameter(Mandatory=$true)][string]$OutFile,[string]$PayloadZip,[switch]$TestUI)
$ErrorActionPreference='Stop'
$root=(Resolve-Path (Join-Path $PSScriptRoot '..')).Path
& (Join-Path $root 'scripts/verify-cef-engine.ps1') -BuildDir $BuildDir
$payload=if($PayloadZip){$PayloadZip}else{$BuildDir}
& (Join-Path $root 'scripts/build-connect-installer.ps1') -PayloadPath $payload -Version '1.0.65-beta' -OutFile $OutFile -TestUI:$TestUI
