from copy import deepcopy

import protocol43905 as previous
from decoders import BitPackedDecoder, VersionedDecoder


def remap_type(info):
    kind, args = deepcopy(info)
    def shift(type_id):
        return type_id + (type_id >= 97)
    if kind == '_array':
        args[1] = shift(args[1])
    elif kind == '_optional':
        args[0] = shift(args[0])
    elif kind == '_choice':
        args[1] = {tag: (name, shift(tid)) for tag, (name, tid) in args[1].items()}
    elif kind == '_struct':
        args[0] = [(name, shift(tid), tag) for name, tid, tag in args[0]]
    return kind, args


typeinfos = [remap_type(info) for info in previous.typeinfos]
typeinfos.insert(97, ('_optional', [88]))
typeinfos[93] = ('_int', [(0, 26)])
typeinfos[98] = ('_struct', [[
    ('m_cmdFlags', 93, -7), ('m_abil', 95, -6), ('m_data', 96, -5),
    ('m_vector', 97, -4), ('m_sequence', 83, -3),
    ('m_otherUnit', 43, -2), ('m_unitGroup', 43, -1),
]])


def remap_events(mapping):
    return {eid: (tid + (tid >= 97), name) for eid, (tid, name) in mapping.items()}


game_event_types = remap_events(previous.game_event_types)
message_event_types = remap_events(previous.message_event_types)
tracker_event_types = remap_events(previous.tracker_event_types)
game_eventid_typeid = 0
message_eventid_typeid = 1
tracker_eventid_typeid = 2
svaruint32_typeid = 7
replay_userid_typeid = 8
replay_header_typeid = 18
game_details_typeid = 40
replay_initdata_typeid = 69


def decode_replay_game_events(contents):
    return previous._decode_event_stream(BitPackedDecoder(contents, typeinfos), 0, game_event_types, True)


def decode_replay_message_events(contents):
    return previous._decode_event_stream(BitPackedDecoder(contents, typeinfos), 1, message_event_types, True)


def decode_replay_tracker_events(contents):
    return previous._decode_event_stream(VersionedDecoder(contents, typeinfos), 2, tracker_event_types, False)


def decode_replay_header(contents):
    return VersionedDecoder(contents, typeinfos).instance(replay_header_typeid)


def decode_replay_details(contents):
    return VersionedDecoder(contents, typeinfos).instance(game_details_typeid)


def decode_replay_initdata(contents):
    return BitPackedDecoder(contents, typeinfos).instance(replay_initdata_typeid)


decode_replay_attributes_events = previous.decode_replay_attributes_events
