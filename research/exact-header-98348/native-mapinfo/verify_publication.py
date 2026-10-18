"""Verify only the published source/metadata snapshot; no private inputs needed."""
import argparse
import hashlib
import importlib
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch


def verify(repo):
    proof=json.loads((repo/'observations/exact-header-98348/native-mapinfo/publication-bindings.json').read_bytes())
    for row in proof['files']:
        path=repo/row['target']
        raw=path.read_bytes()
        if len(raw)!=row['bytes'] or hashlib.sha256(raw).hexdigest()!=row['sha256']:
            raise ValueError('Published frozen payload differs')
    folder=repo/'research/exact-header-98348/header-field-exposure'
    sys.path[:0]=[str(repo),str(folder)]
    native_tests=importlib.import_module('test_native_mapinfo')
    header_tests=importlib.import_module('test_header_field_exposure')
    audit=header_tests.audit
    original_read=audit.read
    public_sources={
        'native-header-mapinfo-selected-graph.json':repo/'observations/exact-header-98348/header-field-exposure/native-header-mapinfo-selected-graph.json',
        'native_mapinfo_schema_98348.json':repo/'native_mapinfo_schema_98348.json'}
    # The frozen research tests use original producer paths. Route only their
    # two immutable metadata inputs to the exact same published bytes. Keep
    # bounded regular-file reads, native binding and every assertion unchanged.
    def published_read(path,limit=512*1024):
        if path.name not in public_sources:
            raise ValueError('Unlisted research test input refused')
        return original_read(public_sources[path.name],limit)
    with patch.object(audit,'read',published_read):
        suite=unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromModule(native_tests),
                                 unittest.defaultTestLoader.loadTestsFromModule(header_tests)])
        result=unittest.TextTestRunner(verbosity=1).run(suite)
    if not result.wasSuccessful() or result.testsRun!=27 or result.skipped:
        raise ValueError('Published synthetic verification incomplete')
    return {'format':'hots-native-mapinfo-published-source-verification-v1',
        'frozen_payload_hashes_verified':len(proof['files']),
        'portable_native_MapInfo_tests_passed':13,'published_header_metadata_tests_passed':14,
        'research_test_input_relocation':'Two exact public metadata files only; assertions and bounded reader unchanged.',
        'private_inputs_PE_replays_headers_or_network_used':False,
        'actual_21_control_audit_reexecuted':False,'client_launched':False,'full_upgrade_complete':False}


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--repo',type=Path,required=True)
    args=parser.parse_args()
    print(json.dumps(verify(args.repo.resolve()),sort_keys=True))
