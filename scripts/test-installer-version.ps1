$ErrorActionPreference='Stop'
$repo=(Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$canonical=& (Join-Path $PSScriptRoot 'get-soulu-version.ps1')
$oldVersion=$env:BETA_VERSION;$oldNumber=$env:BETA_NUMBER
$temp=Join-Path ([IO.Path]::GetTempPath()) ('soulu-version-test-'+[guid]::NewGuid())
function Reject([scriptblock]$action,[string]$message){try{& $action;throw 'Expected version mismatch was accepted'}catch{if($_.Exception.Message -notlike "*$message*"){throw}}}
try{
 Remove-Item Env:BETA_VERSION,Env:BETA_NUMBER -ErrorAction SilentlyContinue
 New-Item -ItemType Directory -Force "$temp/scripts","$temp/cef/soulu" | Out-Null
 Copy-Item (Join-Path $PSScriptRoot 'get-soulu-version.ps1') "$temp/scripts/"
 foreach($version in @('1.0.71-beta','2.3.456-beta.1','3.0.0')){
  "inline constexpr const char* kSouluVersion = `"$version`";" | Set-Content "$temp/cef/soulu/app_version.h"
  $actual=& "$temp/scripts/get-soulu-version.ps1"
  if($actual -cne $version){throw 'Version resolver uses stale hardcoded version'}
 }
 $env:BETA_VERSION='9.9.9'
 Reject {& (Join-Path $PSScriptRoot 'get-soulu-version.ps1')} 'BETA_VERSION must match'
 Remove-Item Env:BETA_VERSION
 $env:BETA_NUMBER='999'
 Reject {& (Join-Path $PSScriptRoot 'get-soulu-version.ps1')} 'BETA_NUMBER must match'
 Remove-Item Env:BETA_NUMBER
 Reject {& (Join-Path $PSScriptRoot 'build-connect-installer.ps1') -PayloadPath 'unused-fixture' -Version '1.0.67-beta' -OutFile 'unused-fixture.exe'} 'Installer version must match'
 Write-Host "PASS: canonical version $canonical; dynamic resolver; stale environment and installer overrides rejected before build"
}finally{
 $env:BETA_VERSION=$oldVersion;$env:BETA_NUMBER=$oldNumber
 Remove-Item $temp -Recurse -Force -ErrorAction SilentlyContinue
}
