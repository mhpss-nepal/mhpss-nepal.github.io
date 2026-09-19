# MHPSS Nepal monorepo foundation

This branch is an isolated, non-deployed foundation for the three static MHPSS Nepal applications. It combines their source-controlled files without changing runtime behavior, production URLs, or existing repositories.

## Architecture

| Source | Build destination | Address preserved |
|---|---|---|
| `apps/public/` | `dist/` | `/` |
| `apps/form/` | `dist/form/` | `/form/` |
| `apps/hub/` | `dist/hub/` | `/hub/` |

`apps/public/` is the former public repository root. `apps/form/` and `apps/hub/` are working-tree imports; their repository metadata was deliberately excluded. Git history import is deferred.

The build is a byte-for-byte static copy from one immutable Git commit (default: `HEAD`). It sanitizes inherited `GIT_*` variables, pins explicit Git/worktree paths, runs strict object verification, and independently recomputes commit, tree, and blob object IDs before use. Exactly 120 classified application files are mapped from `apps/public`, `apps/form`, and `apps/hub`; extra blobs fail closed. Hard limits bound file count, total and per-file bytes, path length/depth, Git output, time, and tree traversal. Unsafe, ambiguous, operational-data, credential, private-key, spreadsheet, delimited-data, snapshot, backup, export, and dump inputs are rejected. The only JSON/JS data exceptions are the documented source-controlled synthetic demo files.

Files get mode `0644`, directories get mode `0755`, and copied mtimes are normalized to 2000-01-01 UTC. The output path must not exist. The builder opens a real parent directory, creates the output exactly once with exclusive directory-creation semantics, and writes beneath its acquired descriptor. It never replaces, recursively deletes, exchanges, or mutates a pre-existing output. A failed fresh output may remain for manual inspection and removal. The JSON manifest is deterministic and unambiguous.

Trust boundary: the generator assumes repository metadata, Git objects, and acquired file descriptors are not maliciously mutated by another process running as the same operating-system user while a build is in progress. Descriptor-relative, no-follow, exclusive operations reject or contain tested path substitutions, but this is not a sandbox against a fully malicious same-UID process that can alter files or act through `/proc` after descriptor acquisition. Run builds in a trusted, single-writer workspace.

## Commands

Only the Python 3 standard library is required; no package or network install is needed.

```bash
# Tests
python3 -m unittest discover -s tests -v

# Fresh build into an absent path from committed HEAD
python3 scripts/build.py

# Or pin both operations to the same full commit ID
python3 scripts/build.py --commit "$(git rev-parse HEAD)"

# Validate exact committed-source/output parity and required addresses
python3 scripts/validate.py --commit "$(git rev-parse HEAD)"

# Inspect a deterministic JSON content manifest
python3 scripts/build.py --manifest dist
```

`dist/` is generated and intentionally untracked. Nothing in this foundation deploys, pushes, or merges.

## V2 executable contracts

The local-only V2 backend contract reference is documented in
[`docs/V2-CONTRACTS.md`](docs/V2-CONTRACTS.md). Its Python standard-library
modules model immutable UUIDv7 event envelopes, explicit sync states, a
transactional source/outbox boundary, exact-body ingestion acknowledgement,
immutable correction projections, data-quality work, reconciliation, and an
atomic cache/release contract. They use synthetic fixtures and have no network
or production integration.

```bash
python3 -m unittest discover -s tests/v2_contract -p 'test_*.py' -v
```

This is an executable review artifact, not a selected production runtime. The
browser IndexedDB implementation, production datastore/runtime, authorization,
retention, institutional ownership, and deployment remain blocked decisions.
The current candidate is held after two independent adversarial review rounds;
see `docs/V2-EVIDENCE-LEDGER.md` for the preserved blocking findings.

## Access ownership target

The Firebase bridge has no personal-email exception or privileged client-side
identity path. Its role controls express client intent only. The authoritative
Firestore Rules and role-key scheme are not versioned here, so server enforcement
is unverified. This non-deployed branch does not migrate credentials or change
production Rules.

## Provenance

Imported on the foundation branch from these local working trees:

| Application | Source | Source commit | Imported source-controlled files |
|---|---|---|---:|
| public | repository root before relocation | `68bf197abe56dd0265dca245e61809100b4c3901` | 54 |
| form | `/root/mhpss-nepal-audit-20260918/form` | `9032bb7a3e198882cce8ca1bf350621aba856db7` | 26 |
| hub | `/root/mhpss-nepal-audit-20260918/hub` | `ff2d4e2a43327ddc99330f83660ec75abd53a762` | 40 |

The form and hub source worktrees were clean. Generated `tools/__pycache__/` files present outside source control were not imported. No raw operational or clinical data was read or copied; the hub's source-controlled synthetic `data/demo.json` and `data/demo.js` remain included.

## Current cross-application dependencies and blockers

The layout preserves today's addresses, so existing relative links continue to resolve in `dist/`; it does not yet make the applications independently buildable.

- Form pages and `sw.js` load shared runtime assets from `../hub/assets/` (resolved as `/hub/assets/` from `/form/`). These include design/app/form CSS; code lists; Layer 1 helpers; QR, store, Firebase bridge/config; branding, marks, icons, and i18n files. The service worker also precaches those cross-app URLs.
- Hub pages link to `../form/` and individual form pages. Hub navigation links to the public root with `../`; `access.html` links to public `../access-explained.html`.
- `apps/hub/index.html` dynamically loads the public renderer at `../assets/public-read.js` when publishing Layer 3 output.
- Public pages link to `form/` and `hub/`; `apps/public/method.html` links into `hub/docs/DATA_MODEL.md`.
- The form deploy checks assume the hub is a sibling directory. Those assumptions remain intentionally unchanged for this foundation.

Until these boundaries are made explicit in a later change, form and hub cannot be moved, versioned, or deployed independently without coordinating their sibling assets and URLs. Existing application checks also remain app-local and must be run from each app directory when source changes.
