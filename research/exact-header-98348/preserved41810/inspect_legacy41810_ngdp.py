"""Read only build/NGDP identities from five preserved crash folders."""
from pathlib import Path
import hashlib
import json
import re

BASE=Path(r'C:\Users\andrz\OneDrive\Dokumenty\Heroes of the Storm\GameLogs')
OUT=Path(__file__).resolve().parent/'legacy41810-ngdp-metadata'
ORIGINAL_ROOT='83d43a8647bb5ca5caa6f2f09064da55'
MAX_FILES=15
MAX_BYTES=128*1024
sha=lambda raw:hashlib.sha256(raw).hexdigest()

def analyze():
    folders=sorted(path for path in BASE.iterdir() if path.is_dir() and 'B41810 Error' in path.name)
    if len(folders)!=5:raise ValueError('Expected exactly five observed crash folders')
    reports=[];count=total=0
    public_keys={'Build Key','CDN Key','Build Id','Version','Product','Active','Branch'}
    for index,folder in enumerate(folders,1):
        files=[folder/'.build.info',*sorted(folder.glob('* NGDP.txt')),*sorted(folder.glob('*NGDPTrace.txt'))]
        if len(files)!=3:raise ValueError('Expected one manifest, NGDP and trace per folder')
        entry={'id':f'crash41810-{index:02}','files':[]}
        for path in files:
            if not path.is_file() or path.stat().st_size>32768:raise ValueError('Unexpected bounded input')
            count+=1;total+=path.stat().st_size
            if count>MAX_FILES or total>MAX_BYTES:raise ValueError('Input budget exceeded')
            raw=path.read_bytes();before=sha(raw)
            text=raw.decode('utf-8-sig')
            record={'kind':'build_manifest' if path.name=='.build.info' else 'NGDP_trace' if 'Trace' in path.name else 'NGDP_diagnostics',
                'bytes':len(raw),'sha256':before,'literal_original_replay_root_occurs':ORIGINAL_ROOT.lower() in text.lower()}
            if path.name=='.build.info':
                lines=text.splitlines();columns=[x.split('!',1)[0] for x in lines[0].split('|')]
                rows=[dict(zip(columns,line.split('|'))) for line in lines[1:] if line]
                record['public_build_fields']=[{key:value for key,value in row.items() if key in public_keys} for row in rows]
            else:
                identities=[];shapes=[]
                for line in text.splitlines():
                    if re.search(r'(?i)token|password|secret|authorization|credential',line):continue
                    for match in re.finditer(r'([A-Za-z][A-Za-z _-]{0,50})\s*[:=]\s*([0-9a-fA-F]{32})\b',line):
                        label=match.group(1).strip()
                        if re.search(r'(?i)build|cdn|encoding|root|config',label):identities.append({'label':label,'hex32':match.group(2).lower()})
                    if re.search(r'(?i)build|config|encoding|root|version',line):
                        label=line.strip().split(':',1)[0].split('=',1)[0].strip()
                        if len(label)<=80 and re.fullmatch(r'[A-Za-z0-9_ .()\[\]-]+',label):shapes.append(label)
                record['public_labeled_build_hashes']=identities
                record['build_line_labels_only']=sorted(set(shapes))
            if sha(path.read_bytes())!=before:raise ValueError('Input changed')
            record['source_unchanged']=True
            entry['files'].append(record)
        reports.append(entry)
    return {'format':'hots-preserved41810-crash-NGDP-metadata-v1','producer_sha256':sha(Path(__file__).read_bytes()),
        'folders':reports,'distinct_input_files':count,'distinct_input_bytes':total,'explicit_input_reads_bytes':total*2,
        'original_replay_root':ORIGINAL_ROOT,'limits':{'files':MAX_FILES,'bytes':MAX_BYTES},
        'Variables_Error_text_or_minidump_memory_read':False,'client_launched':False,'game_storage_modified':False,
        'raw_logs_copied_or_published':False,
        'limitations':['Crash folder B41810 labels do not by themselves authenticate the accompanying content build.',
            'Only the explicitly allowlisted public manifest fields and build/root/config labels are emitted; raw log bodies and all other values remain private.',
            'No original41810 BuildConfig is inferred from a newer manifest.']}

if __name__=='__main__':
    report=analyze();OUT.mkdir(exist_ok=False)
    path=OUT/'preserved41810-NGDP-build-metadata.json'
    with path.open('xb') as handle:handle.write((json.dumps(report,indent=2,sort_keys=True)+'\n').encode())
    print(json.dumps(report,indent=2))
