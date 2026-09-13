#!/usr/bin/env python3
"""Parameterized x86_64 GameCore builder. No installation side effects."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import threading

ROOT = Path(__file__).resolve().parents[1]


def output(*args):
    return subprocess.check_output(args, text=True).strip()


def build(config_path, jobs, incremental):
    config_path = config_path.resolve()
    config = json.loads(config_path.read_text())
    def path(value):
        return (config_path.parent / value).resolve()
    source, sdk, destination = (path(config[k]) for k in ['source_dir', 'sdk_dir', 'output_dir'])
    product = config['product']
    object_dir = destination / 'objects-shared'
    object_dir.mkdir(parents=True, exist_ok=True)
    compiler = os.environ.get('CXX', 'clang++')
    flags = ['-target', 'x86_64-apple-macos10.11.6', '-std=c++11', '-fms-extensions',
             '-fdeclspec', '-fdelayed-template-parsing', '-fvisibility=hidden',
             '-stdlib=libc++', '-O2', '-DNDEBUG', '-DFINAL_RELEASE', '-DFXS_IS_DLL',
             '-DWIN32', '-D_WIN64', '-D_WINPC', '-D_WINDOWS', '-D_USRDLL',
             '-DCVGAMECOREDLL_EXPORTS', '-D_CRT_SECURE_NO_WARNINGS', '-DAUI_VC120_FORMALITIES',
             '-Wno-deprecated-declarations', '-Wno-ignored-attributes', '-Wno-macro-redefined',
             '-Wno-microsoft-pure-definition', '-Wno-nonportable-include-path', '-Wno-unused-value',
             '-Werror=pointer-to-int-cast']
    for include in [ROOT / 'include', source, sdk / 'CvWorldBuilderMap/include',
                    sdk / 'CvGameCoreDLLUtil/include', sdk / 'CvLocalization/include',
                    sdk / 'CvGameDatabase/include', sdk / 'FirePlace/include',
                    sdk / 'FirePlace/include/FireWorks', sdk / 'ThirdPartyLibs/Lua51/include']:
        flags += ['-I', str(include)]
    flags += ['-include', 'Windows.h', '-include', 'FireWorks/FMemHooks.h']
    flags += config.get('extra_flags', [])
    sources = [ROOT / 'src/mac_compat.cpp'] + [path(p) for p in config.get('extra_sources', [])]
    sources += sorted(p for p in source.glob('*.cpp') if p.name != '_precompile.cpp')
    sources += sorted((source / 'Lua').glob('*.cpp'))
    if not (source / 'CvGameCoreDLL.cpp').is_file():
        raise ValueError('missing GameCore source directory')
    toolchain = output(compiler, '--version')
    fingerprint = hashlib.sha256(json.dumps([flags, toolchain, config], sort_keys=True).encode()).hexdigest()
    recipe = object_dir / 'recipe.sha256'
    reuse = incremental and recipe.exists() and recipe.read_text() == fingerprint
    # Write the recipe only after a successful build. An interrupted flag change
    # cannot cause old objects to be reused under a new recipe.
    if recipe.exists() and not reuse:
        recipe.unlink()

    failed = threading.Event()

    def compile_one(src):
        if failed.is_set():
            return None
        key = hashlib.sha256(str(src).encode()).hexdigest()[:16]
        obj = object_dir / (src.stem + '-' + key + '.o')
        dep = obj.with_suffix('.d')
        current = False
        if reuse and obj.exists() and dep.exists():
            dependencies = shlex.split(dep.read_text().replace('\\\n', ' ').split(':', 1)[1])
            current = all(Path(d).is_file() and Path(d).stat().st_mtime_ns <= obj.stat().st_mtime_ns for d in dependencies)
        if not current:
            print('CXX ' + src.name, flush=True)
            temporary = obj.with_suffix('.tmp.o')
            process = subprocess.run([compiler, *flags, '-MMD', '-MF', str(dep),
                                      '-c', str(src), '-o', str(temporary)], capture_output=True, text=True)
            if process.returncode:
                failed.set()
                temporary.unlink(missing_ok=True)
                raise RuntimeError(src.name + '\n' + process.stdout + process.stderr)
            temporary.replace(obj)
        return obj

    with ThreadPoolExecutor(max_workers=jobs) as pool:
        objects = list(pool.map(compile_one, sources))
    binary = destination / 'libCvGameCoreDLL_Expansion2_DLL.dylib'
    temporary = binary.with_suffix('.tmp.dylib')
    subprocess.run([compiler, '-target', 'x86_64-apple-macos10.11.6', '-dynamiclib',
                    '-undefined', 'dynamic_lookup', '-install_name', '/' + binary.name,
                    '-compatibility_version', '1.0.0', '-current_version', '1.0.0',
                    '-Wl,-exported_symbol,_DllGetGameContext', *map(str, objects), '-o', str(temporary)], check=True)
    # Do not replace an existing good binary when ABI validation fails.
    subprocess.run([sys.executable, str(ROOT / 'tools/validate.py'), '--binary', str(temporary)], check=True)
    temporary.replace(binary)
    recipe.write_text(fingerprint)
    report = {'product': product, 'compiler': toolchain, 'sources': len(sources),
              'compat_commit': output('git', '-C', str(ROOT), 'rev-parse', 'HEAD'),
              'source_commit': output('git', '-C', str(source), 'rev-parse', 'HEAD'),
              'source_dirty': bool(output('git', '-C', str(source), 'status', '--porcelain')),
              'binary_sha256': hashlib.sha256(binary.read_bytes()).hexdigest(), 'flags': flags}
    (destination / 'build-report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(binary)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--jobs', type=int, default=min(4, os.cpu_count() or 1))
    parser.add_argument('--incremental', action='store_true')
    args = parser.parse_args()
    if args.jobs < 1:
        parser.error('--jobs must be positive')
    try:
        build(args.config, args.jobs, args.incremental)
    except (ValueError, OSError, RuntimeError, subprocess.CalledProcessError) as error:
        sys.exit(str(error))
