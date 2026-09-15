from pathlib import Path
import json
import os
import tempfile
import time
import unittest
from unittest.mock import patch
from app import scan,clean,restore


class RestoreFailureTests(unittest.TestCase):
    def prepare(self,root):
        source=root/'temp';source.mkdir()
        for name in ('a','b'):
            file=source/name;file.write_text(name);os.utime(file,(time.time()-10*86400,)*2)
        return source,root/'quarantine'

    def test_missing_file_rejects_before_any_restore(self):
        with tempfile.TemporaryDirectory() as temporary:
            source,q=self.prepare(Path(temporary))
            with patch('app.temp_roots',return_value=[source.resolve()]):
                clean(scan(source),q);manifest=json.loads((q/'manifest.json').read_text())
                (q/manifest['files'][-1]['stored']).unlink()
                with self.assertRaises(ValueError):restore(q)
                self.assertEqual(list(source.iterdir()),[])

    def test_repeated_restore_checks_existing_content(self):
        with tempfile.TemporaryDirectory() as temporary:
            source,q=self.prepare(Path(temporary))
            with patch('app.temp_roots',return_value=[source.resolve()]):
                clean(scan(source),q);restore(q)
                self.assertEqual(restore(q)['already_restored'],2)
                (source/'a').write_text('changed')
                with self.assertRaises(ValueError):restore(q)
                self.assertEqual((source/'a').read_text(),'changed')

    def test_duplicate_manifest_rejected_before_mutation(self):
        with tempfile.TemporaryDirectory() as temporary:
            source,q=self.prepare(Path(temporary))
            with patch('app.temp_roots',return_value=[source.resolve()]):
                clean(scan(source),q);path=q/'manifest.json';manifest=json.loads(path.read_text())
                manifest['files'].append(manifest['files'][0]);path.write_text(json.dumps(manifest))
                with self.assertRaises(ValueError):restore(q)
                self.assertEqual(list(source.iterdir()),[])

    def test_file_created_after_preflight_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as temporary:
            source,q=self.prepare(Path(temporary))
            with patch('app.temp_roots',return_value=[source.resolve()]):
                # Windows runners may expose TEMP through an 8.3 alias, while
                # restore uses the canonical root stored in the manifest.
                clean(scan(source),q);original_open=Path.open;target=source.resolve()/'a'
                def racing_open(path,mode='r',*args,**kwargs):
                    if path==target and mode=='xb':
                        with original_open(path,'wb') as stream:stream.write(b'new user file')
                    return original_open(path,mode,*args,**kwargs)
                with patch.object(Path,'open',racing_open):
                    with self.assertRaises(FileExistsError):restore(q)
                self.assertEqual(target.read_bytes(),b'new user file')
                manifest=json.loads((q/'manifest.json').read_text())
                self.assertTrue(all((q/row['stored']).exists() for row in manifest['files']))
