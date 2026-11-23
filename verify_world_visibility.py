"""Tie the fast CRC's second operand to native visibility, Dragon scripts and physical lobby options."""

import argparse
from collections import Counter
from contextlib import closing
from hashlib import sha256
import json
from pathlib import Path
import re
from struct import unpack_from

from first_sync_game import SOURCE, game
from mpq_reader import MPQArchive
from verify_script_sync_words import MAPS, read_scripts, script_closure
from verify_sync_vector_source import TEXT_BASE, need, verify


SCAN = "b28406f12ea05e5a617e87521a88d16de5f2b6a9c6f7fac2fcbb13cd00c459fd"
CALL = re.compile(rb"\b(?:VisEnable|(?:lib\w+_gf_)?GlobalCinematicSetting(?:Tutorial)?)\s*\(")


def native(exe, text_path):
    pinned = verify(exe,text_path)
    text,pe = text_path.read_bytes(),exe.read_bytes()
    def code(rva, length):
        return text[rva-TEXT_BASE:rva-TEXT_BASE+length]
    def ref(rva, prefix):
        ins = bytes.fromhex(prefix)
        need(code(rva,len(ins))==ins,f"opcode {rva:#x}")
        return rva+len(ins)+4+int.from_bytes(code(rva+len(ins),4),"little",signed=True)
    nt, = unpack_from("<I",pe,60)
    sec = nt+24+unpack_from("<H",pe,nt+20)[0]
    sections = [unpack_from("<8sIIII",pe,sec+i*40) for i in range(unpack_from("<H",pe,nt+6)[0])]
    def data(rva,length):
        pos, = [raw+rva-base for _,_,base,size,raw in sections if base<=rva and rva+length<=base+size]
        return pe[pos:pos+length]
    windows = [(0x20e1d30,0x20e1d85,"ed687720cd067b3dc4354efe"), # type 1 switches 0 / ~0
               (0x20e2540,0x20e2571,"c7cafd8fb4e16d7ff7aad124"), # type 1 getter == 0
               (0x977910,0x977971,"b654763bbde50b66eca07dd3"), # constructor submits zero
               (0x977ac0,0x977ad0,"a8f3a711573ef4bfd898296e"), # encoded default -> +14
               (0x986510,0x98656c,"1ce91bb6f7421f04f185960d"), # setter jump dispatch
               (0x985f60,0x985f90,"c70d179c643aab6ff40be15d"), # type 0 sibling -> +10
               (0x986970,0x9869c7,"eecf838f89e0cd161352fdb8"), # getter decodes +14
               (0x985bf2,0x985c51,"bb339d914f8460ae30ad8469")] # checksum decodes +14
    for a,b,h in windows:
        need(sha256(code(a,b-a)).hexdigest().startswith(h),f"code {a:#x}")
    for idx,name,lea,case,site,handler in [
        (1999,b"VisEnable",0x23b9a9,0x2009748,0x200974f,0x20e1d30),
        (2000,b"VisIsEnabled",0x23b9c7,0x200975e,0x2009761,0x20e2540)]:
        need(ref(lea,"488d0d")==0x4120b50+24*idx,"Galaxy name registration")
        need(data(ref(lea-7,"488d15"),len(name)+1)==name+b"\0","Galaxy name")
        need(int.from_bytes(code(0x200accc+4*idx,4),"little")==case and ref(site,"e8")==handler,
             "Galaxy native case")
    for site,target in [(0x20e1d56,0x986510),(0x20e1d76,0x985f60),(0x20e2554,0x986970)]:
        need(ref(site,"e8")==target,"visibility handler edge")
    def targets(table):
        functions = []
        for i in range(16):
            arm = int.from_bytes(code(table+4*i,4),"little")
            pos = code(arm,20).index(b"\xe8")
            functions.append(ref(arm+pos,"e8"))
        need(len(set(functions))==16,"independent representation variants")
        return functions
    need(targets(0x977b9c)==targets(0x986900),"constructor and setter use same 16 encoders")
    need(targets(0x985e54)==targets(0x986af8),"fast checksum and getter use same 16 decoders")
    return dict(build=98348, exe_sha256=pinned["pe_sha256"], static_text_sha256=pinned["static_text_sha256"],
                native_set=1999,native_get=2000,visibility_type=1,
                logical_operand_when_enabled=0,logical_operand_when_disabled=0xffffffff,
                constructor_matches_enabled=True,codec_cases_checked=16)


