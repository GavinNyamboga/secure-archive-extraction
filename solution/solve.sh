#!/bin/bash
set -euo pipefail

cat > /app/extractor.py <<'PYTHON'
#!/usr/bin/env python3

import os
import shutil
import sys
import tarfile
import tempfile
from pathlib import Path, PurePosixPath

class UnsafeArchiveError(Exception):
    """Raised when an archive contains an unsafe member."""

def normalize_member_name(name: str) -> str | None:
    path = PurePosixPath(name)

    if path.is_absolute():
        raise UnsafeArchiveError(f"Absolute path is not allowed: {name}")
    
    if ".." in path.parts:
        raise UnsafeArchiveError(f"Parent traversal is not allowed: {name}")

    normalized = str(path)

    # A root directory entry such as "." is harmless and can be ignored
    if(normalized in {"", "."}):
        return None

    return normalized

def validate_members(
    archive: tarfile.TarFile,
) -> list[tuple[tarfile.TarInfo, str]]:
    validated: list[tuple[tarfile.TarInfo, str]] = []
    path_types: dict[str, str] = {}

    for member in archive.getmembers():
        normalized = normalize_member_name(member.name)

        if normalized is None:
            if not member.isdir():
                raise UnsafeArchiveError(
                    f"Invalid empty member path: {member.name}"
                )
            continue

        if member.isdir():
            member_type = "directory"
        elif member.isreg():
            member_type = "file"
        else:
            raise UnsafeArchiveError(
                f"Unsupported archive member type: {member.name}"
            )

        if normalized in path_types:
            raise UnsafeArchiveError(
                f"Duplicate normalized path: {normalized}"
            )

        path_types[normalized] = member_type
        validated.append((member, normalized))

    for path, member_type in path_types.items():
        current = PurePosixPath(path).parent

        while str(current) not in {"", "."}:
            parent = str(current)

            if path_types.get(parent) == "file":
                raise UnsafeArchiveError(
                    f"Regular file used as a directory: {parent}"
                )

            current = current.parent

        if member_type == "file":
            prefix = f"{path}/"

            if any(
                other_path.startswith(prefix)
                for other_path in path_types
            ):
                raise UnsafeArchiveError(
                    f"Regular file used as a directory: {path}"
                )

    return validated


def extract_validated_members(
    archive: tarfile.TarFile,
    members: list[tuple[tarfile.TarInfo, str]],
    staging_directory: Path,
) -> None:
    for member, normalized in members:
        relative_path = PurePosixPath(normalized)
        target = staging_directory.joinpath(*relative_path.parts)

        if member.isdir():
            target.mkdir(parents=True, exist_ok=True)
            target.chmod(0o755)
            continue

        target.parent.mkdir(parents=True, exist_ok=True)

        source = archive.extractfile(member)
        if source is None:
            raise UnsafeArchiveError(
                f"Could not read regular file: {member.name}"
            )

        with source, target.open("xb") as output:
            shutil.copyfileobj(source, output)

        # Do not preserve setuid, setgid, ownership, or other unsafe metadata.
        target.chmod(0o644)


def extract_archive(archive_path: Path, destination: Path) -> None:
    if os.path.lexists(destination):
        raise UnsafeArchiveError("Destination already exists")

    parent = destination.parent
    parent.mkdir(parents=True, exist_ok=True)

    staging_path = Path(
        tempfile.mkdtemp(
            prefix=f".{destination.name}.extracting-",
            dir=parent,
        )
    )

    try:
        with tarfile.open(archive_path, mode="r:*") as archive:
            members = validate_members(archive)
            extract_validated_members(archive, members, staging_path)

        os.replace(staging_path, destination)
    except Exception:
        shutil.rmtree(staging_path, ignore_errors=True)
        raise


def main() -> int:
    if len(sys.argv) != 3:
        print(
            "Usage: extractor.py <archive-path> <destination-path>",
            file=sys.stderr,
        )
        return 2

    archive_path = Path(sys.argv[1])
    destination = Path(sys.argv[2])

    try:
        extract_archive(archive_path, destination)
    except (
        UnsafeArchiveError,
        tarfile.TarError,
        OSError,
    ) as exc:
        print(f"Extraction failed: {exc}", file=sys.stderr)
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
PYTHON

chmod +x /app/extractor.py