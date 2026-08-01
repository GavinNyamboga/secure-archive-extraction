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