"""Verify 98348 history publication paths and physical replay option/cadence witnesses."""

import argparse
from collections import Counter
from contextlib import closing
from hashlib import sha256
import json
from pathlib import Path
from struct import iter_unpack, unpack_from

from first_sync_game import SOURCE, game, opening
from mpq_reader import MPQArchive
from portable_sync_98348 import decode_sync, encode_sync
from verify_sync_vector_source import TEXT_BASE, need, verify


# RVA, exclusive end, digest of authenticated static instructions.
WINDOWS = [
    (0x132dd98,0x132de69,"121264d1186b0d94b20cfab0"), # frame publication before tick
    (0x132f610,0x132f72d,"a5aabdef2b28a4c7fb69aee7"), # counted history -> publication
    (0x986f20,0x986f5a,"73261e3f2a285d6534c11dcd"), # request: defer then copy latest
    (0x989810,0x9898c8,"0ac04b775798fa3f220b35f4"), # gate + mode0 previous -> latest
    (0x977e40,0x977ee2,"a6c0bfa9140275593d1adc68"), # counted copy
    (0x977fea,0x977ffb,"d64170f1d74392db755c5528"), # full copy includes processed flag
    (0x97d995,0x97dae3,"41d0aa2b26639ed6d2547556"), # append two records, 72 words
    (0x988d90,0x988dba,"0ce0ff6c3c5a00eddd7f64cd"), # new entry count and flag
    (0x985b61,0x985baa,"484fca1d43a27199c7b83111"), # tick sample, mode4, latest
    (0x987d5a,0x987db0,"aaebb92f0fef1535bde611a4"), # clear, mode4 bit6 fast return
    (0x989cc0,0x989d05,"7a6250f198e2cae7bee04fdb"), # primary + component clear
    (0x987db0,0x987e15,"ee5af7967fb31c634e26e66f"), # full primary then mode check
    (0x988065,0x988089,"51beba9f7e5b2b19f686bcd0"), # aggregate and processed byte
    (0x985bb0,0x985e54,"c001c0dee4c05f7bbe8adcab"), # CRC32 of five little-endian u32s
    (0xe0e9d3,0xe0e9f5,"3fb720b15638ab41eaf68cf8"), # option -> receiver +4a
    (0xe0de53,0xe0de87,"f75b803c8ba22185b46cc2b1"), # each active user's option bit
    (0xe0df12,0xe0df20,"d14a67a8c2ffe2b9bc114157"), # missing -> false setter
    (0x97aa10,0x97aa52,"66d9696665c1afff00ea5763"), # replace bit 6 in world flags
    (0xcfa471,0xcfa518,"83fc2c538861bda45cd55813"), # mod identity check, then map load
    (0xe04c44,0xe04c89,"ba45c04afcff0c3a4895aa34"), # load call after validation
    (0x6ac94d,0x6ac965,"3626c930d11b9b8ed7557c38"), # append with edx=1, r8d=0
    (0x97d884,0x97d8d4,"045d2df52dc251fe1b22bbbd"), # optional hydration of the old pair
    (0x97dad1,0x97dae3,"8d1e080c065961a932459ca6"), # keep previously selected mod slice
    (0x980570,0x9805a1,"69c5d3fcb05b2500f511d607"), # mod read takes selected index
    (0x97db59,0x97db8c,"75a2bd706b1e0d78a1ee85e3"), # allocate and construct world
    (0x977910,0x97796a,"965468cede963e5c97c2279f"), # fresh world flags and timer words
    (0x977ac0,0x977ad0,"a8f3a711573ef4bfd898296e"), # copy encoded initial field to +14
    (0x987390,0x9873e8,"45ca41329e48abca7c1d3bc2"), # world reset
    (0x987496,0x9874ef,"7fb55188487a37c108cb4249"), # world time/scalar reset
]


