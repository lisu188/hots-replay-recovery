"""Record narrow primary-source conclusions and exact static XML counterexamples."""
import hashlib
import json
from pathlib import Path

from collection_license_audit import _read, write_new_report


BASE=Path(__file__).resolve().parent
REPO=Path(r'C:/Users/andrz/git/hots-replay-recovery')


def sha(raw):return hashlib.sha256(raw).hexdigest()


def bound(path,expected,maximum=16*1024*1024):
    raw=_read(path,maximum)
    if sha(raw)!=expected:raise ValueError('Input evidence SHA differs')
    return json.loads(raw)


def main():
    registry=bound(BASE/'static-package-registry-comparison.json','f3d2562a541394a2d5400bb12de4f4c70c746d8626f41bb0a0580488bdf62cc8')
    availability=bound(BASE/'availability-aggregate-15-cases.json','ba8938db00088d869d6bd5d0aa2e45c41b5b79d2755d6dd778605384da7ce89f')
    projection=bound(REPO/'observations/collection-license-current-98348.json','c8f03ddbc859feb5c2dc1836761201b5e6fea4632ce0325817abdd7299c8aa22')
    observation=bound(REPO/'observations/collection-identities-2026-10-18.json','0fa8a041fa8d6b9ba22ba6ff8be10d4f42beccc7d9577d0b6ead2d8e0fa909c9')
    files={row['path']:row for row in projection['source_files']}
    current=set(next(case['items'] for case in observation['cases'] if case['encoding']=='big-endian-u64'))
    latest=next(row for row in registry['current_cached_headers'] if row['header_sha256']=='f115def2b9adbc67cfdd8bb4255cff1a8b44a8c921e98f56eebe20708660a7c9')
    missing=set(latest['current_missing_numeric_ids'])
    selected=missing|{1209137}
    records=[]
    for row in projection['declarations']:
        if not row['type'].startswith('CReward'):continue
        values={field.get('numeric_value') for field in row['fields'].get('License',[]) if field['direct_literal_candidate']}
        if values&selected:
            source=files[row['source']]
            records.append({'declaration':row,'source_bytes':source['bytes'],'source_sha256':source['sha256'],
                'observed_5418_membership':{str(value):value in current for value in sorted(values&selected)}})
    def source(filename,url,scope,claim):
        raw=(BASE/'primary'/filename).read_bytes()
        return {'url':url,'local_source_excerpt_sha256':sha(raw),'scope':scope,'supported_observation':claim}
    findings={'format':'hots-collection-registry-primary-source-semantics-assessment-v1',
        'registry_receipt_sha256':'f3d2562a541394a2d5400bb12de4f4c70c746d8626f41bb0a0580488bdf62cc8',
        'availability_receipt_sha256':'ba8938db00088d869d6bd5d0aa2e45c41b5b79d2755d6dd778605384da7ce89f',
        'current_XML_projection_sha256':'c8f03ddbc859feb5c2dc1836761201b5e6fea4632ce0325817abdd7299c8aa22',
        'producer_sha256':sha(Path(__file__).read_bytes()),
        'primary_sources':[
            source('s2mdec-s2m-field23-24-excerpt.go','https://github.com/sc2-arcade-watcher/s2mdec/blob/b48c60a697b12ae1dc8681a2d42ce313958ce94a/s2m.go#L827-L837',
                'Excerpt from lines719-855; no complete-file SHA is claimed.',
                'Field23 comment gives an SC2 voice-pack-name example; field24 comment suggests possible reward IDs. No authoritative HotS ownership or generation name is assigned.'),
            source('HDP-DataParser.cs','https://github.com/HeroesToolChest/HeroesDataParser/blob/1c2488069392d6c465faecb9abb150ec16664688/HeroesDataParser/Infrastructure/XmlDataParsers/DataParser.cs#L78-L84',
                'Full small public source file.', 'SetHyperlinkIdProperty copies the current XML hyperlinkid string into a HyperlinkId property.'),
            source('HDP-StoreItemParserBase.cs','https://github.com/HeroesToolChest/HeroesDataParser/blob/1c2488069392d6c465faecb9abb150ec16664688/HeroesDataParser/Infrastructure/XmlDataParsers/StoreItemParserBase.cs#L81-L84',
                'Full small public source file.', 'A missing HyperlinkId falls back to the current catalog record ID. The code establishes no legacy entitlement migration semantics.'),
            source('IHyperlinkId.cs','https://github.com/HeroesToolChest/Heroes.Element/blob/0e8b1bf97df6d65c190c578df05bca0d0b59f99a/Heroes.Element/Models/ObjectProperties/IHyperlinkId.cs',
                'Full small public interface.', 'The interface describes a hyperlink-ID property and provides no ownership or alias contract.')],
        'conclusions':{'old_ordered_global_registry_is_static_package_bound':registry['legacy_static_registry_order_binding_established'],
            'all13_current_ordered_raw8byte_registries_identical':availability['current_thirteen_ordered_raw8byte_registries_identical'],
            'current_complete_authentic_package_registry_binding_established':False,
            'availability_has_nonconstant_match_state':availability['distinct_full_availability_blobs']==14,
            'availability_flag_or_ownership_meaning_proven':False,'HyperlinkId_legacy_ownership_mapping_proven':False,
            'all_raw_XML_Licenses_equal_observed_registry':False,'current_registry_order_generator_algorithm_proven':False},
        'closest_cached_registry_missing9_current_XML_reward_records_and_extra_counterexample':records,
        'extra1209137_related_loadout_records':[row for row in projection['declarations'] if row['type']=='CSkin' and row['id'] in {'MephistoMoophisto','MephistoMoophistoCommon'}],
        'limitations':['All9 missing cached-registry IDs have current direct CRewardSkin License records, but do not provide the absent exact current package header.',
            'The1209137 MephistoMoophisto raw XML reward is absent from every observed5418 registry. Selected-field projection contains no effective disable/availability reason.',
            'No per-slot value, availability hash, player identity, raw header or raw XML is exported. No replay rewrite was performed.']}
    output=BASE/'registry-semantics-primary-source-findings.json'
    write_new_report(findings,output)
    print(json.dumps({'report_sha256':sha(output.read_bytes()),'direct_reward_records':len(records),'ownership_semantics_proven':False},sort_keys=True))


if __name__=='__main__':main()
