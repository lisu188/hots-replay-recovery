param(
    [ValidateSet('Run', 'Collect')][string]$Mode = 'Run',
    [string]$GameDirectory = '',
    [string]$GameDocuments = '',
    [string]$MapPath = '',
    [string]$OutputDirectory = ''
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$Token = 'HRC98285_20260929_P1'
$ExpectedMapHash = 'a1bc4403fe3f60c6af067ea8ed8a0131ed1d2feaafd1157fe7a1cf5a899d486a'
if (-not $GameDirectory) { $GameDirectory = Join-Path ${env:ProgramFiles(x86)} 'Heroes of the Storm' }
if (-not $GameDocuments) { $GameDocuments = Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'Heroes of the Storm' }
if (-not $MapPath) { $MapPath = Join-Path $PSScriptRoot 'TEN_GREYMANE_CATALOG_PROBE_98285.StormMap' }
if (-not $OutputDirectory) { $OutputDirectory = Join-Path $PSScriptRoot ('catalog-output-' + (Get-Date -Format 'yyyyMMdd-HHmmss')) }
if (-not (Test-Path -LiteralPath $GameDocuments -PathType Container)) { throw 'HotS documents directory not found. Supply -GameDocuments explicitly.' }
$Started = (Get-Date).ToUniversalTime()
$Launched = $false
$MapHash = $null

if ($Mode -eq 'Run') {
    $MapPath = (Resolve-Path -LiteralPath $MapPath).Path
    $MapHash = (Get-FileHash -LiteralPath $MapPath -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($MapHash -ne $ExpectedMapHash) { throw 'Diagnostic map digest mismatch. Nothing was launched.' }
    $Switcher = Join-Path $GameDirectory 'Support64\HeroesSwitcher_x64.exe'
    if (-not (Test-Path -LiteralPath $Switcher -PathType Leaf)) { throw 'HeroesSwitcher_x64.exe not found. Supply -GameDirectory explicitly.' }
    $Running = @(Get-Process -Name 'HeroesOfTheStorm_x64', 'HeroesOfTheStorm' -ErrorAction SilentlyContinue)
    if ($Running.Count -gt 0) { throw 'Close Heroes of the Storm first. This script will not terminate your game.' }
    Write-Host 'Launching a separate diagnostic map, NOT the recovered match. No installation files are replaced.'
    Write-Host 'Wait for HOTS CATALOG PROBE: export requested. Then leave the map.'
    Start-Process -FilePath $Switcher -ArgumentList ('"' + $MapPath + '"') -WorkingDirectory $GameDirectory | Out-Null
    $Launched = $true
    Read-Host 'After leaving the diagnostic map, press Enter to collect the probe bank files' | Out-Null
}

$Manifests = @()
foreach ($Subdirectory in @('Banks', 'Accounts')) {
    $Root = Join-Path $GameDocuments $Subdirectory
    if (Test-Path -LiteralPath $Root -PathType Container) {
        $Manifests += @(Get-ChildItem -LiteralPath $Root -Filter ($Token + '_Manifest.StormBank') -File -Recurse)
    }
}
if ($Manifests.Count -eq 0) { throw 'No probe manifest was found. The diagnostic has not produced a usable export; retain any map error or screenshot.' }
$Manifest = $Manifests | Sort-Object LastWriteTimeUtc -Descending | Select-Object -First 1
if ($Launched -and $Manifest.LastWriteTimeUtc -lt $Started.AddSeconds(-5)) { throw 'Only an older probe export exists. This run did not produce a fresh manifest.' }
$Banks = @(Get-ChildItem -LiteralPath $Manifest.DirectoryName -Filter ($Token + '_*.StormBank') -File)
if ($Banks.Count -gt 129) { throw 'Unexpected bank file count.' }
if (@($Banks | Where-Object { $_.Length -gt 4MB -or ($_.Attributes -band [IO.FileAttributes]::ReparsePoint) }).Count -gt 0) { throw 'Oversized or linked bank input rejected.' }
if (($Banks | Measure-Object Length -Sum).Sum -gt 32MB) { throw 'Probe export exceeds the collection limit.' }
if (Test-Path -LiteralPath $OutputDirectory) { throw 'Output already exists; choose a new directory.' }
$ZipPath = $OutputDirectory + '.zip'
if (Test-Path -LiteralPath $ZipPath) { throw 'Output ZIP already exists.' }
New-Item -ItemType Directory -Path $OutputDirectory | Out-Null
$Digests = @()
foreach ($Bank in $Banks) {
    $Destination = Join-Path $OutputDirectory $Bank.Name
    Copy-Item -LiteralPath $Bank.FullName -Destination $Destination -ErrorAction Stop
    $Digests += [ordered]@{ name = $Bank.Name; sha256 = (Get-FileHash -LiteralPath $Destination -Algorithm SHA256).Hash.ToLowerInvariant(); bytes = $Bank.Length }
}
$VersionLines = @()
$LogFresh = $false
$Logs = Join-Path $GameDocuments 'GameLogs'
if (Test-Path -LiteralPath $Logs -PathType Container) {
    $Latest = Get-ChildItem -LiteralPath $Logs -Filter '*Graphics.txt' -File | Sort-Object LastWriteTimeUtc -Descending | Select-Object -First 1
    if ($null -ne $Latest) {
        $LogFresh = $Launched -and $Latest.LastWriteTimeUtc -ge $Started.AddSeconds(-5)
        $VersionLines = @(Get-Content -LiteralPath $Latest.FullName | Where-Object { $_ -match '(<Version>|<DataBuild>|LocalTime|Heroes of the Storm \(B)' })
    }
}
$Context = [ordered]@{
    format = 'hots-runtime-probe-collection-v1'
    token = $Token
    expected_build = 98285
    map_sha256 = $MapHash
    launched_by_this_invocation = $Launched
    launch_utc = $Started.ToString('o')
    graphics_log_fresh_for_launch = $LogFresh
    observed_version_lines = $VersionLines
    input_banks = $Digests
    export_contents_validated = $false
    runtime_catalog_context_validated = $false
    client_playback_validated = $false
}
$Context | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $OutputDirectory 'collection-context.json') -Encoding UTF8
Compress-Archive -LiteralPath @(Get-ChildItem -LiteralPath $OutputDirectory -File | ForEach-Object { $_.FullName }) -DestinationPath $ZipPath
Write-Host ('Collected ' + $Banks.Count + ' probe files into ' + $ZipPath)
Write-Host 'Collection is not validation. Keep the original banks for independent completeness and catalog-anchor checks.'
