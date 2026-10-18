<#
.SYNOPSIS
Read selected replays with pinned, independent .NET libraries without launching HotS.
.DESCRIPTION
Requires PowerShell running on .NET 10 or newer. Place the two pinned net10.0 DLLs
from the NuGet packages identified in independent-parser-packages.json together in
AssemblyDirectory. The script performs no downloads. Replay paths are required;
optional PythonProfile paths must be in the same order. Output must be a new file.

The original public Parse API result is preserved. Separate isolated core readers
exclude battlelobby parsing/mapping; their completion never becomes full API success.
No replay bytes, player names, message contents, paths or exception messages are saved.
.EXAMPLE
./read_independent_replay.ps1 -Replay ./first.StormReplay,./second.StormReplay `
    -AssemblyDirectory ./work/independent-dlls -Output ./work/independent-read.json
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory)] [ValidateCount(1, 8)] [string[]]$Replay,
    [Parameter(Mandatory)] [string]$AssemblyDirectory,
    [Parameter(Mandatory)] [string]$Output,
    [ValidateCount(0, 8)] [string[]]$PythonProfile = @()
)
$ErrorActionPreference = 'Stop'
if ([Environment]::Version.Major -lt 10) { throw 'This reader requires PowerShell on .NET 10 or newer.' }
if ($PythonProfile.Count -ne 0 -and $PythonProfile.Count -ne $Replay.Count) {
    throw 'PythonProfile must be omitted or contain one profile per Replay, in the same order.'
}
$outputPath = [IO.Path]::GetFullPath($Output)
if ([IO.File]::Exists($outputPath) -or [IO.Directory]::Exists($outputPath)) { throw 'Output already exists.' }
if (-not [IO.Directory]::Exists([IO.Path]::GetDirectoryName($outputPath))) { throw 'Output parent must already exist.' }
$assemblyRoot = [IO.Path]::GetFullPath($AssemblyDirectory)
if (-not [IO.Directory]::Exists($assemblyRoot)) { throw 'AssemblyDirectory must exist.' }
$pins = @(
    @{ id = 'Heroes.MpqTool'; version = '1.4.0'; bytes = 40448;
       sha256 = '0d15438f3b692537a037a55fdb82a536539a186aaf21f0a5239e74a1bc384a0f' },
    @{ id = 'Heroes.StormReplayParser'; version = '2.3.0'; bytes = 145408;
       sha256 = '5a6dfa2651df7271d4063e8277e9a5e32e93fe2e0e12ff95e27a7a82f58f3ca7' }
)
$inputs = @()
for ($index = 0; $index -lt $Replay.Count; $index++) {
    $path = [IO.Path]::GetFullPath($Replay[$index])
    if (-not [IO.File]::Exists($path)) { throw 'Replay input is not a regular file.' }
    $size = [IO.FileInfo]::new($path).Length
    if ($size -lt 48 -or $size -gt 64MB) { throw 'Replay input must contain 48 bytes through 64 MiB.' }
    $profile = $null
    if ($PythonProfile.Count) {
        $profile = [IO.Path]::GetFullPath($PythonProfile[$index])
        if (-not [IO.File]::Exists($profile) -or [IO.FileInfo]::new($profile).Length -gt 2MB) {
            throw 'Python profile must be a regular file no larger than 2 MiB.'
        }
    }
    $inputs += @{ id = ('replay-{0:d3}' -f ($index + 1)); path = $path; profile = $profile; size = $size }
}

# Load the exact bytes just hashed, avoiding a second path read for assembly loading.
# A fresh process is required so an earlier assembly with the same name cannot win.
$parserAssembly = $null
foreach ($pin in $pins) {
    if ([AppDomain]::CurrentDomain.GetAssemblies().GetName().Name -contains $pin.id) {
        throw 'A parser dependency is already loaded; use a fresh PowerShell process.'
    }
    $assemblyPath = Join-Path $assemblyRoot ($pin.id + '.dll')
    if (-not [IO.File]::Exists($assemblyPath) -or [IO.FileInfo]::new($assemblyPath).Length -ne $pin.bytes) {
        throw 'Pinned assembly is missing or its size differs.'
    }
    $raw = [IO.File]::ReadAllBytes($assemblyPath)
    $actual = [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($raw)).ToLowerInvariant()
    if ($actual -ne $pin.sha256) { throw 'Pinned assembly SHA-256 differs.' }
    $stream = [IO.MemoryStream]::new($raw, $false)
    try { $loaded = [Runtime.Loader.AssemblyLoadContext]::Default.LoadFromStream($stream) }
    finally { $stream.Dispose() }
    if ($loaded.GetName().Version.ToString() -ne ($pin.version + '.0')) { throw 'Pinned assembly version differs.' }
    if ($pin.id -eq 'Heroes.StormReplayParser') { $parserAssembly = $loaded }
}
$replayType = $parserAssembly.GetType('Heroes.StormReplayParser.StormReplay', $true)
$privateInstance = [Reflection.BindingFlags]'NonPublic,Instance'
$parseFile = $replayType.GetMethod('ParseMpqFile', $privateInstance)
$parseHeader = $replayType.GetMethod('ParseReplayHeader', $privateInstance)
$delegateType = $replayType.GetNestedType('MpqFileParser', [Reflection.BindingFlags]'NonPublic')
$archiveField = $replayType.GetField('_stormMpqArchive', $privateInstance)
$constructors = @($replayType.GetConstructors($privateInstance) | Where-Object { $_.GetParameters()[0].ParameterType -eq [string] })
if ($constructors.Count -ne 1 -or -not $parseFile -or -not $parseHeader -or -not $delegateType -or -not $archiveField) {
    throw 'Pinned reflection surface differs.'
}
$constructor = $constructors[0]

function Get-SafeError($failure) {
    $result = @()
    $depth = 0
    while ($null -ne $failure -and $depth -lt 8) {
        $method = $null
        if ($failure.TargetSite) { $method = $failure.TargetSite.DeclaringType.FullName + '.' + $failure.TargetSite.Name }
        $code = $null
        if ($failure.Message -eq 'Mismatch on data transfer from pregame to replay') { $code = 'pregame-to-replay-mismatch' }
        $frames = @()
        if ($failure.StackTrace) {
            foreach ($frame in @([Diagnostics.StackTrace]::new($failure, $false).GetFrames()) | Select-Object -First 16) {
                $member = $frame.GetMethod()
                if ($member) { $frames += [ordered]@{ method = $member.DeclaringType.FullName + '.' + $member.Name; il_offset = $frame.GetILOffset() } }
            }
        }
        $result += [ordered]@{ type = $failure.GetType().FullName; method = $method; known_message_code = $code; frames = $frames }
        $failure = $failure.InnerException
        $depth++
    }
    return ,$result
}

function Get-SafeSummary($value) {
    if ($null -eq $value) { return $null }
    return [ordered]@{
        version = $value.ReplayVersion.ToString(); build = $value.ReplayBuild; base_build = $value.ReplayVersion.BaseBuild
        elapsed_game_loops = $value.ElapsedGamesLoops; players_count = $value.PlayersCount
        game_event_count = $value.GameEvents.Count; tracker_event_count = $value.TrackerEvents.Count; message_count = $value.Messages.Count
        reader_event_classes = [ordered]@{
            game = if ($value.GameEvents.Count) { $value.GameEvents[0].GetType().FullName } else { $null }
            tracker = if ($value.TrackerEvents.Count) { $value.TrackerEvents[0].GetType().FullName } else { $null }
            messages = @($value.Messages | ForEach-Object { $_.GetType().FullName } | Sort-Object -Unique)
        }
        battlelobby_player_info_parsed = $value.IsBattleLobbyPlayerInfoParsed
    }
}

$results = @()
foreach ($item in $inputs) {
    $digest = (Get-FileHash -LiteralPath $item.path -Algorithm SHA256).Hash.ToLowerInvariant()
    $entry = [ordered]@{ id = $item.id; input_sha256 = $digest; input_bytes = $item.size }
    $options = [Heroes.StormReplayParser.ParseOptions]::new()
    try {
        $full = [Heroes.StormReplayParser.StormReplay]::Parse($item.path, $options)
        $entry.public_api = [ordered]@{ status = $full.Status.ToString(); summary = (Get-SafeSummary $full.Replay); errors = (Get-SafeError $full.Exception) }
    }
    catch { $entry.public_api = [ordered]@{ status = 'invocation-failed'; summary = $null; errors = (Get-SafeError $_.Exception) } }

    $isolated = [ordered]@{ status = 'not-run'; excluded_stage = 'ParseReplayServerBattlelobby/PregameMapper.TransferTo';
        full_parse_success_claimed = $false; stages = @(); errors = @(); summary = $null }
    $partial = $null
    $activeStage = 'header'
    try {
        $partial = $constructor.Invoke([object[]]@($item.path.PSObject.BaseObject, $options.PSObject.BaseObject))
        $parseHeader.Invoke($partial.PSObject.BaseObject, $null) | Out-Null
        $isolated.stages += [ordered]@{ stage = 'header'; status = 'completed' }
        foreach ($stage in @(
            @{ type = 'ReplayDetails'; member = 'replay.details' }, @{ type = 'ReplayInitData'; member = 'replay.initData' },
            @{ type = 'ReplayAttributeEvents'; member = 'replay.attributes.events' }, @{ type = 'ReplayGameEvents'; member = 'replay.game.events' },
            @{ type = 'ReplayTrackerEvents'; member = 'replay.tracker.events' }, @{ type = 'ReplayMessageEvents'; member = 'replay.message.events' }
        )) {
            $activeStage = $stage.member
            $decoder = $parserAssembly.GetType('Heroes.StormReplayParser.MpqFiles.' + $stage.type, $true)
            $callback = $decoder.GetMethod('Parse', [Reflection.BindingFlags]'Public,Static').CreateDelegate($delegateType)
            $pool = [System.Buffers.ArrayPool[byte]]::Shared
            $parseFile.Invoke($partial.PSObject.BaseObject, [object[]]@($pool.PSObject.BaseObject, $stage.member, $callback.PSObject.BaseObject)) | Out-Null
            $isolated.stages += [ordered]@{ stage = $stage.member; status = 'completed' }
        }
        $isolated.status = 'isolated-core-readers-completed'
    }
    catch {
        $isolated.status = 'isolated-core-reader-failed'
        $isolated.stages += [ordered]@{ stage = $activeStage; status = 'failed' }
        $isolated.errors = Get-SafeError $_.Exception
    }
    finally {
        if ($partial) {
            $isolated.summary = Get-SafeSummary $partial
            $archive = $archiveField.GetValue($partial.PSObject.BaseObject)
            if ($archive) { $archive.Dispose() }
        }
    }
    $entry.isolated_core_readers = $isolated
    $entry.python_comparison = $null
    if ($item.profile) {
        $profile = Get-Content -LiteralPath $item.profile -Raw | ConvertFrom-Json
        if ($profile.file_sha256 -ne $digest) { throw 'Python profile refers to another input; no report written.' }
        $entry.python_comparison = [ordered]@{
            profile_sha256 = (Get-FileHash -LiteralPath $item.profile -Algorithm SHA256).Hash.ToLowerInvariant()
            schema_build = $profile.schema_build; observed_payload_roundtrip = $profile.observed_payload_roundtrip
            header_build_equal = $profile.target.m_version.m_build -eq $isolated.summary.build
            base_build_equal = $profile.target.m_version.m_baseBuild -eq $isolated.summary.base_build
            game_event_count = $profile.streams.game.count; tracker_event_count = $profile.streams.tracker.count; message_count = $profile.streams.message.count
            game_count_equal = $profile.streams.game.count -eq $isolated.summary.game_event_count
            tracker_count_equal = $profile.streams.tracker.count -eq $isolated.summary.tracker_event_count
            message_count_equal = $profile.streams.message.count -eq $isolated.summary.message_count
            event_payload_equality_not_tested = $true
        }
    }
    $entry.input_unchanged = (Get-FileHash -LiteralPath $item.path -Algorithm SHA256).Hash.ToLowerInvariant() -eq $digest
    if (-not $entry.input_unchanged) { throw 'Input replay changed.' }
    $results += $entry
}
$report = [ordered]@{
    format = 'hots-independent-dotnet-reader-observation-v2'; observed_at_utc = [DateTime]::UtcNow.ToString('o')
    parser_repository_commit = 'd381dd9c273205c0fd7ac402c75eef98c6fa6c78'
    assemblies = @($pins | ForEach-Object { [ordered]@{ id = $_.id; version = $_.version; sha256 = $_.sha256; bytes = $_.bytes } })
    runtime = [Runtime.InteropServices.RuntimeInformation]::FrameworkDescription
    parse_options = [ordered]@{ tracker = $true; game = $true; messages = $true; allow_ptr = $false }
    client_launched = $false; sdk_installed = $false; simulation_compatibility_proven = $false
    results = $results
}
$json = (($report | ConvertTo-Json -Depth 12).Replace("`r`n", "`n").Replace("`r", "`n")).TrimEnd("`n") + "`n"
$encoded = [Text.UTF8Encoding]::new($false).GetBytes($json)
if ($encoded.Length -gt 8MB) { throw 'Report exceeds size limit.' }
$outputStream = [IO.File]::Open($outputPath, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::None)
try { $outputStream.Write($encoded) }
finally { $outputStream.Dispose() }
Write-Output ('Wrote independent reader report for {0} replay(s).' -f $results.Count)
