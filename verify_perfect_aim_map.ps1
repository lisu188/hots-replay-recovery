param(
    [Parameter(Mandatory)][string]$ParentMap,
    [Parameter(Mandatory)][string]$CandidateMap,
    [Parameter(Mandatory)][string]$RepeatMap,
    [Parameter(Mandatory)][string]$GennXml,
    [Parameter(Mandatory)][string]$EffectXml,
    [Parameter(Mandatory)][string]$MpqToolDll,
    [Parameter(Mandatory)][string]$CascLibDll,
    [Parameter(Mandatory)][string]$LibraryDirectory
)
$ErrorActionPreference = 'Stop'
function Get-PinnedFile($path, $hash) {
    $item = Get-Item -LiteralPath $path
    if ((Get-FileHash -LiteralPath $item.FullName).Hash -ne $hash) { throw "Unexpected $($item.Name)" }
    return $item
}
$pins = [ordered]@{
    'Heroes.MpqTool'='0d15438f3b692537a037a55fdb82a536539a186aaf21f0a5239e74a1bc384a0f'
    'CascLib'='8be4b72776a3a4eca6708cc204860c51592c8f886224dd6ccbdec03b6fa82a11'
    'Heroes.LocaleText'='1389202f367769652d963280538475558517f191da4ba3e68519b10a1fc27212'
    'Testably.Abstractions.FileSystem.Interface'='478ef5ae4d958fb43372cd4cefd39089856ce97611bb1627c7b146669887a43d'
    'TestableIO.System.IO.Abstractions.Wrappers'='f8d2b73dfe1711b36bfa283fa83b62f760682cdb63dee37b4326a0cc42b90994'
    'U8XmlParser'='77f18acd6da0b799e73eb2f25fc1bfeb88d79a8d898063e2d33eb9068b87336d'
    'Heroes.XmlData'='4013071b5683ce8090096d84082879d34a30620ada741acc5841cb5bd89fa2ee'
}
foreach ($name in $pins.Keys) {
    $path = switch ($name) {
        'Heroes.MpqTool' { $MpqToolDll }
        'CascLib' { $CascLibDll }
        default { Join-Path $LibraryDirectory "$name.dll" }
    }
    $assembly = [Reflection.Assembly]::LoadFrom((Get-PinnedFile $path $pins[$name]).FullName)
}
$baseHash = 'e7ce5d12d5a93840a333a6e27b3f15d9cab9917be2e88d0040f19d638e4f9bbf'
$candidateHash = '9c223f3e4d9fb31324126b91f7e51048dd6c011ac0d4dcdf6f582e2978f92870'
$parent = Get-PinnedFile $ParentMap $baseHash
$candidate = Get-PinnedFile $CandidateMap $candidateHash
$repeat = Get-PinnedFile $RepeatMap $candidateHash
if ($candidate.FullName -eq $repeat.FullName -or $candidate.Length -ne 2198586 -or
    -not [Linq.Enumerable]::SequenceEqual[byte]([IO.File]::ReadAllBytes($candidate.FullName),
                                                [IO.File]::ReadAllBytes($repeat.FullName))) { throw 'Rebuild differs' }
$coreHash = '72eadb172d398a95a37929e62b65247be504b39dbd899bb05a2f47a6991e2ea0'
$core = [Xml.Linq.XElement]::Load((Get-PinnedFile $EffectXml $coreHash).FullName)
$genn = [Xml.Linq.XElement]::Load((Get-PinnedFile $GennXml '78a564ee1334eeaee26c4b6c57a7dd5d5b3c048cba63a9b7131440d778b98cff').FullName)
$id = 'GreymaneGilneanCocktailPerfectAimModifyUnit'
$parentId = 'StormManaRestore'
$records = @($core.Elements('CEffectCreateHealer') | Where-Object { $_.Attribute('id').Value -ceq $parentId })
$records += @($genn.Elements('CEffectCreateHealer') | Where-Object { $_.Attribute('id').Value -ceq $id })
if ($records.Count -ne 2 -or $records[0].Element('RechargeVital').Attribute('value').Value -ne 'Energy' -or
    $records[1].Attribute('parent').Value -cne $parentId) { throw 'Stock energy inheritance differs' }
$flags = [Reflection.BindingFlags]'Public,NonPublic,Instance'
$loaderType = $assembly.GetType('Heroes.XmlData.HeroesXmlLoader',$true)
$loaderConstructor = $loaderType.GetConstructor($flags,$null,[type[]]@([string]),$null)
$modType = $assembly.GetType('Heroes.XmlData.StormMods.StormModType',$true)
$normal = [Enum]::Parse($modType,'Normal')
$mapKind = [Enum]::Parse($modType,'Map')
$sourceType = $assembly.GetType('Heroes.XmlData.Source.IFileHeroesSource',$true)
$modConstructor = $assembly.GetType('Heroes.XmlData.StormMods.FileMpqStormMod',$true).GetConstructor(
    $flags,$null,[type[]]@($sourceType,[string],[string],$modType),$null)
$results = @()
foreach ($case in @(@($parent, '45'), @($candidate, '50'))) {
    $file, $rate = $case
    $loader = $loaderConstructor.Invoke([object[]]@($file.DirectoryName))
    $source = $loaderType.GetField('_heroesSource',$flags).GetValue($loader)
    $source.StormStorage.AddBaseElementTypes($normal,'Effect','CEffect')
    foreach ($entry in $records) {
        $origin = [Heroes.XmlData.StormData.StormPath]::new()
        $origin.StormModName = 'reference'
        $origin.StormModPath = 'reference'
        $origin.Path = 'effect.xml'
        $source.StormStorage.AddElement($normal,[Xml.Linq.XElement]::new($entry),$origin)
    }
    $map = $modConstructor.Invoke([object[]]@($source,'fixture',$file.Name,$mapKind))
    $null = $map.LoadStormData()
    $source.StormStorage.AddModStorage($map.StormModStorage)
    foreach ($method in 'GetStormElement','GetCompleteStormElement') {
        $merged = $loader.HeroesData.$method('Effect',$id).ToXElement()
        if ($merged.Element('RechargeVitalRate').Attribute('value').Value -ne $rate -or
            $merged.Element('ImpactUnit').Attribute('value').Value -cne 'Caster') {
            throw "Merged $method refund differs"
        }
        if ($method -eq 'GetCompleteStormElement' -and
            $merged.Element('RechargeVital').Attribute('value').Value -cne 'Energy') { throw 'Merged vital differs' }
    }
    $results += [ordered]@{rate=[int]$rate; vital='Energy'; recipient='Caster'; methods_checked=2}
}
[ordered]@{reader_sha256=$pins['Heroes.XmlData']; core_effect_sha256=$coreHash; parent_sha256=$baseHash;
    candidate_sha256=$candidateHash; repeated_bytes_equal=$true; maps=$results; native_engine_verified=$false} | ConvertTo-Json -Depth 4
