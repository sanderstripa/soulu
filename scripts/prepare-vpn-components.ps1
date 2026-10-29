param([Parameter(Mandatory=$true)][string]$Destination)
$ErrorActionPreference='Stop'
$source=Join-Path $PSScriptRoot '../vpn'
$pins=Get-Content (Join-Path $source 'components-pin.json') -Raw | ConvertFrom-Json
New-Item -ItemType Directory -Force $Destination | Out-Null
$stamps=@{}
foreach($id in @('xray','sudoku')){
 $pin=$pins.$id
 if($pin.url -notmatch ('^https://github.com/'+[regex]::Escape($pin.repository)+'/releases/download/') -or $pin.sha256 -notmatch '^[a-f0-9]{64}$'){throw 'Invalid VPN component pin'}
 $temp=Join-Path $env:RUNNER_TEMP ('soulu-core-'+[guid]::NewGuid().ToString('N'))
 New-Item -ItemType Directory -Force $temp | Out-Null
 try{
  $archive=Join-Path $temp 'core.zip';Invoke-WebRequest $pin.url -OutFile $archive
  if((Get-FileHash $archive -Algorithm SHA256).Hash.ToLowerInvariant() -cne $pin.sha256){throw "$id archive digest mismatch"}
  $unpacked=Join-Path $temp 'expanded';Expand-Archive $archive $unpacked
  $exe=Get-ChildItem $unpacked -Filter "$id.exe" -File -Recurse
  if(@($exe).Count -ne 1){throw "$id executable missing or duplicated"}
  $target=Join-Path $Destination $id;New-Item -ItemType Directory -Force $target | Out-Null
  Copy-Item $exe.FullName (Join-Path $target "$id.exe") -Force
  foreach($data in @('geoip.dat','geosite.dat')){Get-ChildItem $unpacked -Filter $data -File -Recurse | Select-Object -First 1 | ForEach-Object {Copy-Item $_.FullName (Join-Path $target $data) -Force}}
  $stamps[$id]=@{version=$pin.version;sha256=(Get-FileHash (Join-Path $target "$id.exe") -Algorithm SHA256).Hash.ToLowerInvariant()}
 }finally{Remove-Item $temp -Recurse -Force -ErrorAction SilentlyContinue}
}
$stamps|ConvertTo-Json -Depth 5|Set-Content (Join-Path $Destination 'components.json') -Encoding utf8NoBOM
Push-Location (Join-Path $source 'helper')
try{
 $env:SOULU_VPN_FIXTURE_BIN = (Resolve-Path $Destination).Path
 go test -v ./...
 if($LASTEXITCODE -ne 0){throw 'VPN helper tests failed'}
 $targetExe=Join-Path (Resolve-Path $Destination).Path 'SouluVpnHost.exe'
 go build -trimpath -ldflags '-s -w' -o $targetExe .
 if($LASTEXITCODE -ne 0){throw 'VPN helper build failed'}
}finally{Remove-Item Env:SOULU_VPN_FIXTURE_BIN -ErrorAction SilentlyContinue;Pop-Location}
