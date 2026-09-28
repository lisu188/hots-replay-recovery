from copy import deepcopy
import protocol41810 as source

for name in dir(source):
    if not name.startswith('__'):
        globals()[name]=getattr(source,name)

typeinfos=deepcopy(source.typeinfos)
typeinfos[93]=('_int',[(0,24)])
typeinfos[49]=('_struct',[[
    ('m_lockTeams',13,-16),('m_teamsTogether',13,-15),('m_advancedSharedControl',13,-14),('m_randomRaces',13,-13),
    ('m_battleNet',13,-12),('m_amm',13,-11),('m_competitive',13,-10),('m_practice',13,-9),('m_cooperative',13,-8),
    ('m_noVictoryOrDefeat',13,-7),('m_heroDuplicatesAllowed',13,-6),('m_fog',24,-5),('m_observers',24,-4),('m_userDifficulty',24,-3),
    ('m_clientDebugFlags',21,-2),('m_ammId',43,-1)
]])

def decode_replay_game_events(contents): return _decode_event_stream(BitPackedDecoder(contents,typeinfos),game_eventid_typeid,game_event_types,True)
def decode_replay_message_events(contents): return _decode_event_stream(BitPackedDecoder(contents,typeinfos),message_eventid_typeid,message_event_types,True)
def decode_replay_tracker_events(contents): return _decode_event_stream(VersionedDecoder(contents,typeinfos),tracker_eventid_typeid,tracker_event_types,False)
def decode_replay_header(contents): return VersionedDecoder(contents,typeinfos).instance(replay_header_typeid)
def decode_replay_details(contents): return VersionedDecoder(contents,typeinfos).instance(game_details_typeid)
def decode_replay_initdata(contents): return BitPackedDecoder(contents,typeinfos).instance(replay_initdata_typeid)
