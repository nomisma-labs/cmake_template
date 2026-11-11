#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Alexey Tkachenko
# SPDX-License-Identifier: MIT
"""Initialize, build and sync all license choices using disposable local Git repositories."""

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory

IDENTITY = ["-c", "user.name=License Test", "-c", "user.email=license@example.invalid",
            "-c", "init.defaultBranch=master"]
ENV = dict(os.environ, GIT_ALLOW_PROTOCOL="file", PYTHONDONTWRITEBYTECODE="1")
CHOICES = {"MIT": "MIT", "SUL-1.0": "LicenseRef-Sustainable-Use-1.0",
           "proprietary": "LicenseRef-Nomisma-Labs-Proprietary"}


def run(cwd: Path, *args: str, success: bool = True) -> subprocess.CompletedProcess:
    result = subprocess.run(args, cwd=cwd, env=ENV, text=True, capture_output=True)
    if success and result.returncode:
        raise RuntimeError(f"{' '.join(args)}\n{result.stdout}\n{result.stderr}")
    return result


def git(cwd: Path, *args: str) -> str:
    return run(cwd, "git", *IDENTITY, *args).stdout.strip()


def commit(repo: Path, message: str) -> None:
    git(repo, "add", "--all")
    git(repo, "commit", "--quiet", "-m", message)


def initialize_git(repo: Path) -> None:
    git(repo, "init", "--quiet")
    git(repo, "config", "user.name", "License Test")
    git(repo, "config", "user.email", "license@example.invalid")


def copy_snapshot(source: Path, target: Path, names: list[str]) -> None:
    target.mkdir()
    for name in names:
        src, dst = source / name, target / name
        if src.is_file():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
    initialize_git(target)
    git(target, "add", "--all")
    # Preserve uninitialized gitlinks, as GitHub's template snapshot does.
    for entry in git(source, "ls-files", "--stage").splitlines():
        metadata, name = entry.split("\t", 1)
        mode, sha, _ = metadata.split()
        if mode == "160000":
            (target / name).mkdir(parents=True, exist_ok=True)
            git(target, "update-index", "--add", "--cacheinfo", f"160000,{sha},{name}")
    git(target, "commit", "--quiet", "-m", "Template snapshot")


