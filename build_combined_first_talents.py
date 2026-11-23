"""Compose verified Nova and Brightwing catalog contributions on their common PerfectAim parent."""

import argparse
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from xml.etree import ElementTree as ET

from build_dragonshire_talent_map import EMPTY_CATALOG, digest, inventory
from build_extended_spikes_map import pinned, require
from runtime_catalog_probe import Storm

BASE="9c223f3e4d9fb31324126b91f7e51048dd6c011ac0d4dcdf6f582e2978f92870"
NOVA="8b0cdec389be8a7cc52b438e9798af5903158a59a426d9ab3e08f166e791fd8f"
BRIGHT="bdf99d5bd9610774fe1758855f5c1f7981d9ef126e906cf06fd94177e1d3e72e"


def entries(raw):
    doc=ET.fromstring(raw)
    require(doc.tag=="Catalog","Unexpected catalog root")
    keyed={}
    for item in doc:
        key=item.attrib["id"].casefold()
        require(key not in keyed,"Duplicate catalog key")
        item.tail=None
        keyed[key]=ET.tostring(item,encoding="utf-8")
    return keyed


def appended(base,side):
    prefix,end=base.split(b"</Catalog>")
    tail=b"</Catalog>"+end
    require(side.startswith(prefix) and side.endswith(tail),"Catalog contribution exceeds append scope")
    return side[len(prefix):-len(tail)]


def combine(parent,nova,bright):
    require(parent.keys()<=nova.keys() and parent.keys()<=bright.keys(),"Variant removed a member")
    merged={}
    counts={}
    for name in sorted(nova.keys()|bright.keys()):
        base=parent.get(name)
        n=nova.get(name,base)
        b=bright.get(name,base)
        if n==b==base:
            continue
        if name.endswith(".xml"):
            if base is None: base=EMPTY_CATALOG
            n=n if n is not None else base
            b=b if b is not None else base
            common,left,right=entries(base),entries(n),entries(b)
            require(all(left.get(k)==raw==right.get(k) for k,raw in common.items()),"Base record changed")
            newn,newb=left.keys()-common.keys(),right.keys()-common.keys()
            require(not newn & newb,"Nova and Brightwing edit the same catalog record")
            appended(base,n)
            extra=appended(base,b)
            result=n.replace(b"</Catalog>",extra+b"</Catalog>")
            require(entries(result)=={**left,**right},"Incorrect combined catalog")
            counts[name]=dict(nova=len(newn),brightwing=len(newb))
        else:
            require(name.endswith("LocalizedData\\GameStrings.txt") and n.startswith(base) and b.startswith(base),
                    "Unexpected non-catalog member change")
            addn,addb=n[len(base):],b[len(base):]
            def keys(raw):
                rows=[line.split(b"=",1)[0].lower() for line in raw.splitlines() if line.strip()]
                require(len(rows)==len(set(rows)),"Duplicate localization key")
                return set(rows)
            require(not keys(addn)&keys(addb),"Localization collision")
            result=n+addb
            counts[name]=dict(nova=len(keys(addn)),brightwing=len(keys(addb)))
        merged[name]=result
    return merged,counts


def build(parent,nova,brightwing,output,stormlib=None):
    original=pinned(parent,BASE)
    pinned(nova,NOVA)
    pinned(brightwing,BRIGHT)
    require(not output.exists() and not output.is_symlink(),"Fresh output path required")
    storm=Storm(stormlib)
    before,pc=inventory(parent,storm)
    n,_=inventory(nova,storm)
    b,_=inventory(brightwing,storm)
    changes,counts=combine(before,n,b)
    with TemporaryDirectory(dir=output.parent) as temp:
        staged=Path(temp)/"map.s2ma"
        staged.write_bytes(original)
        storm.replace(staged,changes)
        result,after=inventory(staged,storm)
        require(result=={**before,**changes} and original==parent.read_bytes(),"Unexpected final package")
        raw=staged.read_bytes()
        os.link(staged,output)
    return dict(parent_sha256=BASE,nova_component_sha256=NOVA,brightwing_component_sha256=BRIGHT,
                candidate_sha256=digest(raw),candidate_bytes=len(raw),changed_or_added_members={k:digest(v) for k,v in changes.items()},
                contributions=counts,unchanged_parent_members=len(before.keys()-changes.keys()),parent_checks=pc,
                final_checks=after,historical_brightwing_base_radius_independently_proven=False,
                nova_uses_intended_historical_ramp=True,effective_runtime=False,verified_syncs=0)


if __name__=="__main__":
    cli=argparse.ArgumentParser(description=__doc__)
    for name in ("parent","nova","brightwing","output"):
        cli.add_argument(name,type=Path)
    cli.add_argument("--stormlib")
    print(json.dumps(build(**vars(cli.parse_args())),indent=2))
