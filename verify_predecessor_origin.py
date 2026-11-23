"""Verify clean-versus-stream history selection and test the fresh-zero mod hypothesis on physical controls."""
import argparse
from collections import Counter
from contextlib import closing
from hashlib import sha256
import json
from pathlib import Path
from struct import unpack_from

from first_sync_game import game
from mpq_reader import MPQArchive
from native_resource_checksums import mod_checksum
from verify_sync_history_cadence import native as history
from verify_sync_vector_source import TEXT_BASE, need


def static(exe, text_path):
    prior = history(exe,text_path)
    t,p = text_path.read_bytes(),exe.read_bytes()
    def code(r,n):
        return t[r-TEXT_BASE:r-TEXT_BASE+n]
    def ref(site,op):
        prefix = bytes.fromhex(op)
        ins = code(site,len(prefix)+4)
        need(ins.startswith(prefix),f"opcode {site:#x}")
        return site+len(ins)+int.from_bytes(ins[len(prefix):],"little",signed=True)
    windows = [(0xe0c2a6,0xe0c2d5,"751dd2175a70e232a2ae314f"),(0xd01d62,0xd01da9,"fb75c004a948166fa16ba0e2"),
               (0xd020ce,0xd020da,"9ca0628dbfd851b63b61bd83"),(0xd0211b,0xd02135,"e979318bbd7cedb0ba9b45be"),
               (0xd02135,0xd021b6,"915aa8e185ad614db78f38d4"),(0x97dd10,0x97dd92,"440ec807a9f01f48aab1e59f"),
               (0x97a410,0x97a44f,"2555c9e74bc96a204a47e4bd"),(0x132b840,0x132b865,"47cdcd4eb8af4918ce1f2ba3"),
               (0x2d0110,0x2d0129,"3958ca5db124f3ba5020ea3d"),(0x2fdd10,0x2fdd1c,"0791942089585c7ba3ea50c3"),
               (0x2ffeba,0x2ffec6,"5c4cc18ab006f512f2b19fe2"),(0x9773c0,0x977590,"9efe30f2ac89c4672d7c9653"),
               (0x977590,0x977765,"c4643d4e0d2da9bf39b6f552"),(0x2d2500,0x2d25e8,"2bc922f98a7379bd4a7811c9"),
               (0x2d3100,0x2d3303,"7d1c465eabb00c2ee6f6c685"),(0x2d2640,0x2d26a1,"8200686b9dc817e193017e1a"),
               (0x988d90,0x988dba,"0ce0ff6c3c5a00eddd7f64cd"),(0x97d9db,0x97da10,"a10c1f3b56f90363a542ff8b")]
    for a,b,digest in windows:
        need(sha256(code(a,b-a)).hexdigest().startswith(digest),f"window {a:#x}")
    nt, = unpack_from("<I",p,60)
    sec = nt+24+unpack_from("<H",p,nt+20)[0]
    sections = [unpack_from("<8sIIII",p,sec+40*i) for i in range(unpack_from("<H",p,nt+6)[0])]
    rva = 0x27bc518+0x270
    pos, = [raw+rva-base for _,_,base,size,raw in sections if base<=rva and rva+8<=base+size]
    need(unpack_from("<Q",p,pos)[0] == 0x14132b840 and ref(0x13237f8,"488d05")==0x27bc518,
         "selected native manager vtable")
    for site,opcode,target in [
        (0xe0c2d0,"e8",0xd01cd0),(0xd02127,"e8",0x97dd10),(0xd0215e,"e8",0x97dd10),
        (0xd021aa,"e8",0x9796b0),(0x97dd8d,"e9",0x9773c0),(0x9774da,"e8",0x2717e0),
        (0x97751a,"e8",0x2717e0),(0x977546,"e8",0x2d2500),(0x2d2596,"e8",0x2d3100),
        (0x9776ab,"e8",0x271d60),(0x9776eb,"e8",0x271d60),(0x977713,"e8",0x2d2640),
        (0x988da4,"e8",0x989cc0),(0x132b860,"e9",0x2d0110),(0x2d011e,"0f84",0x3042f0),
        (0x3042f6,"e9",0x2fdd10),(0x2fdd16,"0f84",0x2ffeba),(0x2ffebe,"0f8c",0x2fde13)]:
        need(ref(site,opcode)==target,f"native edge {site:#x}")
    need(code(0x3042f0,6)==bytes.fromhex("41b81a000000") and code(0x2fde13,3)==bytes.fromhex("32c0c3"),
         "empty span produces false")
    return dict(build=98348,exe=prior["pe"],static_text=prior["static_text"],windows=len(windows),
                fresh_count=72,fresh_words_zero=72,fresh_processed=False,
                clean_tail_if_loader_index_minus_one_and_owner_mode_four_or_manager_predicate_false=True,
                initial_manager_vtable_predicate_false_on_empty_span=True,
                stream_has_independent_processed_field=False,
                preserved_case_requires_same_surviving_record=True)


def check_controls(manifest):
    refs = json.loads(manifest.read_bytes())
    import first_sync_game
    known = Path(first_sync_game.__file__).resolve().parent/"observations"/"first-sync-game.json"
    need(set(refs)=={r["replay_sha256"] for r in json.loads(known.read_bytes())["references"]} and len(refs)==24,
         "pinned controls")
    zero_by_length = {mod_checksum([0]*n):n for n in range(256)}
    need(len(zero_by_length)==256,"distinct all-zero hypotheses")
    counts,dragon = Counter(),Counter()
    for digest,name in refs.items():
        path = Path(name)
        proto,_ = game(path,digest,98348)
        with closing(MPQArchive(path)) as m:
            desc = proto.decode_replay_initdata(m.read_file("replay.initData"))["m_syncLobbyState"]["m_gameDescription"]
            title = proto.decode_replay_details(m.read_file("replay.details"))["m_title"]
        word = desc["m_modFileSyncChecksum"]
        counts[word]+=1
        if title == b"Dragon Shire":
            dragon[word]+=1
    matches = sum(n for word,n in counts.items() if word in zero_by_length)
    need(matches==0,"all-zero selected mod-vector hypothesis unexpectedly survives")
    return dict(replays=len(refs),distinct_recorded_mod_words=len(counts),all_zero_lengths_checked=256,
                empty_vec_mod_checksum=hex(mod_checksum([])),zero_72_mod_checksum=hex(mod_checksum([0]*72)),
                physical_all_zero_mod_matches=matches,dragon_mod_checksums={hex(k):n for k,n in dragon.items()})


if __name__=="__main__":
    cli=argparse.ArgumentParser(description=__doc__)
    for name in ("exe","text","controls"):
        cli.add_argument(name,type=Path)
    args=cli.parse_args()
    result=static(args.exe,args.text)
    result["physical_negative_controls"]=check_controls(args.controls)
    result["actual_ten_loop64_predecessor_flag"]=None
    print(json.dumps(result,indent=2))
