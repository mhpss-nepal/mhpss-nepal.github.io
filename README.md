# MHPSS Nepal monorepo foundation

This branch is an isolated, non-deployed foundation for the three static MHPSS Nepal applications. It combines their source-controlled files without changing runtime behavior, production URLs, or existing repositories.

## Architecture

| Source | Build destination | Address preserved |
|---|---|---|
| `apps/public/` | `dist/` | `/` |
| `apps/form/` | `dist/form/` | `/form/` |
| `apps/hub/` | `dist/hub/` | `/hub/` |

`apps/public/` is the former public repository root. `apps/form/` and `apps/hub/` are working-tree imports; their repository metadata was deliberately excluded. Git history import is deferred.

The build is a byte-for-byte static copy from one immutable Git commit (default: `HEAD`). It sanitizes inherited `GIT_*` variables, pins explicit Git/worktree paths, runs strict object verification, and independently recomputes commit, tree, and blob object IDs before use. The classified application file set is the reviewed `config/application-paths.json` manifest in the same commit; exactly those paths are mapped from `apps/public`, `apps/form`, and `apps/hub`, and every other blob fails closed. Hard limits bound file count, total and per-file bytes, path length/depth, Git output, time, and tree traversal. Unsafe, ambiguous, operational-data, credential, private-key, spreadsheet, delimited-data, snapshot, backup, export, and dump inputs are rejected.

The manifest exists so that landing a finished frontend commit is a reviewable data change rather than a Python edit. `scripts/land.py` is the only supported way to change the classified set: it verifies the source commit, applies the same classification/collision/exclusion/secret policy, proves per-file parity, records provenance, and refuses new cross-application runtime dependencies without an explicit recorded override. See `docs/LANDING.md`.

Path safety is complete: every Unicode control and format character (Unicode category `C*`), trailing dot or space, the full legacy Windows reserved-name set (`CON`, `PRN`, `AUX`, `NUL`, `CLOCK$`, `CONIN$`, `CONOUT$`, `COM1`–`COM9`, `LPT1`–`LPT9`, and their superscript variants), and any `.git` variant are rejected, and every classified path is checked against one combined `NFC(path).casefold()` key so case-folding and normalization collisions cannot reach two destinations.

Secret scanning is fail-closed and suffix-independent: every bounded blob — including allowlisted HTML, JavaScript, CSS, and binary files — is scanned for private keys, service-account material, AWS/GitHub/bearer tokens, and secret/token/password assignments. The only bypasses are two narrow, path-and-key-scoped exceptions, each recording why the material is knowingly public: the Firebase **web** config in `apps/*/assets/fb-config.js` may carry the public `apiKey` identifier. Any other secret assignment in those files, or the same text in any other path, still fails.

Classified JSON and `manifest.webmanifest` blobs are strictly parsed before any output exists; duplicate keys, non-finite values, and malformed JSON fail the whole build. The only JSON/JS data exceptions are the documented source-controlled synthetic demo files.

Files get mode `0644`, directories get mode `0755`, and copied mtimes are normalized to 2000-01-01 UTC. The output path must not exist. The builder verifies the output is absent, scans and verifies the entire committed source, and only then creates the output exactly once with exclusive directory-creation semantics, writing beneath its acquired descriptor. A rejected source therefore creates nothing. It never replaces, recursively deletes, exchanges, or mutates a pre-existing output. The deterministic JSON manifest records both files and directories and refuses canonical path collisions, so its structure is unambiguous.

Browser QA isolation lives in `tests/qa_harness.py`: a loopback listener on an operating-system-allocated port, an exact parsed-origin comparison (never a string prefix), a random nonce proving the listener's identity from the intended narrow fixture, a fixture scan for the same excluded content, and listener reaping plus fixture removal on teardown. The in-repo browser sweeps in `apps/*/tools/` allocate their port dynamically and use the same exact-origin check.

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

## NDRRMA capture handover (review artifact)

`scripts/ndrrma_capture.py`, `.github/workflows/ndrrma-weekly.yml` and
`tests/test_ndrrma_capture.py` move the weekly NDRRMA 5Ws capture onto
institution-owned, AI-free GitHub Actions and publish a public-safe aggregate
for Layer 3 to read statically. This is **not enabled and not pushed**: it is a
review artifact plus a Phase 2 plan, and one network assumption (whether a
GitHub-hosted runner can reach the public Power BI endpoint) remains unverified.
See `docs/NDRRMA-GITHUB-ACTIONS.md` for the artifact contract and the probe that
would settle reachability.

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

## Status: review artifact only

This branch is an unmerged, non-deployed review artifact. It fixes the code-level blockers the independent review gate recorded for the monorepo foundation; it does **not** merge, push, deploy, or integrate the rejected safety pair.

Two items remain deliberately open and are **not** resolved here:

- **Firestore Rules remain a deployment gate.** The authoritative rules are still unversioned and unverified in this monorepo; nothing here fabricates or replaces them. See `infra/README.md`.
- **Commit identity is an open institutional item.** The foundation commit's author/committer identity was recorded under a machine hostname rather than an accountable person. Accepting or re-attributing it is a governance decision for the institutional owner and is out of scope for this hardening change.

