# Landing a finished frontend commit into the monorepo

This runbook is the required, verified procedure for installing a finished
frontend branch into this monorepo. It exists because the monorepo does **not**
consume the frontend branches live: `apps/public`, `apps/form` and `apps/hub`
are snapshots of separate repositories, so a finished branch (for example
`design/public-layer3` or `design/form-frontend`) will not appear in a monorepo
build until it is imported with the audited step below.

Nothing here merges, pushes, deploys, or touches production. The landing tool
only writes the monorepo working tree and a local commit intent; publishing
remains a separate, gated decision.

## Tool

`scripts/land.py` (dry-run by default; `--apply` mutates only the monorepo
working tree). It is the *only* supported way to change the classified `apps/`
file set. The builder (`scripts/build.py`) and validator (`scripts/validate.py`)
read the classified path list from `config/application-paths.json`, so landing a
commit is a two-step, reviewable change: the imported tree plus a one-record
manifest update plus a provenance record.

## Source specification (all arguments are mandatory)

| Argument | Meaning |
|---|---|
| `--monorepo` | the monorepo worktree to land into (must be clean) |
| `--source-repo` | a clean worktree of the source repository |
| `--commit` | the source commit as **exact full 40-hex SHA** |
| `--target-app` | `public`, `form`, or `hub` |
| `--apply` | write the landing (omit for a dry run) |
| `--acknowledge-cross-app-dependency TEXT` | required only when the landing adds a new cross-application runtime reference |

The tool **refuses**: a branch/tag/short/unpinned ref; a commit that does not
exist or is not reachable; a source whose `origin` is not the expected repository
for the target app (`mhpss-nepal/mhpss-nepal.github.io`, `mhpss-nepal/form`,
`mhpss-nepal/hub`); a dirty source worktree; and a dirty monorepo. An empty or
short SHA fails before any Git call.

### Obtaining a clean source worktree

The live worktrees are often dirty (for example an untracked session file). Land
from a clean checkout at the exact commit instead of from the working tree:

```bash
git -C <source-worktree> worktree add --detach /tmp/land-src <FULL_SHA>
```

That checkout shares the source repository's `origin` remote (so the identity
check passes) and is clean by construction.

## Procedure

```bash
# 1. Dry run: read the provenance, changes, and per-file parity proof. No writes.
python3 scripts/land.py \
  --monorepo . \
  --source-repo /tmp/land-src \
  --commit <FULL_SHA> \
  --target-app public

# 2. Review the JSON: source commit/timestamp/author, previous vs candidate file
#    counts, added / removed / changed paths, new classified paths, and the
#    cross-application reference delta.

# 3. Apply on a throwaway worktree first if you want a rehearsed result.
git worktree add /tmp/land-rehearsal stabilization/monorepo-foundation
python3 scripts/land.py --monorepo /tmp/land-rehearsal \
  --source-repo /tmp/land-src --commit <FULL_SHA> --target-app public --apply

# 4. Apply for real (monorepo working tree only).
python3 scripts/land.py --monorepo . \
  --source-repo /tmp/land-src --commit <FULL_SHA> --target-app public --apply

# 5. Commit the landing locally, then prove the committed tree builds and
#    validates from the same immutable revision.
git add -A
git commit -m "Land <app> frontend <FULL_SHA>"
python3 -m unittest discover -s tests
python3 scripts/build.py --commit "$(git rev-parse HEAD)"
python3 scripts/validate.py --commit "$(git rev-parse HEAD)"
```

`dist/` is generated, untracked, and never committed.

## What the tool guarantees

1. **Explicit source.** Full SHA only, plus a repository-identity check and a
   clean-worktree check on both sides.
2. **Provenance.** Records `repository`, `repository_key`, `commit`,
   `commit_timestamp` and `author` in `provenance/frontend-sources.json`, plus a
   `rederive_command` that reproduces the import.
3. **Source-controlled file set only, fail-closed classification.** Reuses the
   builder's `_validate_git_path`, canonical collision registry, forbidden-path
   and forbidden-content policy, and strict structured-data parsing. Applies an
   application-asset extension allowlist; anything else is an import error. Files
   outside the classified manifest are reported as `new_classified_paths` and
   added to the manifest, so the change is explicit and reviewable.
4. **Exact parity.** The materialised target is re-read and must match the source
   commit per file (path, length, SHA-256); any missing, extra, or altered file
   fails the landing. The report lists added / removed / changed paths versus the
   previous monorepo snapshot so a dropped file cannot pass unnoticed.
5. **Repository metadata excluded.** The import is by file, so `.git`, gitlinks,
   submodules and non-regular modes never appear; the `rederive_command` records
   how to reproduce the import.
6. **Cross-application runtime contract.** If the landed tree references a
   sibling application path that the previous monorepo snapshot did not (for
   example Form loading `../hub/assets/new-runtime.js`), the landing is refused
   unless `--acknowledge-cross-app-dependency` carries an explicit override text,
   which is recorded in the runbook and in the report.
7. **No production action.** The tool never runs `push`, `merge`, `deploy`,
   `fetch`, or any remote operation; it only writes local files.

## Adversarial tests

`tests/test_land.py` is committed as failing-first coverage and must pass:

- wrong / missing / short / branch SHA and an unreachable commit → refused;
- wrong source repository identity → refused;
- dirty source and dirty monorepo → refused;
- unclassified file kind → refused;
- path collision under the canonical key → refused;
- a secret-shaped blob → refused;
- a dropped file detected by the parity check → refused;
- a new cross-application dependency without and then with a recorded override;
- dry run leaves HEAD and the worktree unchanged; apply replaces the target,
  updates the manifest, records re-derivable provenance, and leaves a local
  change set for review.

## Procedural preconditions

- **Land only from a branch that contains the foundation commit.** The monorepo's
  committed `apps/` trees are *not* byte-identical to the frontend repository
  commits recorded in the provenance table: the foundation commit deliberately
  changed some of them (for example it removed "this branch must not be deployed"
  wording that the public/hub sources still carried, and it replaced several
  fixed-port browser sweeps with dynamic-port ones). Landing a branch cut at the
  *original* upstream base therefore reverts that hardening. Either land from a
  branch that already contains the foundation commit, or accept the revert
  explicitly in review — the tool's `changes` report names every changed path so
  the decision is visible, never silent.
- **The source worktree must be clean.** Live worktrees often carry an untracked
  session file (for example `COMMIT-BEFORE-CLOSE.md`), which the tool correctly
  refuses. Use a detached checkout at the exact commit.

## Current frontend landing examples (dry run)

See `docs/LANDING-EVIDENCE.md` for the recorded commands and exact before/after
path counts of real dry-run landings against current frontend commits.
