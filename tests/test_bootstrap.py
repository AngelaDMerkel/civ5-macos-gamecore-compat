import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('bootstrap', ROOT / 'tools/bootstrap.py')
bootstrap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bootstrap)


class PinningTests(unittest.TestCase):
    def test_exact_commit_isolated_from_dirty_source_and_tampering_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            temporary = Path(temporary)
            source = temporary / 'source'
            source.mkdir()
            def git(*args):
                return subprocess.check_output(['git', '-C', str(source), *args], text=True).strip()
            git('init', '-q')
            git('config', 'user.name', 'Test')
            git('config', 'user.email', 'test@example.invalid')
            (source / 'header.h').write_text('locked contents')
            git('add', '.')
            git('commit', '-qm', 'fixture')
            commit = git('rev-parse', 'HEAD')
            (source / 'header.h').write_text('uncommitted edits')
            lock = temporary / 'compat.lock.json'
            lock.write_text(json.dumps({'repository': 'https://github.com/AngelaDMerkel/civ5-macos-gamecore-compat.git', 'commit': commit}))
            with patch.dict(os.environ, {'CIV5_COMPAT_SOURCE': str(source)}):
                checkout = bootstrap.bootstrap(lock)
                self.assertEqual((checkout / 'header.h').read_text(), 'locked contents')
                (checkout / 'header.h').write_text('tampered')
                with self.assertRaisesRegex(ValueError, 'dirty'):
                    bootstrap.bootstrap(lock)
            lock.write_text(json.dumps({'commit': 'main'}))
            with self.assertRaisesRegex(ValueError, 'exact commit'):
                bootstrap.bootstrap(lock)
