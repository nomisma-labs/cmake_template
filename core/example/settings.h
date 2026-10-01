// SPDX-FileCopyrightText: 2026 Alexey Tkachenko
// SPDX-License-Identifier: LicenseRef-Nomisma-Labs-Proprietary

#pragma once

#include <expected>
#include <filesystem>
#include <string>

namespace nom::example
{
    // A config-like aggregate. Its JSON mapping lives in settings_json.h, outside the module:
    // GCC 15 can't take nlohmann 3.12 through a module (cmake_template docs/lab/third_party_in_modules.md).
    struct settings
    {
        std::string name = "world";
        int repeat = 1;
    };

    [[nodiscard]] std::expected<settings, std::string> load_settings(const std::filesystem::path& path);
} // namespace nom::example
