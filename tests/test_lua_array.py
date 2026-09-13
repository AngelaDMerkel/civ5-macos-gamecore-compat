"""Exercise the sequence adapter against a minimal Lua stack contract."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class LuaArrayTests(unittest.TestCase):
    def test_positive_negative_sparse_and_invalid_arguments_preserve_stack(self):
        # These are test doubles for public Lua API calls, not engine sources.
        declarations = '''#pragma once
#define LUA_REGISTRYINDEX (-10000)
#define LUA_TNIL 0
#define LUA_TTABLE 5
struct lua_State;
int lua_gettop(lua_State*);
void lua_settop(lua_State*, int);
void lua_rawgeti(lua_State*, int, int);
int lua_type(lua_State*, int);
void luaL_checktype(lua_State*, int, int);
int luaL_error(lua_State*, const char*, ...);
#define lua_isnil(L,i) (lua_type(L,i) == LUA_TNIL)
#define lua_pop(L,n) lua_settop(L, -(n)-1)
'''
        source = r'''
#include "civ5/lua_array.h"
#include <cassert>
#include <stdexcept>
#include <vector>
struct Value { int type; std::vector<bool> entries; };
struct lua_State { std::vector<Value> stack; };
int absolute(lua_State* L, int i) { return i > 0 ? i - 1 : int(L->stack.size()) + i; }
int lua_gettop(lua_State* L) { return int(L->stack.size()); }
void lua_settop(lua_State* L, int i) { L->stack.resize(i >= 0 ? i : int(L->stack.size()) + i + 1); }
int lua_type(lua_State* L, int i) { return L->stack.at(absolute(L, i)).type; }
void luaL_checktype(lua_State* L, int i, int expected) {
  if (lua_type(L, i) != expected) throw std::runtime_error("type");
}
int luaL_error(lua_State*, const char*, ...) { throw std::runtime_error("error"); }
void lua_rawgeti(lua_State* L, int i, int key) {
  const auto& entries = L->stack.at(absolute(L, i)).entries;
  bool exists = key > 0 && unsigned(key) <= entries.size() && entries[key-1];
  L->stack.push_back({exists ? 3 : LUA_TNIL, {}});
}
int main() {
  for (int count : {0, 1, 5, 100}) {
    lua_State state{{{3, {}}, {LUA_TTABLE, std::vector<bool>(count, true)}, {3, {}}}};
    assert(civ5_macos::LuaSequenceLength(&state, 2) == unsigned(count));
    assert(civ5_macos::LuaSequenceLength(&state, -2) == unsigned(count));
    assert(state.stack.size() == 3 && state.stack[0].type == 3 && state.stack[2].type == 3);
  }
  lua_State sparse{{{LUA_TTABLE, {true, true, false, true}}}};
  assert(civ5_macos::LuaSequenceLength(&sparse, 1) == 2);
  assert(sparse.stack.size() == 1);
  lua_State invalid{{{3, {}}}};
  bool rejected = false;
  try { civ5_macos::LuaSequenceLength(&invalid, 1); } catch (const std::runtime_error&) { rejected = true; }
  assert(rejected && invalid.stack.size() == 1);
}
'''
        with tempfile.TemporaryDirectory() as temporary:
            temporary = Path(temporary)
            (temporary / 'lua.h').write_text(declarations)
            (temporary / 'lauxlib.h').write_text('#include <lua.h>\n')
            (temporary / 'test.cpp').write_text(source)
            binary = temporary / 'test'
            subprocess.run(['clang++', '-std=c++11', '-fsanitize=address,undefined',
                            '-fno-sanitize-recover=all', '-I', str(temporary), '-I', str(ROOT / 'include'),
                            str(temporary / 'test.cpp'), '-o', str(binary)], check=True)
            subprocess.run([str(binary)], check=True)
