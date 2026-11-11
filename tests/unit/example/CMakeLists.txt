# SPDX-FileCopyrightText: 2026 Alexey Tkachenko
# SPDX-License-Identifier: MIT

nom_c2test(tests IMPORT_STD
    SOURCES
        counter_test.cxx
        join_test.cxx
        settings_test.cxx
    DEPS nom::example)
