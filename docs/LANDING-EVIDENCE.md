# Landing evidence — verified frontend landing procedure

- **Task:** `t_a9ad70f3` — Build verified frontend landing procedure (so install is mechanical)
- **Branch:** `stabilization/monorepo-foundation`
- **Base:** `96e721cbfbcee9a7bb7bce573dcb062bf8d9040e` (t_b23722a7 head)
- **Head:** `5dfbb813642e2310db8c3641e7f46b43c3e73b65` (local commit; not pushed)
- **Generated:** 2026-09-20
- **Result:** DONE — REVIEW ARTIFACT. No push, merge, deploy, or production ref change.

## What shipped

| File | Purpose |
|---|---|
| `scripts/land.py` | The verified landing tool (dry-run default; `--apply` writes the monorepo working tree only) |
| `config/application-paths.json` | The classified `apps/` allowlist, moved out of `layout.py` into reviewed data |
| `provenance/frontend-sources.json` | Provenance records (repo, commit, timestamp, author, re-derive command) |
| `docs/LANDING.md` | The runbook |
| `tests/test_land.py` | 16 focused tests, including the adversarial cases below |
| `tests/fixture_repo.py` | Fixture now seeds `config/` and `provenance/` and provides `write_path_manifest` |

`scripts/layout.py` now reads the classified path list from
`config/application-paths.json` **inside the resolved commit tree**, so a landing
adds paths through a reviewable manifest change rather than a Python literal, and
a dirty worktree cannot alter what the builder accepts.

## Focused test run

```
$ python3 -m unittest discover -s tests -p 'test_land.py'
................
----------------------------------------------------------------------
Ran 16 tests in 3.1s

OK
```

## Failing-first proof

Against the pre-task baseline `96e721cb` (hardened builder, no landing tool, no
manifest), copying only the new tests:

```
$ python3 -m unittest discover -s tests -p 'test_land.py'   # cwd = baseline worktree
FileNotFoundError: '/tmp/land-baseline2/config/application-paths.json'
Ran 1 test in 0.000s
FAILED (errors=1)
```

The baseline has no `scripts/land.py` and no `config/application-paths.json`, so
the adversarial suite cannot pass before this change.

## Adversarial cases (each fails closed)

| Case | Test | Result |
|---|---|---|
| wrong / short / branch / unreachable SHA | `test_rejects_branch_short_sha_and_missing_full_sha` | refused |
| wrong source repository identity | `test_rejects_wrong_repository_identity` | refused |
| dirty source, dirty monorepo | `test_rejects_dirty_source_and_dirty_destination` | refused |
| unclassified file kind (`payload.exe`) | `test_unclassified_file_fails_closed` | refused |
| canonical path collision (`Note.html`/`note.html`) | `test_path_collision_fails_closed` | refused |
| secret-shaped blob | `test_secret_shaped_blob_fails_closed` | refused |
| file dropped from the import | `test_parity_check_rejects_a_dropped_file` | refused |
| gitlink / submodule entry | `test_gitlink_submodule_entry_fails_closed` | refused |
| `.git` metadata path in the tree | `test_repository_metadata_path_fails_closed` | refused |
| new cross-app runtime dependency | `test_new_form_hub_asset_dependency_requires_recorded_override` | refused without override; passes with a recorded one |
| a remote/rewriting git subcommand | `test_no_remote_or_rewriting_git_subcommand_is_used` | proven absent by AST scan |

## Real dry-run landings

Source worktrees were clean detached checkouts at the exact commit
(`git worktree add --detach <path> <FULL_SHA>`). Commands run from the monorepo
working tree; the monorepo stayed clean throughout.

```
# public
python3 scripts/land.py --monorepo . --source-repo /tmp/land-public \
  --commit 252a811cb1fc3e173799d84aca8f0ccab51c5ca5 --target-app public
# form
python3 scripts/land.py --monorepo . --source-repo /tmp/land-form \
  --commit 0bb8771fb6e7501b4cb82ad4a7545c6f3c45b2a6 --target-app form
# hub
python3 scripts/land.py --monorepo . --source-repo /tmp/land-hub-clean \
  --commit ff2d4e2a43327ddc99330f83660ec75abd53a762 --target-app hub
```

