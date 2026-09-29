param(
    [ValidateSet('Run', 'Collect')][string]$Mode = 'Run',
    [string]$GameDirectory = '',
    [string]$GameDocuments = '',
    [string]$OutputDirectory = ''
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$Token = 'HRC98285_20260929_J2'
$MapName = 'TEN_GREYMANE_CATALOG_JOURNAL_98285.StormMap'
$ExpectedMapHash = '@MAP_SHA256@'
$Warnings = New-Object 'System.Collections.Generic.List[string]'
$Utf8 = New-Object System.Text.UTF8Encoding($false)
if (-not $GameDirectory) { $GameDirectory = Join-Path ${env:ProgramFiles(x86)} 'Heroes of the Storm' }
if (-not $GameDocuments) { $GameDocuments = Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'Heroes of the Storm' }
if (-not $OutputDirectory) { $OutputDirectory = Join-Path $PSScriptRoot ('journal-output-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '-' + [guid]::NewGuid().ToString('N').Substring(0, 8)) }
$ZipPath = $OutputDirectory + '.zip'
if ((Test-Path -LiteralPath $OutputDirectory) -or (Test-Path -LiteralPath $ZipPath)) { throw 'Output already exists. Nothing was replaced.' }
$Started = (Get-Date).ToUniversalTime()
$Launched = $false
$MapHash = $null
if (-not ('HRCReplayDiagPath' -as [type])) {
    Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class HRCReplayDiagPath {
    [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
    private struct FindData {
        public uint attributes;
        public System.Runtime.InteropServices.ComTypes.FILETIME created, accessed, written;
        public uint sizeHigh, sizeLow, tag, reserved;
        [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 260)] public string name;
        [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 14)] public string alternate;
    }
    [DllImport("kernel32.dll", EntryPoint = "FindFirstFileW", CharSet = CharSet.Unicode, SetLastError = true)]
    private static extern IntPtr FindFirstFile(string path, out FindData data);
    [DllImport("kernel32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool FindClose(IntPtr handle);
    public static bool IsCloudTag(uint tag) { return (tag & 0xFFFF0FFFu) == 0x9000001Au; }
    public static bool IsCloudPlaceholder(string path) {
        FindData data;
        IntPtr handle = FindFirstFile(path, out data);
        if (handle == new IntPtr(-1)) return false;
        try { return IsCloudTag(data.tag); }
        finally { FindClose(handle); }
    }
}
'@
}

function Is-Linked([IO.FileSystemInfo]$Item) {
    if (-not ($Item.Attributes -band [IO.FileAttributes]::ReparsePoint)) { return $false }
    return (-not [HRCReplayDiagPath]::IsCloudPlaceholder($Item.FullName))
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


if ($Mode -eq 'Run') {
    if ($ExpectedMapHash -notmatch '^[0-9a-f]{64}$') { throw 'Use the generated delivery package, not the unrendered repository template.' }
    $Map = Get-Item -LiteralPath (Join-Path $PSScriptRoot $MapName) -Force
    if ($Map.PSIsContainer -or (Is-Linked $Map)) { throw 'A regular diagnostic map is required.' }
    $MapHash = (Get-FileHash -LiteralPath $Map.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($MapHash -ne $ExpectedMapHash) { throw 'Diagnostic map checksum mismatch. Nothing was launched.' }
    $Switcher = Join-Path $GameDirectory 'Support64\HeroesSwitcher_x64.exe'
    if (-not (Test-Path -LiteralPath $Switcher -PathType Leaf)) { throw 'HeroesSwitcher_x64.exe not found. Supply -GameDirectory.' }
    if (@(Get-Process -Name 'HeroesOfTheStorm_x64', 'HeroesOfTheStorm' -ErrorAction SilentlyContinue).Count) { throw 'Close HotS first. This script does not stop your game.' }
    Write-Host 'Starting a separate catalog diagnostic, not TEN_GREYMANE playback.'
    Write-Host 'Wait for HOTS CATALOG JOURNAL: export requested, then exit the map.'
    Start-Process -FilePath $Switcher -ArgumentList ('"' + $Map.FullName + '"') -WorkingDirectory $GameDirectory | Out-Null
    $Launched = $true
    Read-Host 'After exiting the diagnostic map, press Enter to collect the journal' | Out-Null
}
$Candidates = @()
$Graphics = @()
if (Test-Path -LiteralPath $GameDocuments -PathType Container) {
    $RootItem = Get-Item -LiteralPath $GameDocuments -Force
    if (Is-Linked $RootItem) { throw 'Linked document root rejected.' }
    $Candidates += @(Get-ChildItem -LiteralPath $GameDocuments -File -Force | Where-Object { $_.Name -ieq ($Token + '.txt') -and -not (Is-Linked $_) })
    foreach ($Sub in @('UserLogs', 'GameLogs')) {
        $Found = @(Get-BoundedFiles (Join-Path $GameDocuments $Sub) 6)
        $Candidates += @($Found | Where-Object { $_.Name -ieq ($Token + '.txt') })
        $Graphics += @($Found | Where-Object { $_.Name -like '*Graphics.txt' })
    }
}
else { $Warnings.Add('game_documents_missing') }
if ($Candidates.Count -gt 8) { throw 'Too many candidate journals; no arbitrary session was selected.' }
$Inventory = @()
$VersionLines = @()
$LogFresh = $false
$MapArgumentMatched = $false
foreach ($Log in @($Graphics | Sort-Object LastWriteTimeUtc -Descending | Select-Object -First 20)) {
    if ($Log.Length -gt 1MB) { continue }
    $Lines = [IO.File]::ReadAllLines($Log.FullName)
    if (@($Lines | Where-Object { $_.Contains($MapName) }).Count -gt 0) {
        $MapArgumentMatched = $true
        $LogFresh = $Launched -and $Log.LastWriteTimeUtc -ge $Started.AddSeconds(-5)
        $VersionLines = @($Lines | Where-Object { $_ -match '(<Version>|<DataBuild>|LocalTime|Heroes of the Storm \(B)' } | Select-Object -First 16 | ForEach-Object { if ($_.Length -le 512) { $_ } })
        break
    }
}
New-Item -ItemType Directory -Path $OutputDirectory | Out-Null
$Index = 0
foreach ($File in @($Candidates | Sort-Object FullName)) {
    if ($File.Length -gt 8MB) { $Warnings.Add('journal_size_limit'); continue }
    $Name = 'journal-' + $Index + '.txt'
    $Bytes = [IO.File]::ReadAllBytes($File.FullName)
    if ($Bytes.Length -gt 8MB) { throw 'Journal grew beyond its bound.' }
    $Destination = Join-Path $OutputDirectory $Name
    [IO.File]::WriteAllBytes($Destination, $Bytes)
    $Inventory += [ordered]@{ name = $Name; bytes = $Bytes.Length; sha256 = (Get-FileHash -LiteralPath $Destination -Algorithm SHA256).Hash.ToLowerInvariant(); modified_utc = $File.LastWriteTimeUtc.ToString('o'); fresh_for_launch = ($Launched -and $File.LastWriteTimeUtc -ge $Started.AddSeconds(-5)) }
    $Index++
}
if ($Inventory.Count -eq 0) { $Warnings.Add('no_journal_found') }
$Context = [ordered]@{
    format = 'hots-catalog-journal-collection-v1'
    token = $Token
    expected_build = 98285
    map_sha256 = $MapHash
    launched_by_this_invocation = $Launched
    launch_utc = $Started.ToString('o')
    graphics_log_fresh_for_launch = $LogFresh
    graphics_map_argument_matched = $MapArgumentMatched
    observed_version_lines = $VersionLines
    journals = $Inventory
    warnings = @($Warnings.ToArray())
    export_contents_validated = $false
    client_playback_validated = $false
}
[IO.File]::WriteAllText((Join-Path $OutputDirectory 'collection-context.json'), ($Context | ConvertTo-Json -Depth 8), $Utf8)
Compress-Archive -LiteralPath @(Get-ChildItem -LiteralPath $OutputDirectory -File | ForEach-Object { $_.FullName }) -DestinationPath $ZipPath
Write-Host ('Saved ' + $Inventory.Count + ' journal(s) to ' + $ZipPath)
Write-Host 'The ZIP is diagnostic input, not proof of export completeness or successful replay recovery.'
