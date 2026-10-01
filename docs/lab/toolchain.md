# Toolchain findings

Date: 2026-09-28. GCC 15.2.0 (toolchain PPA), Clang 19.1.1 (Ubuntu 24.04), CMake 4.4.3, Ninja 1.11.1.

## Modules build with both compilers

A CMake + Ninja project with a named module, a partition, a global module fragment and an exported
template builds and runs with `g++-15` and `clang++-19`. The template's own module build (wrapper
module, native module with a partition, installed-module consumer) passes on both.

## Sanitizers: GCC 15.2 crashes on UBSan with modules

| Flags on the module interface | GCC 15.2 | Clang 19 |
|---|---|---|
| `-fsanitize=address` | builds | builds |
| `-fsanitize=undefined` | internal compiler error (`cp/module.cc`, `tree_node`) | builds |
| `-fsanitize=address,undefined -fno-sanitize-recover=undefined` | internal compiler error | builds, tests pass |

The `asan` preset therefore uses Clang 19 with both sanitizers. Retest on each GCC update, and
consider a GCC `asan` preset (address only) if GCC-specific issues need sanitizing.

## compile_commands.json and clang tools

For the same file, the two compilers record different module flags:

```
g++-15:     g++-15 -std=c++23 -fmodules-ts -fmodule-mapper=…/main.cpp.o.modmap -fdeps-format=p1689r5 … -c main.cpp
clang++-19: clang++-19 -std=c++23 @…/main.cpp.o.modmap … -c main.cpp
```

clang-tidy-19 runs cleanly over all 12 translation units of the Clang database, module interface
units and importers included, once the `clang` preset has been built (the BMIs must exist).
`tools/check_naming.sh` does exactly that.

To do (checklist item 9): clangd-19 with `--experimental-modules-support` in VS Code, and gdb on
code that imports modules.
