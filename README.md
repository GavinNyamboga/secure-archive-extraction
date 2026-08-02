# Secure Archive Extraction

A Harbor terminal task that evaluates an AI agent’s ability to repair an unsafe Python archive extraction utility.

The starting implementation extracts tar archives directly into a destination directory without validating archive members. This may allow files to escape the destination directory, unsafe filesystem objects to be created, conflicting paths to overwrite one another, or partial output to remain after an extraction failure.

## Task objective

The agent must update `/app/extractor.py` so that it safely extracts:

- `.tar`
- `.tar.gz`
- `.tgz`

The command-line interface must remain unchanged:

```bash
python3 /app/extractor.py <archive-path> <destination-path>
```

A correct implementation must:

- Extract valid nested directories and regular files.
- Reject absolute archive member paths.
- Reject parent-directory traversal paths.
- Reject symbolic links and hard links.
- Reject device files, FIFOs, and other unsupported member types.
- Reject duplicate normalized paths.
- Reject file and directory path conflicts.
- Refuse to modify an existing destination.
- Leave no partial destination when extraction fails.
- Prevent any file from being written outside the destination.
- Exit with status code 0 on success.
- Exit with status code 2 for invalid or unsafe archives.