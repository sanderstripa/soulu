param(
 [Parameter(Mandatory=$true)][string]$PayloadPath,
 [string]$Version,
 [Parameter(Mandatory=$true)][string]$OutFile,
 [string]$ExtensionPath,[string]$ExpectedExecutable,[string]$CoreRoot,[string]$Go='go',
 [switch]$TestUI
)
$ErrorActionPreference='Stop'
$repo=(Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$canonicalVersion=& (Join-Path $repo 'scripts/get-soulu-version.ps1')
if($Version -and $Version -cne $canonicalVersion){throw 'Installer version must match the canonical Soulu version'}
$Version=$canonicalVersion
if(!$CoreRoot){
 $localCore=Join-Path $repo 'installer-core'
 if(Test-Path (Join-Path $localCore 'build.ps1')){$CoreRoot=$localCore}
 else{
  $pin=Get-Content (Join-Path $repo 'installer-core.json') -Raw | ConvertFrom-Json
  if($pin.repository -ne 'sanderstripa/connect' -or $pin.commit -notmatch '^[a-f0-9]{40}$'){throw 'Invalid shared installer pin'}
  $checkout=Join-Path $repo '.connect-installer-source'
  if(!(Test-Path (Join-Path $checkout '.git'))){
   git init $checkout
   if($LASTEXITCODE){throw 'Core checkout initialization failed'}
   git -C $checkout remote add origin "https://github.com/$($pin.repository).git"
   if($LASTEXITCODE){throw 'Core remote setup failed'}
  }
  $current=git -C $checkout rev-parse HEAD 2>$null
  if($current -ne $pin.commit){
   if(git -C $checkout status --porcelain --untracked-files=no){throw 'Shared core has local source changes'}
   git -C $checkout fetch --depth 1 origin $pin.commit
   if($LASTEXITCODE){throw 'Pinned installer core fetch failed'}
   git -C $checkout checkout --detach $pin.commit
   if($LASTEXITCODE){throw 'Pinned installer core checkout failed'}
  }
  if((git -C $checkout rev-parse HEAD) -ne $pin.commit){throw 'Installer core revision mismatch'}
  $CoreRoot=Join-Path $checkout 'installer-core'
 }
}
$core=(Resolve-Path -LiteralPath $CoreRoot).Path
$sourceCommit=(git -C $repo rev-parse HEAD).Trim()
# The shared core pin predates the engine update. Specialize only Soulu's
# exact distribution allowlist, and restore the pinned source even on failure.
$adapterPath=Join-Path $core 'adapters/soulu/adapter_windows.go'
$adapterBytes=[IO.File]::ReadAllBytes($adapterPath)
$adapterText=[Text.Encoding]::UTF8.GetString($adapterBytes).Replace("`r`n","`n")
$sourceHash=[Convert]::ToHexString([Security.Cryptography.SHA256]::HashData([Text.Encoding]::UTF8.GetBytes($adapterText))).ToLowerInvariant()
if($sourceHash -cne 'e9e76a112beb145b3f09d0a4f19213ed8019db4d0c2620addd2aee311270a0b4'){throw 'Shared Soulu adapter source changed; review engine specialization'}
$oldDistribution='154.0.33+ga03e714+chromium-154.0.8037.94'
$distribution='156.0.14+g4fa4ab5+chromium-156.0.8078.48'
if(([regex]::Matches($adapterText,[regex]::Escape($oldDistribution))).Count -ne 1){throw 'Expected exactly one shared engine allowlist'}
$adapterText=$adapterText.Replace($oldDistribution,$distribution)
$testPath=Join-Path $core 'adapters/soulu/engine_upgrade_windows_test.go'
if(Test-Path -LiteralPath $testPath){throw 'Unexpected installer engine test source already exists'}
try{
 [IO.File]::WriteAllText($adapterPath,$adapterText,[Text.UTF8Encoding]::new($false))
 Copy-Item -LiteralPath (Join-Path $repo 'installer/tests/engine_upgrade_windows_test.go') -Destination $testPath
 & (Join-Path $core 'build.ps1') -Product 'soulu' -PayloadPath $PayloadPath -Version $Version -OutFile $OutFile -ExtensionPath $ExtensionPath -ExpectedExecutable $ExpectedExecutable -ProductCommit $sourceCommit -Go $Go
 if($LASTEXITCODE){throw 'Shared installer build failed'}
 $manifestPath="$OutFile.build.json"
 $manifest=Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
 if($manifest.version -cne $canonicalVersion -or $manifest.productCommit -cne $sourceCommit){throw 'Built installer version/source does not match Soulu'}
 $manifest | Add-Member -NotePropertyName cefDistribution -NotePropertyValue $distribution
 $manifest | Add-Member -NotePropertyName souluAdapterSHA256 -NotePropertyValue (Get-FileHash -LiteralPath $adapterPath -Algorithm SHA256).Hash.ToLowerInvariant()
 $manifest | ConvertTo-Json | Set-Content -LiteralPath $manifestPath -Encoding utf8
 if($TestUI){& (Join-Path $core 'test-ui.ps1') -OutputDirectory (Join-Path $repo '.tmp/installer-review')}
}finally{
 [IO.File]::WriteAllBytes($adapterPath,$adapterBytes)
 Remove-Item -LiteralPath $testPath -Force -ErrorAction SilentlyContinue
}
