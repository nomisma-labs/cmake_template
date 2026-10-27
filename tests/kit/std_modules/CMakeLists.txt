# SPDX-FileCopyrightText: 2026 Alexey Tkachenko
# SPDX-License-Identifier: LicenseRef-Nomisma-Labs-Proprietary

# Exercise std imports across interface, implementation and Catch2 consumer boundaries.
nom_lib(${PROJECT_NAME}_std_module_probe STATIC
    MODULES sequence.cppm
    SOURCES sequence.cpp
    BASE_DIR ${CMAKE_CURRENT_SOURCE_DIR})
nom_enable_std_modules(${PROJECT_NAME}_std_module_probe)

nom_c2test(std_modules
    SOURCES std_modules_test.cxx
    DEPS ${PROJECT_NAME}_std_module_probe
    LABELS kit)
nom_enable_std_modules(${PROJECT_NAME}_std_modules)
