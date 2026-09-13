#include "CvGameCoreDLLPCH.h"
#include "CvEnumSerialization.h"
#include "civ5/serialization.h"

static_assert(sizeof(FDataStream) == 24, "Aspyr x86_64 stream layout");

// The host exports Read(unsigned long long&) but no corresponding writer.
// Keep VP's 64-bit RNG state intact; unsigned long's host writer is only 32-bit.
void FDataStream::Write(const UINT64& value) {
  civ5_macos::WriteUInt64(*this, value);
}

// Additional fixed-width SDK overloads used by VP are not exported by Aspyr.
// The ABI is little-endian x86_64; GUID is the 16-byte Win32 field layout.
void FDataStream::Write(const INT64& value) {
  civ5_macos::WriteUInt64(*this, static_cast<std::uint64_t>(value));
}

void FDataStream::Read(INT64& value) {
  ReadIt(8, &value);
}

void FDataStream::Write(const GUID& value) {
  WriteIt(16, &value);
}

void FDataStream::Read(GUID& value) {
  ReadIt(16, &value);
}

void Database::Connection::Analyze() const {
  Execute("ANALYZE");
}

void Database::Connection::CommitTransaction() {
  Execute("COMMIT");
}

std::string FSerialization::toString(const unsigned char& value) {
  return toString(static_cast<unsigned int>(value));
}

// lua_isnumber and luaL_checknumber use the host's number conversion. Together
// they preserve lua_tonumber's zero result for non-numeric values.
extern "C" lua_Number lua_tonumber(lua_State* state, int index) {
  return lua_isnumber(state, index) ? luaL_checknumber(state, index) : 0;
}
namespace {
template <typename EnumType>
FDataStream& WriteEnum(FDataStream& stream, const EnumType& value) {
  stream << static_cast<int>(value);
  return stream;
}

template <typename EnumType>
FDataStream& ReadEnum(FDataStream& stream, EnumType& value) {
  int serialized_value = 0;
  stream >> serialized_value;
  value = static_cast<EnumType>(serialized_value);
  return stream;
}
}  // namespace

FDataStream& operator<<(FDataStream& stream, const ButtonPopupTypes& value) {
  return WriteEnum(stream, value);
}

FDataStream& operator>>(FDataStream& stream, ButtonPopupTypes& value) {
  return ReadEnum(stream, value);
}

FDataStream& operator<<(FDataStream& stream, const DiploUIStateTypes& value) {
  return WriteEnum(stream, value);
}

FDataStream& operator>>(FDataStream& stream, DiploUIStateTypes& value) {
  return ReadEnum(stream, value);
}

FDataStream& operator<<(FDataStream& stream,
                        const LeaderheadAnimationTypes& value) {
  return WriteEnum(stream, value);
}

FDataStream& operator>>(FDataStream& stream,
                        LeaderheadAnimationTypes& value) {
  return ReadEnum(stream, value);
}
