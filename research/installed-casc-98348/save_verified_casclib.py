"""Save only an exact catalog-hash-verified managed DLL and license/provenance."""
from pathlib import Path
import urllib.request,zipfile,io,json,hashlib,base64
root=Path(__file__).resolve().parent
url='https://api.nuget.org/v3-flatcontainer/heroes.xmldata/1.1.1/heroes.xmldata.1.1.1.nupkg'
expected='9VGSlxKeM3aBKBvtLuvoSc98Ze/VUoiWF7jic3HinzoJSRh4jp2C7CnyZET4QnWUWu7MibuJX8cWfaQGzoWmBQ=='
with urllib.request.urlopen(url,timeout=30) as response:raw=response.read(1024*1024+1)
assert len(raw)==424343 and hashlib.sha256(raw).hexdigest()=='8794feaf1c0a7466e0ece7ec47bb6b35f8ef08b41b64ee4e21edaf3fe0dd7174'
assert base64.b64encode(hashlib.sha512(raw).digest()).decode()==expected
archive=zipfile.ZipFile(io.BytesIO(raw));saved=[]
for source,destination,limit in [('lib/net10.0/CascLib.dll','CascLib.dll',512*1024),('LICENSE','Heroes.XmlData.LICENSE',64*1024)]:
    info=archive.getinfo(source);assert info.file_size<=limit
    content=archive.read(info);assert len(content)==info.file_size
    path=root/destination
    with path.open('xb') as stream:stream.write(content)
    saved.append(dict(path=destination,package_entry=source,bytes=len(content),sha256=hashlib.sha256(content).hexdigest()))
result=dict(format='hots-local-casc-managed-dll-provenance-v1',package_url=url,package_bytes=len(raw),
    package_sha256=hashlib.sha256(raw).hexdigest(),package_sha512=expected,official_nuget_catalog_sha512_verified=True,
    catalog_registration='https://api.nuget.org/v3/registration5-semver1/heroes.xmldata/1.1.1.json',
    repository_commit='1cfc5150320079c79cb7d618778ef5afcb11a3fc',casc_submodule_commit='205154e3c269d5e2a7c099e5bb77050185599d21',
    saved_files=saved,package_archive_saved=False,game_opened=False,dll_loaded=False)
with (root/'saved-casclib-provenance.json').open('x',encoding='utf-8',newline='\n') as stream:json.dump(result,stream,indent=2);stream.write('\n')
print(json.dumps(saved,indent=2))
