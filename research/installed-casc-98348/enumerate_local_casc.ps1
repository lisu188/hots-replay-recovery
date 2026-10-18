param([switch]$ConfigOnly,[switch]$ReadDragonMetadata)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$taskRoot=$PSScriptRoot
$installed='C:\Program Files (x86)\Heroes of the Storm'
$dll=Join-Path $taskRoot 'CascLib.dll'
if ((Get-FileHash -LiteralPath $dll -Algorithm SHA256).Hash.ToLowerInvariant() -ne '8be4b72776a3a4eca6708cc204860c51592c8f886224dd6ccbdec03b6fa82a11') {throw 'DLL digest differs'}
$configCopy=Join-Path $taskRoot 'config-copy'
$output=Join-Path $taskRoot $(if($ConfigOnly){'local-casc-config-only.json'}elseif($ReadDragonMetadata){'local-casc-dragon-metadata.json'}else{'local-casc-root-enumeration-v2.json'})
if(Test-Path -LiteralPath $output){throw 'Report already exists'}
$temp=Join-Path $taskRoot 'temp'
[IO.Directory]::CreateDirectory($temp) | Out-Null
$env:TEMP=$temp; $env:TMP=$temp
Set-Location -LiteralPath $taskRoot
[Environment]::CurrentDirectory=$taskRoot
$assembly=[Reflection.Assembly]::LoadFrom($dll)
if (@($assembly.GetReferencedAssemblies() | Where-Object {-not $_.Name.StartsWith('System.')}).Count){throw 'Unexpected non-BCL dependency'}
$code=@'
using System;
using System.Net.Http;
using System.Threading;
using System.Threading.Tasks;
using System.Collections;
using System.IO;
using System.Reflection;
using System.Security.Cryptography;
using CASCLib;
public sealed class OfflineCascHttp : HttpMessageHandler {
 public static int Rejected;
 protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage request,CancellationToken token) {
  Interlocked.Increment(ref Rejected);
  return Task.FromException<HttpResponseMessage>(new InvalidOperationException("Offline CASC request blocked before transport"));
 }
}
public sealed class ScopedCascLog : ILoggerOptions {
 public string LogFileName {get;}
 public bool TimeStamp => false;
 public ScopedCascLog(string name) {LogFileName=name;}
}
public static class CascMetadata {
 public static string Root(CASCConfig config) => config.RootCKey.ToHexString().ToLowerInvariant();
 public static string RootContentMD5(CASCHandler handler,CASCConfig config) {
  if(!handler.Encoding.GetEntry(config.RootCKey,out var entry)) throw new InvalidOperationException("Root encoding missing");
  using var stream=handler.OpenFile(entry.Keys[0]);
  return Convert.ToHexString(MD5.HashData(stream)).ToLowerInvariant();
 }
 public static int InitializeOnlyPackages(CASCHandler handler) {
  var root=handler.Root;var type=root.GetType();
  var flags=BindingFlags.Instance|BindingFlags.NonPublic;
  var mar=(Array)type.GetField("MarFiles",flags).GetValue(root);
  var db=mar.GetValue(0);
  var names=(IEnumerable)db.GetType().GetMethod("EnumerateFiles").Invoke(db,null);
  var packages=(IDictionary)type.GetField("Packages",flags).GetValue(root);
  var indexes=(IDictionary)type.GetField("IndexByPackages",flags).GetValue(root);
  int count=0;
  foreach(var item in names) {
   if(++count>10000)throw new InvalidOperationException("Package count bound exceeded");
   var itemType=item.GetType();
   var path=(string)itemType.GetProperty("FoundPath").GetValue(item);
   var index=(int)itemType.GetProperty("FileNameIndex").GetValue(item);
   packages.Add(index,path);indexes.Add(path,index);
  }
  return count;
 }
 public static object[] ReadDragonMember(CASCHandler handler,string leaf) {
  if(leaf!="DocumentHeader" && leaf!="DocumentInfo" && leaf!="ComponentList.StormComponents")throw new InvalidOperationException("Member not allowlisted");
  string path="mods/heroesmapmods/battlegroundmapmods/dragonshire.stormmod/"+leaf;
  var root=handler.Root;var type=root.GetType();var flags=BindingFlags.Instance|BindingFlags.NonPublic;
  int package=(int)type.GetMethod("FindMNDXPackage",flags).Invoke(root,new object[]{path});
  var info=type.GetMethod("FindMNDXInfo",flags).Invoke(root,new object[]{path,package});
  var key=(MD5Hash)info.GetType().GetField("cKey").GetValue(info);
  if(!handler.Encoding.GetEntry(key,out var entry) || entry.Size<0 || entry.Size>2*1024*1024)throw new InvalidOperationException("Named metadata missing or exceeds2MiB");
  using var stream=handler.OpenFile(entry.Keys[0]);using var buffer=new MemoryStream();
  byte[] chunk=new byte[65536];int amount;
  while((amount=stream.Read(chunk,0,chunk.Length))!=0) {
   if(buffer.Length+amount>2*1024*1024)throw new InvalidOperationException("Decoded member grew beyond bound");
   buffer.Write(chunk,0,amount);
  }
  var raw=buffer.ToArray();
  if(raw.LongLength!=entry.Size || Convert.ToHexString(MD5.HashData(raw)).ToLowerInvariant()!=key.ToHexString().ToLowerInvariant())throw new InvalidOperationException("Content MD5 or size differs from CASC key");
  return new object[]{raw,key.ToHexString().ToLowerInvariant(),entry.Keys[0].ToHexString().ToLowerInvariant(),entry.Size,path,package};
 }
}
'@
Add-Type -TypeDefinition $code -ReferencedAssemblies @($dll,'System.Net.Http.dll','System.Threading.dll','System.Collections.dll','System.Security.Cryptography.dll')
$http=[Net.Http.HttpClient]::new([OfflineCascHttp]::new())
try { $null=$http.GetAsync('https://offline-canary.invalid/').GetAwaiter().GetResult();throw 'Network guard did not block' }
catch {if([OfflineCascHttp]::Rejected -ne 1){throw 'Network guard canary failed'}}
[OfflineCascHttp]::Rejected=0
[CASCLib.CASCConfig]::UseOnlineFallbackForMissingFiles=$false
[CASCLib.CASCConfig]::LoadFlags=[CASCLib.LoadFlags]::None
[CASCLib.CASCConfig]::ValidateData=$true
[CASCLib.CASCConfig]::ThrowOnFileNotFound=$true
[CASCLib.CASCConfig]::ThrowOnMissingDecryptionKey=$true
[CASCLib.CDNCache]::Enabled=$false
[CASCLib.CDNCache]::CacheData=$false
[CASCLib.CDNCache]::CachePath=Join-Path $taskRoot 'cache-disabled'
$log=Join-Path $taskRoot $(if($ConfigOnly){'config-only.log'}elseif($ReadDragonMetadata){'local-casc-dragon-metadata.log'}else{'local-casc-enumeration-v2.log'})
if(Test-Path -LiteralPath $log){throw 'Log already exists'}
$config=[CASCLib.CASCConfig]::LoadLocalStorageConfig($configCopy,'hero',[ScopedCascLog]::new($log))
if($config.OnlineMode -or $config.GameType.ToString() -ne 'HotS' -or $config.VersionName -ne '2.57.0.98348' -or $config.BuildName -ne 'B98348' -or [CascMetadata]::Root($config) -ne 'c3b3c8bc82e3a5a62e550fdde9a40c28'){throw 'Installed current-build metadata differs'}
if($config.GetBuildInfoVariable('BuildKey') -ne 'a64c9b7ebf1c6a811ffefad97865ed80'){throw 'Build config key differs'}
# The loader requested ReadWrite on scratch copies only. Subsequent index/data paths use explicit Read access.
$config.GetType().GetProperty('BasePath').SetValue($config,$installed)
if($config.BasePath -ne $installed){throw 'Installed read path was not selected'}
$report=[ordered]@{format='hots-local-casc-metadata-enumeration-v1';powershell=$PSVersionTable.PSVersion.ToString();runtime=[Runtime.InteropServices.RuntimeInformation]::FrameworkDescription;
 dll_sha256=(Get-FileHash -LiteralPath $dll -Algorithm SHA256).Hash.ToLowerInvariant();version=$config.VersionName;build_key=$config.GetBuildInfoVariable('BuildKey');root=[CascMetadata]::Root($config);
 config_parsed_from_scratch_copies=$true;installed_indices_and_data_access='explicit-read-only';online_fallback_flag=$false;denying_http_handler_canary_passed=$true;cache_enabled=$false;load_flags='None';
 configuration_only=[bool]$ConfigOnly;game_client_launched=$false;game_storage_modified=$false;file_contents_exported=$false}
