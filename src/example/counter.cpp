// SPDX-FileCopyrightText: 2026 Alexey Tkachenko
// SPDX-License-Identifier: MIT

module nom.example;

import std;

namespace nom::example
{
    void counter::increment() noexcept
    {
        ++count_;
    }

    void counter::reset() noexcept
    {
        count_ = 0;
    }

    std::int64_t counter::value() const noexcept
    {
        return count_;
    }
} // namespace nom::example
