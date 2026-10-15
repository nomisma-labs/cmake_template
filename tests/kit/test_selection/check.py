#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Alexey Tkachenko
# SPDX-License-Identifier: LicenseRef-Nomisma-Labs-Proprietary
"""Check that NOM_SKIP_TEST_LABELS leaves labeled tests out of every ctest run in a build tree."""

import argparse
import json
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory


def run(*args: str) -> str:
    result = subprocess.run(args, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(f"{' '.join(args)}\n{result.stdout}\n{result.stderr}")
    return result.stdout


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('cmake', 'ctest', 'compiler', 'generator', 'kit'):
        parser.add_argument(f'--{name}', required=True)
    args = parser.parse_args()

    with TemporaryDirectory(prefix='nomisma-test-selection-') as temporary:
        root = Path(temporary)
        source, build = root / 'source', root / 'build'
        (source / 'child').mkdir(parents=True)
        # Tests in two directories: labeled, with two labels, and unlabeled.
        (source / 'CMakeLists.txt').write_text(f'''cmake_minimum_required(VERSION 3.30)
project(selection LANGUAGES CXX)
include("{Path(args.kit).resolve().as_posix()}/nom_kit.cmake")
nom_project_options()
enable_testing()
add_test(NAME fast COMMAND "${{CMAKE_COMMAND}}" -E true)
set_tests_properties(fast PROPERTIES LABELS unit)
add_test(NAME unlabeled COMMAND "${{CMAKE_COMMAND}}" -E true)
add_subdirectory(child)
''')
        (source / 'child/CMakeLists.txt').write_text('''add_test(NAME consumer COMMAND "${CMAKE_COMMAND}" -E true)
set_tests_properties(consumer PROPERTIES LABELS integration)
add_test(NAME tooling COMMAND "${CMAKE_COMMAND}" -E true)
set_tests_properties(tooling PROPERTIES LABELS "kit;python_package")
''')
        everything = {'fast', 'unlabeled', 'consumer', 'tooling'}
        # Reconfiguring the same build tree changes the selection both ways.
        for skipped, expected in (('integration;kit', {'fast', 'unlabeled'}), ('', everything),
                                  ('kit', everything - {'tooling'})):
            run(args.cmake, '-S', str(source), '-B', str(build), '-G', args.generator,
                f'-DCMAKE_CXX_COMPILER={args.compiler}', f'-DNOM_SKIP_TEST_LABELS={skipped}')
            listing = json.loads(run(args.ctest, '--test-dir', str(build), '--show-only=json-v1'))
            names = {test['name'] for test in listing['tests']}
            assert names == expected, f'NOM_SKIP_TEST_LABELS={skipped!r} selected {sorted(names)}'
            run(args.ctest, '--test-dir', str(build), '--no-tests=error')
            print(f'PASS: NOM_SKIP_TEST_LABELS={skipped!r} runs {", ".join(sorted(expected))}')


if __name__ == '__main__':
    main()
