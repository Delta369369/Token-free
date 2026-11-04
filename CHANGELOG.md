# ADON AI — Context Efficiency Core v1.0.1

- Aligned Python package and CLI version labels with the v1.0.1 release.
- Added `source-verify` to distinguish verified, changed, missing and unhashed registered files.
- Validate checkpoint payload SHA-256 before display or restore, including compatibility for earlier v1.0.1 checkpoints with omitted empty arrays.
- Close SQLite connections if database initialization raises before a connection can be returned.
- Use the required `description` skill metadata and keep installer backups outside agent skill scan roots to prevent invalid duplicate discovery.
- Add a GitHub-aware skill workflow: prefer the host's existing connector for scoped, read-only search/fetch, keep ADON SQLite local, and record commit-pinned source references.

## Windows SQLite lifecycle correction

- Fixed `adon_context.store.connect()` context manager behavior. The built-in
  `sqlite3.Connection` context manager commits or rolls back but does not close
  its file handle. The previous package consequently failed seven Windows tests
  when `TemporaryDirectory()` attempted to delete `state.sqlite3` (`WinError 32`).
- `ManagedConnection` now retains the normal commit/rollback semantics and
  **always closes** at block exit, even on exception.
- Added two lifecycle regression tests covering close-on-success and
  rollback-and-close-on-error.
- No DB schema, installed agent settings, automatic network integrations or
  model routing changed.

## Install/upgrade (PowerShell)

The previously installed skill folders already exist. Run from the
**extracted corrected** package directory:

```powershell
py -3 -m unittest discover -s tests -v
.\install.ps1 -Claude -Codex -Force
```

`-Force` creates timestamped backups before replacing installed skill folders.
It does not delete the canonical user database under `~/.adon-context/`.
Do not retry the installer using the previous ZIP.
