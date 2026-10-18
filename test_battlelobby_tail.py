import contextlib
from dataclasses import replace
import io
import json
from pathlib import Path
import tempfile
import unittest

from battlelobby_tail import LayerError, Token, crosscheck, decode_tail, encode_tail, main, summary

# Frozen complete synthetic suffixes with nonzero unknown fields, identities,
# availability bytes and optional branches. Names/IDs below are synthetic.
OLD=bytes.fromhex('50524546495821210000000112636f6c6c656374696f6e5f7072697661746500000001aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa12345678cafebabe0100000105004a195c9b030000000100000000007890004a195c9b030000000d00543a5345435245543d422195c92f0000000106543a53454352455480000001010000000000000000000000000000000080000000070000000005000fc10d017b0000001100000080064d59235441470000001300000000034832b937010000000100003d010000000000000b01000000000000000000010d049ccaea74010000010f01908aa44f92869e4e00000025411a9aa20d0100000a1702000b0300000d0d0b0000030d')
CURRENT=bytes.fromhex('505245464958212100010123456789abcdef00000001aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa01416e647512345678cafebabe0100000105004a195c9b030000000100000000007890004a195c9b030000000d00543a5345435245543d422195c92f0000000106543a534543524554800000010100000000000000000000000000000000000000800000000700000000050018020c017b03000004010000000c024d5923544147000004d20100000901000000024a195c9b030000000100001e030000000000000503000000000000000000001d084e657574010000001f014845524f49434f4e00000025050143a9aa26030000002b002a00010f000001153b0000003d004932b9370700000103000000000000000000000040')


def decoded(modern=False):
    return decode_tail(CURRENT if modern else OLD,64,'current-tail' if modern else 'historical-tail')


def structures(tail, extra=False):
    toon=dict(m_region=2,m_programId=b'Hero',m_realm=1,m_id=123456)
    details=dict(m_playerList=[dict(m_workingSetSlotId=0,m_toon=toon)])
    slots=[dict(m_workingSetSlotId=0,m_toonHandle=b'2-Hero-1-123456')]
    if extra:slots.append(dict(m_workingSetSlotId=1,m_toonHandle=b'2-Hero-1-654321'))
    init=dict(m_syncLobbyState=dict(m_lobbyState=dict(m_randomSeed=0x12345678,m_slots=slots),
        m_gameDescription=dict(m_randomValue=0x12345678,m_disabledHeroList=[b'Andu'])))
    return details,init


