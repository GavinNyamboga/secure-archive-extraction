"""
Verify that /app/extractor.py securely extracts tar archives.

The extractor must be called as:

    python3 /app/extractor.py <archive-path> <destination-path>
"""
from __future__ import annotations

import io
import subprocess
import tarfile
from pathlib import Path

EXTRACTOR = Path("/app/extractor.py")

def add_file(
        archive: tarfile.TarFile,
        name: str,
        content: bytes,
) -> None:
    """Add a regular file to the archive."""
    member = tarfile.TarInfo(name = name)
    member.size = len(content)
    member.mode = 0o644
    archive.addfile(member, io.BytesIO(content))


def add_directory(
        archive: tarfile.TarFile,
        name: str,
) -> None:
    """Add directory entry to a tar archive."""
    member = tarfile.TarInfo(name = name)
    member.type = tarfile.DIRTYPE
    member.mode = 0o755
    archive.addfile(member)

def run_extractor(
    archive_path: Path,
    destination: Path,
) -> subprocess.CompletedProcess[str]:
    """Run the extraction utility."""
    return subprocess.run(
        [
            "python3",
            str(EXTRACTOR),
            str(archive_path),
            str(destination),
        ],
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )

def assert_rejected(
    result: subprocess.CompletedProcess[str],
    destination: Path,
) -> None:
    """Assert that an unsafe archive was rejected cleanly."""
    assert result.returncode == 2, (
        f"Expected exit code 2, got {result.returncode}.\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )
    assert not destination.exists(), (
        "The destination must not exist after failed extraction"
    )

def test_extractor_exists() -> None:
    """The required extraction utility exists."""
    assert EXTRACTOR.is_file()

def test_extracts_valid_nested_archive(tmp_path: Path) -> None:
    """A valid archive is extracted with its directory structure."""
    archive_path = tmp_path / "valid.tar"

    with tarfile.open(archive_path, mode="w") as archive:
        add_directory(archive, "docs")
        add_file(archive, "docs/readme.txt", b"hello world")
        add_file(archive, "data/items.json", b'{"count": 3}')

    destination = tmp_path / "output"
    result = run_extractor(archive_path, destination)

    assert result.returncode == 0, result.stderr
    assert destination.is_dir()
    assert (destination / "docs/readme.txt").read_bytes() == b"hello world"
    assert (
        destination / "data/items.json"
    ).read_bytes() == b'{"count": 3}'

def test_extracts_tar_gz_archive(tmp_path: Path) -> None:
    """A gzip-compressed tar archive is supported."""
    archive_path = tmp_path / "compressed.tar.gz"

    with tarfile.open(archive_path, mode="w:gz") as archive:
        add_file(archive, "nested/file.txt", b"compressed content")

    destination = tmp_path / "output"
    result = run_extractor(archive_path, destination)

    assert result.returncode == 0, result.stderr
    assert (
        destination / "nested/file.txt"
    ).read_bytes() == b"compressed content"

def test_extracts_tgz_archive(tmp_path: Path) -> None:
    """An archive with a .tgz extension is supported."""
    archive_path = tmp_path / "compressed.tgz"

    with tarfile.open(archive_path, mode="w:gz") as archive:
        add_file(archive, "file.txt", b"tgz content")

    destination = tmp_path / "output"
    result = run_extractor(archive_path, destination)

    assert result.returncode == 0, result.stderr
    assert (destination / "file.txt").read_bytes() == b"tgz content"

def test_rejects_parent_directory_traversal(tmp_path: Path) -> None:
    """Parent-directory traversal cannot escape the destination."""
    archive_path = tmp_path / "traversal.tar"

    with tarfile.open(archive_path, mode="w") as archive:
        add_file(archive, "../../escaped.txt", b"unsafe")

    destination = tmp_path / "output"
    escaped_path = tmp_path.parent / "escaped.txt"
    escaped_path.unlink(missing_ok=True)

    result = run_extractor(archive_path, destination)

    assert_rejected(result, destination)
    assert not escaped_path.exists()

def test_rejects_nested_parent_traversal(tmp_path: Path) -> None:
    """Traversal segments are rejected even when nested in a path."""
    archive_path = tmp_path / "nested-traversal.tar"

    with tarfile.open(archive_path, mode="w") as archive:
        add_file(
            archive,
            "documents/../../escaped.txt",
            b"unsafe",
        )

    destination = tmp_path / "output"
    escaped_path = tmp_path / "escaped.txt"

    result = run_extractor(archive_path, destination)

    assert_rejected(result, destination)
    assert not escaped_path.exists()

def test_rejects_absolute_member_path(tmp_path: Path) -> None:
    """Absolute archive member paths are rejected."""
    archive_path = tmp_path / "absolute.tar"
    escaped_path = tmp_path / "absolute-escape.txt"
    escaped_path.unlink(missing_ok=True)

    with tarfile.open(archive_path, mode="w") as archive:
        add_file(
            archive,
            str(escaped_path),
            b"unsafe",
        )

    destination = tmp_path / "output"
    result = run_extractor(archive_path, destination)

    assert_rejected(result, destination)
    assert not escaped_path.exists()

def test_rejects_symbolic_link(tmp_path: Path) -> None:
    """Symbolic-link archive members are rejected."""
    archive_path = tmp_path / "symlink.tar"

    with tarfile.open(archive_path, mode="w") as archive:
        link = tarfile.TarInfo(name="safe/link")
        link.type = tarfile.SYMTYPE
        link.linkname = "../../outside"
        archive.addfile(link)

    destination = tmp_path / "output"
    result = run_extractor(archive_path, destination)

    assert_rejected(result, destination)


def test_rejects_hard_link(tmp_path: Path) -> None:
    """Hard-link archive members are rejected."""
    archive_path = tmp_path / "hardlink.tar"

    with tarfile.open(archive_path, mode="w") as archive:
        add_file(archive, "source.txt", b"source")

        link = tarfile.TarInfo(name="linked.txt")
        link.type = tarfile.LNKTYPE
        link.linkname = "source.txt"
        archive.addfile(link)

    destination = tmp_path / "output"
    result = run_extractor(archive_path, destination)

    assert_rejected(result, destination)


def test_rejects_fifo(tmp_path: Path) -> None:
    """FIFO archive members are rejected."""
    archive_path = tmp_path / "fifo.tar"

    with tarfile.open(archive_path, mode="w") as archive:
        fifo = tarfile.TarInfo(name="unsafe-pipe")
        fifo.type = tarfile.FIFOTYPE
        archive.addfile(fifo)

    destination = tmp_path / "output"
    result = run_extractor(archive_path, destination)

    assert_rejected(result, destination)


def test_rejects_character_device(tmp_path: Path) -> None:
    """Character-device archive members are rejected."""
    archive_path = tmp_path / "device.tar"

    with tarfile.open(archive_path, mode="w") as archive:
        device = tarfile.TarInfo(name="unsafe-device")
        device.type = tarfile.CHRTYPE
        device.devmajor = 1
        device.devminor = 3
        archive.addfile(device)

    destination = tmp_path / "output"
    result = run_extractor(archive_path, destination)

    assert_rejected(result, destination)


def test_failure_leaves_no_partial_destination(tmp_path: Path) -> None:
    """A late invalid member cannot leave earlier files extracted."""
    archive_path = tmp_path / "partial.tar"

    with tarfile.open(archive_path, mode="w") as archive:
        add_file(
            archive,
            "valid/first.txt",
            b"this member appears first",
        )
        add_file(
            archive,
            "../unsafe.txt",
            b"this member is invalid",
        )

    destination = tmp_path / "output"
    result = run_extractor(archive_path, destination)

    assert_rejected(result, destination)
    assert not (tmp_path / "unsafe.txt").exists()


def test_rejects_duplicate_normalized_paths(tmp_path: Path) -> None:
    """Different member names cannot normalize to one output path."""
    archive_path = tmp_path / "duplicates.tar"

    with tarfile.open(archive_path, mode="w") as archive:
        add_file(
            archive,
            "docs/./readme.txt",
            b"first",
        )
        add_file(
            archive,
            "docs/readme.txt",
            b"second",
        )

    destination = tmp_path / "output"
    result = run_extractor(archive_path, destination)

    assert_rejected(result, destination)


def test_rejects_duplicate_identical_paths(tmp_path: Path) -> None:
    """Two members cannot target the same exact path."""
    archive_path = tmp_path / "exact-duplicates.tar"

    with tarfile.open(archive_path, mode="w") as archive:
        add_file(archive, "value.txt", b"first")
        add_file(archive, "value.txt", b"second")

    destination = tmp_path / "output"
    result = run_extractor(archive_path, destination)

    assert_rejected(result, destination)


def test_rejects_file_used_as_parent_directory(tmp_path: Path) -> None:
    """A regular file cannot also be a parent directory."""
    archive_path = tmp_path / "parent-conflict.tar"

    with tarfile.open(archive_path, mode="w") as archive:
        add_file(archive, "node", b"regular file")
        add_file(archive, "node/child.txt", b"child")

    destination = tmp_path / "output"
    result = run_extractor(archive_path, destination)

    assert_rejected(result, destination)


def test_rejects_file_after_child_path(tmp_path: Path) -> None:
    """A file-parent conflict is rejected regardless of member order."""
    archive_path = tmp_path / "reverse-parent-conflict.tar"

    with tarfile.open(archive_path, mode="w") as archive:
        add_file(archive, "node/child.txt", b"child")
        add_file(archive, "node", b"regular file")

    destination = tmp_path / "output"
    result = run_extractor(archive_path, destination)

    assert_rejected(result, destination)


def test_existing_destination_is_not_modified(tmp_path: Path) -> None:
    """An existing destination causes failure and remains unchanged."""
    archive_path = tmp_path / "valid.tar"

    with tarfile.open(archive_path, mode="w") as archive:
        add_file(archive, "new.txt", b"new content")

    destination = tmp_path / "output"
    destination.mkdir()

    existing_file = destination / "existing.txt"
    existing_file.write_bytes(b"preserve this")

    result = run_extractor(archive_path, destination)

    assert result.returncode == 2
    assert destination.is_dir()
    assert existing_file.read_bytes() == b"preserve this"
    assert not (destination / "new.txt").exists()


def test_rejects_malformed_archive(tmp_path: Path) -> None:
    """Malformed input is rejected without creating a destination."""
    archive_path = tmp_path / "malformed.tar"
    archive_path.write_bytes(b"this is not a valid tar archive")

    destination = tmp_path / "output"
    result = run_extractor(archive_path, destination)

    assert_rejected(result, destination)


def test_rejects_missing_archive(tmp_path: Path) -> None:
    """A missing archive exits with status code two."""
    archive_path = tmp_path / "missing.tar"
    destination = tmp_path / "output"

    result = run_extractor(archive_path, destination)

    assert_rejected(result, destination)


def test_invalid_arguments_exit_with_code_two() -> None:
    """Calling the utility with missing arguments fails correctly."""
    result = subprocess.run(
        ["python3", str(EXTRACTOR)],
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )

    assert result.returncode == 2