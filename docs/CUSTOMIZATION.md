# Customization

SafaraKeet keeps customization intentionally small and local.

## Appearance

The Settings sheet provides theme and skin controls. Theme chooses dark, light,
or system appearance. Skin changes semantic accent and glass-lighting tokens:

- Pickle: moss-green live state and soft violet depth.
- Graphite: neutral silver glass.
- Frost: cool blue glass.

New skins should override semantic CSS variables such as `--app-bg`,
`--glass-fill`, `--glass-stroke`, `--glass-highlight`, `--text`, `--text-muted`,
`--accent`, `--danger`, and `--record-ring`. Do not fork component markup for a
color change.

## Storage

SQLite on the Mac is the canonical transcript store. Active and archived items
survive browser refreshes and service restarts. Archive is reversible; Delete is
not. Browser storage must not become a second history database. A future recovery
draft cache may store only the current unsaved partial and must remain optional
and clearable.

JSONL is appropriate for a future explicit export/import feature, not live
storage: it does not provide the indexed updates needed for archive, restore, and
concurrent requests.

## Runtime

The backend remains on loopback. Change the local port only for the current
shell or local service configuration, then rerun the private-share command with
the same port. Use `<local-port>` in shared instructions and logs.
