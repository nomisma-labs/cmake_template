#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Alexey Tkachenko
# SPDX-License-Identifier: LicenseRef-Nomisma-Labs-Proprietary
"""Reports compilers and dependencies newer than the ones cmake_template uses.

    python3 tools/toolchain_updates.py

cmake_template moves the toolchain first, so ./bootstrap.sh runs this template-only script and
shows its result as a note; docs/lab/toolchain.md#keeping-the-toolchain-current is what to do
about it. The script reads what the repo uses from the presets, the kit and the submodules, and
compares it with:

- Ubuntu packages, from apt's package lists: newer g++-N and clang-N packages than the presets
  name, a newer Boost than the one installed, and newer candidates for installed toolchain packages;
- upstream release tags, through git ls-remote: each git submodule, the Catch2 release the kit
  downloads where Catch2 isn't installed, and CMake. Without a network these are reported unchecked.

The last line of output is a summary. Exit status: 0 when nothing is newer, 3 when something is,
1 on errors.
"""

import json
import os
import re
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NEWER = 3  # exit status when something is newer
APT_UPDATED = Path("/var/lib/apt/periodic/update-success-stamp")
CMAKE_REPOSITORY = "https://github.com/Kitware/CMake.git"
RELEASE_TAG = re.compile(r"v?(\d+(?:\.\d+)+)")  # v3.12.0 or 4.4.3; never v4.5.0-rc1

Version = tuple[int, ...]


def output(*command: str, timeout: float | None = None) -> str:
    environment = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}  # a remote must never wait for a password
    return subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=True,
                          timeout=timeout, env=environment).stdout


def version(text: str) -> Version:
    return tuple(int(part) for part in text.split("."))


def dotted(numbers: Version) -> str:
    return ".".join(map(str, numbers))


def upstream(package_version: str) -> str:
    """A Debian version without its epoch and revision: 1:22.1.2-1ubuntu1 is 22.1.2."""
    return re.sub(r"^\d+:", "", package_version).rsplit("-", 1)[0]


def preset_compilers() -> dict[str, int]:
    """The oldest major version of each compiler the presets name: {'g++': 16, 'clang++': 19}."""
    presets = json.loads((ROOT / "cmake/kit/presets.json").read_text())
    majors: dict[str, int] = {}
    for preset in presets["configurePresets"]:
        compiler = preset.get("cacheVariables", {}).get("CMAKE_CXX_COMPILER", "")
        if match := re.fullmatch(r"(g\+\+|clang\+\+)-(\d+)", compiler):
            majors[match[1]] = min(int(match[2]), majors.get(match[1], int(match[2])))
    return majors


def files_naming(pattern: re.Pattern[str]) -> list[str]:
    """The tracked files that mention pattern, except the changelog's history."""
    names = output("git", "ls-files").splitlines()
    return [name for name in names if name != "CHANGELOG.md" and (ROOT / name).is_file()
            and pattern.search((ROOT / name).read_text(errors="ignore"))]


class Report:
    def __init__(self) -> None:
        self.newer: list[str] = []
        self.unchecked: list[str] = []

    def line(self, status: str, text: str) -> None:
        print(f"  {status:<10}{text}")

    def update(self, summary: str, text: str, *details: str) -> None:
        self.newer.append(summary)
        self.line("newer", text)
        for detail in details:
            self.line("", detail)


def apt_versions(prefix: str, pattern: str) -> list[Version]:
    """The versions in the names of the packages apt knows that match pattern, oldest first."""
    names = output("apt-cache", "pkgnames", prefix).split()
    return sorted(version(match[1]) for name in names if (match := re.fullmatch(pattern, name)))


