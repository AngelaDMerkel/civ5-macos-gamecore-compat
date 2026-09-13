# Provenance and scope

The six files in `include/` and the enum stream adapters in
`src/mac_compat.cpp` were extracted from AngelaDMerkel/Lekmod at local
checkpoint `0952b9e5c57e062ed4e849061ae0060718ae0946` (2026-09-13).
The independently authored macOS port first appeared in commits
`531680dd520b12fa6b5af371b9b86d428be132cf` and `4066dd92` by Colin Alexander
Duffy. This repository's MIT license covers that compatibility code and
the newly authored build, validation, bootstrap, and test infrastructure.

No Firaxis, Aspyr, Vox Populi, or Lekmod gameplay implementation or content
is included or relicensed here. Consumers retain their own source licenses.
The stream adapters reference consumer-provided SDK declarations; those
headers remain in the consumer repository. Lekmod rendering diagnostics
remain in Lekmod because their paths, output, and callers are product-specific.

`abi/` contains symbol names and metadata observed using `nm`, `otool`,
and SHA-256 on the locally installed Aspyr Steam application. It contains
no executable bytes. The stock SHA-256 identifies the previously retained
stock GameCore, not the active custom dylib. `system-imports.txt` is a finite
list of additional libc++/libSystem imports used by the working Lekmod build;
there are no wildcard exemptions. Adding imports requires explicit review.

Local checkpoint records under `docs/local-*.json` are ignored and are not
part of the distributable repository. No proprietary binary is distributed.
