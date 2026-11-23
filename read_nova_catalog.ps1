param([Parameter(Mandatory)][string]$Map,[Parameter(Mandatory)][string]$NovaXml,[Parameter(Mandatory)][string]$LibraryDirectory,[Parameter(Mandatory)][string]$MpqToolDll,[Parameter(Mandatory)][string]$CascLibDll)
$ErrorActionPreference='Stop'
$def=[ordered]@{
 'Heroes.MpqTool'='0d15438f3b692537a037a55fdb82a536539a186aaf21f0a5239e74a1bc384a0f'
 'CascLib'='8be4b72776a3a4eca6708cc204860c51592c8f886224dd6ccbdec03b6fa82a11'
 'Heroes.LocaleText'='1389202f367769652d963280538475558517f191da4ba3e68519b10a1fc27212'
 'Testably.Abstractions.FileSystem.Interface'='478ef5ae4d958fb43372cd4cefd39089856ce97611bb1627c7b146669887a43d'
 'TestableIO.System.IO.Abstractions.Wrappers'='f8d2b73dfe1711b36bfa283fa83b62f760682cdb63dee37b4326a0cc42b90994'
 'U8XmlParser'='77f18acd6da0b799e73eb2f25fc1bfeb88d79a8d898063e2d33eb9068b87336d'
 'Heroes.XmlData'='4013071b5683ce8090096d84082879d34a30620ada741acc5841cb5bd89fa2ee'
}
foreach($key in $def.Keys){
    $path=switch($key){'Heroes.MpqTool'{$MpqToolDll};'CascLib'{$CascLibDll};default{Join-Path $LibraryDirectory "$key.dll"}}
    if((Get-FileHash -LiteralPath $path).Hash -ne $def[$key]){throw "Assembly differs $key"}
    $assembly=[Reflection.Assembly]::LoadFrom((Get-Item $path).FullName)
}
$f=Get-Item $Map
$hash=(Get-FileHash -LiteralPath $f.FullName).Hash.ToLowerInvariant()
if($hash -notin @('8b0cdec389be8a7cc52b438e9798af5903158a59a426d9ab3e08f166e791fd8f','13493e67e36594f908239dd0cce37fda0c0b386bbef385dcef22a83848f589d1')){throw 'Map differs'}
if((Get-FileHash -LiteralPath $NovaXml).Hash -ne '721086138a01ff65659616556ea617c85f968d8bd28ec888fa6397bde0ce113a'){throw 'Stock XML differs'}
$stock=[Xml.Linq.XElement]::Load((Get-Item $NovaXml).FullName)
$flags=[Reflection.BindingFlags]'Public,NonPublic,Instance'
$lt=$assembly.GetType('Heroes.XmlData.HeroesXmlLoader',$true)
$loader=$lt.GetConstructor($flags,$null,[type[]]@([string]),$null).Invoke([object[]]@($f.DirectoryName))
$mt=$assembly.GetType('Heroes.XmlData.StormMods.StormModType',$true)
$normal=[Enum]::Parse($mt,'Normal')
$source=$lt.GetField('_heroesSource',$flags).GetValue($loader)
$types=@('Hero','Talent','Effect','Behavior','Validator','Button','Abil')
foreach($k in $types){$source.StormStorage.AddBaseElementTypes($normal,$k,"C$k")}
foreach($entry in $stock.Elements()){
    if(!($types | Where-Object {$entry.Name.LocalName.StartsWith("C$_")})){continue}
    $origin=[Heroes.XmlData.StormData.StormPath]::new()
    $origin.StormModName='reference'
    $origin.StormModPath='reference'
    $origin.Path='nova.xml'
    $source.StormStorage.AddElement($normal,[Xml.Linq.XElement]::new($entry),$origin)
}
$t=$assembly.GetType('Heroes.XmlData.Source.IFileHeroesSource',$true)
$ctor=$assembly.GetType('Heroes.XmlData.StormMods.FileMpqStormMod',$true).GetConstructor($flags,$null,[type[]]@($t,[string],[string],$mt),$null)
$mod=$ctor.Invoke([object[]]@($source,'fixture',$f.Name,[Enum]::Parse($mt,'Map')))
$null=$mod.LoadStormData()
$source.StormStorage.AddModStorage($mod.StormModStorage)
function Entry($kind,$id){ $loader.HeroesData.GetStormElement($kind,$id).ToXElement() }
function Field($kind,$id,$field,$want) {
    $actual=(Entry $kind $id).Element($field).Attribute('value').Value
    if($actual -cne $want){throw "$id $field expected $want got $actual"}
}
$rule='NovaMasteryCovertOpsPinningShot'
$prefix='TEN41810NovaCovertOps'
$hero=Entry 'Hero' 'Nova'
$tree=@($hero.Elements('TalentTreeArray'))
$row=$tree[3]
if($row.Element('Talent').Attribute('value').Value -cne $rule -or $row.Element('Tier').Attribute('value').Value -ne '1' -or $row.Element('Column').Attribute('value').Value -ne '4'){throw "Effective inserted row $row"}
$oldhero=@($stock.Elements('CHero') | Where-Object {$_.Attribute('id').Value -ceq 'Nova'})[0]
$old=@($oldhero.Elements('TalentTreeArray'))
if($tree.Length -ne $old.Length+1){throw "Array length"}
for($i=0;$i -lt $old.Length;$i++){
    $j=if($i -lt 3){$i}else{$i+1}
    foreach($k in @('Talent','Tier','Column')){
        if($tree[$j].Element($k).Attribute('value').Value -cne $old[$i].Attribute($k).Value){throw "Displaced cell $i"}
    }
}
Field 'Talent' $rule 'Face' ($prefix+'Button')
Field 'Talent' $rule 'Abil' 'NovaPinningShot'
Field 'Validator' ($prefix+'HasTalent') 'Value' $rule
Field 'Behavior' ($prefix+'Driver') 'Period' '1'
Field 'Behavior' ($prefix+'Stacks') 'MaxStackCount' '10'
Field 'Behavior' ($prefix+'Grace') 'Duration' '1'
Field 'Behavior' 'NovaPermanentCloak' 'PeriodicEffect' ($prefix+'CloakPoll')
$launch=@((Entry 'Effect' 'NovaPinningShotMissileLaunchSet').Elements('EffectArray'))
if($launch.Length -ne 2 -or $launch[0].Attribute('value').Value -cne 'NovaPinningShotCovertOpsApplyMissileMarkerBehavior' -or $launch[1].Attribute('value').Value -cne ($prefix+'MarkMissile')){throw 'Missile markers'}
$impact=@((Entry 'Effect' 'NovaPinningShotSlowSwitch').Elements('CaseArray'))
if($impact.Length -ne 11){throw 'Impact cases'}
$cost=(Entry 'Abil' 'NovaPinningShot').Element('Cost').Elements('Vital') | Where-Object {$_.Attribute('index').Value -ceq 'Energy'}
if($cost.Attribute('value').Value -ne '65'){throw 'Mana'}
foreach($i in 1..10){
    Field 'Validator' ($prefix+'CasterStacks'+$i) 'Value' ([string]$i)
    if($impact[$i].Element('Validator').Attribute('value').Value -cne ($prefix+'SourceMarker'+$i) -or $impact[$i].Element('Effect').Attribute('value').Value -cne ($prefix+'ApplySlow'+$i)){throw 'Impact tier'}
    $v=(Entry 'Behavior' ($prefix+'Slow'+$i)).Element('Modification').Element('UnifiedMoveSpeedFactor').Attribute('value').Value
    if([decimal]$v -ne -([decimal](40+2*$i))/100){throw "Slow $i"}
    Field 'Behavior' ($prefix+'Slow'+$i) 'Duration' '2.25'
}
[ordered]@{candidate_sha256=$hash; native_execution=$false; preserved_stock_talent_cells=$old.Length; inserted_selector=3; tier=1; column=4; slow_steps=10; mana=65; reader_sha256=$def['Heroes.XmlData']} | ConvertTo-Json
