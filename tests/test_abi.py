from pathlib import Path
import platform
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(platform.system() == 'Darwin', 'requires macOS toolchain')
class AbiTests(unittest.TestCase):
    def test_layout_and_atomic_behavior(self):
        with tempfile.TemporaryDirectory() as temporary:
            binary = Path(temporary) / 'abi-test'
            subprocess.run(['clang++', '-target', 'x86_64-apple-macos10.11.6',
                            '-std=c++11', '-I', str(ROOT / 'include'),
                            str(ROOT / 'tests/abi.cpp'), '-o', str(binary)], check=True)
            subprocess.run([str(binary)], check=True)
