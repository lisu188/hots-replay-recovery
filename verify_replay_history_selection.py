"""Check the file-open replay route independently of any recorded checksum value."""
import argparse
from contextlib import closing
from hashlib import sha256
import json
from pathlib import Path
from struct import unpack_from

from first_sync_game import SOURCE, game
from mpq_reader import MPQArchive
from verify_predecessor_origin import static as predecessor
from verify_sync_vector_source import TEXT_BASE, need


# Half-open RVA windows independently decoded in IDA. The parent verifier pins
# the complete original PE and the complete static text before checking these.
WINDOWS = (
    (0xfb870b, 0xfb8734, 'a1fc621a3691bc2e2b1e611b'),
    (0xfb4afe, 0xfb4b12, 'e8e69e0d47d79887bec3a6a5'),
    (0xfb4e63, 0xfb4ea5, '6390dccf4a1ac02bf924e362'),
    (0xcbef50, 0xcbef89, '6317e1da7b1d8b390ff53753'),
    (0x6b8f48, 0x6b8f6e, 'da6bca136da67903406ad07a'),
    (0x6b8fd9, 0x6b9036, 'dcccf7ebc90345b02133f93e'),
    (0xd00220, 0xd0024c, 'cd31a5b3a0a5743e82a84142'),
    (0xd0016b, 0xd001be, '70876becf60858d69694e521'),
    (0xe01890, 0xe018a9, '37ee47b224c9166a5cd27324'),
    (0xdfdf40, 0xdfdf59, '9dfa1c6e93daa6f21bdb4b67'),
    (0xe01e40, 0xe01ea0, 'fc9f7a7ab6fe104153a330c0'),
    (0xe01ec7, 0xe01ee4, '16cc6ff4f4bce40f9f3e2235'),
    (0xe02d7b, 0xe02e82, '4bdeb1171f40876da1a108fb'),
    (0xe03034, 0xe03078, 'e7ac7e27fae9410e688d8c97'),
    (0xcfe3df, 0xcfe442, 'f1555d34598a674f3005b631'),
    (0xcfeadb, 0xcfeaf1, '6740637d740677495cf9d99f'),
    (0xcfec43, 0xcfec56, 'ee50181f01b9075aeb70f8f8'),
    (0xcfecd1, 0xcfece0, 'b81125977a4d6a496627979a'),
    (0xdfe419, 0xdfe454, '6f72699fa860baa6644fcca7'),
    (0xdfe5e1, 0xdfe620, 'bdd4dadba9a312d9642edb44'),
    (0xcbf880, 0xcbf88f, 'a2bb06cb2c283aab5094a827'),
    (0x1323802, 0x13238a8, 'eecd8b4f1e65402ad0598a2f'),
    (0x133bff6, 0x133c02f, 'b137280a83c704e5c6a524af'),
    (0x26861a, 0x268628, 'ae37301eedd4af0f69dee101'),
    (0x1327dd6, 0x1327deb, '58c79b577d2e4f83f21f675d'),
    (0x133bf50, 0x133bfe8, 'd302dc943c5dc3e64d3f65d7'),
    (0x132cff7, 0x132d027, '805751193a774b51df984cea'),
    (0xcd6d83, 0xcd6d9a, '31eb5e58ff959ec5f6934fff'),
    (0xcc1647, 0xcc164d, 'e8c0577e933aaef994c496e6'),
    (0xcd6e24, 0xcd6e62, '0c9604b6aa86b0c164977cf0'),
)


