"""Candidate-only checks; tiny XML fixtures are synthetic, never real ownership."""
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from collection_license_audit import CollectionError, collect_version_bound
import plan_collection_candidates as planner


class PlannerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        mods = self.root / 'extract' / 'mods'
        mods.mkdir(parents=True)
        (mods/'hdp.info').write_text('{"Version":"2.57.0.98348","IsPtr":false}', encoding='utf-8')
        (mods/'test.xml').write_text('''<Catalog>
          <CRewardSkin id="Alpha"><License value="10"/></CRewardSkin>
          <CRewardMount id="Beta"><License value="11"/><License value="12"/></CRewardMount>
          <CRewardIcon id="Horse" parent="Parent"><License value="13"/></CRewardIcon>
          <CSkin id="ProductOnly"><ProductId value="14"/></CSkin>
          <CRewardHero id="Peer"><License value="10"/></CRewardHero>
          <CRewardHero id="Default" default="1"><License value="15"/></CRewardHero>
          <CRewardHero id="Indexed"><License value="15" index="0"/></CRewardHero>
          <CRewardSkin id="Duplicate"><License value="16"/></CRewardSkin>
          <CRewardSkin id="Duplicate"><License value="16"/></CRewardSkin>
          <CRewardHero id="Unobserved"><License value="99"/></CRewardHero>
          <CHero id="NumericCollision"><ProductId value="10"/></CHero>
        </Catalog>''', encoding='utf-8')
        names = ['Alpha','Beta','Horse','Missing','ProductOnly','Peer','Default','Indexed','Duplicate','Unobserved']
        self.observation = self.root/'observation.json'
        self.obs = dict(format='hots-collection-identity-projection-v1', contains_player_ownership_or_identity_data=False,
            cases=[dict(id='old',member_sha256='a'*64,encoding='utf8-name',items=names,count=len(names),distinct_items=len(names)),
                   dict(id='current',member_sha256='b'*64,encoding='big-endian-u64',items=list(range(10,17)),count=7,distinct_items=7)])
        self.observation.write_text(json.dumps(self.obs), encoding='utf-8')
        log = self.root/'version.log'
        log.write_text(planner.VERSION,encoding='utf-8')
        self.data = collect_version_bound(mods.parent,self.observation,planner.VERSION,log)
        self.data['generation_provenance'] = dict(collector_sha256='c'*64,expected_build_config=planner.BUILD_CONFIG,
            extractor_archive_sha256='d'*64,extractor_release='5.1.0',github_run_id='123',official_manifest_sha256='e'*64,
            repository_commit='f'*40,workflow_url='https://github.com/example/project/actions/runs/123')
        self.licenses = self.root/'licenses.json'

    def run_plan(self, data=None):
        raw = json.dumps(self.data if data is None else data).encode('utf-8')
        self.licenses.write_bytes(raw)
        return planner.plan(self.licenses,self.observation,expected_sha256=hashlib.sha256(raw).hexdigest())

    def test_candidates_do_not_join_product_namespace_or_resolve_ambiguity(self):
        report = self.run_plan()
        self.assertEqual(report['counts'], dict(legacy_names=10,current_observed_ids=7,
            single_observed_license_candidates=4,single_without_record_reasons=2,single_with_record_reasons=2,
            unresolved_names=6,unresolved_status_counts={'no-observed-literal-license':3,
                'multiple-observed-literal-licenses':1,'no-exact-reward-record':2}))
        rows = {row['legacy_name']:row for row in report['candidates']}
        self.assertEqual(rows['ProductOnly']['observed_license_candidates'],[])
        self.assertEqual(rows['Beta']['observed_license_candidates'],[11,12])
        self.assertEqual(rows['Alpha']['numeric_product_namespace_collisions'],[10])
        self.assertEqual(rows['Alpha']['other_legacy_names_sharing_candidate'],['Peer'])
        self.assertFalse(rows['Horse']['one_candidate_without_record_reasons'])
        self.assertFalse(rows['Duplicate']['one_candidate_without_record_reasons'])
        self.assertEqual(rows['Duplicate']['license_values_with_multiple_reward_declarations'],[16])
        self.assertFalse(report['whole_collection_conversion_eligible'])
        self.assertTrue(all(not row['alias_or_effective_mapping_proven'] for row in rows.values()))

    def test_default_and_indexed_declarations_do_not_supply_candidates(self):
        rows = {row['legacy_name']:row for row in self.run_plan()['candidates']}
        self.assertEqual(rows['Default']['observed_license_candidates'],[])
        self.assertEqual(rows['Indexed']['observed_license_candidates'],[])

    def test_missing_duplicate_labels_cannot_hide_record_order_blocker(self):
        for row in self.data['declarations']:
            if row['id']=='Duplicate': row['unresolved']=[]
        rows = {row['legacy_name']:row for row in self.run_plan()['candidates']}
        self.assertFalse(rows['Duplicate']['one_candidate_without_record_reasons'])
        self.assertIn('duplicate_record_identity_catalog_order_not_resolved',rows['Duplicate']['declaration_unresolved_reasons'])

    def test_cli_projection_pin_rejects_changed_bytes(self):
        self.run_plan()
        with self.assertRaisesRegex(CollectionError,'SHA256'):
            planner.plan(self.licenses,self.observation)

    def test_wrong_version_unbound_or_wrong_build_configuration(self):
        for section,key,value in [('version_binding','expected_version','2.57.0.98285'),
            ('version_binding','status','unversioned-research-only'),
            ('generation_provenance','expected_build_config','0'*32)]:
            with self.subTest(key=key):
                data=copy.deepcopy(self.data); data[section][key]=value
                with self.assertRaises(CollectionError): self.run_plan(data)

    def test_version_metadata_and_log_must_agree(self):
        for key,value in [('observed_versions',['2.57.0.98285']),('bytes',True),('sha256','invalid')]:
            with self.subTest(key=key):
                data=copy.deepcopy(self.data); data['version_binding']['version_log'][key]=value
                with self.assertRaises(CollectionError): self.run_plan(data)

    def test_malformed_source_schema_paths_and_indexes(self):
        mutations=[lambda d:d['source_files'][0].update(path='mods/../outside.xml'),
            lambda d:d['source_files'][0].update(kind='arbitrary'),
            lambda d:d['source_files'][0].update(raw_xml='forbidden'),
            lambda d:d['declarations'][1].update(declaration_index=0),
            lambda d:d['declarations'][0].update(source='mods/unlisted.xml'),
            lambda d:d['declarations'][0].update(unresolved=[{}])]
        for mutate in mutations:
            with self.subTest(mutate=mutate):
                data=copy.deepcopy(self.data); mutate(data)
                with self.assertRaises(CollectionError): self.run_plan(data)

    def test_numeric_bounds_and_literal_disagreement(self):
        for number in [-1,True,1<<64,10.0,11]:
            with self.subTest(number=number):
                data=copy.deepcopy(self.data); data['declarations'][0]['fields']['License'][0]['numeric_value']=number
                with self.assertRaises(CollectionError): self.run_plan(data)

    def test_duplicate_json_key_and_nonfinite_json(self):
        for raw in [b'{"format":0,"format":1}',b'{"format":NaN}']:
            with self.subTest(raw=raw):
                self.licenses.write_bytes(raw)
                with self.assertRaises(CollectionError):
                    planner.plan(self.licenses,self.observation,expected_sha256=hashlib.sha256(raw).hexdigest())

    def test_collection_binding_and_player_fields_rejected(self):
        self.obs['cases'][0]['items'][0]='Changed'
        self.observation.write_text(json.dumps(self.obs),encoding='utf-8')
        with self.assertRaisesRegex(CollectionError,'binding'): self.run_plan()
        self.obs['player_ownership'] = [[True]]
        self.observation.write_text(json.dumps(self.obs),encoding='utf-8')
        with self.assertRaisesRegex(CollectionError,'catalog-only'): self.run_plan()

    def test_stored_comparison_cannot_override_declarations(self):
        self.data['direct_comparison']['current_ids_with_direct_license_declarations']=999
        with self.assertRaisesRegex(CollectionError,'comparison'): self.run_plan()

    def test_output_refuses_overwrite_before_planning(self):
        output=self.root/'report.json'; output.write_bytes(b'preserve')
        with patch.object(planner,'plan') as plan_call, patch('sys.stderr',new=io.StringIO()):
            with self.assertRaises(SystemExit): planner.main(['--licenses','missing','--collection-observation','missing','--output',str(output)])
            plan_call.assert_not_called()
        self.assertEqual(output.read_bytes(),b'preserve')