def native(pe_path, text_path):
    base = verify(pe_path,text_path)
    pe = pe_path.read_bytes()
    text = text_path.read_bytes()
    def code(start, end):
        return text[start-TEXT_BASE:end-TEXT_BASE]
    for start,end,digest in WINDOWS:
        need(sha256(code(start,end)).hexdigest().startswith(digest),f"code {start:#x}")
    for site,target in [(0x132dda4,0x132f610),(0x132ddae,0x132fcf0),(0x132de64,0x983c50),
                        (0x985b88,0x987d10),(0x987d5a,0x989cc0),(0x987d9b,0x985bb0),
                        (0xe0de82,0x97aa10),(0xe0c3de,0xe0dd00),(0x25f983,0x97d870),
                        (0x6ac960,0x97d870),(0xdfb763,0x97d870),(0xcfa47c,0xe04850),
                        (0xcfa504,0xe04a60),(0xe04c7e,0x6ac830),(0xe0486b,0x980570),
                        (0x98057b,0x989810),(0x97d8c5,0x989810),(0x97db6b,0x977910)]:
        ins = code(site,site+5)
        need(ins[0] == 0xe8 and site+5+int.from_bytes(ins[1:],"little",signed=True)==target,
             f"direct call {site:#x}")
    nt, = unpack_from("<I",pe,60)
    opt = nt+24
    sections = opt + unpack_from("<H",pe,nt+20)[0]
    ranges = [unpack_from("<8sIIII",pe,sections+40*i) for i in range(unpack_from("<H",pe,nt+6)[0])]
    def data(rva, length):
        pos, = [raw+rva-start for _,_,start,size,raw in ranges if start<=rva and rva+length<=start+size]
        return pe[pos:pos+length]
    def scalar(rva, size):
        return int.from_bytes(data(rva,size),"little")
    pr,pl = unpack_from("<II",pe,opt+136)
    chained, = [u for a,b,u in iter_unpack("<III",data(pr,pl)) if a<=0x985b88<b]
    unwind = data(chained,16)
    need(unwind[0] == 0x21 and unwind[2]==0 and unpack_from("<I",unwind,4)[0]==0x983c50,
         "mode4 tail belongs to the tick")
    need(scalar(0x2f3d318,4)==0 and scalar(0x2f3d328,8)==0,"image history initialization")
    need(scalar(0x27c9fd4,4)==225,"native root type of input #7")
    field_table = 0x27becb0+8*scalar(0x27becb0+8*(225+1),8)
    need(field_table==0x27c2098 and scalar(field_table+5*8,8)==4,"native option byte offset")
    return dict(build=98348,pe=base["pe_sha256"],static_text=base["static_text_sha256"],
                exact_code_windows=len(WINDOWS),mode4_tick_tail_parent="0x983c50",
                deferred_gate="count > 1 and (count-2).processed == 0",
                deferred_action="build mode 0 on count-2, copy whole predecessor to count-1",
                post_tick_fast_mode4_nonzero_capable_slots=[0],fast_counted_words=72,
                fast_crc32_input_le32=["world+0x0c","decoded world+0x14","world+0","world+4","RVA 0x34ef5c0"],
                initialized_world_fields={"+0":"0xffffffff","+4":0,"+0xc":0},
                reset_scalar_34ef5c0=0,
                map_load_after_successful_mod_check=dict(append_fresh_entries=2,count_per_entry=72,
                    prior_mod_index_preserved=True, gameplay_cycle_identity_established=False),
                universal_full_build_on_request=False)


def count_replays(paths, build):
    counts = Counter()
    for digest,path in paths.items():
        protocol,raw = game(Path(path),digest,build)
        options = [e for e,_,_ in opening(raw,protocol) if e["_eventid"]==7]
        ids = [e["_userid"]["m_userId"] for e in options]
        need(len(set(ids))==len(ids) and all(e["_gameloop"]==0 for e in options),"opening options")
        if build==41810:
            need(ids==list(range(10)),"TEN physical users")
        counts["options_false"] += sum(not e["m_syncChecksummingEnabled"] for e in options)
        counts["options_true"] += sum(e["m_syncChecksummingEnabled"] for e in options)
        with closing(MPQArchive(Path(path))) as a:
            raw_sync = a.read_file("replay.sync.events")
        rows = decode_sync(raw_sync)
        need(encode_sync(rows)==raw_sync and rows and all(
            r.event_id==2 and r.gameloop==64*i for i,r in enumerate(rows,1)),"physical sync cadence")
        counts["physical_type2_records"] += len(rows)
        counts["replays"] += 1
    return dict(counts)


def fixed_pair(frames, append_at=()):
    """Count lazy full builds assuming no other history writer and bit 6 clear."""
    previous_processed = False
    latest_shape = None
    samples = Counter()
    for frame in range(frames):
        if frame in append_at:
            previous_processed = False
        if not previous_processed:
            previous_processed = True
            latest_shape = "full_mode0"
        samples[latest_shape] += 1
        latest_shape = "fast_mode4"
    return dict(samples)


if __name__=="__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    for name in ("exe","text","ten","controls"):
        cli.add_argument(name,type=Path)
    args = cli.parse_args()
    controls = json.loads(args.controls.read_bytes())
    import first_sync_game
    ref = Path(first_sync_game.__file__).resolve().parent/"observations"/"first-sync-game.json"
    need(set(controls)=={r["replay_sha256"] for r in json.loads(ref.read_bytes())["references"]} and
         len(controls)==24,"pinned controls")
    result = native(args.exe,args.text)
    result["ten"] = count_replays({SOURCE:args.ten},41810)
    result["controls"] = count_replays(controls,98348)
    result["conditional_65_publications_fixed_pair"] = fixed_pair(65)
    result["conditional_65_publications_new_pair_at_64"] = fixed_pair(65,{64})
    need(result["conditional_65_publications_fixed_pair"]=={"full_mode0":1,"fast_mode4":64}
         and result["conditional_65_publications_new_pair_at_64"]=={"full_mode0":2,"fast_mode4":63},
         "history recurrence")
    result["target_ten_loop64_check_word"] = None
    print(json.dumps(result,indent=2))
