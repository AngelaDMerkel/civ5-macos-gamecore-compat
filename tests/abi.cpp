#include "Windows.h"
#include "tchar.h"
#include <cassert>
#include <thread>
#include <vector>

static_assert(sizeof(void*) == 8, "Aspyr requires 64-bit pointers");
static_assert(sizeof(DWORD) == 4 && sizeof(LONG) == 4 && sizeof(ULONG) == 4,
              "Win32 integer widths must survive LP64");
static_assert(sizeof(GUID) == 16 && alignof(GUID) == 4, "GUID ABI");
static_assert(sizeof(FILETIME) == 8 && sizeof(SYSTEMTIME) == 16, "time ABI");
static_assert(sizeof(POINT) == 8 && sizeof(LARGE_INTEGER) == 8, "integer ABI");
static_assert(sizeof(TCHAR) == 1 && sizeof(wchar_t) == 4, "Aspyr character ABI");

int main() {
  volatile LONG counter = 0;
  std::vector<std::thread> threads;
  for (int i = 0; i < 4; ++i) threads.emplace_back([&counter] {
    for (int n = 0; n < 10000; ++n) InterlockedIncrement(&counter);
  });
  for (auto& thread : threads) thread.join();
  assert(counter == 40000);
  assert(InterlockedCompareExchange(&counter, 2, 40000) == 40000);
  assert(InterlockedExchangeAdd(&counter, -1) == 2 && counter == 1);
  FILETIME low = {0xffffffffu, 0}, high = {0, 1};
  assert(CompareFileTime(&low, &high) == -1);
  assert(CompareFileTime(&high, &low) == 1);
  assert(CompareFileTime(&high, &high) == 0);
  char word[] = "AbCd";
  assert(std::strcmp(_strrev(word), "dCbA") == 0);
  assert(std::strcmp(_strlwr(word), "dcba") == 0);
  assert(_stricmp("aBc", "ABC") == 0);
}
