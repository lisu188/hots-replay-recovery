"""Synthetic transport/body guards; no network or real header fixtures."""
from io import BytesIO
import hashlib
import unittest
from unittest.mock import patch

import search_exact_public_datamod as subject


class Response(BytesIO):
    def __init__(self,raw,length=None):
        super().__init__(raw);self.headers={} if length is None else {'Content-Length':length}


class ExactObjectGuards(unittest.TestCase):
    def test_complete_declared_body(self):
        raw,reason=subject.bounded_body(Response(b'synthetic','9'),100)
        self.assertEqual(raw,b'synthetic');self.assertIsNone(reason)

    def test_declared_oversize_refused_before_read(self):
        response=Response(b'synthetic',str(subject.PER_OBJECT+1))
        raw,reason=subject.bounded_body(response,subject.AGGREGATE)
        self.assertEqual(raw,b'');self.assertEqual(response.tell(),0)
        self.assertEqual(reason,'invalid_or_oversize_declared_body')

    def test_unknown_length_never_reads_past_remaining_budget(self):
        response=Response(bytes(101))
        raw,reason=subject.bounded_body(response,100)
        self.assertEqual(len(raw),100);self.assertEqual(response.tell(),100)
        self.assertEqual(reason,'unknown_length_reached_body_bound')

    def test_truncated_declared_body_is_acquisition_failure(self):
        raw,reason=subject.bounded_body(Response(b'partial','10'),100)
        self.assertEqual(len(raw),7);self.assertEqual(reason,'truncated_declared_body')

    def test_redirect_and_nonplan_URL_refused(self):
        self.assertIsNone(subject.NoRedirect().redirect_request(None,None,None,None,None,None))
        for url in ('https://us-s2-depot.classic.blizzard.com/unlisted.s2mh','https://example.com/',subject.PLAN[0][1]+'?credentials=no'):
            with self.assertRaises(ValueError):subject.checked_url(url)

    def test_wrong_digest_refused_before_decoder(self):
        with patch.object(subject,'decode_verified_header') as decoder:
            with self.assertRaises(ValueError):subject.validated_body(b'synthetic')
            decoder.assert_not_called()

    def test_hash_match_still_requires_exact_package(self):
        raw=b'synthetic';sha=hashlib.sha256(raw).hexdigest()
        with patch.object(subject,'EXPECTED',sha),patch.object(subject,'decode_verified_header',return_value={0:{0:{0:280539,1:15}}}):
            with self.assertRaises(ValueError):subject.validated_body(raw)

    def test_synthetic_full_guard_positive(self):
        raw=b'synthetic';sha=hashlib.sha256(raw).hexdigest()
        with patch.object(subject,'EXPECTED',sha),patch.object(subject,'decode_verified_header',return_value={0:{0:{0:280539,1:16}}}):
            self.assertEqual(subject.validated_body(raw),{'complete_generic_decode':True,'mod_id':280539,'version':16})


if __name__=='__main__':unittest.main()