class ActualProjectionTests(unittest.TestCase):
    def test_pinned_actual_56_candidates_207_unresolved(self):
        root=Path(os.environ.get('COLLECTION_PLAN_FIXTURES',Path(__file__).resolve().parent))
        licenses=root/'observations'/'collection-license-current-98348.json'
        if not licenses.exists(): self.skipTest('Set COLLECTION_PLAN_FIXTURES to the repository with pinned observations')
        observation=root/'observations'/'collection-identities-2026-10-18.json'
        before=(hashlib.sha256(licenses.read_bytes()).hexdigest(),hashlib.sha256(observation.read_bytes()).hexdigest())
        result=planner.plan(licenses,observation)
        self.assertEqual(before[0],planner.LICENSE_SHA256)
        self.assertEqual(before[1],'0fa8a041fa8d6b9ba22ba6ff8be10d4f42beccc7d9577d0b6ead2d8e0fa909c9')
        self.assertEqual(result['counts'],dict(legacy_names=263,current_observed_ids=5418,
            single_observed_license_candidates=56,single_without_record_reasons=54,single_with_record_reasons=2,
            unresolved_names=207,unresolved_status_counts={'no-exact-reward-record':201,'no-observed-literal-license':6}))
        blocked=[row for row in result['candidates'] if len(row['observed_license_candidates'])==1 and row['declaration_unresolved_reasons']]
        self.assertEqual({row['legacy_name']:row['observed_license_candidates'] for row in blocked},{'Horse':[10182],'Vulture':[18535]})
        self.assertTrue(all(row['declaration_unresolved_reasons']==['parent_inheritance_not_resolved'] for row in blocked))
        self.assertEqual(before,(hashlib.sha256(licenses.read_bytes()).hexdigest(),hashlib.sha256(observation.read_bytes()).hexdigest()))


if __name__=='__main__': unittest.main()