def apt_policy(*packages: str) -> dict[str, tuple[str | None, str | None]]:
    """The installed and candidate versions of each package apt knows; None where it has none."""
    versions: dict[str, tuple[str | None, str | None]] = {}
    name = None
    for line in output("apt-cache", "policy", *packages).splitlines():
        if not line.startswith(" ") and line.endswith(":"):
            name = line[:-1]
        elif name and (match := re.match(r"\s+(Installed|Candidate): (\S+)", line)):
            installed, candidate = versions.get(name, (None, None))
            value = None if match[2] == "(none)" else match[2]
            versions[name] = (value, candidate) if match[1] == "Installed" else (installed, value)
    return versions


def check_compiler(report: Report, name: str, package: str, pinned: int, mentions: str) -> None:
    """Report packages of a newer major version than the presets name, such as clang-22.

    mentions matches the ways files name the pinned version, to list the files an update changes.
    """
    majors = [major for (major,) in apt_versions(f"{package}-", rf"{re.escape(package)}-(\d+)")]
    newer = [major for major in majors if major > pinned]
    candidates = apt_policy(*(f"{package}-{major}" for major in [pinned, *newer]))
    newer = [major for major in newer if candidates.get(f"{package}-{major}", (None, None))[1]]
    if not newer:
        installed = candidates.get(f"{package}-{pinned}", (None, None))[0]
        report.line("current", f"{name} {pinned}, the newest {package} package"
                    + (f" ({package}-{pinned} {upstream(installed)} installed)" if installed else ""))
        return
    newest = f"{package}-{newer[-1]}"
    files = files_naming(re.compile(mentions))
    report.update(f"{name} {newer[-1]}",
                  f"{name}: the presets use {pinned}; Ubuntu packages {', '.join(map(str, newer))} "
                  f"({newest} {upstream(candidates[newest][1] or '')})",
                  f"files naming {name} {pinned}: {', '.join(files)}")


