"""Bind primary slots 46 and 68 to script data in HotS 98348."""

import argparse
from contextlib import closing
from hashlib import sha256
import json
from pathlib import Path
import re
import struct
from xml.etree import ElementTree
from zlib import crc32

from mpq_reader import MPQArchive
from protocol_loader import load_protocol
from verify_sync_vector_source import verify as verify_vector


SOURCE = "e8f167cbb163f178c3f01c0eaf6eba393d9f010c2eec533e3ca82c35e7f4c824"
SCRIPT_MANIFEST_SHA = "87b44ff3f91d9058f5001f926129a04d225f8a11fa05b99e1571362539ec3b7b"
PACKAGE_SCAN_SHA = "563059862406f74ce8ff04d340232d694e710f0258beb4e70abd2ed5f1ced6d6"
MAPS = {
    41810: ("e0a58745837b3b5351015c933560dbffb178d747009d2d57b4153ef425cf7250",
            "3cbca9c5b3c95bd0b5f8eb8d2218d129d89e21c3466cb242e7c54b22e67c7e18"),
    98348: ("f557190f8aaab160789272ce086b8b69d6a8037b152de150332603dae3dc098f",
            "3577dc0e4c0c02524e83ab6d025aa5955fe4aa414c421d37a2254ed3260b1556"),
    "GateOrder": ("bda7aafd1d63c77b3b4d29ff2afee96da09a3104b54b4a1d625bb299607d9008",
                  "6b6f8f51778ed77cc6bd183827a349d9f8b817ca51b1fa9b816926df9d603d6e"),
}
WINDOWS = (
    (0x1ff2f03,0x1ff2fc7,"59b6cdba25aff83bc5f7f47b"), # accepted file and cumulative CRC
    (0x1ff1e40,0x1ff1e96,"496b371840905912845f76e2"), # checksum word
    (0x2d6ff0,0x2d70cd,"8d97133b21647ff42fcc56d2"), # aligned and unaligned input bytes
    (0x970b80,0x970b98,"f9917b6808f1f11a1f3beac2"), # slot 46
    (0xb17060,0xb170b6,"41f7d45e87da73c91d1d03f0"), # panel state
    (0x970ebe,0x970ed3,"2aed2754091e3a675b6e1dc0"), # slot 68
    (0xb17160,0xb171ae,"d883b91eb7c7cad4f9795da0"), # conditional bool setter
)
PANEL = "SetHeroLeaderPanelEnabled"
HELPER = "libStEx_gf_CinematicModeTutorial"


def need(value, message):
    if not value:
        raise ValueError(message)


def native(executable, text):
    verify_vector(executable,text)
    pe, code = executable.read_bytes(), text.read_bytes()
    nt, = struct.unpack_from("<I", pe, 60)
    sec = nt + 24 + struct.unpack_from("<H", pe, nt + 20)[0]
    ranges = [struct.unpack_from("<III",pe,sec+i*40+12)
              for i in range(struct.unpack_from("<H",pe,nt+6)[0])]

    def original(rva, length):
        for base, size, off in ranges:
            if base <= rva and rva + length <= base + size:
                start = off + rva - base
                return pe[start:start+length]
        raise ValueError("Missing file-backed PE bytes")

    def at(rva, length):
        return code[rva-0xba000:rva-0xba000+length]

    def ref(rva, prefix, target):
        opcode = bytes.fromhex(prefix)
        need(at(rva,len(opcode)) == opcode and
             rva + len(opcode) + 4 + struct.unpack("<i",at(rva+len(opcode),4))[0] == target,
             f"Native reference {rva:x}")

    for a,b,digest in WINDOWS:
        need(sha256(at(a,b-a)).hexdigest().startswith(digest),f"Native window {a:x}")
    for rva, prefix, target in [
        (0x230d6f,"488d15",0x29a82c8),(0x230d76,"488d0d",0x4120b50+24*776),
        (0x20003a9,"e8",0x20a27b0),(0x20a27b0,"e9",0xb17160),(0xb1717a,"8905",0x2f7292c),
        (0xb1706a,"8b05",0x2f7292c),(0x970ec4,"e8",0xb17060),(0xb170d8,"8905",0x2f7292c),
        (0x1ff5565,"8b1d",0x3b8c900),(0x1ff556b,"488d05",0x29a5a50),
        (0x1ff2dde,"488d05",0x26a5f28),(0x1ff2f44,"e8",0x2d6ff0),
        (0x1ff2f66,"448b0d",0x3b8c900),(0x1ff2fc0,"448905",0x3b8c900),
        (0x1ff1e4a,"8b05",0x3b8c900),(0x970b86,"e8",0x1ff1e40),
    ]:
        ref(rva,prefix,target)
    need(struct.unpack("<I",at(0x200accc+4*776,4))[0] == 0x20003a5, "Galaxy jump case")
    for rva, value in [(0x2f7292c,b"\x01\0\0\0"),(0x29a82c8,PANEL.encode()+b"\0"),
                       (0x26a5f28,b".galaxy\0"),(0x29a5a50,b"ScriptChecksum: \0")]:
        need(original(rva,len(value)) == value,"Native initial value or name")
    for reset in (0xb17140,0xb171b0):
        need(at(reset,2)==b"\xc7\x05" and reset+10+struct.unpack("<i",at(reset+2,4))[0]==0x2f7292c
             and at(reset+6,5)==bytes.fromhex("01000000c3"),"Native reset to enabled")
    ref(0xb170f0,"488d15",0x2f7292c)
    ref(0xb170f7,"e9",0x2d6ea0)
    ref(0x2d6ea0,"e9",0x2d62e0)
    need(at(0x2d62fe,2)==bytes.fromhex("8b17"),"Diagnostic scalar read")
    return struct.unpack("<1024I",original(0x2648210,4096))


