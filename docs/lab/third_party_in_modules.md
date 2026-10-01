# Third-party code with CMake and modules

Date: 2026-09-28. GCC 15.2.0, Clang 19.1.1, CMake 4.4.3.

## nlohmann_json in a module's global module fragment

**Result:** GCC 15.2 rejects a module interface whose global module fragment includes
`<nlohmann/json.hpp>`; Clang 19 accepts it.

GCC reports `… exposes TU-local entity …`: nlohmann defines helper functions `static` in its
headers (`detail::unescape`, `detail::little_endianness`, and on the development branch also
`detail::is_valid_utf8`), and templates that the module makes reachable use them. C++20 forbids
such exposures, and GCC 15 enforces the rule.

| nlohmann version | GCC 15.2 | Clang 19 |
|---|---|---|
| v3.12.0 (latest release, April 2025) | error | builds |
| develop at `373005f` (2026-09-27) | error (fewer helpers, still `is_valid_utf8`) | not tried |

Upstream: issue [#4759](https://github.com/nlohmann/json/issues/4759) and PR
[#4764](https://github.com/nlohmann/json/pull/4764) (C++20 modules support, on develop). nlohmann's
docs also report a separate GCC bug, "redefinition" errors when `nlohmann/json.hpp` is included in
a module preamble together with other imports, unresolved as of GCC 16
([modules page](https://json.nlohmann.me/features/modules/)). The development branch also adds
its own module (`NLOHMANN_JSON_BUILD_MODULES`, `import nlohmann.json;`).

**What the template does:** the nlohmann mapping of `settings` lives in `settings_json.h`, a
public header outside the module. `settings.h` (the type and `load_settings`) stays
nlohmann-free and is exported by `nom.example`. Files that import `nom.example` and need the JSON
mapping include `settings_json.h` before the import. nlohmann remains a public dependency, which
is the case the config repo has with `DEFINE_CONFIG`.

**For the config repo:** keep `config.h` (the `DEFINE_CONFIG` macros) a plain header; a wrapper
module must not include it until nlohmann works in a GCC module.

**Retest** when nlohmann releases after 3.12.0: move the submodule pin, put
`#include <example/settings_json.h>` into `core/example/example.cppm` and export `to_json`/`from_json`,
then build the `dev` preset.

## Third-party CMake projects as subprojects

**metal** (v2.1.4): running its CMake project through `FetchContent_MakeAvailable` adds about
2,100 targets with generic names (`example`, `bundle`, `doc`), looks for Doxygen and Boost, and
prints a deprecation warning under CMake 4.4. In a superbuild those names would collide. Since metal
is header-only, use it through its include directory and never run its CMake project; for example,
declare it with a `SOURCE_SUBDIR` that has no `CMakeLists.txt`, so FetchContent only records
the sources, and add `${metal_SOURCE_DIR}/include` to the target that needs it.

**nlohmann_json** (v3.12.0): works as a subproject. When it isn't the top-level project its tests
are off, and its install rules are off too unless `JSON_Install` is set, which the template does
(so an installed package brings nlohmann along for `find_package` consumers).

Other libraries: case by case.
