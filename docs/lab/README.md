# Lab

`cmake_template` is also the place to try build and C++ features before real repos rely on them.
Experiments live in `apps/sandbox/` (`python3 tools/add_sandbox_app.py <name>` adds one); findings
go here, one file per topic, with the compiler and CMake versions, the verdict and any workaround.
Build experiments with `cmake --workflow --preset complete`; for Clang use
`cmake --preset clang -DNOM_BUILD_PRESET=complete` and `cmake --build --preset clang`.
New repos don't get this folder.

Toolchain for all results below, unless noted: GCC 15.2, Clang 19.1.1, CMake 4.4.3, Ninja 1.11.1.

## Checklist

| # | Topic | Status | Where |
|---|---|---|---|
| 1 | Named modules: interfaces, partitions, implementation units, on GCC 15.2 and Clang 19 | Interfaces and partitions work on both; implementation units not tried yet | `apps/sandbox/native_module/` |
| 2 | Headers and modules side by side (wrapper module; `#include` and `import` users in one build) | Works on both compilers | `core/example/example.cppm`, `apps/hello/`, `tests/unit/example_import/` |
| 3 | Macros next to a module | Works: the macro header is included beside `import` | `core/example/macros.h` |
| 4 | Third-party headers in the global module fragment | **GCC 15 rejects nlohmann 3.12**; Clang 19 accepts it. Workaround in place. metal not tried yet. | [third_party_in_modules.md](third_party_in_modules.md) |
| 5 | Template-heavy code through a module (relay-like typelist dispatch on metal) | To do | |
| 6 | Installed modules: consumer builds its own BMIs from an installed package | Works on both compilers | `tests/integration/library_usage/` (`use_library_import`) |
| 7 | `import std;` (GCC 15 and CMake's experimental switch) | To do (optional) | |
| 8 | Inlining across module boundaries (hot path) | To do | |
| 9 | Tooling with modules: clangd, clang-tidy, gdb | clang-tidy works over module units with the Clang database; clangd and gdb to do | [toolchain.md](toolchain.md) |
| 10 | Build time: headers vs modules | To do | |
| 11 | Dependency mechanics: submodules + FetchContent, diamonds, standalone, source override | Submodule + FetchContent and consumption from source work; diamond superbuild and the `FETCHCONTENT_SOURCE_DIR_<NAME>` override to do | `tests/integration/library_usage/`, [third_party_in_modules.md](third_party_in_modules.md) |
| 12 | macOS (Homebrew LLVM) | To do | |
| 13 | C++26: pack indexing, static reflection | To do (later) | |

## Findings outside the checklist

- **GCC 15.2 crashes on `-fsanitize=undefined` with modules** (internal compiler error in
  `cp/module.cc` compiling the module interface). `-fsanitize=address` alone is fine, and Clang 19
  handles both, so the `asan` preset uses Clang. Retest with each GCC update. See [toolchain.md](toolchain.md).
- **Importers must include the std headers they use.** A module's global module fragment doesn't
  make those declarations visible to importers: comparing `std::string`s in a file that only
  imports `nom.example` fails until it includes `<string>`.