def native(exe, section):
    previous = predecessor(exe, section)
    physical, code = exe.read_bytes(), section.read_bytes()
    nt, = unpack_from('<I', physical, 60)
    first = nt + 24 + unpack_from('<H', physical, nt + 20)[0]
    sections = [unpack_from('<8sIIII', physical, first + i*40)
                for i in range(unpack_from('<H', physical, nt + 6)[0])]

    def target(site, prefix):
        loc = site - TEXT_BASE
        op = bytes.fromhex(prefix)
        need(code[loc:loc+len(op)] == op, f'opcode {site:x}')
        return site + len(op) + 4 + unpack_from('<i', code, loc + len(op))[0]

    for lo, hi, digest in WINDOWS:
        need(sha256(code[lo-TEXT_BASE:hi-TEXT_BASE]).hexdigest().startswith(digest), f'window {lo:x}')
    for table, slots in {
        0x271d938: {0x68:0xe01e40, 0x70:0xe01ea0},
        0x271d600: {0x68:0xdfe2f0, 0x70:0xdfe7d0},
        0x27bc518: {0x1f8:0x133bf50, 0x260:0x133bff0, 0x268:0x1327dd0, 0x270:0x132b840},
    }.items():
        for slot, dest in slots.items():
            rva = table + slot
            offset, = (raw+rva-start for _,_,start,size,raw in sections if start <= rva and rva+8 <= start+size)
            need(unpack_from('<Q', physical, offset)[0] == 0x140000000 + dest, f'vtable slot {rva:x}')
    for site, dest in {
        0xfb871b:0xfb4ae0, 0xfb872f:0xd00220, 0xfb4b01:0xcbef50, 0xd0023b:0x6b8f40,
        0xd0018f:0xdfdf40, 0xd001ab:0xe01890, 0xe01edf:0xe02b90,
        0x133bf60:0x132cff0, 0x132d004:0x134e680, 0xcfeaec:0x134e680, 0xcfec51:0x134dd30,
        0x133c000:0x2685a0, 0x1327de6:0x2685a0, 0xdfe447:0xcbf880, 0xcd6d95:0xcc1630,
        0xcd6e98:0xcd2f40, 0xcd301c:0xd00070, 0xd000f4:0x6b8f40,
    }.items():
        need(target(site, 'e8') == dest, f'call {site:x}')
    need(target(0xcfe43c,'0f84') == 0xcfea2d and target(0xe02de8,'0f85') == 0xe02e82,
         'recorded archive success branch')
    need(target(0xd000c1,'e9') == 0xd000d0, 'StartReplay transfers the same descriptor')
    return dict(build=98348, original=previous['exe'], static_text=previous['static_text'],
                checked_code_windows=len(WINDOWS), fresh_archive_mode=2, fresh_state_class=0,
                archive_setter_slot='0x1f8', optional_history_setter_slot='0x260',
                state_class_zero_dispatches_alternate_history_method=False,
                start_replay_ipc=dict(mode=2, state_class=1, descriptor_variant=2,
                                      alternate_history_guard_returns=0),
                optional_path_empty_at_manager_construction=True)


def physical(path, digest, build):
    protocol, _ = game(path, digest, build)
    with closing(MPQArchive(path)) as archive:
        data = archive.read_file('replay.initData')
        protocol.decode_replay_initdata(data)
        details = protocol.decode_replay_details(archive.read_file('replay.details'))
    return dict(sha256=digest, build=build, init_data_sha256=sha256(data).hexdigest(),
                mini_save=details['m_miniSave'], restart_as_transition=details['m_restartAsTransitionMap'])


def verify(exe, section, ten, manifest):
    result = native(exe, section)
    references = json.loads(manifest.read_bytes())
    import first_sync_game
    pin_file = Path(first_sync_game.__file__).resolve().parent/'observations'/'first-sync-game.json'
    need(set(references) == {row['replay_sha256'] for row in json.loads(pin_file.read_bytes())['references']}
         and len(references) == 24, 'expected independent native controls')
    result['ten'] = physical(ten, SOURCE, 41810)
    result['controls'] = [physical(Path(name), key, 98348) for key,name in sorted(references.items())]
    need(all(row['mini_save'] is False and row['restart_as_transition'] is False
             for row in [result['ten'], *result['controls']]), 'unexpected saved or transition map')
    result['prediction_for_each_control'] = (
        'Opening on the fresh file-request route FB870B selects archive mode 2 and state class 0. '
        'With the manager still in its initial optional-path state at Apply, it selects the clean setup tail.')
    result['recording_time_history_vector'] = None
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('exe', 'section', 'ten', 'controls'):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    print(json.dumps(verify(args.exe, args.section, args.ten, args.controls), indent=2))
