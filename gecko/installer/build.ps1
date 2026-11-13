param([Parameter(Mandatory=$true)][string]$BuildDir,[Parameter(Mandatory=$true)][string]$OutFile)
$ErrorActionPreference='Stop'
$repo=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$coreCommit='589669b4dec6411cc31ec6c99d29dbbde7ab7fe8'
$checkout=Join-Path $repo '.gecko-installer-source'
if(Test-Path $checkout){throw 'Installer checkout must start empty'}
git init $checkout
git -C $checkout remote add origin https://github.com/sanderstripa/connect.git
git -C $checkout fetch --depth 1 origin $coreCommit
if($LASTEXITCODE){throw 'Installer source clone failed'}
git -C $checkout checkout --detach $coreCommit
if($LASTEXITCODE){throw 'Pinned installer checkout failed'}
$core=Join-Path $checkout 'installer-core'
python (Join-Path $repo 'gecko/rename-owned.py') $core
if($LASTEXITCODE){throw 'Installer identity conversion failed'}
$adapter=Join-Path $core 'adapters/sona'
Copy-Item (Join-Path $PSScriptRoot 'adapter_windows.go') (Join-Path $adapter 'adapter_windows.go') -Force
$migration=[IO.File]::ReadAllText((Join-Path $repo 'gecko/launcher/migration.go')).Replace('package main','package sona')
[IO.File]::WriteAllText((Join-Path $adapter 'migration.go'),$migration,[Text.UTF8Encoding]::new($false))
# CEF-specific adapter tests do not apply to the Gecko integrity manifest.
Get-ChildItem $adapter -Filter '*_test.go' | Remove-Item
Copy-Item (Join-Path $PSScriptRoot 'payload_windows_test.go') $adapter
Copy-Item (Join-Path $PSScriptRoot 'repair_windows_test.go') $adapter
Copy-Item (Join-Path $PSScriptRoot 'migration_windows.go') $adapter
$product=Get-Content (Join-Path $core 'products/sona.json') -Raw | ConvertFrom-Json
$product.name='Sona';$product.version='1.160.31';$product.id='sona';$product.engine='Sona'
$product | ConvertTo-Json | Set-Content (Join-Path $core 'products/sona.json') -Encoding utf8
Copy-Item (Join-Path $repo 'ui/branding/sona-128.png') (Join-Path $core 'core/web/assets/icon.png') -Force
python (Join-Path $PSScriptRoot 'prepare-theme23.py') $core $BuildDir
if($LASTEXITCODE){throw 'Sona installer presentation failed'}
$uiPath=Join-Path $core 'core/web/setup.js'
$ui=[IO.File]::ReadAllText($uiPath)
$ui=$ui.Replace('Выйдите из CONNECT через меню трея, отключите расширение Chrome и повторите.','Закройте все окна CONNECT и повторите.').Replace('Quit CONNECT from its tray menu, disconnect the Chrome extension and retry.','Close all CONNECT windows and retry.').Replace('Ваши соединения и настройки сохранятся. Перед удалением выйдите из CONNECT через меню трея.','Ваши профили, история и закладки сохранятся. Перед удалением закройте CONNECT.').Replace('Your connections and settings will be kept. Quit CONNECT from its tray menu before uninstalling.','Your profiles, history and bookmarks will be kept. Close CONNECT before uninstalling.')
[IO.File]::WriteAllText($uiPath,$ui,[Text.UTF8Encoding]::new($false))

$build=(Resolve-Path $BuildDir).Path
python (Join-Path $PSScriptRoot 'prepare-payload.py') $build
if($LASTEXITCODE){throw 'Payload manifest failed'}
Compress-Archive -Path (Join-Path $build '*') -DestinationPath (Join-Path $adapter 'payload.zip') -CompressionLevel Optimal
$version=Get-Content (Join-Path $repo 'gecko/launcher/versioninfo.json') -Raw | ConvertFrom-Json
$version.StringFileInfo.FileDescription='Sona Preview 1.160.31 Setup'
$version.StringFileInfo.InternalName='SonaSetup'
$version.StringFileInfo.OriginalFilename='Sona-1.160.31-Preview-x64.exe'
$version.IconPath=(Join-Path $repo 'ui/sona-installer-icon.ico')
$version | Add-Member -NotePropertyName ManifestPath -NotePropertyValue (Join-Path $core 'products/sona.manifest')
$version | ConvertTo-Json -Depth 10 | Set-Content (Join-Path $core 'versioninfo.json') -Encoding utf8NoBOM
$output=[IO.Path]::GetFullPath($OutFile)
$env:CGO_ENABLED='0'
Push-Location $core
try{
 gofmt -w adapters/sona/adapter_windows.go adapters/sona/payload_windows_test.go
 $oldTest=$env:CONNECT_INSTALLER_CI_TEST;$env:CONNECT_INSTALLER_CI_TEST='1'
 go test -ldflags '-X connect-installer.local/core/products.VersionOverride=1.160.31' ./core ./installprefs ./products ./adapters/sona
 $testExit=$LASTEXITCODE;$env:CONNECT_INSTALLER_CI_TEST=$oldTest
 if($testExit){throw 'Installer component tests failed'}
 go run github.com/josephspurrier/goversioninfo/cmd/goversioninfo@v1.5.0 -64 -o cmd/sona/resources_windows_amd64.syso
 if($LASTEXITCODE){throw 'Installer version/icon resources failed'}
 go build -tags production -trimpath -buildvcs=false -ldflags '-s -w -H windowsgui -X connect-installer.local/core/products.VersionOverride=1.160.31' -o $output ./cmd/sona
 if($LASTEXITCODE){throw 'Installer compilation failed'}
 [ordered]@{name='Sona Preview 1.160.31';version='1.160.31';coreCommit=$coreCommit;sourceCommit=(git -C $repo rev-parse HEAD).Trim();installerSHA256=(Get-FileHash $output -Algorithm SHA256).Hash.ToLowerInvariant();payloadSHA256=(Get-FileHash adapters/sona/payload.zip -Algorithm SHA256).Hash.ToLowerInvariant()} | ConvertTo-Json | Set-Content "$output.build.json" -Encoding utf8
}finally{Pop-Location}

