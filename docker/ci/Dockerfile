# SPDX-FileCopyrightText: 2026 Alexey Tkachenko
# SPDX-License-Identifier: LicenseRef-Nomisma-Labs-Proprietary
#
# CI image for all Nomisma repos: the toolchain from docs/kit/build.md. Built and published by
# .github/workflows/ci_image.yml.
FROM ubuntu:26.04

ARG DEBIAN_FRONTEND=noninteractive
# CMake comes from Kitware's apt repository at the version docs/kit/build.md records; cmake_template's
# toolchain report names a difference between this pin and the CMake installed where it runs.
ARG CMAKE_VERSION=4.4.4-0kitware1ubuntu26.04.1

# Kitware's archive key. apt reads an ASCII-armored key from a .asc file.
ADD https://apt.kitware.com/keys/kitware-archive-latest.asc /usr/share/keyrings/kitware-archive-keyring.asc

# ADD leaves the key readable by root only, but apt's _apt user must read it. The base image has no
# CA certificates, which Kitware's https repository needs.
RUN chmod 644 /usr/share/keyrings/kitware-archive-keyring.asc \
 && apt-get update \
 && apt-get install -y --no-install-recommends ca-certificates \
 && printf '%s\n' 'Types: deb' 'URIs: https://apt.kitware.com/ubuntu/' 'Suites: resolute' 'Components: main' \
      'Signed-By: /usr/share/keyrings/kitware-archive-keyring.asc' > /etc/apt/sources.list.d/kitware.sources \
 && apt-get update \
 && apt-get install -y --no-install-recommends \
      git python3 python3-venv python3-dev \
      g++-16 cmake=${CMAKE_VERSION} cmake-data=${CMAKE_VERSION} ninja-build \
      clang-19 clang-tools-19 clang-tidy-19 clang-format-19 clangd-19 \
      catch2 libboost-log-dev libboost-iostreams-dev libboost-filesystem-dev \
      libboost-thread-dev libboost-date-time-dev libboost-program-options-dev libboost-url-dev \
      libssl-dev libfmt-dev nlohmann-json3-dev zlib1g-dev capnproto libcapnp-dev \
 && cmake --version \
 && rm -rf /var/lib/apt/lists/*