class TailTests(unittest.TestCase):
    def test_historical_frozen_golden(self):
        tail=decoded();r=summary(tail)
        self.assertEqual(encode_tail(tail),OLD)
        self.assertEqual((r['collection_count'],r['collection_entry_sizes']),(1,[18]))
        self.assertEqual(r['player_unknown_block_bits'],174)
        self.assertEqual(r['player_unknown_blocks_set_bits_total'],3)
        self.assertEqual(r['community_named_build32_distinct_values'],[64541])
        self.assertFalse(r['community_named_build32_verified_client_build'])
        self.assertEqual((r['hero_table_count'],r['hero_icon_record_count']),(1,1))
        self.assertIsNone(r['allheroes_count'])

    def test_current_frozen_golden(self):
        tail=decoded(True);r=summary(tail)
        self.assertEqual(encode_tail(tail),CURRENT)
        self.assertEqual(r['collection_entry_sizes'],[8])
        self.assertEqual(r['player_unknown_block_bits'],198)
        self.assertEqual(r['community_named_build32_distinct_values'],[98348])
        self.assertEqual(r['allheroes_count'],1)
        self.assertEqual(r['disabled_hero_count'],1)

    def test_private_crosschecks_pass(self):
        for modern in (False,True):
            tail=decoded(modern);d,i=structures(tail);r=crosscheck(tail,d,i)
            self.assertTrue(r['details_identity_multiset_equal'])
            self.assertTrue(r['initdata_identity_multiset_equal'])
            self.assertTrue(r['all_details_participants_match_tail_by_slot'])
            self.assertTrue(r['seed_matches_lobby'])
            self.assertTrue(r['seed_matches_game_description'])

    def test_crosscheck_identity_mutation_detected(self):
        tail=decoded();d,i=structures(tail);d['m_playerList'][0]['m_toon']['m_id']+=1
        r=crosscheck(tail,d,i)
        self.assertFalse(r['details_identity_multiset_equal'])
        self.assertEqual(r['details_identity_and_slot_matches'],0)
        self.assertTrue(r['initdata_identity_multiset_equal'])

    def test_crosscheck_seed_mutation_detected(self):
        tail=decoded();d,i=structures(tail);i['m_syncLobbyState']['m_lobbyState']['m_randomSeed']+=1
        self.assertFalse(crosscheck(tail,d,i)['seed_matches_lobby'])

    def test_crosscheck_duplicate_slots_refused(self):
        tail=decoded();d,i=structures(tail);d['m_playerList'].append(d['m_playerList'][0])
        with self.assertRaisesRegex(LayerError,'Duplicate'):crosscheck(tail,d,i)

    def test_malformed_toon_handle_refused(self):
        tail=decoded();d,i=structures(tail);i['m_syncLobbyState']['m_lobbyState']['m_slots'][0]['m_toonHandle']=b'bad'
        with self.assertRaisesRegex(LayerError,'format'):crosscheck(tail,d,i)

    def test_wrong_profile_refused(self):
        for raw,profile in ((OLD,'current-tail'),(CURRENT,'historical-tail')):
            with self.subTest(profile=profile),self.assertRaises(LayerError):decode_tail(raw,64,profile)

    def test_truncated_member_refused(self):
        for raw,profile in ((OLD,'historical-tail'),(CURRENT,'current-tail')):
            with self.subTest(profile=profile),self.assertRaises(LayerError):decode_tail(raw[:-1],64,profile)

    def test_extra_bytes_refused(self):
        with self.assertRaisesRegex(LayerError,'trailing'):decode_tail(OLD+b'\x00',64,'historical-tail')

    def test_nonzero_eof_padding_refused(self):
        r=summary(decoded());self.assertGreater(r['trailing_padding_bits'],0)
        raw=bytearray(OLD);raw[-1]|=0x80
        with self.assertRaisesRegex(LayerError,'padding'):decode_tail(bytes(raw),64,'historical-tail')

    def test_oversized_collection_count_refused(self):
        raw=bytearray(OLD);raw[8:12]=bytes.fromhex('00010000')
        with self.assertRaisesRegex(LayerError,'bound'):decode_tail(bytes(raw),64,'historical-tail')

    def test_collection_availability_mismatch_refused(self):
        raw=bytearray(OLD);raw[34]^=1
        with self.assertRaisesRegex(LayerError,'counts differ'):decode_tail(bytes(raw),64,'historical-tail')

    def test_legacy_utf8_corruption_refused(self):
        raw=bytearray(OLD);raw[13]=0xff
        with self.assertRaisesRegex(LayerError,'UTF-8'):decode_tail(bytes(raw),64,'historical-tail')

    def test_invalid_profile_or_boundary_refused(self):
        for start,profile in ((63,'historical-tail'),(-8,'historical-tail'),(64,'guessed')):
            with self.subTest(start=start,profile=profile),self.assertRaises(LayerError):decode_tail(OLD,start,profile)

    def test_conversion_refused(self):
        with self.assertRaisesRegex(LayerError,'conversion'):encode_tail(decoded(),'current-tail')

    def test_modified_tokens_never_encoded(self):
        tail=decoded();first=tail.tokens[0]
        changed=replace(tail,tokens=(Token(first.path,first.width,first.value+1),)+tail.tokens[1:])
        with self.assertRaisesRegex(LayerError,'changed'):encode_tail(changed)

    def test_privacy_and_summary_copy(self):
        tail=decoded();r=summary(tail);value=json.dumps(r)
        for secret in ('collection_private','T:SECRET','MY#TAG','123456'):
            self.assertNotIn(secret,value);self.assertNotIn(secret,repr(tail))
        r['collection_count']=999
        self.assertEqual(summary(tail)['collection_count'],1)
        self.assertFalse(r['private_names_toons_slots_or_ownership_values_emitted'])

    def test_cli_refuses_existing_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'report.json';out.write_text('preserve')
            with contextlib.redirect_stderr(io.StringIO()),self.assertRaises(SystemExit):
                main(['unused','--start-bit','64','--profile','historical-tail','--report',str(out)])
            self.assertEqual(out.read_text(),'preserve')

    def test_cli_outputs_only_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw=Path(tmp)/'member.bin';out=Path(tmp)/'report.json';raw.write_bytes(OLD)
            with contextlib.redirect_stdout(io.StringIO()):main([str(raw),'--start-bit','64','--profile','historical-tail','--report',str(out)])
            self.assertEqual(len(list(Path(tmp).iterdir())),2)
            self.assertTrue(json.loads(out.read_text())['complete_eof_covered'])
            self.assertEqual(raw.read_bytes(),OLD)


if __name__=='__main__':unittest.main()