def raw_word(table, raw, value):
    x = raw ^ value
    return table[768+(x&255)] ^ table[512+((x>>8)&255)] ^ table[256+((x>>16)&255)] ^ table[x>>24]


def script_step(table, previous, body):
    """One accepted script-buffer update, including the native empty-buffer branch."""
    if not body:
        return previous
    raw = 0xffffffff
    for item in body:
        raw = table[(raw ^ item) & 255] ^ (raw >> 8)
    result = raw_word(table, raw, previous) ^ 0xffffffff
    need(result == crc32(struct.pack("<I",crc32(body)),previous), "Script CRC recurrence")
    return result


def read_scripts(installed):
    raw = (installed/"member.json").read_bytes()
    need(sha256(raw).hexdigest() == SCRIPT_MANIFEST_SHA,"Installed Galaxy extraction manifest")
    manifest = json.loads(raw)
    need(manifest["root"] == "c3b3c8bc82e3a5a62e550fdde9a40c28", "Unexpected CASC root")
    files = {}
    for member in manifest["members"]:
        name = member["saved_name"]
        body = (installed/name).read_bytes()
        need(sha256(body).hexdigest() == member["sha256"], name)
        files[name.lower()] = body
    return files


def script_closure(root, files):
    included = {}

    def visit(body):
        for path in re.findall(rb'(?im)^\s*include\s+"([^"]+)"',body):
            key = path.decode().lower()
            need(key.startswith("triggerlibs/") and key.count("/") == 1,key)
            name = key.partition("/")[2] + ".galaxy"
            if name not in included:
                included[name] = files[name]
                visit(files[name])

    visit(root)
    need(len(included) == 22,"Unexpected Dragon include closure")
    return included


