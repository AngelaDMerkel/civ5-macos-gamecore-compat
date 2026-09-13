import importlib.util
from pathlib import Path
import platform
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('validator', ROOT / 'tools/validate.py')
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)


@unittest.skipUnless(platform.system() == 'Darwin', 'requires Mach-O tools')
class BinaryValidationTests(unittest.TestCase):
    def test_actual_macho_contract_and_unknown_import(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / 'core.cpp'
            binary = Path(temporary) / 'core.dylib'
            source.write_text('extern "C" void DllGetGameContext() {}\n')
            base = ['clang++', '-target', 'x86_64-apple-macos10.11.6', '-dynamiclib',
                    '-undefined', 'dynamic_lookup', '-fvisibility=hidden',
                    '-Wl,-exported_symbol,_DllGetGameContext', '-compatibility_version', '1.0.0',
                    '-current_version', '1.0.0', '-install_name', '/libCvGameCoreDLL_Expansion2_DLL.dylib']
            source.write_text('extern "C" __attribute__((visibility("default"))) void DllGetGameContext() {}\n')
            subprocess.run([*base, str(source), '-o', str(binary)], check=True)
            self.assertTrue(validator.validate(binary)['validated'])
            source.write_text('extern "C" void NotAnAspyrImportForTest();\nextern "C" __attribute__((visibility("default"))) void DllGetGameContext() { NotAnAspyrImportForTest(); }\n')
            subprocess.run([*base, str(source), '-o', str(binary)], check=True)
            with self.assertRaisesRegex(ValueError, 'NotAnAspyrImportForTest'):
                validator.validate(binary)

    def test_wrong_install_name_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / 'core.cpp'
            binary = Path(temporary) / 'core.dylib'
            source.write_text('extern "C" void DllGetGameContext() {}\n')
            subprocess.run(['clang++', '-target', 'x86_64-apple-macos10.11.6', '-dynamiclib',
                            '-compatibility_version', '1.0.0', '-current_version', '1.0.0',
                            '-install_name', '/wrong.dylib', str(source), '-o', str(binary)], check=True)
            with self.assertRaisesRegex(ValueError, 'identity'):
                validator.validate(binary)
