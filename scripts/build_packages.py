#!/usr/bin/env python3
"""Validate this library and build reproducible, self-contained skill ZIPs."""

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit
import zipfile

import yaml


ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"
SKIP = {".git", ".venv", "__pycache__", ".pytest_cache", "archive", "sandbox", "dist"}


def files_under(directory: Path) -> list[Path]:
    files = []
    for parent, dirs, names in os.walk(directory, followlinks=False):
        dirs[:] = sorted(name for name in dirs if name not in SKIP)
        for name in dirs + names:
            path = Path(parent) / name
            if path.is_symlink():
                raise ValueError(f"Package must contain real files, not symlinks: {path}")
        for name in sorted(names):
            if name == ".DS_Store" or name.endswith(".pyc"):
                continue
            files.append(Path(parent) / name)
    return sorted(files)


def validate_skill(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    match = re.match(r"\A---\n(.*?)\n---(?:\n|\Z)", text, re.DOTALL)
    if not match:
        raise ValueError(f"Missing YAML frontmatter: {path.relative_to(ROOT)}")
    metadata = yaml.safe_load(match.group(1))
    if not isinstance(metadata, dict):
        raise ValueError(f"Frontmatter must be a mapping: {path.relative_to(ROOT)}")
    name = metadata.get("name")
    description = metadata.get("description")
    if not isinstance(name, str) or name != path.parent.name:
        raise ValueError(f"Skill name must match its folder: {path.relative_to(ROOT)}")
    if len(name) > 64 or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name):
        raise ValueError(f"Invalid skill name: {path.relative_to(ROOT)}")
    if not isinstance(description, str) or not 1 <= len(description.strip()) <= 1024:
        raise ValueError(f"Missing or oversized description: {path.relative_to(ROOT)}")


def check_markdown_links(paths: list[Path]) -> int:
    count = 0
    for path in paths:
        if path.suffix != ".md":
            continue
        text = path.read_text(encoding="utf-8")
        # Ignore example links inside fenced code; verify actual local file links.
        text = re.sub(r"^```[^\n]*\n.*?^```[ \t]*$", "", text, flags=re.M | re.S)
        for target in re.findall(r"\[[^\]\n]*\]\(([^)]+)\)", text):
            target = target.strip().strip("<>")
            url = urlsplit(target)
            if url.scheme or url.netloc or not url.path:
                continue
            destination = (path.parent / unquote(url.path)).resolve()
            if not destination.is_relative_to(ROOT) or not destination.exists():
                raise ValueError(f"Broken local link in {path.relative_to(ROOT)}: {target}")
            count += 1
    return count


def package_files(skill: Path) -> dict[str, bytes]:
    entries = {}
    for path in files_under(skill):
        if path.name == "HANDOFF.md":
            raise ValueError(f"Session notes do not belong in a skill package: {path}")
        entries[f"{skill.name}/{path.relative_to(skill).as_posix()}"] = path.read_bytes()
    entries.setdefault(f"{skill.name}/LICENSE", (ROOT / "LICENSE").read_bytes())
    return entries


def write_package(destination: Path, entries: dict[str, bytes]) -> None:
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as output:
        for name, content in sorted(entries.items()):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            output.writestr(info, content, compresslevel=9)
    with zipfile.ZipFile(destination) as result:
        if result.testzip() is not None or set(result.namelist()) != set(entries):
            raise ValueError(f"ZIP integrity check failed: {destination.name}")
        for name, content in entries.items():
            if result.read(name) != content:
                raise ValueError(f"ZIP differs from source: {destination.name}:{name}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Validate without writing packages")
    args = parser.parse_args()
    skills = sorted(path for path in SKILLS.iterdir() if path.is_dir() and (path / "SKILL.md").is_file())
    if not skills:
        raise ValueError("No skills found")
    all_files = files_under(ROOT)
    skill_files = [path for path in all_files if path.name == "SKILL.md" and path.is_relative_to(SKILLS)]
    for path in skill_files:
        validate_skill(path)
    links = check_markdown_links(all_files)
    packages = {skill.name: package_files(skill) for skill in skills}
    print(f"PASS: {len(skills)} packages, {len(skill_files)} skill headers, {links} local Markdown file links")
    if args.check:
        return

    output = ROOT / "dist"
    expected = {f"{name}.zip" for name in packages} | {"SHA256SUMS"}
    if output.exists():
        unexpected = {path.name for path in output.iterdir()} - expected
        if unexpected:
            raise ValueError(f"Move unexpected files out of dist/ before building: {sorted(unexpected)}")
    output.mkdir(exist_ok=True)
    checksums = []
    for name, entries in packages.items():
        path = output / f"{name}.zip"
        write_package(path, entries)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        checksums.append(f"{digest}  {path.name}\n")
        print(f"VERIFIED: {path.name} ({len(entries)} files, {path.stat().st_size} bytes)")
    (output / "SHA256SUMS").write_text("".join(checksums), encoding="utf-8")
    print("Wrote dist/SHA256SUMS")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, yaml.YAMLError, zipfile.BadZipFile) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        sys.exit(1)
