"""Bounded NGS-only MPQ metadata screening, with no full-object fallback."""
from __future__ import annotations

import hashlib
import bz2
import io
from pathlib import Path
import re
import struct
import urllib.error
import urllib.parse
import urllib.request
import zlib

import mpyq

MPYQ_SHA256='526d3e3ae1f5254d8bc32e0248b0763ec5998f350846876c38794373983bed78'
MAX_REQUESTS=24
MAX_RESPONSE_BYTES=128*1024
MAX_READ_BYTES=64*1024
MAX_OBJECT_BYTES=5*1024*1024


class RangeError(ValueError):
    pass


def allowed_url(url):
    if type(url) is not str:
        raise RangeError('Expected an observed public URL')
    parts=urllib.parse.urlsplit(url)
    if (parts.scheme!='https' or parts.netloc!='s3.amazonaws.com' or parts.query or parts.fragment
            or not re.fullmatch(r'/ngs-replay-storage/[A-Za-z0-9_.%-]+\.[Ss]torm[Rr]eplay',parts.path)):
        raise RangeError('Only observed anonymous NGS S3 object URLs are allowed')
    if '%' in parts.path:
        decoded=urllib.parse.unquote(parts.path)
        if urllib.parse.quote(decoded,safe='/_.-')!=parts.path or any(x in decoded for x in ('..','\\','\0')):
            raise RangeError('Unsupported encoded object key')
    return url


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class SharedBudget:
    def __init__(self,max_requests=400,max_bytes=4*1024*1024):
        if type(max_requests) is not int or not 1<=max_requests<=400 or type(max_bytes) is not int or not 1<=max_bytes<=4*1024*1024:
            raise RangeError('Invalid shared budget; maximum400requests/4MiB')
        self.max_requests,self.max_bytes=max_requests,max_bytes
        self.requests,self.response_bytes=[],0


class NgsRangeFile:
    """Minimal seekable mpyq input. All reads are explicit positive bounded ranges."""
    def __init__(self,url,*,opener=None,budget=None):
        self.url=allowed_url(url)
        self.opener=opener or urllib.request.build_opener(NoRedirect)
        self.position=0
        self.size=None
        self.etag=None
        self.requests=[]
        self.response_bytes=0
        self.budget=budget or SharedBudget()
        self.cached=[]
        self.closed=False
        self._request(0,16)

    def _request(self,start,count):
        if type(count) is not int or not 0<count<=MAX_READ_BYTES:
            raise RangeError('Explicit range byte bound exceeded')
        if len(self.requests)>=MAX_REQUESTS or self.response_bytes+count+1>MAX_RESPONSE_BYTES:
            raise RangeError('Metadata screening request or byte budget exceeded')
        if len(self.budget.requests)>=self.budget.max_requests or self.budget.response_bytes+count+1>self.budget.max_bytes:
            raise RangeError('Shared screening request or byte budget exceeded')
        end=start+count-1
        if start<0 or self.size is not None and end>=self.size:
            raise RangeError('Requested range is outside the object')
        headers={'Range':f'bytes={start}-{end}','Accept-Encoding':'identity',
                 'User-Agent':'HotS-Offline-NGS-Metadata/1.0'}
        if self.etag is not None:
            headers['If-Match']=self.etag
        request=urllib.request.Request(self.url,headers=headers)
        receipt=dict(start=start,end=end,if_match_supplied=self.etag is not None)
        self.requests.append(receipt)
        self.budget.requests.append(dict(url=self.url,receipt=receipt))
        try:
            response=self.opener.open(request,timeout=20)
        except urllib.error.HTTPError as error:
            response=error
        with response:
            receipt['status']=response.code
            if response.code!=206:
                # In particular, do not consume a 200 full-object response body.
                raise RangeError('NGS must return HTTP206; no full-object or redirect fallback')
            if response.headers.get('Content-Encoding','identity').lower()!='identity':
                raise RangeError('Encoded HTTP range response is unsupported')
            match=re.fullmatch(r'bytes ([0-9]+)-([0-9]+)/([0-9]+)',response.headers.get('Content-Range',''))
            if not match:
                raise RangeError('Missing or invalid Content-Range')
            got_start,got_end,total=map(int,match.groups())
            if (got_start,got_end)!=(start,end) or not 16<=total<=MAX_OBJECT_BYTES:
                raise RangeError('Content-Range differs or object exceeds the screening bound')
            if self.size is not None and total!=self.size:
                raise RangeError('Remote object size changed')
            etag=response.headers.get('ETag','')
            if not re.fullmatch(r'"[!#-~]{1,160}"',etag) or self.etag is not None and etag!=self.etag:
                raise RangeError('A stable strong ETag is required')
            length=response.headers.get('Content-Length')
            if length is not None and (not re.fullmatch('[0-9]+',length) or int(length)!=count):
                raise RangeError('Content-Length differs from exact requested range')
            raw=response.read(count+1)
            self.response_bytes+=len(raw)
            self.budget.response_bytes+=len(raw)
            receipt['body_bytes']=len(raw)
            if len(raw)!=count:
                raise RangeError('HTTP range response has the wrong byte length')
            self.size,self.etag=total,etag
            self.cached.append((start,raw))
            return raw

    def seek(self,offset,whence=io.SEEK_SET):
        if self.closed or type(offset) is not int or type(whence) is not int or whence not in (0,1,2):
            raise RangeError('Invalid seek')
        position=offset+{0:0,1:self.position,2:self.size}[whence]
        if not 0<=position<=self.size:
            raise RangeError('Seek outside object')
        self.position=position
        return position

    def tell(self):
        return self.position

    def read(self,count=-1):
        if self.closed or type(count) is not int or not 0<=count<=MAX_READ_BYTES:
            raise RangeError('Unbounded or oversized file-like reads are refused')
        if count==0:
            return b''
        if self.position+count>self.size:
            raise RangeError('MPQ requested bytes beyond EOF')
        start=self.position
        for offset,raw in self.cached:
            if offset<=start and start+count<=offset+len(raw):
                result=raw[start-offset:start-offset+count]
                break
        else:
            result=self._request(start,count)
        self.position+=count
        return result

    def close(self):
        self.closed=True


