import hashlib
import io
import os
from types import SimpleNamespace
from unittest.mock import Mock
from pathlib import Path
import re
import unittest
import zlib

import ngs_range_details as r

URL='https://s3.amazonaws.com/ngs-replay-storage/known.stormReplay'


class Response(io.BytesIO):
    def __init__(self,raw,code,headers):
        super().__init__(raw)
        self.code,self.headers,self.read_calls=code,headers,0
    def read(self,n=-1):
        self.read_calls+=1
        return super().read(n)


class Opener:
    def __init__(self,data=b'a'*200,mutate=None):
        self.data,self.mutate,self.responses,self.requests=data,mutate,[],[]
    def open(self,request,timeout):
        start,end=map(int,re.fullmatch(r'bytes=(\d+)-(\d+)',request.get_header('Range')).groups())
        body=self.data[start:end+1]
        headers={'Content-Range':f'bytes {start}-{end}/{len(self.data)}','ETag':'"unchanged-object"','Content-Length':str(len(body))}
        response=Response(body,206,headers)
        self.requests.append(request)
        self.responses.append(response)
        if self.mutate:
            self.mutate(response,len(self.responses))
        return response


class RangeTests(unittest.TestCase):
    def test_exact_ranges_cache_seek_and_conditional_request(self):
        transport=Opener()
        source=r.NgsRangeFile(URL,opener=transport)
        self.assertEqual(source.read(4),b'aaaa')
        self.assertEqual(len(transport.requests),1)
        source.seek(20); self.assertEqual(source.read(5),b'a'*5)
        self.assertEqual(transport.requests[-1].get_header('If-match'),'"unchanged-object"')
        self.assertEqual(source.response_bytes,21)

    def test_full_200_is_refused_without_body_read(self):
        transport=Opener(mutate=lambda response,n:setattr(response,'code',200))
        with self.assertRaises(r.RangeError): r.NgsRangeFile(URL,opener=transport)
        self.assertEqual(transport.responses[0].read_calls,0)

    def test_redirect_is_refused_without_body_read(self):
        transport=Opener(mutate=lambda response,n:setattr(response,'code',302))
        with self.assertRaises(r.RangeError): r.NgsRangeFile(URL,opener=transport)
        self.assertEqual(transport.responses[0].read_calls,0)

    def test_invalid_content_range_total_encoding_or_length(self):
        for key,value in [('Content-Range','bytes 1-16/200'),('Content-Range','bytes 0-15/*'),
            ('Content-Range','bytes 0-15/999999999'),('Content-Length','200'),('Content-Encoding','gzip')]:
            with self.subTest(key=key,value=value):
                transport=Opener(mutate=lambda response,n:response.headers.update({key:value}))
                with self.assertRaises(r.RangeError): r.NgsRangeFile(URL,opener=transport)
                self.assertEqual(transport.responses[0].read_calls,0)

    def test_strong_stable_etag_and_size_required(self):
        for value in ('','W/"weak"','unquoted'):
            with self.subTest(value=value):
                transport=Opener(mutate=lambda response,n:response.headers.update(ETag=value))
                with self.assertRaises(r.RangeError): r.NgsRangeFile(URL,opener=transport)
        for key,value in [('ETag','"changed"'),('Content-Range','bytes 20-24/201')]:
            transport=Opener(mutate=lambda response,n:response.headers.update({key:value}) if n==2 else None)
            source=r.NgsRangeFile(URL,opener=transport); source.seek(20)
            with self.assertRaises(r.RangeError): source.read(5)

    def test_short_body_rejected(self):
        transport=Opener(mutate=lambda response,n:response.truncate(15))
        with self.assertRaises(r.RangeError): r.NgsRangeFile(URL,opener=transport)

    def test_unbounded_reads_bad_seek_and_close_refused(self):
        source=r.NgsRangeFile(URL,opener=Opener())
        for count in (-1,True,r.MAX_READ_BYTES+1):
            with self.assertRaises(r.RangeError): source.read(count)
        for offset,whence in [(-1,0),(201,0),(0,9),(True,0)]:
            with self.assertRaises(r.RangeError): source.seek(offset,whence)
        source.close()
        with self.assertRaises(r.RangeError): source.read(1)

    def test_request_and_response_budgets_refused_before_network(self):
        for attribute,value in [('requests',[{}]*r.MAX_REQUESTS),('response_bytes',r.MAX_RESPONSE_BYTES)]:
            transport=Opener(); source=r.NgsRangeFile(URL,opener=transport)
            setattr(source,attribute,value); source.seek(30)
            with self.assertRaises(r.RangeError): source.read(10)
            self.assertEqual(len(transport.requests),1)

    def test_shared_caps_apply_across_distinct_objects(self):
        for budget in (r.SharedBudget(max_requests=1),r.SharedBudget(max_bytes=25)):
            transport=Opener()
            r.NgsRangeFile(URL,opener=transport,budget=budget)
            with self.assertRaises(r.RangeError):
                r.NgsRangeFile(URL.replace('known','other'),opener=transport,budget=budget)
            self.assertEqual(len(transport.requests),1)
            self.assertEqual(budget.response_bytes,16)

    def test_host_credentials_query_and_encoded_traversal_rejected(self):
        for url in ['http://s3.amazonaws.com/ngs-replay-storage/a.stormReplay',URL+'?other=1',
            URL.replace('s3.amazonaws.com','s3.amazonaws.com.evil.test'),
            URL.replace('s3.amazonaws.com','name@s3.amazonaws.com'),
            URL.replace('known','%2e%2e%2fsecret')]:
            with self.subTest(url=url):
                with self.assertRaises(r.RangeError): r.allowed_url(url)

    def test_bounded_inflate_rejects_bomb_and_trailing_data(self):
        compressed=b'\x02'+zlib.compress(b'x'*100000)
        with self.assertRaises(r.RangeError): r._inflate(compressed,10)
        compressed=b'\x02'+zlib.compress(b'abc')
        self.assertEqual(r._inflate(compressed,3),b'abc')
        with self.assertRaises(r.RangeError): r._inflate(compressed+b'extra',3)

    def test_exact_sector_boundaries_are_explicitly_refused_before_io(self):
        for size in (512,1024):
            with self.subTest(size=size):
                file=Mock()
                block=SimpleNamespace(size=size,archived_size=50,flags=r.mpyq.MPQ_FILE_EXISTS|r.mpyq.MPQ_FILE_COMPRESS,offset=0)
                archive=SimpleNamespace(file=file,header={'offset':0,'sector_size_shift':0},block_table=[block],
                    get_hash_table_entry=lambda name:SimpleNamespace(block_table_index=0))
                with self.assertRaisesRegex(r.RangeError,'Exact sector-boundary'):
                    r.read_member(archive,'replay.tracker.events')
                file.seek.assert_not_called()
                file.read.assert_not_called()

    def test_invalid_shared_budgets_refused(self):
        for requests,maximum in [(0,100),(401,100),(True,100),(1,0),(1,4*1024*1024+1)]:
            with self.assertRaises(r.RangeError): r.SharedBudget(requests,maximum)

    def test_member_scope_and_decompression_caps_are_not_overridable(self):
        for name,bound in [('replay.message.events',100),('replay.details',65537),
                ('replay.tracker.events',2*1024*1024+1),('replay.details',True)]:
            with self.assertRaises(r.RangeError): r.read_member(None,name,output_bound=bound)
        with self.assertRaises(r.RangeError): r._inflate(b'\x02',2*1024*1024+1)

    def test_actual_control_fake_ranges_match_unmodified_mpyq(self):
        fixture=os.environ.get('NGS_RANGE_CONTROL')
        if not fixture:
            self.skipTest('Set NGS_RANGE_CONTROL to the SHA-pinned already-downloaded control')
        path=Path(fixture)
        raw=path.read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(),'afcf49a656068f343173fc79afff2d2ebf15066f531cb192382cdba9d1ea3272')
        source,archive,details=r.screen(URL,opener=Opener(raw))
        original=r.mpyq.MPQArchive(io.BytesIO(raw),listfile=False)
        self.assertEqual(archive.header,original.header)
        self.assertEqual(details,original.read_file('replay.details'))
        tracker=r.read_member(archive,'replay.tracker.events',output_bound=2*1024*1024)
        self.assertEqual(tracker,original.read_file('replay.tracker.events'))
        self.assertLess(source.response_bytes,r.MAX_RESPONSE_BYTES)


if __name__=='__main__': unittest.main()
