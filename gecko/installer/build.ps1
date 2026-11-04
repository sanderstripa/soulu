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
$adapter=Join-Path $core 'adapters/soulu'
Copy-Item (Join-Path $PSScriptRoot 'adapter_windows.go') (Join-Path $adapter 'adapter_windows.go') -Force
# CEF-specific adapter tests do not apply to the Gecko integrity manifest.
Get-ChildItem $adapter -Filter '*_test.go' | Remove-Item
Copy-Item (Join-Path $PSScriptRoot 'payload_windows_test.go') $adapter
$product=Get-Content (Join-Path $core 'products/soulu.json') -Raw | ConvertFrom-Json
$product.name='Soulu Gecko';$product.version='0.8.0-preview8';$product.id='soulu-gecko';$product.engine='Firefox Gecko; verified isolated runtime'
$product | ConvertTo-Json | Set-Content (Join-Path $core 'products/soulu.json') -Encoding utf8
$build=(Resolve-Path $BuildDir).Path
python (Join-Path $PSScriptRoot 'prepare-payload.py') $build
if($LASTEXITCODE){throw 'Payload manifest failed'}
Compress-Archive -Path (Join-Path $build '*') -DestinationPath (Join-Path $adapter 'payload.zip') -CompressionLevel Optimal
$version=Get-Content (Join-Path $repo 'gecko/launcher/versioninfo.json') -Raw | ConvertFrom-Json
$version.StringFileInfo.FileDescription='Soulu Gecko Preview 8 Setup'
$version.StringFileInfo.InternalName='SouluGeckoSetup'
$version.StringFileInfo.OriginalFilename='Soulu-Gecko-Preview-8-Setup-win64.exe'
$version.IconPath=(Join-Path $repo 'ui/soulu-installer-icon.ico')
$version | Add-Member -NotePropertyName ManifestPath -NotePropertyValue (Join-Path $core 'products/soulu.manifest')
$version | ConvertTo-Json -Depth 10 | Set-Content (Join-Path $core 'versioninfo.json') -Encoding utf8NoBOM
$output=[IO.Path]::GetFullPath($OutFile)
$env:CGO_ENABLED='0'
Push-Location $core
try{
 gofmt -w adapters/soulu/adapter_windows.go adapters/soulu/payload_windows_test.go
 $oldTest=$env:CONNECT_INSTALLER_CI_TEST;$env:CONNECT_INSTALLER_CI_TEST='1'
 go test -ldflags '-X connect-installer.local/core/products.VersionOverride=0.8.0-preview8' ./core ./installprefs ./products ./adapters/soulu
 $testExit=$LASTEXITCODE;$env:CONNECT_INSTALLER_CI_TEST=$oldTest
 if($testExit){throw 'Installer component tests failed'}
 go run github.com/josephspurrier/goversioninfo/cmd/goversioninfo@v1.5.0 -64 -o cmd/soulu/resources_windows_amd64.syso
 if($LASTEXITCODE){throw 'Installer version/icon resources failed'}
 go build -tags production -trimpath -buildvcs=false -ldflags '-s -w -H windowsgui -X connect-installer.local/core/products.VersionOverride=0.8.0-preview8' -o $output ./cmd/soulu
 if($LASTEXITCODE){throw 'Installer compilation failed'}
 [ordered]@{name='Soulu Gecko Preview 8';version='0.8.0-preview8';coreCommit=$coreCommit;sourceCommit=(git -C $repo rev-parse HEAD).Trim();installerSHA256=(Get-FileHash $output -Algorithm SHA256).Hash.ToLowerInvariant();payloadSHA256=(Get-FileHash adapters/soulu/payload.zip -Algorithm SHA256).Hash.ToLowerInvariant()} | ConvertTo-Json | Set-Content "$output.build.json" -Encoding utf8
}finally{Pop-Location}
