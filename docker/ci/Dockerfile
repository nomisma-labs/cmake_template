# SPDX-FileCopyrightText: 2026 Alexey Tkachenko
# SPDX-License-Identifier: LicenseRef-Nomisma-Labs-Proprietary
#
# CI image for all Nomisma repos: the toolchain from docs/build.md. Built and published by
# .github/workflows/ci_image.yml.
FROM ubuntu:24.04

ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
 && apt-get install -y --no-install-recommends ca-certificates curl git gnupg python3 software-properties-common \
 && add-apt-repository -y ppa:ubuntu-toolchain-r/test \
 && curl -fsSL https://apt.kitware.com/keys/kitware-archive-latest.asc \
      | gpg --dearmor -o /usr/share/keyrings/kitware-archive-keyring.gpg \
 && echo "deb [signed-by=/usr/share/keyrings/kitware-archive-keyring.gpg] https://apt.kitware.com/ubuntu/ noble main" \
      > /etc/apt/sources.list.d/kitware.list \
 && apt-get update \
 && apt-get install -y --no-install-recommends \
      g++-15 cmake ninja-build \
      clang-19 clang-tools-19 clang-tidy-19 clang-format-19 clangd-19 \
      catch2 \
 && rm -rf /var/lib/apt/lists/*