def check_packages(report: Report, compilers: dict[str, int]) -> None:
    if not shutil.which("apt-cache"):
        report.unchecked.append("Ubuntu packages")
        print("Ubuntu packages: not checked, apt-cache is missing")
        return
    stamp = APT_UPDATED if APT_UPDATED.exists() else Path("/var/lib/apt/lists")
    days = int((time.time() - stamp.stat().st_mtime) // 86400)
    updated = time.strftime("%Y-%m-%d", time.localtime(stamp.stat().st_mtime))
    print(f"Ubuntu packages (apt package lists from {updated}"
          + (f", {days} days old; sudo apt update refreshes them)" if days > 7 else ")"))
    if gcc := compilers.get("g++"):
        check_compiler(report, "GCC", "g++", gcc, rf"\bg\+\+-{gcc}\b|\bgcc-{gcc}\b|\bGCC {gcc}\b")
    if clang := compilers.get("clang++"):
        # clang-19, clang++-19, clangd-19, clang-tidy-19, run-clang-tidy-19 and so on.
        check_compiler(report, "Clang", "clang", clang, rf"\bclang[a-z+-]*-{clang}\b|\bClang {clang}\b")

    boost = apt_versions("libboost1.", r"libboost(1\.\d+)-dev")
    installed = apt_policy("libboost-dev").get("libboost-dev", (None, None))[0]
    if boost and installed:
        current = version(".".join(upstream(installed).split(".")[:2]))
        if boost[-1] > current:
            report.update(f"Boost {dotted(boost[-1])}",
                          f"Boost: {dotted(current)} installed; Ubuntu packages {dotted(boost[-1])} "
                          f"(libboost{dotted(boost[-1])}-dev)")
        else:
            report.line("current", f"Boost {dotted(current)}, the newest Boost package")

    # The installed packages of the toolchain table in docs/kit/build.md.
    tools = [f"g++-{gcc}"] if gcc else []
    if clang:
        tools += [f"{tool}-{clang}" for tool in ("clang", "clang-tools", "clang-tidy", "clang-format", "clangd")]
    tools += ["cmake", "ninja-build", "catch2", "libboost-dev", "python3"]
    upgrades = [f"{name} {upstream(installed)} -> {upstream(candidate)}"
                for name, (installed, candidate) in apt_policy(*tools).items()
                if installed and candidate and installed != candidate]
    if upgrades:
        report.update("apt upgrades", f"apt upgrades for installed tools: {'; '.join(upgrades)}")
    else:
        report.line("current", "installed tools match apt's candidates (" + ", ".join(tools) + ")")


def release_tags(url: str) -> dict[Version, tuple[str, str]]:
    """The release tags of a remote repository: version -> (tag, commit)."""
    commits: dict[str, str] = {}
    versions: dict[Version, str] = {}
    for line in output("git", "ls-remote", "--tags", url, timeout=30).splitlines():
        sha, ref = line.split("\t")
        name = ref.removeprefix("refs/tags/")
        peeled = name.endswith("^{}")  # an annotated tag's commit follows the tag itself
        name = name.removesuffix("^{}")
        if match := RELEASE_TAG.fullmatch(name):
            if peeled or name not in commits:
                commits[name] = sha
            versions[version(match[1])] = name
    return {number: (name, commits[name]) for number, name in versions.items()}


def check_upstream(report: Report) -> None:
    print("Upstream releases (git ls-remote)")
    checks = []  # (label, url, how the repo uses it: a recorded commit or a version)
    if (ROOT / ".gitmodules").exists():
        entries = output("git", "config", "--file", ".gitmodules", "--get-regexp",
                         r"^submodule\..*\.(path|url)$").splitlines()
        settings = dict(entry.split(" ", 1) for entry in entries)
        for key, path in settings.items():
            if key.endswith(".path"):
                url = settings[key.removesuffix(".path") + ".url"]
                commit = output("git", "ls-files", "--stage", "--", path).split()[1]
                checks.append((f"{Path(path).name} ({path})", url, commit))
    catch2 = (ROOT / "cmake/kit/deps/catch2.cmake").read_text()
    if (url := re.search(r"GIT_REPOSITORY\s+(\S+)", catch2)) and (tag := re.search(r"GIT_TAG\s+(\S+)", catch2)):
        checks.append(("Catch2 download (cmake/kit/deps/catch2.cmake)", url[1], tag[1]))
    if cmake := shutil.which("cmake"):
        installed = re.search(r"cmake version (\d+(?:\.\d+)+)", output(cmake, "--version"))
        if installed:
            checks.append(("CMake installed", CMAKE_REPOSITORY, installed[1]))

    with ThreadPoolExecutor() as pool:
        futures = [pool.submit(release_tags, url) for _, url, _ in checks]
    for (label, _, used), future in zip(checks, futures):
        try:
            tags = future.result()
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
            reason = (error.stderr or str(error)).strip().splitlines()  # such as: Could not resolve host
            report.unchecked.append(label.split(" ")[0])
            report.line("unchecked", f"{label}: {reason[-1] if reason else error}")
            continue
        if not tags:
            report.unchecked.append(label.split(" ")[0])
            report.line("unchecked", f"{label}: the remote has no release tags")
            continue
        newest_version = max(tags)
        newest = tags[newest_version][0]
        if match := RELEASE_TAG.fullmatch(used):
            current, name = version(match[1]), used
        else:
            # A submodule records a commit; the release tag that points at it names the version.
            current, name = next(((number, tag) for number, (tag, commit) in tags.items() if commit == used),
                                 ((), used[:12]))
        if current >= newest_version:
            report.line("current", f"{label}: {name}, the newest release")
        else:
            report.update(f"{label.split(' ')[0]} {newest}", f"{label}: {name}; newest release {newest}")


def main() -> int:
    print("Toolchain updates for cmake_template (docs/lab/toolchain.md#keeping-the-toolchain-current)\n")
    report = Report()
    compilers = preset_compilers()
    check_packages(report, compilers)
    check_upstream(report)
    unchecked = f"; not checked: {', '.join(report.unchecked)}" if report.unchecked else ""
    if report.newer:
        print(f"\nNewer: {', '.join(report.newer)}{unchecked}")
        return NEWER
    print(f"\nNothing newer than the repo uses{unchecked}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
