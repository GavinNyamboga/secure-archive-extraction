#!/usr/bin/env python3

import sys
import tarfile
from pathlib import Path

def extract_archive(archive_path: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)

    with tarfile.open(archive_path, 'r:*') as archive:
        archive.extractall(destination)

def main() -> int:
    if len(sys.argv) != 3:
        print(
            "Usage: extractor.py <archive_path> <destination>",
            file=sys.stderr
        )
        return 2

    archive_path = Path(sys.argv[1])
    destination = Path(sys.argv[2])

    try:
        extract_archive(archive_path, destination)
    except Exception as e:
        print(f"Error extracting archive: {e}", file=sys.stderr)
        return 2
    return 0

if __name__ == "__main__":
    raise SystemExit(main())