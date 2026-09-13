# Civ V macOS GameCore compatibility

Shared build and ABI support for **separate** native Lekmod and Vox Populi
GameCores. This repository contains no gameplay source, content payload,
game binary, or installer. Wir Schaffen DLC owns installation and switching.

Consumers commit `compat.lock.json` and a copy of `tools/bootstrap.py`.
The lock specifies an exact 40-character Git commit. Bootstrap verifies
the checkout and tracked/untracked file state before allowing a build.
For local work use `CIV5_COMPAT_SOURCE=/path/to/civ5-macos-gamecore-compat`;
bootstrap creates an isolated, detached checkout of the locked commit.
It never builds directly from a mutable sibling working tree.
Without the override it fetches the exact commit from the lock's repository.
The future remote must be published before remote bootstrap or CI can work.

```sh
python3 tools/build.py --config /path/to/consumer/macos/build.json --jobs 4
python3 tools/validate.py --binary /path/to/output/libCvGameCoreDLL_Expansion2_DLL.dylib
python3 -m unittest discover -s tests -v
```

Build paths in a consumer configuration are relative to that file. Headers
and compiler/config changes invalidate incremental objects. Output names are
derived from complete source paths to avoid basename collisions. Builds write
a provenance report including source, dependency revision, and toolchain.

The validator checks the exact architecture, export set, deployment target,
install name, dylib versions, and a finite stock/host/system import allowlist.
`--app` additionally verifies the host executable against the ABI manifest.
Neither builds nor validation write to the installed game.

See [ABI contract](docs/abi.md) and [provenance](PROVENANCE.md).
