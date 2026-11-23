"""Bind the nested opening SoundLink and SoundPlayForPlayer calls to distinct registry allocations."""

from argparse import ArgumentParser
from hashlib import sha256
import json
from pathlib import Path
import struct

from announcer_allocation_constraints import allocation_constraints
from build_gate_order_map import definition
from dragon_announcer_default_map import script
from sound_object_registry import ObjectRegistry
from verify_sound_registry import verify as verify_registry
from verify_dispatch_group_native import PE, TEXT, TEXT_RVA, pinned


def require(check, reason):
    if not check:
        raise ValueError(reason)


def pair_trace(seed_objects=0):
    """One possible native allocation history with one retained, temporary soundlink per call."""
    state = ObjectRegistry()
    for _ in range(seed_objects):
        state.allocate(11)
    words=[]
    for _ in range(11):
        link = state.allocate(16)
        sound = state.allocate(15)
        require(state.live[link & 65535]==16 and state.live[sound & 65535]==15 and link!=sound, "Classes overlap")
        state.retire_slot(link & 65535)
        words.append(sound)
    require(allocation_constraints(words)["allocation_lower_bound"]==22+seed_objects,"Synthetic minimum not tight")
    return words


def verify(executable, static_text, lib, signed_map):
    base = verify_registry(executable,static_text)
    image,code = pinned(executable,PE),pinned(static_text,TEXT)
    nt, = struct.unpack_from("<I",image,60)
    optional = nt+24
    sh = optional+struct.unpack_from("<H",image,nt+20)[0]
    sections = [struct.unpack_from("<8sIIII",image,sh+40*i) for i in range(struct.unpack_from("<H",image,nt+6)[0])]
    image_base, = struct.unpack_from("<Q",image,optional+24)
    def original(site,count):
        offsets=[p+site-v for _,_,v,n,p in sections if v<=site and site+count<=v+n]
        require(len(offsets)==1,"Unbacked original RVA")
        return image[offsets[0]:offsets[0]+count]
    def op(site, hex_bytes):
        value=bytes.fromhex(hex_bytes)
        require(code[site-TEXT_RVA:site-TEXT_RVA+len(value)] == value, f"Unexpected native bytes {site:#x}")
    def rel(site,opcode,target):
        op(site,opcode)
        operand=site+len(bytes.fromhex(opcode))
        require(operand+4+struct.unpack_from("<i",code,operand-TEXT_RVA)[0]==target,f"Unexpected relative reference at {site:#x}")
    bindings={}
    for name,literal,ref,desc,ordinal,vm,call,handler in (
        ("PlayerGroupNextPlayer",0x29aa1c8,0x233dc1,0x233dc8,1142,0x2002906,0x200290c,0x20c6670),
        ("SoundLink",0x2991ff0,0x234aeb,0x234af2,1236,0x2003404,0x200340a,0x20d37f0),
        ("SoundPlayForPlayer",0x29aa950,0x234b21,0x234b2d,1238,0x2003460,0x2003475,0x20d4050),
        ("SoundLastPlayed",0x29aa9c0,0x234c03,0x234c0a,1242,0x2003518,0x2003518,0x20d33c0),
        ("SoundWait",0x29aaa40,0x234d10,0x234d1c,1250,0x20035cf,0x20035d9,0x20d5480)):
        require(original(literal,len(name)+1)==name.encode()+b"\0","Native name differs")
        rel(ref,"488d15",literal)
        rel(desc,"488d0d",0x4120b50+24*ordinal)
        require(struct.unpack_from("<I",code,0x200accc-TEXT_RVA+4*ordinal)[0]==vm,"VM handler differs")
        rel(call,"e8",handler)
        bindings[name]=ordinal
    for origin,target in ((0x20d3b34,0x1ff7240),(0x20d4076,0x9fb110),(0x20d4081,0x9fd780),
                          (0x20d409d,0x20d60f0),(0x20d62dc,0x1ff7240),(0x20d40bb,0x9fb110),
                          (0x20d40c6,0x9fd780),(0x20d33c4,0x9fb110),(0x9fd7c5,0x1ff71b0)):
        rel(origin,"e8",target)
    rel(0x20d39f0,"e9",0x20d3a80)
    rel(0x20d3b1e,"488d05",0x26b4bb8)
    require(struct.unpack("<Q",original(0x26b4bb8+32,8))[0]-image_base==0xae8100,"Link class method differs")
    for addr,v in {
        0xae8100:"b810000000c3", 0x20d380e:"83faff0f84c3010000",
        0x20d3b31:"488bcbe80737f2ff488b03488bcbff5050488b8590010000488943108b7b08",
        0x20d3c87:"8bc7", 0x20d6121:"43807cca06100f85da0100004b8b74ca08",
        0x20d407b:"33d2488d4828", 0x20d40b8:"8b5b08",0x20d40c0:"8bd3488d4828",
        0x20d33c9:"8b40284883c428c3",0x9fd78f:"39117439",0x9fd7a6:"6642ff44c004",
        0x9fd7bd:"6641015400047505",0x9fd7ca:"891f",
        0x20c667e:"8079060b",0x20c668d:"8d420185c0781883f8107d13418b48100f1f000fa3c1720cffc083f8107cf4b8ffffffffc3",
    }.items():
        op(addr,v)
    raw=lib.read_bytes()
    require(sha256(raw).hexdigest()=="d59cddc1401cb067ed269e8c9f86fd0dd0e9ddb9309b0b6b505a643bddeb671e","Wrong target SoundLib")
    playback=definition(raw.decode("utf-8-sig").replace("\r\n","\n"),"void","libSond_gf_SoundAnnouncerVOPlayAnnouncerVOForPlayer")
    call="SoundPlayForPlayer(SoundLink(lv_soundID, c_soundIndexAny), c_maxPlayers, libCore_gv_playerGroupFromPlayer[lp_player], 100.0, 0.0);"
    require(playback.count(call)==1,"Missing nested link call")
    require(sha256(signed_map.read_bytes()).hexdigest()=="150bdcea5435021263c84648d892c2c3dcc26bff8c72d1be5198c31a4bb09791"
            and sha256(script(signed_map)).hexdigest()=="dbf9e1fd81e63250961e2fddb7ede47d84ff7c441a94335a60dc20c7d915c4c8","Wrong signed map")
    examples=[pair_trace(seed)[0] for seed in (0,1)]
    require(examples==[0x10003,0x10004],"Trace failed to distinguish pre-states")
    return dict(build=base["build"],vm_ordinals=bindings,regular_group_order=list(range(11)),soundlink_class=16,sound_class=15,
                soundlink_virtual_table="0x26b4bb8",allocator="0x1ff7240",minimum_ordinary_allocations_per_successful_call=2,
                prior_last_played_reference_cleared_before_sound_allocation=True,synthetic_first_words=examples,
                target_first_sound_handle=None)


if __name__=="__main__":
    parser=ArgumentParser(description=__doc__)
    for key in ("executable","static_text","lib","signed_map"):
        parser.add_argument(key,type=Path)
    print(json.dumps(verify(**vars(parser.parse_args())),indent=2))
