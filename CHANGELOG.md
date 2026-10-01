# Changelog

Notable changes to this repo. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and versions follow [Semantic Versioning](https://semver.org); how to release:
[docs/build.md](docs/build.md#versioning).

## [Unreleased]

## [0.1.0] - 2026-10-02

### Fixed

- Leave `.template_ref` blank in the unhosted template and require a resolvable template
  commit before initializing a new repository.

### Added

- Use `*_test.cxx` for C++ unit and integration test sources so they can be selected separately
  from regular `*.cpp` sources; include `.cxx` in formatting and SPDX checks.

- Python environment check in bootstrap and CI: Python 3.10+, repository script syntax, and
  imported modules. Python-dependent steps are skipped on failure.

- Optional preset argument for `bootstrap.sh`, with available presets discovered through CMake
  and listed in `--help`. The default selects all matching configure/build/test names except
  `release`; cleanup is limited to the selected builds. CMake checks each preset's toolchain.

- `nom_app(... BUILD_FOR ...)` selects normal build/install participation; `any` is the default.
  The `complete` preset is a Debug build with every app, including sandbox experiments;
  bootstrap covers it. Excluded apps remain explicitly buildable.

- Discover Catch2 and enable testing at the project root before code directories, supporting
  both top-level and inline unit test suites.

- Separate `tests/unit/` and `tests/integration/`, with CTest labels for selecting either group;
  rename the library usage integration helper to `nom_library_usage_tests()`.

- `nom_app()` collects an adjacent `config/` directory into the build tree and installs it with the app executable.
- Name target helpers `nom_lib`, `nom_app` and `nom_c2test`, keeping the testing framework explicit.
- `bootstrap.sh`: clears prior validation builds/logs, initializes dependencies and runs fresh
  preset builds/tests and quality checks, with per-step
  results, logs, a final summary and next steps; included in template synchronization.
- The template: the CMake kit, presets, checks, CI and the CI image, agent files, and the recipes
  for adding code (`docs/howto.md`).
- The example code (library `example`, app `hello`, their tests, the library usage test project) and the lab.
- `tools/init_project.py`, which turns a copy of the template into an empty repo, and
  `tools/sync_template.py`, which keeps derived repos in step with the template.