def check_headers(repo: Path, *args: str, success: bool = True) -> subprocess.CompletedProcess:
    return run(repo, sys.executable, "tools/kit/checks/headers.py", *args, success=success)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True)
    parser.add_argument("--cmake", default="cmake")
    parser.add_argument("--compiler", default="g++-16")
    parser.add_argument("--generator", default="Ninja")
    args = parser.parse_args()
    source = Path(args.source).resolve()
    # Include the working-tree changes being tested without committing the real template.
    names = sorted(set(git(source, "ls-files", "--cached", "--others", "--exclude-standard").splitlines()))
    with TemporaryDirectory(prefix="nomisma-project-license-") as temporary:
        root = Path(temporary)
        upstream = root / "upstream"
        copy_snapshot(source, upstream, names)
        baseline = git(upstream, "rev-parse", "HEAD")
        consumers = []
        for choice, license_id in CHOICES.items():
            name = "sample_" + choice.lower().replace("-", "_").replace(".", "_")
            repo = root / name
            copy_snapshot(upstream, repo, git(upstream, "ls-files").splitlines())
            command = [sys.executable, "tools/init_project.py", name, "--template-url", str(upstream)]
            # Selecting a license is mandatory, and failure must leave the snapshot intact.
            for extra in ([], ["--license", "unknown"]):
                result = run(repo, *command, *extra, success=False)
                assert result.returncode and not git(repo, "status", "--porcelain"), result
            owner = "2026 License Test" if choice == "SUL-1.0" else "2026 Alexey Tkachenko"
            run(repo, *command, "--license", choice, "--copyright", owner)
            assert not git(repo, "status", "--porcelain"), "initializer left an uncommitted repo"
            assert not (repo / "src/example").exists() and not (repo / "tests/kit").exists()
            assert not (repo / "tools/init_project.py").exists()
            policy = json.loads((repo / "project_license.json").read_text())
            assert policy["license"] == license_id and "CMakeLists.txt" in policy["mit_files"]
            assert policy["copyright"] == owner and owner in (repo / "LICENSE").read_text()
            assert "SPDX-License-Identifier: MIT" in (repo / "CMakeLists.txt").read_text()
            assert baseline in (repo / ".template_ref").read_text()
            if choice == "SUL-1.0":
                notice = (repo / "LICENSE").read_text()
                assert "Version 1.0" in notice and "n8n Enterprise" not in notice
            check_headers(repo)

            run(repo, sys.executable, "tools/kit/add_sandbox_app.py", "probe")
            generated = repo / "apps/sandbox/probe/main.cpp"
            assert f"SPDX-License-Identifier: {license_id}" in generated.read_text()
            assert f"SPDX-FileCopyrightText: {owner}" in generated.read_text()
            git(repo, "add", "--force", "apps/sandbox/probe")
            check_headers(repo, "--staged")
            # Staged checks must use staged contents, not an unstaged fix.
            valid = generated.read_text()
            generated.write_text(valid.replace(license_id, "LicenseRef-Wrong"))
            git(repo, "add", "--force", "apps/sandbox/probe/main.cpp")
            generated.write_text(valid)
            assert check_headers(repo, "--staged", success=False).returncode
            git(repo, "add", "--force", "apps/sandbox/probe/main.cpp")
            check_headers(repo, "--staged")
            commit(repo, "Add project-owned code")

            saved_policy = (repo / "project_license.json").read_bytes()
            saved_notice = (repo / "LICENSE").read_bytes()
            alternative = "LicenseRef-Nomisma-Labs-Proprietary" if choice == "MIT" else "MIT"
            run(repo, sys.executable, "-c",
                "from pathlib import Path; import json; "
                "from tools.kit.project_license import load_policy, project_license_text; "
                f"p=load_policy(Path('.')); p['license']={alternative!r}; "
                "Path('project_license.json').write_text(json.dumps(p)); "
                "Path('LICENSE').write_text(project_license_text(Path('.'),p))")
            git(repo, "add", "project_license.json", "LICENSE")
            result = check_headers(repo, "--staged", success=False)
            assert result.returncode and "wrong SPDX license: apps/sandbox/probe" in result.stdout
            (repo / "project_license.json").write_bytes(saved_policy)
            (repo / "LICENSE").write_bytes(saved_notice)
            git(repo, "add", "project_license.json", "LICENSE")

            run(repo, args.cmake, "-S", str(repo), "-B", str(repo / "build/probe"), "-G", args.generator,
                f"-DCMAKE_CXX_COMPILER={args.compiler}", f"-D{name.upper()}_BUILD_TESTS=OFF",
                "-DNOM_BUILD_PRESET=complete")
            run(repo, args.cmake, "--build", str(repo / "build/probe"), "--target", "sandbox_probe", "-j2")
            assert "sandbox: probe" in run(repo, str(repo / "build/probe/bin/sandbox_probe")).stdout
            # Kit licensing cannot be changed to match a non-MIT project.
            kit_file = repo / "tools/kit/add_sandbox_app.py"
            original = kit_file.read_text()
            kit_file.write_text(original.replace("SPDX-License-Identifier: MIT", "SPDX-License-Identifier: LicenseRef-Wrong", 1))
            assert check_headers(repo, success=False).returncode
            kit_file.write_text(original)
            consumers.append((repo, {p: (repo / p).read_bytes() for p in
                                     ("LICENSE", "project_license.json", "CMakeLists.txt", "apps/sandbox/probe/main.cpp")}))

        # A local upstream update exercises the real sync script, including its staged result.
        helper = upstream / "tools/kit/add_sandbox_app.py"
        helper.write_text(helper.read_text() + "\n# Local regression-test update.\n")
        commit(upstream, "Update shared tool")
        target = git(upstream, "rev-parse", "HEAD")
        for repo, before in consumers:
            run(repo, sys.executable, "tools/kit/sync_template.py", "--to", target)
            for name, content in before.items():
                assert (repo / name).read_bytes() == content, f"sync changed {name} in {repo.name}"
            assert target in (repo / ".template_ref").read_text()
            assert (repo / "tools/kit/add_sandbox_app.py").read_text() == helper.read_text()
            check_headers(repo)
            check_headers(repo, "--staged")
            commit(repo, "Sync local template")
            assert "up to date" in run(repo, sys.executable, "tools/kit/sync_template.py", "--to", target).stdout
            print(f"PASS: {repo.name}: initialize, generate, build, check, sync; project license preserved")
    print("Temporary repositories removed; no hosted repositories or workspace registrations created.")


if __name__ == "__main__":
    main()
