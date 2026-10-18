"""Synthetic unit fixtures only; no fixture asserts real98348 completeness."""
from dataclasses import replace
from contextlib import redirect_stderr, redirect_stdout
import copy
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import collection_license_audit as collector
import plan_collection_candidates as planner
import scan_collection_alias_nodes as scanner


class SyntheticAliasScanTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='SYNTHETIC-alias-scanner-')
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / 'extracted'
        self.mods = self.root / 'mods'
        self.mods.mkdir(parents=True)
        self.xml = self.mods / 'test.xml'
        self.xml.write_text('''<Catalog>
          <CRewardHero id="ExactHero"><License value="10"/></CRewardHero>
          <CRewardSkin id="NewSkin"><License value="10"/><LegacyRewardId value="OldSkin"/></CRewardSkin>
          <CSkin id="NewSkin" parent="SkinBase"><DisplayModel value="OldSkin"/>
            <RequiredRewardArray value="NewSkin"/><AttributeId value="Skin"/></CSkin>
          <CModel id="OldSkin"><Model value="Assets/OldSkin.m3"/></CModel>
          <CMount id="CurrentMount"><OldItem value="OldMount"/><RequiredRewardArray value="NewMount"/></CMount>
          <CNote id="Note"><Value value="prefixOldSkin"/><Value value="OldSkinSuffix"/>
            <Value value="oldskin"/><Value value=" OldSkin "/><Alias>OldMount</Alias>
            <Alias> OldMount </Alias><Value hidden="PRIVATE-UNMATCHED-TEXT"/></CNote>
        </Catalog>''', encoding='utf-8')
        self.metadata = self.mods / 'hdp.info'
        self.metadata.write_text('{"Version":"2.57.0.98348","IsPtr":false,"ExtractedDate":"SYNTHETIC"}', encoding='utf-8')
        self.log = self.base / 'version.log'
        self.log.write_text(planner.VERSION, encoding='utf-8')
        self.observation = self.base / 'observation.json'
        observation = dict(format='hots-collection-identity-projection-v1', contains_player_ownership_or_identity_data=False,
            cases=[dict(id='old',member_sha256='a'*64,encoding='utf8-name',items=['ExactHero','OldSkin','OldMount'],count=3,distinct_items=3),
                   dict(id='current',member_sha256='b'*64,encoding='big-endian-u64',items=[10],count=1,distinct_items=1)])
        self.observation.write_text(json.dumps(observation), encoding='utf-8')
        self.projection = self.base / 'projection.json'
        self.data = collector.collect_version_bound(self.root,self.observation,planner.VERSION,self.log)
        self.data['generation_provenance'] = dict(collector_sha256='c'*64,expected_build_config=planner.BUILD_CONFIG,
            extractor_archive_sha256='d'*64,extractor_release='5.1.0',github_run_id='123',official_manifest_sha256='e'*64,
            repository_commit='f'*40,workflow_url='https://github.com/example/project/actions/runs/123')
        self.policy = scanner.EvidencePolicy(xml_files=1,legacy_names=3,unresolved_names=2,current_ids=1)
        self.save()
        self.output = self.base / 'output.json'

    def save(self, data=None):
        raw = json.dumps(self.data if data is None else data).encode('utf-8')
        self.projection.write_bytes(raw)
        self.policy = replace(self.policy,projection_sha256=hashlib.sha256(raw).hexdigest())

    def complete(self, root=None, **kwargs):
        return scanner.scan_complete(root or self.root,self.projection,self.observation,self.log,policy=self.policy,**kwargs)

    def subset(self, mapping=None, **kwargs):
        return scanner.scan_subset(mapping or {'mods/test.xml':self.xml},self.projection,self.observation,policy=self.policy,**kwargs)

    def forge_expected_xml_bytes(self, raw):
        self.xml.write_bytes(raw)
        old = next(row for row in self.data['source_files'] if row['kind']=='XML')
        self.data['counts']['source_bytes'] += len(raw)-old['bytes']
        old['bytes'],old['sha256'] = len(raw),hashlib.sha256(raw).hexdigest()
        self.save()

    def args(self):
        return ['--root',str(self.root),'--projection',str(self.projection),
                '--collection-observation',str(self.observation),'--version-log',str(self.log),'--output',str(self.output)]

    def test_exact_matches_exclude_substrings_case_and_whitespace(self):
        result = self.complete()
        self.assertEqual(result['unresolved_names'],['OldMount','OldSkin'])
        self.assertEqual(result['match_count'],5)
        self.assertEqual({row['matched_value'] for row in result['matches']},{'OldMount','OldSkin'})
        self.assertEqual(sum(row['attribute_name']=='#text' for row in result['matches']),1)
        for bad in ('prefixOldSkin','OldSkinSuffix','oldskin',' OldSkin ',' OldMount '):
            self.assertNotIn(bad,json.dumps(result))

    def test_visual_and_named_reward_alias_roles_remain_separate_and_unproven(self):
        rows = self.complete()['matches']
        alias = next(row for row in rows if 'LegacyRewardId' in row['node_path'])
        self.assertEqual(alias['role'],'named-reward-alias-or-migration-field-unverified')
        model = next(row for row in rows if row['owner']['kind']=='CModel')
        display = next(row for row in rows if row['owner']['kind']=='CSkin')
        self.assertEqual(model['role'],'visual-or-audio-asset-reference')
        self.assertEqual(display['role'],'visual-or-audio-asset-reference')
        self.assertTrue(all(not row['alias_or_entitlement_mapping_proven'] for row in rows))

    def test_only_related_fields_from_same_matched_owner_are_exported(self):
        result = self.complete()
        owners = result['related_owning_record_fields']
        reward = next(row for row in owners if row['owner']['kind']=='CRewardSkin')
        self.assertEqual([field['tag'] for field in reward['direct_fields']],['License'])
        skin = next(row for row in owners if row['owner']['kind']=='CSkin')
        self.assertEqual({f['tag'] for f in skin['direct_fields']},{'DisplayModel','RequiredRewardArray','AttributeId'})
        self.assertNotIn('ExactHero',json.dumps(owners))
        self.assertTrue(all(not row['inheritance_or_cross_record_join_performed'] for row in owners))

    def test_no_unmatched_attribute_values_raw_xml_or_absolute_paths_exported(self):
        serialized = json.dumps(self.complete())
        for value in ('PRIVATE-UNMATCHED-TEXT','Assets/OldSkin.m3','<Catalog>',str(self.base)):
            self.assertNotIn(value,serialized)

    def test_complete_inventory_digest_equal_and_subset_explicitly_incomplete(self):
        full = self.complete()
        self.assertTrue(full['all_projected_XML_files_exact_digest_verified'])
        self.assertEqual(full['expected_xml_inventory_sha256'],full['scanned_xml_inventory_sha256'])
        subset = self.subset()
        self.assertFalse(subset['all_projected_XML_files_exact_digest_verified'])
        self.assertFalse(subset['complete_absence_scope_established'])
        self.assertIsNone(subset['fresh_version_log'])
        self.assertEqual(subset['scope'],'subset-pinned-XML-file-digests-only')

    def test_fresh_metadata_timestamp_can_change_but_version_cannot(self):
        self.metadata.write_text('{"Version":"2.57.0.98348","IsPtr":false,"ExtractedDate":"NEW-SYNTHETIC"}',encoding='utf-8')
        result = self.complete()
        self.assertNotEqual(result['fresh_extracted_metadata'][0]['sha256'],self.data['version_binding']['metadata'][0]['sha256'])
        self.assertEqual(result['fresh_extracted_metadata'][0]['observed_version_strings'],[planner.VERSION])

    def test_old_ptr_and_wrong_shape_fresh_metadata_refused(self):
        for text in ('{"Version":"2.57.0.98285","IsPtr":false}',
                     '{"Version":"2.57.0.98348","IsPtr":true}',
                     '{"version":"2.57.0.98348","isPtr":false}',
                     '{"other":"2.57.0.98348"}'):
            with self.subTest(text=text):
                self.metadata.write_text(text,encoding='utf-8')
                with self.assertRaises(collector.CollectionError):self.complete()

    def test_fresh_live_version_log_cannot_be_missing_or_ambiguous(self):
        for text in ('2.57.0.98285','2.57.0.98348\n2.57.0.98285','2.57.0.98348_ptr','no version'):
            with self.subTest(text=text):
                self.log.write_text(text,encoding='utf-8')
                with self.assertRaisesRegex(collector.CollectionError,'Fresh live log'):self.complete()

    def test_missing_extra_or_moved_xml_inventory_is_refused(self):
        empty = self.base/'missing-tree'/'mods'
        empty.mkdir(parents=True)
        (empty/'hdp.info').write_bytes(self.metadata.read_bytes())
        with self.assertRaisesRegex(collector.CollectionError,'inventory differs'):self.complete(empty.parent)
        (self.mods/'extra.xml').write_text('<Catalog/>',encoding='utf-8')
        with self.assertRaisesRegex(collector.CollectionError,'inventory differs'):self.complete()

    def test_same_path_mutated_xml_is_refused_before_node_claims(self):
        self.xml.write_bytes(self.xml.read_bytes().replace(b'OldSkin',b'NewSkin'))
        with self.assertRaisesRegex(collector.CollectionError,'digest or byte size'):self.complete()

    def test_wrong_projection_hash_and_changed_collection_are_refused(self):
        with self.assertRaisesRegex(collector.CollectionError,'SHA256'):
            scanner.scan_complete(self.root,self.projection,self.observation,self.log)
        value=json.loads(self.observation.read_bytes())
        value['cases'][0]['items'][1]='OtherSkin'
        self.observation.write_text(json.dumps(value),encoding='utf-8')
        with self.assertRaisesRegex(collector.CollectionError,'binding differs'):self.complete()

    def test_stored_unresolved_candidate_counts_cannot_be_forged(self):
        self.data['direct_comparison']['exact_legacy_record_name_candidates']=[]
        self.save()
        with self.assertRaisesRegex(collector.CollectionError,'comparison differs'):self.complete()

    def test_projection_ptr_or_wrong_build_provenance_is_refused(self):
        for section,key,value in (('generation_provenance','expected_build_config','0'*32),
                                  ('version_binding','expected_version','2.57.0.98285')):
            data=copy.deepcopy(self.data);data[section][key]=value;self.save(data)
            with self.assertRaises(collector.CollectionError):self.complete()

    def test_ownership_fields_in_projection_are_refused(self):
        data=copy.deepcopy(self.data);data['ownership']=[];self.save(data)
        with self.assertRaisesRegex(collector.CollectionError,'schema'):self.complete()

    def test_projected_metadata_descriptor_must_match_binding(self):
        self.data['version_binding']['metadata'][0]['sha256']='0'*64
        self.save()
        with self.assertRaisesRegex(collector.CollectionError,'metadata descriptor differs'):self.complete()

    def test_projected_byte_totals_cannot_hide_phantom_sources(self):
        self.data['counts']['source_bytes']+=1;self.save()
        with self.assertRaisesRegex(collector.CollectionError,'aggregate source bytes'):self.complete()

    def test_dtd_entities_rejected_in_utf8_utf16_and_utf32(self):
        text='<!DOCTYPE Catalog [<!ENTITY a "OldSkin">]><Catalog><CRewardSkin id="NewSkin"><LegacyId value="&a;"/></CRewardSkin></Catalog>'
        for encoding in ('utf-8','utf-16','utf-32'):
            with self.subTest(encoding=encoding):
                self.forge_expected_xml_bytes(text.encode(encoding))
                with self.assertRaisesRegex(collector.CollectionError,'DTD'):self.complete()

    def test_malformed_xml_is_refused_even_if_projected_digest_matches(self):
        self.forge_expected_xml_bytes(b'<Catalog><CReward></Catalog>')
        with self.assertRaisesRegex(collector.CollectionError,'Malformed XML'):self.complete()

    def test_xml_metrics_are_checked_against_projection(self):
        next(row for row in self.data['source_files'] if row['kind']=='XML')['xml_elements']+=1
        self.save()
        with self.assertRaisesRegex(collector.CollectionError,'shape differs'):self.complete()

    def test_match_node_path_and_related_field_budgets_fail_without_truncation(self):
        for limits in (replace(scanner.LIMITS,matches=0),replace(scanner.LIMITS,matches_per_file=0),
                       replace(scanner.LIMITS,node_path_characters=5),replace(scanner.LIMITS,related_fields=0),
                       replace(scanner.LIMITS,related_fields_per_record=0)):
            with self.subTest(limits=limits),self.assertRaisesRegex(collector.CollectionError,'bound|budget'):
                self.complete(limits=limits)

    def test_unprojected_subset_path_and_empty_subset_are_refused(self):
        for files in ({},{'mods/unlisted.xml':self.xml}):
            with self.subTest(files=files),self.assertRaises(collector.CollectionError):
                scanner.scan_subset(files,self.projection,self.observation,policy=self.policy)

    def test_node_paths_disambiguate_same_tags_by_child_ordinals(self):
        paths=[row['node_path'] for row in self.complete()['matches']]
        self.assertEqual(len(paths),len(set(paths)))
        self.assertTrue(all(path.startswith('Catalog[0]/') for path in paths))

    def test_mixed_content_tail_text_is_not_silently_absent(self):
        raw=b'<Catalog><CNote id="Note"><Value/>OldSkin<Value/>prefixOldSkin</CNote></Catalog>'
        rows,related=scanner._nodes(raw,'mods/synthetic.xml',{'OldSkin'},scanner.LIMITS,{'matches':0,'related':0})
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['attribute_name'],'#tail')
        self.assertEqual(rows[0]['node_path'],'Catalog[0]/CNote[0]/Value[0]')
        self.assertFalse(rows[0]['alias_or_entitlement_mapping_proven'])

    def test_namespace_paths_and_nested_related_content_are_preserved_as_unresolved(self):
        raw=b'<Catalog xmlns:a="urn:a" xmlns:b="urn:b"><CSkin id="Current"><a:Link value="OldSkin"/><b:Link value="OldSkin"/><RequiredRewardArray><Inner value="PrivateNested"/></RequiredRewardArray></CSkin></Catalog>'
        rows,related=scanner._nodes(raw,'mods/synthetic.xml',{'OldSkin'},scanner.LIMITS,{'matches':0,'related':0})
        self.assertEqual(len(rows),2)
        self.assertIn('{urn:a}Link',rows[0]['node_path'])
        self.assertIn('{urn:b}Link',rows[1]['node_path'])
        field=related[0]['direct_fields'][0]['field']
        self.assertIn('nested_or_text_field_content_not_interpreted',field['unresolved'])
        self.assertFalse(field['direct_literal_candidate'])
        self.assertNotIn('PrivateNested',json.dumps(related))

    def test_tail_after_record_belongs_to_catalog_not_previous_reward(self):
        raw=b'<Catalog><CRewardSkin id="Current"><License value="10"/></CRewardSkin>OldSkin</Catalog>'
        rows,related=scanner._nodes(raw,'mods/synthetic.xml',{'OldSkin'},scanner.LIMITS,{'matches':0,'related':0})
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['owner'],{'kind':'Catalog','id':None})
        self.assertEqual(rows[0]['owner_node_path'],'Catalog[0]')
        self.assertEqual(rows[0]['attribute_name'],'#tail')
        self.assertEqual(related,[])

    def test_fixed_unit_queries_require_direct_exact_CUnit_and_preserve_fields(self):
        raw=b'''<Catalog><CUnit id="NovaHoloClone" parent="UnitBase"><BehaviorArray Link="NovaPermanentCloak"/><UnitAlias value="NovaAlias" index="0"/><BehaviorArray value="##id##" removed="1"/></CUnit><CUnit id="NovaHoloCloneCloakedExtra"/><CActorUnit id="AbathurEvolvedMonstrosity"/><Nested><CUnit id="TownCannonTowerL2Standalone"/></Nested></Catalog>'''
        budget={'unit_declarations':0,'unit_fields':0}
        rows=scanner._unit_nodes(raw,'mods/synthetic.xml',{'bytes':len(raw),'sha256':'a'*64},scanner.LIMITS,budget)
        self.assertEqual([row['id'] for row in rows],['NovaHoloClone'])
        self.assertEqual(rows[0]['parent'],'UnitBase')
        self.assertEqual(rows[0]['sha256'],'a'*64)
        fields=rows[0]['direct_fields']
        self.assertEqual(fields[0]['field']['attributes'],{'Link':'NovaPermanentCloak'})
        self.assertIn('indexed_array_operation_not_resolved',fields[1]['field']['unresolved'])
        self.assertIn('template_not_resolved',fields[2]['field']['unresolved'])
        self.assertIn('removal_operation_not_resolved',fields[2]['field']['unresolved'])
        self.assertFalse(rows[0]['inheritance_or_alias_resolution_performed'])

    def test_unit_query_absence_requires_full_inventory_and_does_not_change_legacy_scope(self):
        full,subset=self.complete(),self.subset()
        self.assertEqual(full['unresolved_names'],['OldMount','OldSkin'])
        self.assertEqual(full['match_count'],5)
        self.assertTrue(all(row['absent_from_all_projected_XML'] is True for row in full['unit_identity_queries']['results']))
        self.assertTrue(all(row['absent_from_all_projected_XML'] is None for row in subset['unit_identity_queries']['results']))
        self.assertFalse(subset['unit_identity_queries']['complete_pinned_XML_inventory_verified'])
        self.assertFalse(full['unit_identity_queries']['numeric_unit_links_or_replacements_inferred'])

    def test_unit_query_budgets_refuse_instead_of_truncating(self):
        raw=b'<Catalog><CUnit id="NovaHoloClone"><BehaviorArray Link="Cloak"/></CUnit></Catalog>'
        for limits in (replace(scanner.LIMITS,unit_declarations=0),replace(scanner.LIMITS,unit_fields=0),
                       replace(scanner.LIMITS,unit_fields_per_record=0)):
            with self.subTest(limits=limits),self.assertRaisesRegex(collector.CollectionError,'Unit.*budget'):
                scanner._unit_nodes(raw,'mods/synthetic.xml',{'bytes':len(raw),'sha256':'a'*64},limits,
                                    {'unit_declarations':0,'unit_fields':0})

    def test_cli_existing_or_missing_parent_is_rejected_before_scanning(self):
        for output in (self.output,self.base/'missing'/'report.json'):
            if output==self.output:output.write_bytes(b'preserve')
            self.output=output
            with patch.object(scanner,'scan_complete') as scan,redirect_stderr(io.StringIO()):
                self.assertEqual(scanner.main(self.args()),1)
                scan.assert_not_called()

    def test_cli_full_fixture_creates_only_new_projection_and_keeps_inputs(self):
        before={path:path.read_bytes() for path in (self.xml,self.metadata,self.projection,self.observation)}
        real_scan=scanner.scan_complete
        with patch.object(scanner,'scan_complete',side_effect=lambda *args:real_scan(*args,policy=self.policy)),redirect_stdout(io.StringIO()):
            self.assertEqual(scanner.main(self.args()),0)
        raw=self.output.read_bytes()
        self.assertNotIn(b'\r',raw)
        self.assertTrue(raw.endswith(b'\n'))
        self.assertFalse(json.loads(raw)['aliases_registered'])
        for path,value in before.items():self.assertEqual(path.read_bytes(),value)


if __name__=='__main__':unittest.main()
