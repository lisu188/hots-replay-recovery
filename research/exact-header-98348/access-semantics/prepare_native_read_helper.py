"""Create a separate bounded derivative of the frozen read-only CASC helper."""
from pathlib import Path
BASE=Path(__file__).resolve().parent
source=(BASE.parent/'casc-feasibility/enumerate_local_casc.ps1').read_text()
source=source.replace('param([switch]$ConfigOnly,[switch]$ReadDragonMetadata)', '$ConfigOnly=$false; $ReadDragonMetadata=$true')
source=source.replace('$taskRoot=$PSScriptRoot', "$taskRoot=$PSScriptRoot\n$sourceRoot=Join-Path (Split-Path -Parent $taskRoot) 'casc-feasibility'")
for name in ('CascLib.dll','config-copy','staged-config-provenance.json'):
    source=source.replace("Join-Path $taskRoot '"+name+"'", "Join-Path $sourceRoot '"+name+"'")
source=source.replace('local-casc-dragon-metadata.json','installed-native-three-members.json').replace('local-casc-dragon-metadata.log','installed-native-three-members.log')
source=source.replace('ReadDragonMember(CASCHandler handler,string leaf)', 'ReadNativeMember(CASCHandler handler,string path,int remaining)')
old='''  if(leaf!="DocumentHeader" && leaf!="DocumentInfo" && leaf!="ComponentList.StormComponents")throw new InvalidOperationException("Member not allowlisted");
  string path="mods/heroesmapmods/battlegroundmapmods/dragonshire.stormmod/"+leaf;'''
new='''  string prefix="mods/core.stormmod/base.stormdata/TriggerLibs/";
  if(path!=prefix+"natives.galaxy" && path!=prefix+"NativeLib_h.galaxy" && path!=prefix+"NativeLib.galaxy")throw new InvalidOperationException("Native member not allowlisted");
  if(remaining<0 || remaining>2*1024*1024)throw new InvalidOperationException("Aggregate text limit differs");'''
assert old in source
source=source.replace(old,new)
source=source.replace('if(!handler.Encoding.GetEntry(key,out var entry) || entry.Size<0 || entry.Size>2*1024*1024)throw new InvalidOperationException("Named metadata missing or exceeds2MiB");', '''if(!handler.Encoding.GetEntry(key,out var entry) || entry.Size<0)throw new InvalidOperationException("Named native encoding missing");
  if(entry.Size>remaining)return new object[]{Array.Empty<byte>(),key.ToHexString().ToLowerInvariant(),entry.Keys[0].ToHexString().ToLowerInvariant(),entry.Size,path,package,false};''')
source=source.replace('if(buffer.Length+amount>2*1024*1024)throw new InvalidOperationException("Decoded member grew beyond bound");','if(buffer.Length+amount>remaining)throw new InvalidOperationException("Decoded text grew beyond remaining aggregate bound");')
source=source.replace('entry.Size,path,package};','entry.Size,path,package,true};')
a=source.index("   foreach($leaf in @('DocumentHeader'")
b=source.index("   $report.members=@($members);",a)
source=source[:a]+'''   $totalBytes=0
   foreach($leaf in @('natives.galaxy','NativeLib_h.galaxy','NativeLib.galaxy')){
    $cascPath='mods/core.stormmod/base.stormdata/TriggerLibs/'+$leaf
    $value=[CascMetadata]::ReadNativeMember($handler,$cascPath,(2*1024*1024-$totalBytes))
    if(-not $value[6]){
     $members.Add([pscustomobject]@{casc_path=$cascPath;declared_bytes=$value[3];read=$false;reason='exceeds-remaining-2MiB-aggregate-bound'})
     continue
    }
    $destination=Join-Path $taskRoot $leaf
    $stream=[IO.File]::Open($destination,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write)
    try{$stream.Write([byte[]]$value[0])}finally{$stream.Dispose()}
    $totalBytes+=$value[3]
    $members.Add([pscustomobject]@{casc_path=$value[4];saved_name=(Split-Path -Leaf $destination);bytes=$value[3];casc_content_md5=$value[1];encoded_key=$value[2];package_index=$value[5];sha256=(Get-FileHash -LiteralPath $destination -Algorithm SHA256).Hash.ToLowerInvariant();full_casc_content_md5_verified=$true;read=$true})
   }
   $report.total_text_bytes_read=$totalBytes
   if($totalBytes -gt 2*1024*1024 -or $members.Count -gt 3){throw 'Text scope cap exceeded'}
''' + source[b:]
source=source.replace("$report.scope='only-three-identified-DragonShire-metadata-members'", "$report.scope='only-three-MNDX-confirmed-Core-native-text-members-2MiB-total'")
gate='''$inventory=Join-Path $taskRoot 'installed-native-filename-inventory.json'
if((Get-FileHash -LiteralPath $inventory -Algorithm SHA256).Hash.ToLowerInvariant() -ne 'a8aa2ed045f32e77d5685d4353f48a48b9e6a35557d1b82508f1a6f1f8bd83b2'){throw 'Actual MNDX inventory differs'}
$names=(Get-Content -LiteralPath $inventory -Raw|ConvertFrom-Json).metadata_filenames
foreach($leaf in @('natives.galaxy','NativeLib_h.galaxy','NativeLib.galaxy')){
 if(('mods/core.stormmod/base.stormdata/TriggerLibs/'+$leaf) -cnotin $names){throw 'Native path not confirmed in actual MNDX inventory'}
 if(Test-Path -LiteralPath (Join-Path $taskRoot $leaf)){throw 'Refuse existing native text output'}
}
'''
source=source.replace("$temp=Join-Path $taskRoot 'temp'",gate+"$temp=Join-Path $taskRoot 'temp'")
output=BASE/'read_three_installed_native_members.ps1'
with output.open('x',encoding='utf-8',newline='\n') as f:
    f.write(source)
print('Created separate native reader source; not executed.')