if(-not $ConfigOnly){
 $watch=[Diagnostics.Stopwatch]::StartNew()
 $handler=[CASCLib.CASCHandler]::OpenStorage($config,$http,$null)
 try {
  $rootType=$handler.Root.GetType()
  if($rootType.FullName -ne 'CASCLib.MNDXRootHandler'){throw 'Unexpected root handler'}
  if($handler.Root.Count -gt 1500000){throw 'Root name count exceeds bounded scan'}
  if($ReadDragonMetadata){
   $report.actual_root_content_md5=[CascMetadata]::RootContentMD5($handler,$config)
   if($report.actual_root_content_md5 -ne $report.root){throw 'Actual root content does not match exact current root'}
   $report.package_names_initialized=[CascMetadata]::InitializeOnlyPackages($handler)
   $members=[Collections.Generic.List[object]]::new()
   foreach($leaf in @('DocumentHeader','DocumentInfo','ComponentList.StormComponents')){
    $value=[CascMetadata]::ReadDragonMember($handler,$leaf)
    $destination=Join-Path $taskRoot ('dragonshire-'+$leaf+'.bin')
    $stream=[IO.File]::Open($destination,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write)
    try{$stream.Write([byte[]]$value[0])}finally{$stream.Dispose()}
    $members.Add([pscustomobject]@{casc_path=$value[4];saved_name=(Split-Path -Leaf $destination);bytes=$value[3];casc_content_md5=$value[1];encoded_key=$value[2];package_index=$value[5];sha256=(Get-FileHash -LiteralPath $destination -Algorithm SHA256).Hash.ToLowerInvariant();full_casc_content_md5_verified=$true})
   }
   $report.members=@($members);$report.file_contents_exported=$true
   $report.scope='only-three-identified-DragonShire-metadata-members';$report.resolution='unchanged-private-MNDX-lookup-with-original-package-catalog-values'
  }else{
  # Enumerate the already decoded internal filename DB without creating a full asset tree.
  $mar=$rootType.GetField('MarFiles',[Reflection.BindingFlags]'Instance,NonPublic').GetValue($handler.Root)
  $method=$mar[2].GetType().GetMethod('EnumerateFiles',[Reflection.BindingFlags]'Instance,Public')
  $names=$method.Invoke($mar[2],@())
  $candidates=[Collections.Generic.List[string]]::new();$total=0;$matched=0
  foreach($item in $names){
   $total++;if($total -gt 1500000){throw 'Enumeration exceeds bounded scan'}
   $name=$item.FoundPath.Replace('\','/')
   if($name.Length -gt 2048){throw 'Metadata filename too long'}
   $base=$name.Split('/')[-1]
   if($base -match '(?i)^(documentinfo|documentheader|componentlist\.stormcomponents|hdp\.info)$|\.s2mh$|(^|[._-])(package|build|manifest)([._-]|$)'){
    $matched++;if($candidates.Count -lt 512){$candidates.Add($name)}
   }
  }
  $watch.Stop()
  $report.root_handler=$rootType.FullName;$report.root_declared_names=$handler.Root.Count;$report.names_examined=$total
  $report.metadata_filename_matches=$matched;$report.metadata_filenames=@($candidates);$report.metadata_filenames_truncated=($matched -gt $candidates.Count)
  $report.scan_seconds=$watch.Elapsed.TotalSeconds
  }
 } finally {
  try{$handler.Clear();$report.library_clear_succeeded=$true}
  catch{$report.library_clear_succeeded=$false;$report.library_clear_exception_type=$_.Exception.InnerException.GetType().FullName}
 }
}
$sourceChecks=Get-Content -LiteralPath (Join-Path $taskRoot 'staged-config-provenance.json') -Raw | ConvertFrom-Json
foreach($source in $sourceChecks.files){
 if((Get-FileHash -LiteralPath (Join-Path $installed $source.path) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $source.sha256){throw 'Installed configuration changed during inspection'}
}
$report.installed_config_hashes_unchanged=$true
$report.blocked_http_attempts_during_casc=[OfflineCascHttp]::Rejected
$http.Dispose()
$json=$report | ConvertTo-Json -Depth 6
$stream=[IO.File]::Open($output,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write)
try{$bytes=[Text.UTF8Encoding]::new($false).GetBytes($json+"`n");$stream.Write($bytes)}finally{$stream.Dispose()}
[pscustomobject]@{output=(Split-Path -Leaf $output);configuration_only=[bool]$ConfigOnly;blocked_http_attempts=[OfflineCascHttp]::Rejected} | ConvertTo-Json
