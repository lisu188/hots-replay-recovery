"""Verify the target Dragon Shire opening announcer path, sound assets and native event gates."""

from argparse import ArgumentParser
from hashlib import sha256
from pathlib import Path
from xml.etree import ElementTree as ET
import json
import struct

from build_gate_order_map import definition
from dragon_announcer_default_map import digest, require
from verify_dispatch_group_native import TEXT, TEXT_RVA, pinned
from verify_sound_offset_native import verify as verify_offset

LIBS = "87b44ff3f91d9058f5001f926129a04d225f8a11fa05b99e1571362539ec3b7b"
LADY = "c46ea47c94c391b60f33eeda4bee10b96f82588f43246906a7dc69a44d4e26f2"
PACK = "2dc90f41fd15e9e3e569e1da7bd5d9c809ba067cd14c705b77ea2e3fe9c6315a"
AUDIO = {
    "LadyofThorns_HeroSelect00": ("bec61da678e8a44a6af01a347d3ed9861aef64a44fade06405c3e1a15aa04973",124641),
    "LadyofThorns_HeroSelect_Observer00": ("fc1a3ff452a7480310fe5864910da90b91424adc3b5d19451f6730df9a632c23",133688),
}
REPLAY_RESULT = "e4c5b37d0d3e95cb499e62341e254dec5f10a0eb2349658ba64e0b75b8b5ef9d"


def ordered(text, *tokens):
    i = 0
    for token in tokens:
        pos = text.find(token,i)
        require(pos >= 0, "Missing ordered token: "+token)
        i = pos+len(token)


def identity(path, expected):
    raw = path.read_bytes()
    require(digest(raw)==expected, "Wrong input "+path.name)
    return raw


def library_sources(folder):
    document = json.loads(identity(folder/"member.json", LIBS))
    return {r["saved_name"]: identity(folder/r["saved_name"],r["sha256"]).decode("utf-8-sig").replace("\r\n","\n")
            for r in document["members"]}


def ogg_stream(raw):
    cursor = 0
    final = rate = None
    serial = None
    seq = 0
    while cursor < len(raw):
        require(raw[cursor:cursor+5] == b"OggS\0" and final is None, "Unexpected Ogg page")
        flags = raw[cursor+5]
        granule, stream, page = struct.unpack_from("<QII",raw,cursor+6)
        require(page==seq and (serial is None or serial==stream), "Noncontiguous Ogg serial")
        serial = stream
        count = raw[cursor+26]
        header = cursor + 27 + count
        end = header + sum(raw[cursor+27:header])
        require(end<=len(raw), "Truncated Ogg page")
        if seq == 0:
            require(flags & 2 and raw[header:header+7] == b"\x01vorbis", "Missing Vorbis ID")
            rate = struct.unpack_from("<I",raw,header+12)[0]
        if flags & 4:
            final = granule
        cursor, seq = end, seq+1
    require(rate == 44100 and final is not None, "Missing EOS or unexpected audio rate")
    return dict(samples=final,sample_rate_hz=rate,loops_at_16hz=round(16*final/rate,5))


