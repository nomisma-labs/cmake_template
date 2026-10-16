# Toolchain findings

Supported tools and versions are recorded in [Build: Toolchain](../kit/build.md#toolchain).
The presets use GCC 16 for normal builds and Clang 19 for the second compiler and sanitizers.

## Keeping the toolchain current

The template moves to new compilers and dependency releases first, and every repo follows it.
`./bootstrap.sh` here ends with two reports, recorded as a `NOTE` when something is newer:

- `Dependency updates`, which every repo runs: its git submodules against their upstream releases
  ([build.md](../kit/build.md#dependencies)).
- `Toolchain updates`, from `tools/toolchain_updates.py`, here only: the compilers and Boost
  against apt's packages, and the Catch2 download and the installed CMake against their releases.

```text
[PASS] Dependency updates — Current: nlohmann_json v3.12.0
[NOTE] Toolchain updates — Newer: Clang 22, Catch2 v3.16.1, CMake v4.4.4; build/bootstrap/…/step-24.log
```

The log lists each finding and, for a compiler, the files that name its current version. Run
`python3 tools/toolchain_updates.py` on its own for the same report; `sudo apt update` first
refreshes what apt knows. When a note appears, or at least once a month:

1. Try the new version beside the current one, in a personal preset in `CMakeUserPresets.json`:
   ```json
   {
     "version": 6,
     "configurePresets": [
       { "name": "clang22", "inherits": "clang", "cacheVariables": { "CMAKE_CXX_COMPILER": "clang++-22" } }
     ],
     "buildPresets": [{ "name": "clang22", "configurePreset": "clang22" }],
     "testPresets": [{ "name": "clang22", "inherits": "base", "configurePreset": "clang22" }]
   }
   ```
   `./bootstrap.sh clang22` builds and tests it. A new clang-format can reformat code in every
   repo: `CLANG_FORMAT=clang-format-22 tools/kit/checks/format.sh` shows the difference, and
   `RUN_CLANG_TIDY=run-clang-tidy-22` runs the naming check with the new clang-tidy.
2. Record the verdict and any workaround here, with the versions, as the findings below do.
3. To adopt it, change the files the report lists (presets, bootstrap, checks, the CI image and
   the [toolchain table](../kit/build.md#toolchain)), run `./bootstrap.sh`, and release with an
   `### Upgrade` step that names the packages to install. The CI image rebuilds when its
   Dockerfile changes on `master`; the other repos get the change through their next sync.

To stay on a version for now, note why here; the report keeps listing the newer one.

## Native modules

The `nom.example` primary interface, exported partitions, implementation units and importing
apps and tests build on GCC 16 and Clang 19. Library usage tests cover both source and installed
package consumption; installed consumers build their own compiler-specific BMIs. The sandbox
geometry module exercises a native interface and partition with the `complete` preset.

Run the current module builds and tests from the template root:

```bash
cmake --workflow --preset dev
cmake --workflow --preset clang
cmake --workflow --preset complete
```

## Sanitizers

The `asan` preset uses Clang 19 with AddressSanitizer and UBSan:
`-fsanitize=address,undefined -fno-sanitize-recover=undefined -fno-omit-frame-pointer`.
It covers the native-module example and importing consumers.

```bash
cmake --workflow --preset asan
```

## Third-party module boundaries

The [third-party findings](third_party_in_modules.md) cover the GCC 16 warning when exporting a
nlohmann JSON alias and the tested Metal typelist alias on GCC 16 and Clang 19. JSON stays private
to the settings implementation; the exported typelist alias uses the standard library since Metal
moved to assembly.

## compile_commands.json and clang tools

The `dev` and `clang` presets generate compilation databases. For the same importing source,
`apps/hello/main.cpp`, the compilers record different module flags (other options omitted):

```text
g++-16 -std=c++23 -fmodules-ts -fmodule-mapper=…/main.cpp.o.modmap -fdeps-format=p1689r5 … -c main.cpp
clang++-19 -std=c++23 @…/main.cpp.o.modmap … -c main.cpp
```

Use `build/clang/compile_commands.json` for Clang tools; the GCC database contains module flags
they cannot use. `.clangd` selects the Clang database for the editor.

`tools/kit/checks/naming.sh` configures the `clang` preset with `-DNOM_BUILD_PRESET=complete`, then
builds it so that module BMIs are available, including those used by sandbox apps. It runs
`run-clang-tidy-19` over the native module units and importers in `core/`, `apps/` and `tests/`
using that database. The naming check passes for the current native-module example and
generated-repository recipe.

clangd-19 with `--experimental-modules-support` in VS Code, and gdb on importing code, remain
checklist items to validate.
