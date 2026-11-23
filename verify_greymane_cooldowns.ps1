param(
    [Parameter(Mandatory)][string]$BaseMap,
    [Parameter(Mandatory)][string]$CandidateMap,
    [Parameter(Mandatory)][string]$GennXml,
    [Parameter(Mandatory)][string]$MpqToolDll,
    [Parameter(Mandatory)][string]$CascLibDll,
    [Parameter(Mandatory)][string]$LibraryDirectory,
    [string]$NegativeMap,
    [string]$CocktailMap
)
$ErrorActionPreference = 'Stop'
$files = [ordered]@{
    'Heroes.MpqTool' = $MpqToolDll
    'CascLib' = $CascLibDll
}
foreach ($name in 'Heroes.LocaleText','Testably.Abstractions.FileSystem.Interface','TestableIO.System.IO.Abstractions.Wrappers','U8XmlParser','Heroes.XmlData') {
    $files[$name] = Join-Path $LibraryDirectory "$name.dll"
}
$pins = @{
    'Heroes.MpqTool'='0d15438f3b692537a037a55fdb82a536539a186aaf21f0a5239e74a1bc384a0f'
    'CascLib'='8be4b72776a3a4eca6708cc204860c51592c8f886224dd6ccbdec03b6fa82a11'
    'Heroes.XmlData'='4013071b5683ce8090096d84082879d34a30620ada741acc5841cb5bd89fa2ee'
    'Heroes.LocaleText'='1389202f367769652d963280538475558517f191da4ba3e68519b10a1fc27212'
    'Testably.Abstractions.FileSystem.Interface'='478ef5ae4d958fb43372cd4cefd39089856ce97611bb1627c7b146669887a43d'
    'TestableIO.System.IO.Abstractions.Wrappers'='f8d2b73dfe1711b36bfa283fa83b62f760682cdb63dee37b4326a0cc42b90994'
    'U8XmlParser'='77f18acd6da0b799e73eb2f25fc1bfeb88d79a8d898063e2d33eb9068b87336d'
}
foreach ($name in $files.Keys) {
    $dll = (Get-Item -LiteralPath $files[$name]).FullName
    if ((Get-FileHash -LiteralPath $dll).Hash -ne $pins[$name]) { throw "Component changed: $name" }
    $assembly = [Reflection.Assembly]::LoadFrom($dll)
}
$v=[Reflection.BindingFlags]'Public,NonPublic,Instance'
$loaderType=$assembly.GetType('Heroes.XmlData.HeroesXmlLoader',$true)
$ctor=$loaderType.GetConstructor($v,$null,[type[]]@([string]),$null)
$mapType=$assembly.GetType('Heroes.XmlData.StormMods.StormModType',$true)
$normal=[Enum]::Parse($mapType,'Normal')
$mapKind=[Enum]::Parse($mapType,'Map')
$origin=$assembly.GetType('Heroes.XmlData.Source.IFileHeroesSource',$true)
$mod=$assembly.GetType('Heroes.XmlData.StormMods.FileMpqStormMod',$true).GetConstructor($v,$null,[type[]]@($origin,[string],[string],$mapType),$null)
$ids = [ordered]@{
    GreymaneDarkflightDisengageRunningWild='Talent'
    GreymaneDisengageHeroicUseSwitch='Effect'
    GreymaneGoForTheThroatResetPlayerCooldown='Effect'
    GreymaneGoForTheThroat='Abil'
}
$genn = (Get-Item -LiteralPath $GennXml).FullName
if ((Get-FileHash $genn).Hash -ne '78a564ee1334eeaee26c4b6c57a7dd5d5b3c048cba63a9b7131440d778b98cff') {throw 'Stock hero changed'}
if ($CocktailMap) { $ids['GreymaneGilneanCocktail'] = 'Abil' }
function New-Baseline($expected,$directory,$cocktailEnabled) {
    $loader=$ctor.Invoke([object[]]@($directory))
    $source=$loaderType.GetField('_heroesSource',$v).GetValue($loader)
    $raw=[Xml.Linq.XElement]::Load($genn)
    foreach ($catalog in 'Model','Talent','Effect','Abil') {$source.StormStorage.AddBaseElementTypes($normal,$catalog,"C$catalog")}
    foreach ($id in $ids.Keys) {
        $node=@($raw.Elements() | Where-Object {$_.Attribute('id').Value -ceq $id -and $_.Name.LocalName.StartsWith('C'+$ids[$id])})
        if($node.Count -ne 1){throw "Stock record count: $id"}
        $n=$node[0]
        if($expected) {
            switch ($id) {
                'GreymaneDarkflightDisengageRunningWild' {
                    $rows=@($n.Element('AbilityModificationArray').Elements('Modifications'))
                    foreach ($row in $rows[7..8]) {$row.Element('Value').SetAttributeValue('value','0')}
                }
                'GreymaneDisengageHeroicUseSwitch' {$n.Element('CaseArray').SetAttributeValue('Effect','DisengageHeroicUseModifyCooldown')}
                'GreymaneGoForTheThroatResetPlayerCooldown' {@($n.Elements('EffectArray'))[2].SetAttributeValue('Value','60')}
                'GreymaneGoForTheThroat' {$n.Element('Cost').Element('Cooldown').SetAttributeValue('TimeUse','60')}
                'GreymaneGilneanCocktail' {
                    if ($cocktailEnabled) { $n.Element('Cost').Element('Cooldown').SetAttributeValue('TimeUse','8') }
                }
            }
        }
        $recordPath=[Heroes.XmlData.StormData.StormPath]::new()
        $recordPath.StormModName='control';$recordPath.StormModPath='control';$recordPath.Path='selected-genndata.xml'
        $source.StormStorage.AddElement($normal,$n,$recordPath)
    }
    return $loader
}
$cases=@(
    @($BaseMap,$false,'662a90d5ea72c8454d66a1070b3200e6a2929f3d2069e2c07ecc07cfcc79b800'),
    @($CandidateMap,$true,'e8d151e5d574babf187e3c0b06cd4b29d2280ac085773afda36a3ebb9c79ffa7')
)
if ($NegativeMap) {
    $cases += ,@($NegativeMap,$true,'df12447e01d95566bb3266083b25e6f00c25a462e24500628e352664493a245f')
}
if ($CocktailMap) {
    $cases += ,@($CocktailMap,$true,'e6167145ee82e6c139f07336cd65fced5c86d162da19baad57a2d3e82b3a455e')
}
$results=@()
foreach ($case in $cases) {
    $file=Get-Item -LiteralPath $case[0]
    if((Get-FileHash $file.FullName).Hash -ne $case[2]){throw 'Map hash'}
    $reader=New-Baseline $false $file.DirectoryName $false
    $expect=New-Baseline $case[1] $file.DirectoryName ($CocktailMap -and $file.FullName -eq (Get-Item -LiteralPath $CocktailMap).FullName)
    $source=$loaderType.GetField('_heroesSource',$v).GetValue($reader)
    $mapLoader=$mod.Invoke([object[]]@($source,'fixture',$file.Name,$mapKind))
    $null=$mapLoader.LoadStormData()
    $source.StormStorage.AddModStorage($mapLoader.StormModStorage)
    $negative=$case[2] -eq 'df12447e01d95566bb3266083b25e6f00c25a462e24500628e352664493a245f'
    $matches=0
    foreach ($id in $ids.Keys) {
        foreach ($method in 'GetStormElement','GetCompleteStormElement') {
            $a=$reader.HeroesData.$method($ids[$id],$id).ToXElement()
            $b=$expect.HeroesData.$method($ids[$id],$id).ToXElement()
            $equal=[Xml.Linq.XNode]::DeepEquals($a,$b)
            if ($negative -and $id -eq 'GreymaneGoForTheThroat') {
                if ($equal -or $a.Element('Cost').Element('Cooldown').Element('TimeUse').Attribute('value').Value -ne '80') {throw 'Indexed Cost negative control did not retain 80'}
            } elseif (-not $equal) {
                throw "Difference $id $method. Actual: $a Expected: $b"
            }
            if ($equal) {$matches++}
        }
    }
    $results+=[ordered]@{map_sha256=$case[2];changed=$case[1];loaded_xml=$mapLoader.StormModStorage.NumberOfXmlDataFiles;full_record_comparisons=2*$ids.Count;matched_whole_record=$matches;indexed_cost_negative=$negative}
}
$receipt=[ordered]@{format='greymane-cooldowns-released-loader-v1';library_sha256=$pins['Heroes.XmlData'];maps=$results;selected_records=@($ids.Keys);native_engine_proof=$false}
$receipt | ConvertTo-Json -Depth 4