| Target | Source commit | Author | Timestamp | Files before → after | added / changed / removed | Cross-app refs | Parity |
|---|---|---:|---:|---:|---:|---:|---|
| public | `252a811cb1fc3e173799d84aca8f0ccab51c5ca5` | Adib Asrori | 2026-09-20T05:11:40Z | 54 → 54 | +0 / ~11 / −0 | 3 → 3 | verified |
| form | `0bb8771fb6e7501b4cb82ad4a7545c6f3c45b2a6` | Thar Lay | 2026-09-20T05:34:59Z | 26 → 52 | +26 / ~2 / −0 | 17 → 17 | verified |
| hub | `ff2d4e2a43327ddc99330f83660ec75abd53a762` | Adib Asrori | 2026-09-18T10:21:37+05:45 | 40 → 40 | +0 / ~12 / −0 | 7 → 7 | verified |

- `public` changed paths: `.gitignore`, `access-explained.html`, `assets/design.css`,
  `assets/fb-config.js`, `assets/i18n-strings.js`, `assets/public-read.js`,
  `assets/referral-map.js`, `assets/site.css`, `flood-response.html`,
  `tools/contrast-sweep.py`, `tools/justify-sweep.py`.
- `form` new classified paths (26): `5ws-report-b2.html` plus 25 files under
  `design-preview/` (preview CSS/JS, build and check scripts, PNG evidence, the
  preservation inventory and the pending hub patch note).
- `hub` changed paths include `README.md`, `access.html`, `assets/fb.js`,
  `assets/store.js`, `index.html`, `tools/rail.py` (same lineage divergence below).

### Fail-closed demonstration on a real branch

The hub `stabilization/trial-safety` commit `52ff901013d6d6325d6abc7a3193a556e04acc31`
contains `release-contract.json`. The landing correctly refused it:

```
land failed: excluded content refused by policy: apps/hub/release-contract.json
```

### Rehearsed apply (throwaway worktree)

```
git worktree add --detach /tmp/land-rehearsal-3 5dfbb81
python3 scripts/land.py --monorepo . --source-repo /tmp/land-public \
  --commit 252a811... --target-app public --apply
python3 scripts/land.py --monorepo . --source-repo /tmp/land-form \
  --commit 0bb8771... --target-app form --apply
# commit both landings, then:
python3 scripts/build.py    --commit "$(git rev-parse HEAD)"   # rc 0
python3 scripts/validate.py --commit "$(git rev-parse HEAD)"   # "validation passed"
```

The rehearsal manifest grew to **146 classified paths**; the tool's own
`build.py` and `validate.py` both accepted the landed tree, proving the builder
consumes what the landing produced. The commit is capped by `MAX_FILES = 4096`
and traversal by `MAX_TRAVERSAL_WORK = 256`, which is comfortable: the current
tree traverses 120 entries and the merged rehearsal tree 146.

## Lineage divergence (recorded, not silent)

The monorepo's committed `apps/` trees are not byte-identical to the frontend
repository commits in the provenance table, because the foundation commit
deliberately changed them: it removed "this branch must not be deployed" wording
the public/hub sources still carried, and replaced frontend fixed-port browser
sweeps with dynamic-port ones. A dry run from the upstream base therefore reports
those paths as *changed*, and an apply would revert that hardening:

| App | Divergent committed paths |
|---|---|
| public | `.gitignore`, `access-explained.html`, `assets/fb-config.js`, `assets/public-read.js`, `tools/contrast-sweep.py`, `tools/justify-sweep.py` |
| form | `.gitignore` |
| hub | `.gitignore`, `README.md`, `access.html`, `assets/design.css`, `assets/fb-config.js`, `assets/fb.js`, `assets/store.js`, `forms.html`, `index.html`, `tools/contrast-sweep.py`, `tools/justify-sweep.py`, `tools/rail.py` |

`docs/LANDING.md` records this as a required precondition: land only from a branch
that contains the foundation commit, or accept the revert explicitly. Because the
tool lists every changed path, the decision is always visible.

## Constraints honoured

- No push, merge, deploy, tag, or remote mutation. The landed changes are a local
  commit `5dfbb81` on `stabilization/monorepo-foundation` only.
- Production refs unchanged: public `68bf197abe56dd0265dca245e61809100b4c3901`,
  form `9032bb7a3e198882cce8ca1bf350621aba856db7`,
  hub `ff2d4e2a43327ddc99330f83660ec75abd53a762`.
- Worktrees clean at end (see the task's closing `git status`).

## Open items (unchanged, out of scope)

- Firestore Rules remain a deployment gate (BLOCKED — DECISION).
- Commit identity governance (machine hostname) remains open.
- Staging domain / cache activation and deployed rollout remain BLOCKED — DECISION.
