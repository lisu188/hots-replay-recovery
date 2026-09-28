param(
    [string[]]$ReplayRoot = @(),
    [int]$MinimumBuild = 98025
)

$ErrorActionPreference = 'Stop'
$Repository = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$Pinned = '9af3ea7150f1a8acb53464c92519a9bbcc7a3594'
$OldLocation = Get-Location
$OldPythonPath = $env:PYTHONPATH
$Git = (Get-Command git -ErrorAction Stop).Source
$PythonCommand = Get-Command py -ErrorAction SilentlyContinue
$PythonArgs = @('-3')
if (-not $PythonCommand) {
    $PythonCommand = Get-Command python -ErrorAction Stop
    $PythonArgs = @()
}

try {
    Set-Location $Repository
    & $PythonCommand.Source @PythonArgs -c 'import sys; sys.exit(0 if sys.version_info >= (3,11) else 1)'
    if ($LASTEXITCODE -ne 0) { throw 'Python 3.11 or newer is required.' }
    $Venv = Join-Path $Repository 'work/reference-venv'
    $Python = Join-Path $Venv 'Scripts/python.exe'
    if (-not (Test-Path -LiteralPath $Python)) {
        & $PythonCommand.Source @PythonArgs -m venv $Venv
        if ($LASTEXITCODE -ne 0) { throw 'Could not create the isolated Python environment.' }
    }
    & $Python -m pip install six==1.17.0 mpyq==0.2.5
    if ($LASTEXITCODE -ne 0) { throw 'Could not install the pinned parser dependencies.' }
    $Upstream = Join-Path $Repository '_upstream'
    if (-not (Test-Path -LiteralPath $Upstream)) {
        & $Git init $Upstream
        if ($LASTEXITCODE -ne 0) { throw 'Could not create the upstream checkout.' }
        & $Git -C $Upstream fetch --depth=1 https://github.com/Blizzard/heroprotocol.git $Pinned
        if ($LASTEXITCODE -ne 0) { throw 'Could not fetch the pinned Blizzard schema.' }
        & $Git -C $Upstream checkout --detach FETCH_HEAD
        if ($LASTEXITCODE -ne 0) { throw 'Could not check out the pinned Blizzard schema.' }
    }
    $Actual = (& $Git -C $Upstream rev-parse HEAD).Trim()
    if ($LASTEXITCODE -ne 0 -or $Actual -ne $Pinned) {
        throw 'Existing _upstream is not the pinned revision; it has not been overwritten.'
    }
    $Dirty = @(& $Git -C $Upstream status --porcelain --untracked-files=no)
    if ($LASTEXITCODE -ne 0 -or $Dirty.Count -ne 0) { throw 'The pinned upstream checkout has local changes.' }
    $env:PYTHONPATH = $Upstream + [IO.Path]::PathSeparator + $Repository
    if ($ReplayRoot.Count -eq 0) {
        $Documents = [Environment]::GetFolderPath('MyDocuments')
        $ReplayRoot += Join-Path $Documents 'Heroes of the Storm/Accounts'
        foreach ($Drive in @($env:OneDrive, $env:OneDriveConsumer, $env:OneDriveCommercial)) {
            if ($Drive) {
                $ReplayRoot += Join-Path $Drive 'Dokumenty/Heroes of the Storm/Accounts'
                $ReplayRoot += Join-Path $Drive 'Documents/Heroes of the Storm/Accounts'
            }
        }
    }
    $Roots = @($ReplayRoot | Where-Object { Test-Path -LiteralPath $_ -PathType Container } | Sort-Object -Unique)
    if ($Roots.Count -eq 0) { throw 'No replay folder was found. Pass its location with -ReplayRoot.' }
    $Output = Join-Path $Repository ('work/reference-input-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
    New-Item -ItemType Directory -Path $Output -ErrorAction Stop | Out-Null
    $Found = @()
    $Index = 0
    foreach ($Root in $Roots) {
        $Scan = Join-Path $Output ('private-scan-' + $Index + '.json')
        & $Python reference_replay.py scan $Root --minimum-build $MinimumBuild --output $Scan
        if ($LASTEXITCODE -ne 0) { throw 'Replay discovery failed.' }
        $Result = Get-Content -LiteralPath $Scan -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($Result.truncated) { Write-Warning 'The scan reached its file limit; narrow -ReplayRoot.' }
        $Found += @($Result.matches)
        $Index++
    }
    $Candidates = @($Found | Where-Object {
        $_.local_path -notmatch '[\\/]98-Hero-' -and $_.local_path -notmatch 'EXPERIMENTAL|protocol[0-9]+'
    } | Sort-Object -Property @{ Expression = { $_.target.m_version.m_build }; Descending = $true },
        @{ Expression = { $_.local_path }; Descending = $true } | Select-Object -First 5)
    $Selected = $null
    $Profile = Join-Path $Output 'reference-profile.json'
    foreach ($Candidate in $Candidates) {
        $Build = [int]$Candidate.target.m_version.m_build
        & $Python reference_replay.py inspect $Candidate.local_path --schema-build 96477 --expected-build $Build --output $Profile
        if ($LASTEXITCODE -eq 0) { $Selected = $Candidate; break }
    }
    if (-not $Selected) {
        throw 'No compatible modern reference was found. Save a new replay in the installed live client; no game file has been changed.'
    }
    $Replay = Join-Path $Output 'reference.StormReplay'
    Copy-Item -LiteralPath $Selected.local_path -Destination $Replay -ErrorAction Stop
    $Metadata = Get-Content -LiteralPath $Profile -Raw -Encoding UTF8 | ConvertFrom-Json
    if ((Get-FileHash -LiteralPath $Replay -Algorithm SHA256).Hash.ToLowerInvariant() -ne $Metadata.file_sha256) {
        throw 'The selected replay changed while being copied.'
    }
    $Zip = $Output + '.zip'
    Compress-Archive -LiteralPath $Replay, $Profile -DestinationPath $Zip -ErrorAction Stop
    Write-Output ('Declared build: ' + $Metadata.target.m_version.m_build)
    Write-Output ('Reference package: ' + $Zip)
    Write-Output 'The package remains local. No replay was uploaded and no game installation was modified.'
}
finally {
    $env:PYTHONPATH = $OldPythonPath
    Set-Location $OldLocation
}
