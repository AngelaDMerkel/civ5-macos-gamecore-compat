#!/usr/bin/env python3
"""Create a self-contained, hashed GameCore archive for Wir Schaffen DLC."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

sys.dont_write_bytecode = True
from validate import validate, sha256, ROOT

PRODUCTS = {
    'lekmod': 'https://github.com/AngelaDMerkel/Lekmod',
    'vox-populi': 'https://github.com/AngelaDMerkel/Community-Patch-DLL-macOS',
}
BINARY = 'libCvGameCoreDLL_Expansion2_DLL.dylib'


def inventory(root):
    files = {}
    for path in sorted(root.rglob('*')):
        if path.is_symlink():
            raise ValueError('payload symlinks are forbidden: ' + str(path))
        if path.is_file():
            relative = path.relative_to(root).as_posix()
            if '\n' in relative or '\r' in relative or '\\' in relative:
                raise ValueError('unsafe payload filename: ' + relative)
            files[relative] = sha256(path)
    return files


def tree_hash(files):
    return hashlib.sha256(''.join(f'{digest}  {name}\n' for name, digest in sorted(files.items())).encode()).hexdigest()


def package(args):
    if args.output.exists():
        raise ValueError('output already exists; choose a new archive path')
    validated = validate(args.binary)
    abi = json.loads((ROOT / 'abi/aspyr-bnw.json').read_text())
    source_commit = subprocess.check_output(['git', '-C', str(args.source_repo), 'rev-parse', 'HEAD'], text=True).strip()
    dirty = bool(subprocess.check_output(['git', '-C', str(args.source_repo), 'status', '--porcelain'], text=True).strip())
    compat_commit = subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip()
    destinations = {}
    with tempfile.TemporaryDirectory(prefix='civ5-release-') as temporary:
        stage = Path(temporary)
        shutil.copy2(args.binary, stage / BINARY)
        for value in args.payload:
            name, directory = value.split('=', 1)
            if not re.fullmatch(r'[A-Za-z0-9_-]+', name) or name in destinations:
                raise ValueError('invalid or duplicate payload destination')
            src = Path(directory)
            inventory(src)  # Reject symlinks before copytree follows them.
            if not src.is_dir() or not any(src.glob('*.Civ5Pkg')):
                raise ValueError('payload must be prepared DLC with a root .Civ5Pkg: ' + name)
            shutil.copytree(src, stage / 'payload' / name)
            destinations[name] = 'Contents/Assets/Assets/DLC/' + name
        license_dir = stage / 'licenses'
        license_dir.mkdir()
        for index, license_path in enumerate(args.license):
            shutil.copy2(license_path, license_dir / f'{index}-{license_path.name}')
        shutil.copy2(ROOT / 'LICENSE', license_dir / 'shared-compat-MIT.txt')
        shutil.copy2(ROOT / 'PROVENANCE.md', license_dir / 'shared-compat-PROVENANCE.md')
        files = inventory(stage)
        payload_files = {name: digest for name, digest in files.items() if name.startswith('payload/')}
        manifest = {
            'schema_version': 1, 'product': args.product, 'version': args.version,
            'source': {'repository': PRODUCTS[args.product], 'commit': source_commit, 'dirty': dirty},
            'compat': {'repository': 'https://github.com/AngelaDMerkel/civ5-macos-gamecore-compat', 'commit': compat_commit},
            'abi_id': abi['abi_id'], 'supported_stock_game_hashes': {
                'gamecore': abi['stock_gamecore_sha256'], 'executable': abi['host_executable_sha256']},
            'gamecore_sha256': validated['sha256'], 'payload_sha256': tree_hash(payload_files),
            'files': files, 'conflicts': [p for p in PRODUCTS if p != args.product],
            'destinations': {'gamecore': 'Contents/MacOS/' + BINARY, 'payload': destinations},
            'licenses': sorted(name for name in files if name.startswith('licenses/')),
            'runtime_validated': False,
        }
        (stage / 'manifest.json').write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n')
        sums = inventory(stage)
        (stage / 'SHA256SUMS').write_text(''.join(f'{digest}  {name}\n' for name, digest in sorted(sums.items())))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(args.output, 'x', compression=zipfile.ZIP_DEFLATED) as archive:
            for name in sorted(inventory(stage)):
                archive.write(stage / name, name)
    print(json.dumps({'archive': str(args.output.resolve()), 'sha256': sha256(args.output)}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--product', choices=PRODUCTS, required=True)
    parser.add_argument('--version', required=True)
    parser.add_argument('--source-repo', type=Path, required=True)
    parser.add_argument('--binary', type=Path, required=True)
    parser.add_argument('--payload', action='append', required=True, help='DLC_DIRECTORY=prepared_path')
    parser.add_argument('--license', type=Path, action='append', required=True)
    parser.add_argument('--output', type=Path, required=True)
    try:
        package(parser.parse_args())
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        sys.exit(str(error))
