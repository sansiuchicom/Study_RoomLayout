# Migration Log

Trail of how predecessor repos and individual modules entered `Study_RoomLayout`.

## 2026-05-24 — Repo initialization

- `git init` at `/workspace/Study_RoomLayout/`.
- Initial commit: `README.md` + `MIGRATION_LOG.md`.

## 2026-05-24 — Subtree merge: `Study_RoomLayout_proto3` → `archive/proto3/`

- Source: `/workspace/Study_RoomLayout_proto3` @ branch `main`.
- Method: `git subtree add --prefix=archive/proto3 proto3 main`.
- Full git history preserved. Use `git log -- archive/proto3/...` to inspect.
- Treat as **read-only**: do not edit files under `archive/proto3/`. Cherry-pick
  decisions / modules into `src/` (or root-level docs) with a new entry in this
  log noting source path + commit hash.

## 2026-05-24 — Subtree merge: `Study_RoomLayout_Cell` → `archive/celllayout/`

- Source: `/workspace/Study_RoomLayout_Cell` @ branch `master`.
- Method: `git subtree add --prefix=archive/celllayout cell master`.
- Full git history preserved. The algorithm code lives at
  `archive/celllayout/algorithm/celllayout_tf/`.
- Treat as **read-only**: same convention as proto3.

## Convention for future entries

When porting a file or decision from `archive/` into the live tree, append:

```
## YYYY-MM-DD — <short title>

- Source: archive/<repo>/<path> @ <commit-hash-or-HEAD>
- Destination: <new path>
- Changes: (none | brief diff summary)
- Rationale: (one sentence, why this lands now)
```
