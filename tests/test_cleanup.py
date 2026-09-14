from pathlib import Path
import os
import tempfile
import time
import unittest
from unittest.mock import patch
from app import scan,clean,restore

class CleanupTests(unittest.TestCase):
    def test_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            source=Path(d)/'temp';source.mkdir();p=source/'old';p.write_text('data');os.utime(p,(time.time()-10*86400,)*2)
            with patch('app.temp_roots',return_value=[source.resolve()]):
                plan=scan(source);q=Path(d)/'quarantine';clean(plan,q);self.assertFalse(p.exists());restore(q);self.assertEqual(p.read_text(),'data')
    def test_personal_forbidden(self):
        with tempfile.TemporaryDirectory() as d,patch('app.temp_roots',return_value=[]):
            with self.assertRaises(ValueError):clean(scan(d),Path(d)/'q')
    def test_changed(self):
        with tempfile.TemporaryDirectory() as d:
            source=Path(d)/'temp';source.mkdir();p=source/'old';p.write_text('a');os.utime(p,(time.time()-10*86400,)*2)
            with patch('app.temp_roots',return_value=[source.resolve()]):
                plan=scan(source);p.write_text('b')
                with self.assertRaises(ValueError):clean(plan,Path(d)/'q')
