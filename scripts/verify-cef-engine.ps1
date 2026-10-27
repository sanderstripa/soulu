param(
  [Parameter(Mandatory=$true)][string]$BuildDir,
  [string]$ReportPath,
  [string]$DistributionDir
)
$ErrorActionPreference = 'Stop'
$build = (Resolve-Path -LiteralPath $BuildDir).Path
$exe = Join-Path $build 'Soulu.exe'
$dll = Join-Path $build 'libcef.dll'
if (!(Test-Path -LiteralPath $exe) -or !(Test-Path -LiteralPath $dll)) {
  throw 'Soulu.exe or bundled libcef.dll is missing'
}
$manifestPath = Join-Path $build 'cef-runtime-manifest.json'
if ($DistributionDir) {
  $distribution = (Resolve-Path -LiteralPath $DistributionDir).Path
  $names = (Get-Content (Join-Path $build 'cef-runtime-list.txt') -Raw).Split(';')
  $files = @()
  foreach ($name in $names) {
    $source = Join-Path $distribution "Release/$name"
    if (!(Test-Path -LiteralPath $source)) { $source = Join-Path $distribution "Resources/$name" }
    if (!(Test-Path -LiteralPath $source)) { throw "CEF distribution component missing: $name" }
    if ((Get-Item -LiteralPath $source).PSIsContainer) {
      foreach ($file in Get-ChildItem -LiteralPath $source -Recurse -File) {
        $relative = $name + '/' + [IO.Path]::GetRelativePath($source, $file.FullName).Replace('\', '/')
        $files += @{ path = $relative; sha256 = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash }
      }
    } else {
      $files += @{ path = $name; sha256 = (Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash }
    }
  }
  @{ distribution = '156.0.14+g4fa4ab5+chromium-156.0.8078.48'; files = $files } |
    ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $manifestPath -Encoding utf8
}
if (!(Test-Path -LiteralPath $manifestPath)) { throw 'CEF runtime manifest is missing' }
$manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
if ($manifest.distribution -cne '156.0.14+g4fa4ab5+chromium-156.0.8078.48') {
  throw 'CEF runtime manifest belongs to another distribution'
}
foreach ($file in $manifest.files) {
  $runtimeFile = Join-Path $build $file.path
  if (!(Test-Path -LiteralPath $runtimeFile) -or
      (Get-FileHash -LiteralPath $runtimeFile -Algorithm SHA256).Hash -cne $file.sha256) {
    throw "CEF runtime component is missing or mixed: $($file.path)"
  }
}
$probe = Join-Path ([IO.Path]::GetTempPath()) ("soulu-engine-" + [guid]::NewGuid() + ".json")
try {
  $process = Start-Process -FilePath $exe -WorkingDirectory $build -WindowStyle Hidden -PassThru -ArgumentList @("--engine-version-file=`"$probe`"")
  if (!$process.WaitForExit(30000)) {
    $process.Kill()
    throw 'Engine version probe timed out'
  }
  if ($process.ExitCode -ne 0 -or !(Test-Path -LiteralPath $probe)) {
    throw "Engine version probe failed: exit $($process.ExitCode)"
  }
  $version = Get-Content -LiteralPath $probe -Raw | ConvertFrom-Json
  if ($version.cef -cne '156.0.14' -or $version.chromium -cne '156.0.8078.48' -or
      $version.cef_build -cne '156.0.14+g4fa4ab5+chromium-156.0.8078.48') {
    throw "Unsupported engine: CEF $($version.cef), Chromium $($version.chromium)"
  }
  $report = [ordered]@{
    cef = $version.cef
    cef_build = $version.cef_build
    chromium = $version.chromium
    commit = $env:GITHUB_SHA
    run_id = $env:GITHUB_RUN_ID
    soulu_sha256 = (Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash
    libcef_sha256 = (Get-FileHash -LiteralPath $dll -Algorithm SHA256).Hash
    distribution = $manifest.distribution
    runtime_files_verified = @($manifest.files).Count
    manifest_sha256 = (Get-FileHash -LiteralPath $manifestPath -Algorithm SHA256).Hash
  }
  $json = $report | ConvertTo-Json
  Write-Host $json
  if ($ReportPath) { $json | Set-Content -LiteralPath $ReportPath -Encoding utf8 }
} finally {
  Remove-Item -LiteralPath $probe -Force -ErrorAction SilentlyContinue
}