def map_calls(archives, files):
    cases = {}
    for key,path in archives.items():
        need(sha256(path.read_bytes()).hexdigest()==MAPS[key][0],"map archive")
        with closing(MPQArchive(path)) as m:
            root = m.read_file("MapScript.galaxy")
        need(sha256(root).hexdigest()==MAPS[key][1] and not CALL.search(root),"map script")
        closure = script_closure(root,files)
        hits = {n:[line.strip().decode() for line in body.splitlines() if CALL.search(line)]
                for n,body in closure.items() if CALL.search(body)}
        need(set(hits)=={"nativelib.galaxy","nativelib_h.galaxy","startingexperiencelib.galaxy",
                        "startingexperiencelib_h.galaxy"},"Dragon visibility references")
        need(len(hits["nativelib.galaxy"])==5 and len(hits["startingexperiencelib.galaxy"])==2
             and len(hits["nativelib_h.galaxy"])==len(hits["startingexperiencelib_h.galaxy"])==1,
             "unexpected cinematic caller")
        cases[str(key)] = dict(archive_sha256=MAPS[key][0], closure_files=len(closure), root_calls=0,
                              included_non_declaration_callers=["NativeLib global cinematic switch",
                                                                 "StartingExperience tutorial wrapper"])
    return cases


def run(args):
    result = native(args.exe,args.text)
    raw = args.scan.read_bytes()
    full_scan = sha256(raw).hexdigest() == SCAN
    summary_hash = sha256(raw.replace(b"\r\n", b"\n")).hexdigest()
    need(full_scan or summary_hash == "4eb9d356446f9bddc6a06a796b07ac18a4d2198643d32fa98e3969df31f0e3a0",
         "CASC visibility caller scan or published digest-and-count summary")
    scan = json.loads(raw)
    if not full_scan:
        need(scan["source_sha256"] == SCAN, "summary source")
    need(scan["scripts_scanned"]==215 and not scan["errors"] and not scan["blocked_http_attempts_during_casc"],
         "CASC scan")
    external = [m["name"] for m in scan["members"] if "/triggerlibs/" not in m["name"].lower()]
    need(len(external)==3 and all("/singleplayermaps/startingexperience/" in f.lower() for f in external),
         "unexpected additional script use")
    result["maps"] = map_calls({41810:args.source_map,98348:args.control_map,"GateOrder":args.overlay},
                               read_scripts(args.scripts))
    controls = json.loads(args.controls.read_bytes())
    import first_sync_game
    pins = Path(first_sync_game.__file__).resolve().parent/"observations"/"first-sync-game.json"
    need(len(controls)==24 and set(controls)=={r["replay_sha256"] for r in json.loads(pins.read_bytes())["references"]},
         "control set")
    for key,build,paths in [("ten",41810,{SOURCE:args.ten}),("controls",98348,controls)]:
        fog = Counter()
        for digest,file in paths.items():
            path = Path(file)
            proto,_ = game(path,digest,build)
            with closing(MPQArchive(path)) as m:
                desc = proto.decode_replay_initdata(m.read_file("replay.initData"))["m_syncLobbyState"]["m_gameDescription"]
            fog[desc["m_gameOptions"]["m_fog"]]+=1
        result[key+"_lobby_fog_histogram"] = dict(fog)
    result["named_installed_scripts_checked"] = 215
    result["ordinary_dragon_without_external_writer_candidate"] = 0
    result["actual_ten_sampled_value"] = None
    return result


if __name__=="__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    for name in ("exe","text","ten","controls","source_map","control_map","overlay","scripts","scan"):
        cli.add_argument(name,type=Path)
    print(json.dumps(run(cli.parse_args()),indent=2))
