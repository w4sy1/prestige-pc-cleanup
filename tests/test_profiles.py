import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from app import clean,scan,restore


class ProfileTests(unittest.TestCase):
    def test_thumbnail_whitelist_and_restore(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)/'Explorer';root.mkdir()
            file=root/'thumbcache_96.db';file.write_bytes(b'fixture');os.utime(file,(time.time()-10*86400,)*2)
            with patch('app.profiles',return_value={'thumbnails':str(root)}),patch('app.temp_roots',return_value=[]):
                plan=scan(root);self.assertTrue(plan['clean_allowed'])
                clean(plan,Path(temporary)/'quarantine');restore(Path(temporary)/'quarantine')
                self.assertEqual(file.read_bytes(),b'fixture')
                other=root/'settings.dat';other.write_bytes(b'keep');os.utime(other,(time.time()-10*86400,)*2)
                with self.assertRaises(ValueError):clean(scan(root),Path(temporary)/'other')
                self.assertTrue(file.exists());self.assertTrue(other.exists())

    def test_logs_are_review_only(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);file=root/'old.log';file.write_text('log');os.utime(file,(time.time()-10*86400,)*2)
            with patch('app.temp_roots',return_value=[]),patch('app.profiles',return_value={'windows-logs':str(root)}):
                data=scan(root)
                self.assertEqual(data['files'][0]['categories'],['log'])
                self.assertFalse(data['clean_allowed'])
                with self.assertRaises(ValueError):clean(data,root.parent/'never-created-quarantine')