def map_evidence(path, build, files, table):
    map_sha, script_sha = MAPS[build]
    need(sha256(path.read_bytes()).hexdigest() == map_sha,"Map archive identity")
    with closing(MPQArchive(path)) as archive:
        root = archive.read_file("MapScript.galaxy")
        metadata = archive.read_file("DocumentInfo")
        document = ElementTree.fromstring(metadata)
        members = archive.read_file("(listfile)").decode().lower().splitlines()
    need(sha256(root).hexdigest() == script_sha and
         [m for m in members if m.endswith(".galaxy")] == ["mapscript.galaxy"],"Map script membership")
    packages = [e.text for e in document.findall(".//Dependencies/Value")]
    need(len(packages) == 1 and not any("brawl" in p.lower() or "tutorial" in p.lower()
                                       for p in packages),"Special mode dependency")
    included = script_closure(root,files)
    hits = {}
    for name,body in {**included,"mapscript.galaxy":root}.items():
        lines = [ln.strip() for ln in body.decode("utf-8-sig").splitlines()
                 if PANEL in ln or re.search(HELPER+r"2?\b",ln)]
        if lines:
            hits[name] = lines
    need(set(hits)=={"startingexperiencelib.galaxy","startingexperiencelib_h.galaxy","mapmechanicslib.galaxy"},
         "Unexpected setter or wrapper use in map/script package")
    mechanics, = hits["mapmechanicslib.galaxy"]
    need(mechanics.startswith(HELPER+"(false,") and len(hits["startingexperiencelib_h.galaxy"])==2
         and len(hits["startingexperiencelib.galaxy"])==5,"Panel call sites")
    st = included["startingexperiencelib.galaxy"].decode("utf-8-sig")
    branch = st.index("if ((lp_onOff == true)) {",st.index("libNtve_gf_CinematicMode(lp_onOff,"))
    setter = st.index(PANEL+"(false);",branch)
    other = st.index("    else {",setter)
    need(branch < setter < other < st.index(PANEL+"(true);",other),"Tutorial setter branch")
    closure = {name:sha256(body).hexdigest() for name,body in sorted(included.items())}
    closure_hash = sha256(json.dumps(closure,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    return dict(map_sha256=map_sha, root_script_sha256=script_sha, root_script_bytes=len(root),
                root_script_crc32=hex(crc32(root)), root_update_from_zero_if_first_verbatim=hex(script_step(table,0,root)),
                included_files=len(included), include_name_and_content_sha256=closure_hash,
                document_info_sha256=sha256(metadata).hexdigest(), declared_dependencies=packages,
                root_panel_calls=0)


def verify(args):
    table = native(args.exe,args.text)
    files = read_scripts(args.scripts)
    scan_raw = args.scan.read_bytes()
    need(sha256(scan_raw).hexdigest()==PACKAGE_SCAN_SHA,"Installed native caller scan manifest")
    sweep = json.loads(scan_raw)
    need(sweep["root"]=="c3b3c8bc82e3a5a62e550fdde9a40c28" and sweep["scripts_scanned"]==215
         and not sweep["errors"] and sweep["blocked_http_attempts_during_casc"] == 0,"Installed scan")
    extras = []
    for item in sweep["members"]:
        path = item["name"].lower()
        if "/triggerlibs/" in path:
            need(path.rsplit("/",1)[1] in ("startingexperiencelib.galaxy","startingexperiencelib_h.galaxy",
                                           "mapmechanicslib.galaxy"),"Unknown package call")
        else:
            need("/singleplayermaps/startingexperience/" in path or path.startswith("mods/heroesbrawlmods/"),
                 "Extra standard mod call")
            extras.append(path)
    need(len(extras)==8,"Extra setter or helper references")
    cases = {n:map_evidence(path,n,files,table) for n,path in
             [(41810,args.original_map),(98348,args.control_map),("GateOrder",args.gate_order_map)]}
    for field in ("include_name_and_content_sha256","document_info_sha256","declared_dependencies"):
        need(cases["GateOrder"][field]==cases[41810][field], "GateOrder script scope differs")
    controls = 0
    for build,path in [(41810,args.original)]+[(98348,p) for p in args.control]:
        if build == 41810:
            need(sha256(path.read_bytes()).hexdigest() == SOURCE,"Original replay")
        protocol = load_protocol(41810 if build==41810 else 96477)
        with closing(MPQArchive(path)) as archive:
            header = protocol.decode_replay_header(archive.header["user_data_header"]["content"])
            detail = protocol.decode_replay_details(archive.read_file("replay.details"))
        need(header["m_version"]["m_build"] == build and detail["m_title"]==b"Dragon Shire"
             and detail["m_cacheHandles"][-1][8:].hex()==MAPS[build][0],"Replay's map or build")
        controls += build == 98348
    need(controls>=2 and len({sha256(p.read_bytes()).digest() for p in args.control})==controls,
         "Independent target controls")
    for seed in (0,1,0xffffffff,0x12345678):
        for chunk in (b"",b"a",b"word",b"five!",files["startingexperiencelib.galaxy"]):
            script_step(table,seed,chunk)
    panel_word = raw_word(table,0xffffffff,1) ^ 0xffffffff
    need(panel_word==crc32(struct.pack("<I",1))==0x99f8b879,"Clean panel word")
    return dict(build=98348, maps=cases, script_manifest_sha256=SCRIPT_MANIFEST_SHA,
                package_scan_sha256=PACKAGE_SCAN_SHA, independent_target_replays=controls,
                control_replay_sha256=sorted(sha256(p.read_bytes()).hexdigest() for p in args.control),
                installed_scripts_scanned=215, other_mode_files=len(extras),
                slot68=dict(semantic="SetHeroLeaderPanelEnabled",native_index=776,
                            clean_dragon_value=1,word_when_primary_producer_runs=hex(panel_word),
                            gate_order_word_when_primary_producer_runs=hex(panel_word),
                            mode4_fast_word=0, published_first_word=None,
                            conditions="Clean process, named Dragon packages, no additional injected/dynamic script or restore. The sampled history entry determines the published word."),
                slot46=dict(semantic="ScriptChecksum", source_rva="0x3b8c900",
                            per_buffer="crc32(le32(crc32(buffer)), previous); empty buffers leave previous unchanged",
                            word_when_primary_producer_runs="crc32(le32(ScriptChecksum))",
                            mode4_fast_word=0, ten_value=None,
                            missing="Exact ordered list of all nonempty buffers accepted by the loader by sample time, including added mod libraries."))


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    for field in ("exe","text","scripts","scan","original","original_map","control_map"):
        parser.add_argument(field,type=Path)
    parser.add_argument("--gate-order-map",required=True,type=Path)
    parser.add_argument("--control",required=True,action="append",type=Path)
    print(json.dumps(verify(parser.parse_args()),indent=2))
