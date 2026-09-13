#pragma once
#include <lua.h>
#include <lauxlib.h>
#include <climits>
#include <cstddef>

namespace civ5_macos {
// Length for the sequence-valued arguments used by VP's Lua bindings.
// For sparse tables the first border is a valid Lua 5.1 length. Unlike a
// general lua_objlen replacement this API explicitly requires a table.
inline std::size_t LuaSequenceLength(lua_State* state, int index) {
  luaL_checktype(state, index, LUA_TTABLE);
  if (index < 0 && index > LUA_REGISTRYINDEX)
    index += lua_gettop(state) + 1;
  for (int length = 0; length < INT_MAX; ++length) {
    lua_rawgeti(state, index, length + 1);
    const bool at_end = lua_isnil(state, -1);
    lua_pop(state, 1);
    if (at_end) return static_cast<std::size_t>(length);
  }
  luaL_error(state, "Lua sequence exceeds supported integer indices");
  return 0;
}
}