def _inflate(raw,expected):
    if type(expected) is not int or not 0<=expected<=2*1024*1024 or not isinstance(raw,bytes) or not 0<len(raw)<=MAX_RESPONSE_BYTES:
        raise RangeError('Compressed sector input/output bounds exceeded')
    if not raw:
        raise RangeError('Empty compressed MPQ sector')
    if raw[0]==2:
        decoder=zlib.decompressobj()
        result=decoder.decompress(raw[1:],expected+1)
        if not decoder.eof or decoder.unconsumed_tail or decoder.unused_data:
            raise RangeError('Incomplete, oversized or trailing zlib data')
    elif raw[0]==16:
        decoder=bz2.BZ2Decompressor()
        result=decoder.decompress(raw[1:],max_length=expected+1)
        if not decoder.eof or decoder.unused_data:
            raise RangeError('Incomplete, oversized or trailing bzip2 data')
    else:
        raise RangeError('Unsupported compressed MPQ sector')
    if len(result)!=expected:
        raise RangeError('Decoded MPQ sector size differs')
    return result


def read_member(archive,filename,*,output_bound=64*1024):
    """Only metadata/tracker members; bounded decompression replaces mpyq's unbounded inflater."""
    if filename not in ('replay.details','replay.tracker.events'):
        raise RangeError('Member is outside metadata-screening scope')
    bound=64*1024 if filename=='replay.details' else 2*1024*1024
    if type(output_bound) is not int or not 0<output_bound<=bound:
        raise RangeError('Invalid metadata/tracker decompression bound')
    entry=archive.get_hash_table_entry(filename)
    if entry is None or not 0<=entry.block_table_index<len(archive.block_table):
        raise RangeError('No valid requested block')
    block=archive.block_table[entry.block_table_index]
    if not 0<block.size<=output_bound or not 0<block.archived_size<=MAX_RESPONSE_BYTES:
        raise RangeError('Member exceeds its screening size bound')
    allowed=mpyq.MPQ_FILE_EXISTS|mpyq.MPQ_FILE_COMPRESS|mpyq.MPQ_FILE_SINGLE_UNIT
    if not block.flags & mpyq.MPQ_FILE_EXISTS or block.flags & ~allowed:
        raise RangeError('Unsupported MPQ block flags')
    if not block.flags & mpyq.MPQ_FILE_SINGLE_UNIT:
        shift=archive.header['sector_size_shift']
        if not 0<=shift<=8:
            raise RangeError('Unsupported MPQ sector size')
        if block.size%(512<<shift)==0:
            raise RangeError('Exact sector-boundary members are outside the verified profile')
    archive.file.seek(block.offset+archive.header['offset'])
    chunks=[]
    left=block.archived_size
    while left:
        piece=archive.file.read(min(left,MAX_READ_BYTES))
        chunks.append(piece)
        left-=len(piece)
    raw=b''.join(chunks)
    if block.flags & mpyq.MPQ_FILE_SINGLE_UNIT:
        result=_inflate(raw,block.size) if block.flags & mpyq.MPQ_FILE_COMPRESS and block.size>len(raw) else raw
    else:
        shift=archive.header['sector_size_shift']
        if not 0<=shift<=8:
            raise RangeError('Unsupported MPQ sector size')
        sector_size=512<<shift
        count=block.size//sector_size+1
        table_bytes=4*(count+1)
        if table_bytes>len(raw):
            raise RangeError('Truncated sector table')
        offsets=struct.unpack('<%dI'%(count+1),raw[:table_bytes])
        if offsets[0]!=table_bytes or offsets[-1]!=len(raw) or any(a>b for a,b in zip(offsets,offsets[1:])):
            raise RangeError('Invalid MPQ sector offsets')
        chunks=[]
        left=block.size
        for start,end in zip(offsets,offsets[1:]):
            size=min(left,sector_size)
            sector=raw[start:end]
            decoded=_inflate(sector,size) if block.flags & mpyq.MPQ_FILE_COMPRESS and size>len(sector) else sector
            if len(decoded)!=size:
                raise RangeError('Decoded MPQ sector size differs')
            chunks.append(decoded)
            left-=size
        result=b''.join(chunks)
    if len(result)!=block.size:
        raise RangeError('Decoded member size differs')
    return result


def screen(url,*,opener=None,budget=None):
    if mpyq.__version__!='0.2.5' or hashlib.sha256(Path(mpyq.__file__).read_bytes()).hexdigest()!=MPYQ_SHA256:
        raise RangeError('Pinned mpyq0.2.5 source differs')
    remote=NgsRangeFile(url,opener=opener,budget=budget)
    archive=mpyq.MPQArchive(remote,listfile=False)
    if archive.header['magic']!=b'MPQ\x1a' or archive.header['format_version'] not in (0,1,3):
        raise RangeError('Unsupported observed MPQ legacy-table profile')
    details=read_member(archive,'replay.details')
    return remote,archive,details
