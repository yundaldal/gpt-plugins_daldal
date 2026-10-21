"""Build and verify the public 품의 plugin ZIP without external packages."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import stat
import tempfile
import zipfile
from pathlib import Path, PurePosixPath


ROOT = Path(__file__).resolve().parents[1]
PLUGIN_DIR = ROOT / "plugins" / "pumui-daldal"
DOWNLOADS_DIR = ROOT / "downloads"
PLUGIN_NAME = "pumui-daldal"
FORBIDDEN_PARTS = {
    ".git",
    "node_modules",
    "verification",
    "input",
    "inputs",
    "output",
    "outputs",
    "question_state",
    "question-state",
}


def plugin_version() -> str:
    metadata = json.loads((PLUGIN_DIR / "plugin.json").read_text(encoding="utf-8"))
    version = metadata.get("version")
    if not isinstance(version, str) or not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise ValueError("plugins/pumui-daldal/plugin.json has an invalid release version")
    return version


def release_paths(version: str | None = None) -> tuple[Path, Path]:
    version = version or plugin_version()
    archive = DOWNLOADS_DIR / f"{PLUGIN_NAME}-{version}.zip"
    return archive, archive.with_suffix(archive.suffix + ".sha256")


def collect_plugin_files() -> list[tuple[Path, str]]:
    root = PLUGIN_DIR.resolve(strict=True)
    if PLUGIN_DIR.is_symlink():
        raise ValueError("plugin root must not be a symlink")

    files: list[tuple[Path, str]] = []
    folded_names: set[str] = set()
    for path in sorted(PLUGIN_DIR.rglob("*"), key=lambda item: item.as_posix().casefold()):
        relative = path.relative_to(PLUGIN_DIR)
        if path.is_symlink():
            raise ValueError(f"symlinks are not allowed in the package: {relative}")
        if "__pycache__" in {part.casefold() for part in relative.parts} or path.suffix.casefold() == ".pyc":
            continue
        if any(part.casefold() in FORBIDDEN_PARTS for part in relative.parts):
            raise ValueError(f"private or generated path is not allowed: {relative}")
        if relative.name.casefold() == "case.json":
            raise ValueError(f"private or generated file is not allowed: {relative}")
        if not path.is_file():
            continue
        resolved = path.resolve(strict=True)
        try:
            resolved.relative_to(root)
        except ValueError as exc:
            raise ValueError(f"package file escapes plugin root: {relative}") from exc
        archive_name = f"{PLUGIN_NAME}/{relative.as_posix()}"
        key = archive_name.casefold()
        if key in folded_names:
            raise ValueError(f"case-insensitive duplicate ZIP path: {archive_name}")
        folded_names.add(key)
        files.append((path, archive_name))

    if not files:
        raise ValueError("plugin package is empty")
    return files


def build_archive_bytes(files: list[tuple[Path, str]] | None = None) -> bytes:
    files = files or collect_plugin_files()
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path, archive_name in files:
            info = zipfile.ZipInfo(archive_name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            archive.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    return buffer.getvalue()


def verify_archive_bytes(payload: bytes, files: list[tuple[Path, str]] | None = None) -> None:
    files = files or collect_plugin_files()
    expected = {archive_name: path.read_bytes() for path, archive_name in files}
    with zipfile.ZipFile(io.BytesIO(payload), "r") as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise ValueError("ZIP contains duplicate paths")
        if set(names) != set(expected):
            raise ValueError("ZIP members do not match the plugin source tree")
        for name in names:
            posix_path = PurePosixPath(name)
            if (
                "\\" in name
                or posix_path.is_absolute()
                or ".." in posix_path.parts
                or not posix_path.parts
                or posix_path.parts[0] != PLUGIN_NAME
            ):
                raise ValueError(f"unsafe ZIP path: {name}")
            if archive.read(name) != expected[name]:
                raise ValueError(f"ZIP content differs from source: {name}")
        broken = archive.testzip()
        if broken:
            raise ValueError(f"ZIP CRC validation failed: {broken}")


def _atomic_write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=f".{path.name}.", delete=False) as temp:
            temporary_name = temp.name
            temp.write(content)
            temp.flush()
            os.fsync(temp.fileno())
        os.replace(temporary_name, path)
    finally:
        if temporary_name and os.path.exists(temporary_name):
            os.unlink(temporary_name)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify the existing ZIP and SHA-256 sidecar")
    args = parser.parse_args(argv)

    files = collect_plugin_files()
    archive_path, checksum_path = release_paths()

    if args.check:
        if not archive_path.is_file():
            raise SystemExit(f"release ZIP is missing: {archive_path}")
        payload = archive_path.read_bytes()
        try:
            verify_archive_bytes(payload, files)
        except (OSError, ValueError, zipfile.BadZipFile) as exc:
            raise SystemExit(f"release ZIP does not match the plugin source tree: {exc}") from exc
        digest = hashlib.sha256(payload).hexdigest()
        checksum = f"{digest}  {archive_path.name}\n".encode("ascii")
        if not checksum_path.is_file() or checksum_path.read_bytes() != checksum:
            raise SystemExit(f"SHA-256 sidecar is missing or out of date: {checksum_path}")
    else:
        payload = build_archive_bytes(files)
        verify_archive_bytes(payload, files)
        digest = hashlib.sha256(payload).hexdigest()
        checksum = f"{digest}  {archive_path.name}\n".encode("ascii")
        _atomic_write(archive_path, payload)
        _atomic_write(checksum_path, checksum)

    print(f"files={len(files)} archive={archive_path.relative_to(ROOT).as_posix()} sha256={digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
