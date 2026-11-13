# Confirmed maintenance archive

Created 13 November 2026 with user authorisation. Ten one-off source patch helpers were moved; their changes were verified in target code and no filename references were found in the checked source/configuration/documentation formats. No science data, runtime implementations, saved reviews or provenance snapshots were moved.

archive_manifest.json records original paths, archived paths, SHA256 hashes and verification evidence. The original directory structure is preserved beneath this folder.

To restore an item, stop related development work, verify its SHA256 against the manifest, and move it back to its original repository-relative path. Refuse to overwrite an existing file. These patch scripts require their ORIGINAL working directories and may not be safe or idempotent to rerun on current code. Archiving preserves them for inspection, not automatic execution.
