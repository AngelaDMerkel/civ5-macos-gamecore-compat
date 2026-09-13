# Aspyr BNW ABI contract

Identifier: `aspyr-civ5-bnw-x86_64-10.11.6-v1`.

The host is x86_64, using libc++ and the Clang/Itanium C++ ABI. Apple Silicon
executes it through Rosetta. The deployment target is macOS 10.11.6, install
name `/libCvGameCoreDLL_Expansion2_DLL.dylib`, and both dylib versions 1.0.0.
The sole public export is `_DllGetGameContext`.

Consumer source must retain ABI-sensitive SDK adjustments locally:

* Aspyr's `ICvPreGame1::smtpHost` vtable slot belongs immediately after
  `era`, before `findPlayerByNickname`.
* Legacy TR1 layout padding: `Database::Connection` 184 bytes,
  `Database::Results` 112 bytes, `Database::ResultsCache` 80 bytes.
* Pointer arithmetic and allocation alignment use pointer-width integers.
* RNG state serialized through FDataStream unsigned-long overloads must
  preserve the engine's 32-bit stream representation on LP64.
* VP uses an independent 64-bit RNG. The host exports
  `FDataStream::Read(unsigned long long&)`, which reads eight raw bytes, but
  lacks the corresponding exported writer. The shared writer emits eight
  little-endian bytes through WriteIt, preserving VP's complete RNG state.
  FDataStream is 24 bytes on x86_64. These observations were checked by static
  disassembly of the recorded host; the application was not launched.
  Signed 64-bit and GUID read/write overloads absent from the host use the
  same fixed-width stream interface: 8-byte integers and 16-byte GUIDs.
  Their encoding is specific to the little-endian x86_64 ABI. Save-file
  compatibility still needs the separate runtime/save-load validation gate.
* SDK long typedefs and overloads require explicit platform choices.

The consumer static assertions are essential; aliases to modern unordered
containers alone do not establish binary compatibility. Passing these checks
does not establish gameplay, save, or UI correctness. Runtime testing is a
separate, explicitly authorized stage.
