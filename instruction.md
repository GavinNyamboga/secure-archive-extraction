A command-line utility is available at `/app/extractor.py`.

It extracts `.tar`, `.tar.gz`, and `.tgz` archives using this interface:

```bash
python /app/extractor.py <archive-path> <destination-path>
```

The current implementation may write files outside the destination directory
or leave partially extracted files when an archive is invalid.
Fix the utility so that:

Valid archives are extracted successfully.
Nested directories and regular files are supported.
Absolute member paths are rejected.
Member paths containing parent-directory traversal are rejected.
Symbolic links, hard links, device files, and FIFOs are rejected.
Two archive members must not resolve to the same normalized path.
A regular file cannot also be used as a parent directory.
The destination must not already exist.
An unsafe or malformed archive exits with status code 2.
When extraction fails, the destination path must not be created.
No file may be written outside the destination directory.
Successful extraction exits with status code 0.