param(
    [string]$GameDocuments = '',
    [string]$OutputDirectory = ''
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$Token = 'HRC98285_20260929_P1'
$Warnings = New-Object 'System.Collections.Generic.List[string]'
$Utf8 = New-Object System.Text.UTF8Encoding($false)
if (-not $GameDocuments) { $GameDocuments = Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'Heroes of the Storm' }
if (-not $OutputDirectory) { $OutputDirectory = Join-Path $PSScriptRoot ('catalog-diagnostics-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '-' + [guid]::NewGuid().ToString('N').Substring(0, 8)) }
$ZipPath = $OutputDirectory + '.zip'
if ((Test-Path -LiteralPath $OutputDirectory) -or (Test-Path -LiteralPath $ZipPath)) { throw 'Diagnostic output already exists; no existing file was replaced.' }

function Is-Linked([IO.FileSystemInfo]$Item) {
    return [bool]($Item.Attributes -band [IO.FileAttributes]::ReparsePoint)
}

function Get-BoundedFiles([string]$Root, [int]$MaxDepth = 8) {
    if (-not (Test-Path -LiteralPath $Root -PathType Container)) { return }
    $RootItem = Get-Item -LiteralPath $Root -Force
    if (Is-Linked $RootItem) { $Warnings.Add('linked_input_root_ignored'); return }
    $Queue = New-Object 'System.Collections.Generic.Queue[object]'
    $Queue.Enqueue(@{ path = $RootItem.FullName; depth = 0 })
    $Visited = 0
    while ($Queue.Count -gt 0) {
        $Node = $Queue.Dequeue()
        try { $Children = @(Get-ChildItem -LiteralPath $Node.path -Force -ErrorAction Stop) }
        catch { $Warnings.Add('unreadable_input_directory'); continue }
        foreach ($Child in $Children) {
            $Visited++
            if ($Visited -gt 10000) { $Warnings.Add('input_enumeration_limit_reached'); return }
            if (Is-Linked $Child) { $Warnings.Add('linked_input_ignored'); continue }
            if ($Child.PSIsContainer) {
                if ($Node.depth -lt $MaxDepth) { $Queue.Enqueue(@{ path = $Child.FullName; depth = $Node.depth + 1 }) }
                else { $Warnings.Add('input_depth_limit_reached') }
            }
            else { $Child }
        }
    }
}

function Scrub-Line([string]$Line) {
    if ($Line -match '(?i)(password|authorization|cookie|access_token|refresh_token)') { return '[credential-like line omitted]' }
    $Clean = [regex]::Replace($Line, '(?i)[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}', '[email]')
    $Clean = [regex]::Replace($Clean, '"(?:[A-Za-z]:\\|\\\\)[^"]*"', '"[absolute path]"')
    $Clean = [regex]::Replace($Clean, '(?:[A-Za-z]:\\|\\\\)[^\r\n]*', '[absolute path]')
    if ($Clean.Length -gt 1024) { $Clean = $Clean.Substring(0, 1024) + ' [truncated]' }
    return $Clean
}

$DocumentsExist = Test-Path -LiteralPath $GameDocuments -PathType Container
$Banks = @()
$Logs = @()
$LastReplay = $null
if ($DocumentsExist -and -not (Is-Linked (Get-Item -LiteralPath $GameDocuments -Force))) {
    foreach ($Subdirectory in @('Banks', 'Accounts')) {
        $Banks += @(Get-BoundedFiles (Join-Path $GameDocuments $Subdirectory) | Where-Object { $_.Name -cmatch ('^' + $Token + '_(Manifest|Unit_[0-9]+|Abil_[0-9]+)\.StormBank$') })
    }
    foreach ($Subdirectory in @('GameLogs', 'UserLogs')) {
        $Logs += @(Get-BoundedFiles (Join-Path $GameDocuments $Subdirectory) | Where-Object { $_.Extension -match '^\.(txt|log)$' })
    }
    $Variables = Join-Path $GameDocuments 'Variables.txt'
    if (Test-Path -LiteralPath $Variables -PathType Leaf) {
        $V = Get-Item -LiteralPath $Variables -Force
        if (-not (Is-Linked $V) -and $V.Length -le 1MB) {
            try {
                $Match = [regex]::Match([IO.File]::ReadAllText($V.FullName), '(?m)^lastReplayFilePath=([^\r\n]+)')
                if ($Match.Success) { $LastReplay = Scrub-Line (($Match.Groups[1].Value -split '[\\/]')[-1]) }
            }
            catch { $Warnings.Add('variables_read_failed') }
        }
    }
}
else { $Warnings.Add('documents_missing_or_linked') }

$ManifestCount = @($Banks | Where-Object { $_.Name -ceq ($Token + '_Manifest.StormBank') }).Count
$Banks = @($Banks | Sort-Object LastWriteTimeUtc -Descending)
if ($Banks.Count -gt 129) { $Warnings.Add('bank_count_limit_reached'); $Banks = @($Banks | Select-Object -First 129) }
$Logs = @($Logs | Sort-Object LastWriteTimeUtc -Descending)
if ($Logs.Count -gt 40) { $Warnings.Add('log_count_limit_reached'); $Logs = @($Logs | Select-Object -First 40) }
New-Item -ItemType Directory -Path $OutputDirectory | Out-Null
$Inventory = @()
$BankBytes = 0
$GroupIds = @{}
foreach ($Bank in $Banks) {
    if ($Bank.Length -gt 4MB -or $BankBytes + $Bank.Length -gt 32MB) { $Warnings.Add('bank_size_limit_reached'); continue }
    if (-not $GroupIds.ContainsKey($Bank.DirectoryName)) { $GroupIds[$Bank.DirectoryName] = $GroupIds.Count }
    $Relative = 'banks/set' + ('{0:D3}' -f $GroupIds[$Bank.DirectoryName]) + '/' + $Bank.Name
    $Destination = Join-Path $OutputDirectory $Relative
    New-Item -ItemType Directory -Path ([IO.Path]::GetDirectoryName($Destination)) -Force | Out-Null
    try {
        $Raw = [IO.File]::ReadAllBytes($Bank.FullName)
        if ($Raw.Length -gt 4MB -or $BankBytes + $Raw.Length -gt 32MB) { $Warnings.Add('bank_size_changed_during_read'); continue }
        [IO.File]::WriteAllBytes($Destination, $Raw)
        $Inventory += [ordered]@{ name = $Relative; bytes = $Raw.Length; sha256 = (Get-FileHash -LiteralPath $Destination -Algorithm SHA256).Hash.ToLowerInvariant() }
        $BankBytes += $Raw.Length
    }
    catch { $Warnings.Add('bank_read_failed') }
}

$LogEvidence = @()
$LogBytes = 0
foreach ($Log in $Logs) {
    if ($Log.Length -gt 4MB -or $LogBytes + $Log.Length -gt 16MB) { $Warnings.Add('log_size_limit_reached'); continue }
    try { $Raw = [IO.File]::ReadAllText($Log.FullName) }
    catch { $Warnings.Add('log_read_failed'); continue }
    if ($Raw.Length -gt 4MB) { $Warnings.Add('log_size_changed_during_read'); continue }
    $LogBytes += $Log.Length
    $Selected = @($Raw -split '\r?\n' | Where-Object { $_ -match '(?i)(<Version>|<DataBuild>|LocalTime|Heroes of the Storm \(B|galaxy|syntax|compil|HRC98285|bank|catalog|desync|unable to open|mod data|fatal|error)' } | Select-Object -First 300 | ForEach-Object { Scrub-Line $_ })
    $MapArgument = [regex]::Match($Raw, '(?im)^.*<Parameters>[^\r\n]*(TEN_GREYMANE_CATALOG_PROBE_98285\.StormMap)')
    if ($Selected.Count -gt 0 -or $MapArgument.Success) {
        $LogEvidence += [ordered]@{ source_kind = $Log.Extension.ToLowerInvariant(); modified_utc = $Log.LastWriteTimeUtc.ToString('o'); probe_map_argument_observed = $MapArgument.Success; selected_lines = $Selected }
    }
}
$Report = [ordered]@{
    format = 'hots-probe-failure-diagnostics-v1'
    collected_utc = (Get-Date).ToUniversalTime().ToString('o')
    target_label_build = 98285
    token = $Token
    documents_directory_found = [bool]$DocumentsExist
    observed_manifest_files = $ManifestCount
    collected_bank_files = $Inventory.Count
    collected_bank_bytes = $BankBytes
    bank_files = $Inventory
    last_replay_basename_recorded = $LastReplay
    log_evidence = $LogEvidence
    warnings = @($Warnings | Select-Object -Unique)
    collection_status = $(if ($ManifestCount -eq 0) { 'manifest-not-found' } else { 'manifest-present-not-validated' })
    capture_eligible_for_catalog_mapping = $false
    export_contents_validated = $false
    runtime_catalog_context_validated = $false
    game_launched_by_collector = $false
    game_installation_modified = $false
    replay_modified = $false
    client_playback_validated = $false
    search_is_complete = $false
}
[IO.File]::WriteAllText((Join-Path $OutputDirectory 'diagnostic-context.json'), ($Report | ConvertTo-Json -Depth 12), $Utf8)
Compress-Archive -Path (Join-Path $OutputDirectory '*') -DestinationPath $ZipPath
Write-Host ('Saved diagnostics: ' + $ZipPath)
Write-Host ('Collection status: ' + $Report.collection_status)
Write-Host 'This is not a validated catalog export and does not change or launch the game.'