def verify(scripts, catalog, voice, timeline, exe, text):
    libs = library_sources(scripts)
    game, core, sound, ntv, header = [libs[k+".galaxy"] for k in ("gamelib","heroeslib","soundlib","nativelib","heroeslib_h")]
    countdown = definition(game,"bool","libGame_gt_AnnounceCountdown_Func")
    ordered(countdown,"announceCountdownCallback != null","GameModes_Tutorial1","WaitForTimer(libGame_gv_openTheGatesTimer, 34.0, false)",
            "AnnouncementAddItemForPlayerGroup(libCore_gv_allHeroPlayersPlusObserver","AnnouncerVOEvents_GetReadyForBattle",
            "announcement_NoDelay_C","WaitForTimer(libGame_gv_openTheGatesTimer, 12.125")
    ordered(definition(ntv,"void","libNtve_gf_WaitForTimer"),"TimerGetRemaining(lp_timer) <= lp_time","Wait(0.05, c_timeGame)")
    ordered(header,"oBSERVER_ObserverUIPlayer = 0","bALMaxPlayers = 10")
    ordered(game,"auto410EB58E_ae = libCore_gv_bALMaxPlayers","PlayerGroupAdd(libCore_gv_allHeroPlayersPlusObserver, lv_index);",
            "PlayerGroupAdd(libCore_gv_allHeroPlayersPlusObserver, libCore_gv_oBSERVER_ObserverUIPlayer);")
    ordered(core,"autoFE901BA2_ae = libCore_gv_bALMaxEnginePlayerCount","lv_itPlayer = 0;",
            "libCore_gv_playerGroupFromPlayer[lv_itPlayer] = PlayerGroupSingle(lv_itPlayer);")
    ordered(definition(game,"void","libGame_gf_AnnouncementAddItemForPlayerGroup"),"announcement_SystemEnabled == false",
            "PlayerGroupNextPlayer(","MapMechanicIntroFinished(","AnnouncementInsertItemIntoQueueForPlayer(","TimerGetRemaining(",
            "AnnouncementPlayNextItemForPlayer(lv_itPlayer)")
    ordered(definition(game,"void","libGame_gf_AnnouncementPlayNextItemForPlayer"),
            "lv_announcerVOEvent[1] != libCore_ge_AnnouncerVOEvents_Null","SoundAnnouncerVOPlayAnnouncerVOForPlayer(")
    legacy = definition(core,"void","libCore_gf_DataAnnouncerVOSetAnnouncerPackForPlayerGroup")
    modern = definition(core,"void","libCore_gf_DataAnnouncerVOSetDefaultAnnouncerForPlayerGroup")
    ordered(legacy,".lv_selectedAnnouncerVOPack = lp_announcerPack;")
    require("DataLootContentLoadAnnouncer" not in legacy and "lv_lootContent" not in legacy, "Legacy setter now feeds current store")
    ordered(modern,"lv_announcerIsPlayerAssigned == false","DataLootContentLoadAnnouncerPackDataIntoIndex(lp_announcerPackLink, lv_itPlayer, false);")
    require(modern.count("DataLootContentLoadAnnouncerPackDataIntoIndex(")==1, "Unexpected default path")
    loader = definition(core,"void","libCore_gf_DataLootContentLoadAnnouncerPackDataIntoIndex")
    prefix = "lv_lootContent.lv_loot_AnnouncerPack.lv_announcerVOLines"
    ordered(loader,'"VoiceOver", c_playerAny','lv_announcerIsPlayerAssigned = lp_announcerIsPlayerAssigned',
            "lv_itEvent == libCore_ge_AnnouncerVOEvents_GetReadyForBattle", "lv_heroCatalogLink ==",
            'lv_vOString + "Player"', 'lv_announcerVOID + "_" + lv_dataFieldMapString','CatalogEntryIsValid(c_gameCatalogSound',
            prefix+"[lv_itEvent].lv_soundLink = lv_soundID")
    ordered(core,'DataAnnouncerVOMapDataField(libCore_ge_AnnouncerVOEvents_GetReadyForBattle, "HeroSelect", false)')
    ordered(definition(sound,"void","libSond_gf_SoundAnnouncerVOPlayAnnouncerVOForPlayer"),prefix+"[lv_vOEvent].lv_soundLink",
            "if ((lv_soundID == null))","return ;","SoundPlayForPlayer(SoundLink(lv_soundID, c_soundIndexAny), c_maxPlayers, libCore_gv_playerGroupFromPlayer[lp_player]",
            "SendEventAnnouncerVOInitiated(SoundLastPlayed(), lp_player, (lp_event))")
    ordered(definition(sound,"bool","libSond_gt_HeroVOCheckForHeroVOAfterAnnouncerEvents_Func"),
            "lv_sound = libGame_gf_AnnouncerVOInitiatedSound();","lv_announcerEvent = libGame_gf_AnnouncerVOInitiatedAnnouncerEvent();",
            "lv_announcerEvent == libCore_ge_AnnouncerVOEvents_GetReadyForBattle","GameModes_ArenaMode","GameModes_AttackDefend",
            "SoundWait(lv_sound, 0.0, c_soundOffsetEnd);")
    pack = ET.fromstring(identity(catalog/"announcerpackdata.xml",PACK)).find("CAnnouncerPack[@id='StormAnnouncerPackQuick']")
    xml = ET.fromstring(identity(catalog/"ladyofthornsvodata.xml",LADY))
    item = xml.find("CAnnouncerPack[@id='LadyofThorns']")
    require((item.get("parent"),item.get("heroid"),pack.find("VoiceOver").get("value"),pack.find("Hero").get("value")) ==
            ("StormAnnouncerPackQuick","AI","##id##","##heroid##"),"Wrong voice inheritance")
    variants = {}
    for key,(expected_hash,samples) in AUDIO.items():
        entry = xml.find("CSound[@id='"+key[:-2]+"']")
        require([a.get("TemplateParam") for a in entry.findall("AssetArray")] == [key], "Unexpected catalog sound variant")
        candidates = [p for p in voice.glob("*.ogg") if p.name.endswith(key+".ogg") and digest(p.read_bytes())==expected_hash]
        require(len(candidates)==1,"Missing enUS voice variant "+key)
        variants[key]=ogg_stream(candidates[0].read_bytes())
        require(variants[key]["samples"]==samples,"Unexpected Vorbis sample count")
    native = verify_offset(exe,text)
    code = pinned(text,TEXT)
    for site,op in {
        0xAC60DB:"8b87c000000085c00f849e000000", 0x689A3F:"0fb6480c8b060fa3c8736f",
        0x689A5A:"837f54007559488b4f404885c9744683b9a80200000074474885c9743883b9a802000003742f",
        0x689A94:"85db740e83fb01751c2bc63bc50f96c0eb053bf50f93c084c0740a488b4c2460e8a7200f00",
    }.items():
        require(code[site-TEXT_RVA:site-TEXT_RVA+len(op)//2]==bytes.fromhex(op),"Unexpected offset predicate")
    doc=json.loads(timeline.read_bytes())
    require(digest(json.dumps(doc, sort_keys=True,separators=(",",":")).encode("ascii"))==REPLAY_RESULT,"Unmatched replay report")
    return dict(registered_event=native["event"], producer_candidate="GetReadyForBattle",
                default_sound="LadyofThorns_HeroSelect",default_restricted_to_unassigned=True,
                legacy_assignment_reaches_modern_store=False,english_audio=variants,controls=doc["totals"],
                first_target_sound_word=None)


if __name__=="__main__":
    cli=ArgumentParser(description=__doc__)
    for name in ("scripts","catalog","voice","timeline","exe","text"): cli.add_argument(name,type=Path)
    print(json.dumps(verify(**vars(cli.parse_args())),indent=2))
