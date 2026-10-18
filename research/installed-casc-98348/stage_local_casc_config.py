"""Copy three bounded config inputs so third-party ReadWrite opens stay in work."""
from pathlib import Path
import hashlib,json,sys
sys.path.insert(0,r'C:\Users\andrz\git\hots-replay-recovery')
from collection_license_audit import _read
root=Path(__file__).resolve().parent
installed=Path(r'C:\Program Files (x86)\Heroes of the Storm')
info=_read(installed/'.build.info',65536)
lines=info.decode('utf-8-sig').splitlines()
keys=[x.split('!')[0].replace(' ','') for x in lines[0].split('|')]
rows=[dict(zip(keys,line.split('|'))) for line in lines[1:] if line]
assert len(rows)==1 and rows[0]['Active']=='1' and rows[0]['Version']=='2.57.0.98348'
row=rows[0];assert row['BuildKey']=='a64c9b7ebf1c6a811ffefad97865ed80'
stage=root/'config-copy';stage.mkdir(exist_ok=False)
inputs=[('.build.info',info)]
for key in (row['BuildKey'],row['CDNKey']):
    relative=f'HeroesData/config/{key[:2]}/{key[2:4]}/{key}'
    raw=_read(installed/relative,256*1024)
    assert hashlib.md5(raw).hexdigest()==key
    inputs.append((relative,raw))
build=dict((line.split('=',1)[0].strip(),line.split('=',1)[1].strip())
    for line in inputs[1][1].decode().splitlines() if '=' in line and not line.startswith('#'))
assert build['root']=='c3b3c8bc82e3a5a62e550fdde9a40c28'
assert '98348' in build['build-name'] and build['build-uid']=='hero'
assert int(build['encoding-size'].split()[0])<128*1024*1024
saved=[]
for relative,raw in inputs:
    path=stage/relative;path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('xb') as stream:stream.write(raw)
    saved.append(dict(path=relative,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),installed_source_unchanged=True))
for relative,raw in inputs:assert _read(installed/relative,256*1024)==raw
report=dict(format='hots-local-casc-config-stage-v1',version=row['Version'],build_key=row['BuildKey'],cdn_key=row['CDNKey'],
    declared_root=build['root'],declared_encoding=build['encoding'],encoding_size=build['encoding-size'],
    build_name=build['build-name'],build_uid=build['build-uid'],game_storage_modified=False,files=saved)
with (root/'staged-config-provenance.json').open('x',encoding='utf-8',newline='\n') as stream:json.dump(report,stream,indent=2);stream.write('\n')
print(json.dumps(report,indent=2))
