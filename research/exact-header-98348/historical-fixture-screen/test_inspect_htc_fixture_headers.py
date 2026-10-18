import http.client
import socket
import struct
import unittest
import urllib.error
from unittest.mock import patch
import inspect_htc_fixture_headers as probe

class Response:
    def __init__(self,*,status=206,headers=None,url=None,raw=b'X'*4096,error=None):
        self.status=status;self.headers=headers if headers is not None else {'Content-Range':'bytes 0-4095/5000','Content-Length':'4096'}
        self.url=url;self.raw=raw;self.error=error;self.reads=[];self.closed=False
    def __enter__(self): return self
    def __exit__(self,*_): self.close()
    def close(self): self.closed=True
    def geturl(self): return self.url
    def read(self,n):
        self.reads.append(n)
        if self.error: raise self.error
        return self.raw[:n]

class Opener:
    def __init__(self,response=None,error=None): self.response=response;self.error=error;self.requests=[]
    def open(self,request,timeout):
        self.requests.append((request,timeout))
        if self.error: raise self.error
        return self.response

class ProbeTests(unittest.TestCase):
    def spec(self):
        path='Tests/Heroes.StormReplayParser.Tests/Replays/example.StormR'
        return {'path':path,'url':probe.PREFIX+probe.COMMIT+'/'+path,'listed_bytes':5000}
    def response(self,**kwargs):
        kwargs.setdefault('url',self.spec()['url']);return Response(**kwargs)
    def test_actual_metadata_all20_and24canonical_trees(self):
        specs,count=probe.fixtures();self.assertEqual((len(specs),count),(20,24))
        self.assertEqual(sum(len(x['duplicate_paths']) for x in specs),2)
        self.assertEqual(len({x['git_blob_sha1'] for x in specs}),20)
    def test_single206_exact_read_headers_and_close(self):
        response=self.response();opener=Opener(response)
        raw,meta,error=probe.fetch_prefix(opener,self.spec())
        self.assertIsNone(error);self.assertEqual(len(raw),4096)
        self.assertEqual(response.reads,[4096]);self.assertTrue(response.closed)
        self.assertEqual(meta['application_body_bytes_read'],4096)
        self.assertEqual(opener.requests[0][0].get_header('Range'),'bytes=0-4095')
        self.assertEqual(opener.requests[0][0].get_header('Accept-encoding'),'identity')
        self.assertEqual(len(opener.requests),1)
    def test_ignored200_gets_zero_body_reads(self):
        response=self.response(status=200)
        raw,meta,error=probe.fetch_prefix(Opener(response),self.spec())
        self.assertEqual(error,'non206_refused_before_body');self.assertIsNone(raw)
        self.assertEqual(response.reads,[]);self.assertTrue(response.closed)
        self.assertEqual(meta['application_body_bytes_read'],0)
    def test_wrong_range_size_length_and_encoding_get_zero_reads(self):
        for change in ({'Content-Range':'bytes 0-4095/5001'},{'Content-Range':'bytes 1-4096/5000'},{'Content-Length':'5000'},{'Content-Encoding':'gzip'}):
            with self.subTest(change=change):
                headers={'Content-Range':'bytes 0-4095/5000','Content-Length':'4096'}|change
                response=self.response(headers=headers)
                raw,meta,error=probe.fetch_prefix(Opener(response),self.spec())
                self.assertIsNone(raw);self.assertIsNotNone(error)
                self.assertEqual(response.reads,[]);self.assertEqual(meta['application_body_bytes_read'],0)
                self.assertTrue(response.closed)
    def test_changed_URL_and_private_host_refused_before_read_or_request(self):
        response=self.response(url='https://127.0.0.1/private')
        raw,meta,error=probe.fetch_prefix(Opener(response),self.spec())
        self.assertEqual(error,'changed_url_refused');self.assertEqual(response.reads,[])
        opener=Opener(response)
        with self.assertRaises(ValueError):probe.fetch_prefix(opener,self.spec()|{'url':'https://127.0.0.1/private'})
        self.assertEqual(opener.requests,[])
    def test_redirect_handler_closes_without_read(self):
        response=self.response(status=302)
        with self.assertRaisesRegex(probe.TransportRefused,'redirect_refused'):
            probe.NoRedirect().http_error_302(None,response,302,'redirect',{})
        self.assertTrue(response.closed);self.assertEqual(response.reads,[])
    def test_short_prefix_and_incomplete_read_count_actual_bytes(self):
        response=self.response(raw=b'X'*27)
        raw,meta,error=probe.fetch_prefix(Opener(response),self.spec())
        self.assertEqual((raw,error,meta['application_body_bytes_read']),(None,'short_prefix_body',27))
        response=self.response(error=http.client.IncompleteRead(b'X'*31,4096))
        raw,meta,error=probe.fetch_prefix(Opener(response),self.spec())
        self.assertEqual((raw,error,meta['application_body_bytes_read']),(None,'incomplete_HTTP_body',31))
        self.assertTrue(response.closed);self.assertEqual(response.reads,[4096])
    def test_network_failure_classified_without_retry(self):
        opener=Opener(error=urllib.error.URLError(socket.gaierror(11001,'not included')))
        raw,meta,error=probe.fetch_prefix(opener,self.spec())
        self.assertEqual(error,'network_error');self.assertEqual(meta['application_body_bytes_read'],0)
        self.assertEqual(meta['network_error_class'],'gaierror');self.assertEqual(len(opener.requests),1)
    def test_MPQ_extent_and_allowlisted_version_decoding(self):
        class Protocol:
            def decode_replay_header(self,raw):
                self.raw=raw
                return {'m_version':dict(m_flags=1,m_major=0,m_minor=17,m_revision=0,m_build=41810,m_baseBuild=41810)}
        protocol=Protocol();raw=struct.pack('<4s3I',b'MPQ\x1b',512,1024,3)+b'abc'+b'\0'*(4096-19)
        result=probe.decode_header(raw,protocol)
        self.assertEqual(protocol.raw,b'abc');self.assertEqual(result['version']['m_build'],41810)
        self.assertIsNone(result['data_build']);self.assertIsNone(result['NGDP_root'])
        self.assertEqual(set(result),{'version','data_build','NGDP_root','MPQ_user_header_bytes','MPQ_user_data_size','MPQ_archive_offset'})
        with self.assertRaises(ValueError):probe.decode_header(raw[:30],protocol)
        with self.assertRaises(ValueError):probe.decode_header(b'BAD!'+raw[4:],protocol)
    def test_canonical_tree_negative_control(self):
        specs,_=probe.fixtures()
        with self.assertRaises(ValueError):probe.canonical_trees([{'path':'x','type':'blob','mode':'100644','sha':specs[0]['git_blob_sha1']}],probe.TREE)

if __name__=='__main__':unittest.main()
