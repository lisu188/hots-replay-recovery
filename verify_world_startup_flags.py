"""Verify the six world flag bits set from recorded per-user options on normal setup."""
import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
from struct import unpack_from

from first_sync_game import SOURCE, game, opening
from protocol_loader import load_protocol
from verify_sync_vector_source import TEXT_BASE, need, verify


FIELDS = ("m_developmentCheatsEnabled","m_testCheatsEnabled","m_multiplayerCheatsEnabled",
          "m_syncChecksummingEnabled","m_isMapToMapTransition","m_debugPauseEnabled")
MASK = sum(1<<(i+3) for i in range(len(FIELDS)))
SETTERS = [(0xe0dd78,0x97a970),(0xe0dddc,0x97aa60),(0xe0de4e,0x97a9c0),
           (0xe0de82,0x97aa10),(0xe0deb9,0x986070),(0xe0dee9,0x97a920)]


def native(exe, static):
    pins = verify(exe,static)
    t = static.read_bytes()
    def code(r,n):
        return t[r-TEXT_BASE:r-TEXT_BASE+n]
    for a,b,h in [(0xe0e955,0xe0ea3c,"f6a449cbe6528ad02bf9585f"),
                  (0xe0dd2b,0xe0def0,"bef6d9e68c9779e455fd68d4"),(0xe0df12,0xe0df21,"bb5acdbbd92273365bd4b4a8"),
                  (0x97a970,0x97a9b2,"aa254306627182bcc5fb1bc8"),(0x97aa8c,0x97aaa2,"7875450ab403db044047a354"),
                  (0x97a9c0,0x97aa02,"6b1375ddc15e32ef9f1a7590"),(0x97aa3c,0x97aa52,"991bdd08814634cd2cd866e1"),
                  (0x986070,0x9860c1,"8a30d9749971bf0cfff9470b"),(0x97a920,0x97a964,"7fac83ca955dc9dd1d8af3f4")]:
        need(sha256(code(a,b-a)).hexdigest().startswith(h),f"native option block {a:#x}")
    for site,target in SETTERS:
        ins = code(site,5)
        need(ins[0]==0xe8 and site+5+int.from_bytes(ins[1:],"little",signed=True)==target,f"setter {site:#x}")
    pe = exe.read_bytes()
    nt, = unpack_from("<I",pe,60)
    sec = nt+24+unpack_from("<H",pe,nt+20)[0]
    sections = [unpack_from("<8sIIII",pe,sec+i*40) for i in range(unpack_from("<H",pe,nt+6)[0])]
    def value(r,size):
        o, = [raw+r-base for _,_,base,length,raw in sections if base<=r<=base+length-size]
        return int.from_bytes(pe[o:o+size],"little")
    need(value(0x27c9fd4,4)==225,"physical type-7 payload")
    table = 0x27becb0+8*value(0x27becb0+8*226,8)
    need(table==0x27c2098 and [value(table+8*i,8) for i in range(2,8)]==list(range(1,7)),
         "native structure byte offsets")
    def ref(r, prefix):
        pre = bytes.fromhex(prefix)
        data = code(r,len(pre)+4)
        need(data.startswith(pre),"native reference")
        return r+len(data)+int.from_bytes(data[len(pre):],"little",signed=True)
    need(ref(0x2308a8,"488d0d")==0x4120b50+24*740 and ref(0x2308a1,"488d15")==0x29a80c8
         and bytes(value(0x29a80c8+i,1) for i in range(21))==b"GameSetTransitionMap\0"
         and int.from_bytes(code(0x200accc+4*740,4),"little")==0x2000003
         and ref(0x2000006,"e8")==0xacd630 and ref(0xacd694,"e8")==0x986070,
         "separate Galaxy bit-7 setter")
    fields = load_protocol(96477).typeinfos[79][1][0]
    need(tuple(f[0] for f in fields[1:7])==FIELDS,"target field order")
    return dict(pe=pins["pe_sha256"],static_text=pins["static_text_sha256"],
                option_world_bits={f:i+3 for i,f in enumerate(FIELDS)},
                alternate_bit7_setter="Galaxy native 740 GameSetTransitionMap")


def witnesses(build, paths):
    hist = Counter()
    for digest,path in paths.items():
        proto,raw = game(Path(path),digest,build)
        opts = [e for e,_,_ in opening(raw,proto) if e["_eventid"]==7]
        users = [e["_userid"]["m_userId"] for e in opts]
        need(opts and all(e["_gameloop"]==0 for e in opts) and len(set(users))==len(users),"opening options")
        if build==41810:
            need(users==list(range(10)),"TEN expected users")
        hist.update(sum(int(e[f])<<(i+3) for i,f in enumerate(FIELDS)) for e in opts)
    need(set(hist)=={0},"all-absent consensus premise")
    return dict(replays=len(paths),option_rows=sum(hist.values()),requested_mask_histogram=dict(hist))


if __name__=="__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    for name in ("exe","static","ten","controls"):
        cli.add_argument(name,type=Path)
    args = cli.parse_args()
    out = native(args.exe,args.static)
    controls = json.loads(args.controls.read_bytes())
    import first_sync_game
    refs = Path(first_sync_game.__file__).resolve().parent/"observations"/"first-sync-game.json"
    need(len(controls)==24 and set(controls)=={r["replay_sha256"] for r in json.loads(refs.read_bytes())["references"]},
         "pinned controls")
    out.update(ten=witnesses(41810,{SOURCE:args.ten}),controls=witnesses(98348,controls),
               after_applying_recorded_options_mask=hex(MASK),masked_value=0,
               published_world_flags=None)
    print(json.dumps(out,indent=2))
