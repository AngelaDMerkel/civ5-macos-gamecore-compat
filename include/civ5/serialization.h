#pragma once
#include <cstdint>

namespace civ5_macos {
// Aspyr's unsigned-long-long reader consumes eight raw bytes. Native Civ V
// saves use little-endian x86_64 values, independently of LP64 unsigned long.
template<class Stream>
inline void WriteUInt64(Stream& stream, std::uint64_t value) {
  unsigned char bytes[8];
  for (unsigned i = 0; i < 8; ++i)
    bytes[i] = static_cast<unsigned char>(value >> (i * 8));
  stream.WriteIt(8, bytes);
}
}
