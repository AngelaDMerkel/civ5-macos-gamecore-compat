#!/usr/bin/env python3
"""Validate a GameCore against a finite, recorded Aspyr ABI contract."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def output(*args):
    return subprocess.check_output(args, text=True).strip()


def sha256(path):
    with open(path, 'rb') as stream:
        digest = hashlib.sha256()
        for data in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(data)
        return digest.hexdigest()


def validate(binary, manifest=ROOT / 'abi/aspyr-bnw.json', app=None):
    binary, manifest = Path(binary), Path(manifest)
    abi = json.loads(manifest.read_text())
    if output('lipo', '-archs', str(binary)).split() != [abi['architecture']]:
        raise ValueError('expected thin x86_64 Mach-O')
    if 'Mach-O 64-bit' not in output('file', str(binary)):
        raise ValueError('expected Mach-O 64-bit binary')
    exports = {line.split()[-1] for line in output('nm', '-gU', str(binary)).splitlines() if line.split()}
    if exports != set(abi['exports']):
        raise ValueError('unexpected public exports: ' + repr(sorted(exports)))
    load = output('otool', '-l', str(binary))
    commands = re.split(r'Load command \d+\n', load)
    identity = next((c for c in commands if re.search(r'cmd LC_ID_DYLIB\b', c)), '')
    for pattern in [r'name ' + re.escape(abi['install_name']) + r' \(offset',
                    r'current version ' + re.escape(abi['current_version']) + r'\b',
                    r'compatibility version ' + re.escape(abi['compatibility_version']) + r'\b']:
        if not re.search(pattern, identity):
            raise ValueError('incorrect dylib identity/version')
    deployment = next((c for c in commands if 'cmd LC_VERSION_MIN_MACOSX' in c), '')
    if not re.search(r'version ' + re.escape(abi['deployment_target']) + r'\s', deployment):
        raise ValueError('incorrect deployment target')
    allowed = set()
    engine_allowed = set()
    for key in ['stock_imports', 'host_exports', 'system_imports']:
        symbols = set((manifest.parent / abi[key]).read_text().splitlines())
        allowed.update(symbols)
        if key != 'system_imports':
            engine_allowed.update(symbols)
    imports = set(output('nm', '-u', str(binary)).splitlines())
    extra = imports - allowed
    if extra:
        raise ValueError('imports absent from ABI allowlist:\n' + '\n'.join(sorted(extra)))
    dynamic = set(re.findall(r'\bexternal\s+(\S+)\s+\(dynamically looked up\)',
                             output('nm', '-mu', str(binary))))
    if dynamic - engine_allowed:
        raise ValueError('unresolved engine imports absent from stock/host:\n' + '\n'.join(sorted(dynamic - engine_allowed)))
    libraries = output('otool', '-L', str(binary)).splitlines()[1:]
    expected_libraries = {abi['install_name'], '/usr/lib/libc++.1.dylib', '/usr/lib/libSystem.B.dylib'}
    if {line.strip().split(' (', 1)[0] for line in libraries} != expected_libraries:
        raise ValueError('unexpected runtime library dependencies')
    if app:
        exe = Path(app) / 'Contents/MacOS/Civilization V'
        if sha256(exe) not in abi['host_executable_sha256']:
            raise ValueError('unsupported host executable hash')
    return {'abi_id': abi['abi_id'], 'sha256': sha256(binary),
            'exports': sorted(exports), 'import_count': len(imports),
            'dynamic_lookup_count': len(dynamic), 'validated': True}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binary', type=Path, required=True)
    parser.add_argument('--manifest', type=Path, default=ROOT / 'abi/aspyr-bnw.json')
    parser.add_argument('--app', type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(validate(args.binary, args.manifest, args.app), indent=2))
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        sys.exit(str(error))
