"""Small synthetic filesystem guards; genuine reproduction is a separate check."""
import hashlib,json,tempfile,unittest
from pathlib import Path
from recover_current_eu_heroesdata_header import save_exact_header,read_bounded,new_output,main

class HeaderWriteGuards(unittest.TestCase):
    # Generic versioned-wire {0:{},1:{}}. No genuine game/publisher data.
    BODY=bytes.fromhex('0504000500020500')
    DIGEST='085c40ee7f2fbf16a47e3bf6e14d96f3e6fc30ff65a35b77d47bde0876fcef0b'
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.out=self.root/'synthetic.s2mh'
    def test_mismatching_digest_creates_no_file_or_sibling(self):
        self.assertFalse(save_exact_header(self.BODY,self.out,'0'*64))
        self.assertEqual(list(self.root.iterdir()),[])
    def test_exact_digest_and_complete_wire_creates_exact_bytes(self):
        self.assertTrue(save_exact_header(self.BODY,self.out,self.DIGEST))
        self.assertEqual(self.out.read_bytes(),self.BODY)
        self.assertEqual(hashlib.sha256(self.out.read_bytes()).hexdigest(),self.DIGEST)
    def test_existing_output_is_refused_and_preserved(self):
        self.out.write_bytes(b'preserve this checkpoint')
        with self.assertRaises(FileExistsError):save_exact_header(self.BODY,self.out,self.DIGEST)
        self.assertEqual(self.out.read_bytes(),b'preserve this checkpoint')
    def test_exact_hash_with_trailing_wire_bytes_still_cannot_write(self):
        body=self.BODY+b'\0'
        with self.assertRaises(ValueError):save_exact_header(body,self.out,hashlib.sha256(body).hexdigest())
        self.assertFalse(self.out.exists())
    def test_noncanonical_expected_digest_rejected_before_write(self):
        with self.assertRaises(ValueError):save_exact_header(self.BODY,self.out,self.DIGEST.upper())
        self.assertFalse(self.out.exists())
    def test_header_over_size_bound_never_written(self):
        with self.assertRaises(ValueError):save_exact_header(b'x'*(512*1024+1),self.out,self.DIGEST)
        self.assertFalse(self.out.exists())
    def test_input_over_limit_is_refused(self):
        source=self.root/'large.bin';source.write_bytes(b'x'*9)
        with self.assertRaises(ValueError):read_bounded(source,8)
    def test_cli_refuses_existing_report_before_reading_inputs(self):
        report=self.root/'receipt.json';report.write_text('preserve')
        args=['--source-header',str(self.root/'absent-source'),'--prior-header',str(self.root/'absent-prior'),'--reference-replay',str(self.root/'absent-replay'),'--output',str(self.out),'--report',str(report)]
        self.assertEqual(main(args),1)
        self.assertEqual(report.read_text(),'preserve');self.assertFalse(self.out.exists())

if __name__=='__main__':unittest.main()
