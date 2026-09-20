# NDRRMA capture + publish on GitHub Actions (AI-free handover)

Status: **REVIEW ARTIFACT — NOT MERGED, NOT ENABLED, NOT DEPLOYED.**
Phase 2 (push) is a plan awaiting Adib's explicit go-ahead. See "Phase 2" below.

## Why this exists

Adib's end-state requirement is that the system keeps running automatically after his
two-month contract ends, with **no dependency on AI, on his laptop, or on the Thar Lay
server**. The weekly NDRRMA 5Ws capture already satisfies the AI-free half of that: it is
pure Python standard library and talks to the report's own *public* Power BI embed
endpoint with the embed's own public headers — no account, no token, no LLM.

What failed the handover test was the *host*: it ran under Adib's personal Hermes cron
(`9c6818dcc0ec`, Mondays 09:00 WIB) on the Thar Lay server, which stops when his contract
and access end. This change moves the same capture-and-publish chain onto
institution-owned, AI-free infrastructure: GitHub Actions under the `mhpss-nepal`
organisation.

## What is in this change

| Path | Purpose |
|---|---|
| `scripts/ndrrma_capture.py` | Standalone capture. No `~/.hermes`, no Hermes cron, no LLM, no secrets. |
| `scripts/ndrrma_dry_run.py` | Offline dry-run harness: proves per-day idempotence and the WIB guard with synthetic data only. |
| `config/ndrrma-powerbi-query.json` | The two public-embed semantic queries and the resource key, extracted verbatim from the working cron script. |
| `.github/workflows/ndrrma-weekly.yml` | The workflow: weekly schedule + `workflow_dispatch`, least privilege, pinned action SHA, commit-back only on real movement. |
| `tests/test_ndrrma_capture.py` | Failing-first offline tests for parse, disk, commit, and workflow contracts. |
| `.gitignore` | Whitelists the two public-safe artifact directories and the query config. |

## Behaviour preserved from the working script

1. **Read-only against the source.** The script only POSTs the report's own semantic query
   and parses the reply. It never writes to the source and stores no person-level data.
2. **Idempotent per source movement.** The ledger keys on `(data_date, source_payload_sha256)`.
   If the last ledger row already carries the same pair, **the run writes nothing at all** —
   no ledger row, no version file, no public artifact. That is what makes an unchanged week
   produce no commit and no notification.
3. **Append-only ledger.** `ledger.jsonl` only ever grows, in observation order; an existing
   row is never edited, reordered, or rewritten.
4. **Real freshness/provenance.** Every published record carries `capture_date`, `data_date`,
   `last_successful_refresh` and `success`. The site can therefore say "checked on X, source
   still carries data as of Y" instead of implying a trend.
   *Honest limit:* on this local path `success` is always `true`, because a failed fetch or
   parse writes **no record at all** and exits 2 (the failure is visible as a failed Actions
   run). The field exists so the Layer 3 contract has a place to render a stale or failed
   refresh; a captured-but-failed run does not yet write one.
5. **Pinned WIB timezone.** `WIB = UTC+07:00` is pinned in the script; `TZ` is never inherited.
   A UTC-labelled runner instant is still written and displayed as WIB.
6. **Explicit asset path.** The path comes from `--asset-dir` (default `data/ndrrma`), never
   from `__file__`. A missing directory is a hard failure, not something the script invents.
7. **Archive-root guard — retained, currently unused.** `require_archive_root()` is carried over
   and unit-tested, but the GitHub Actions chain performs **no** tar/archive step (there is no
   mirror sync here), so nothing on this path calls it. It is kept as a tested primitive for the
   next host that needs an archive swap — not as an active guard. Saying "preserved" would be
   true; implying it protects this pipeline would not.
8. **Exact read-back verification.** Every write is re-read and its SHA-256 compared against
   the bytes intended. A successful transfer is never treated as proof of correct content.
9. **Immutable version per record, not per minute.** A version filename is
   `<capture-stamp>-<sha256[:12]>.json`, so two movements inside one clock minute get distinct
   files. `_write_verified` additionally refuses to replace an existing `versions/*.json` with
   different bytes, so even a naming regression fails loudly instead of destroying history.
   `public/latest.json` is the one mutable pointer and `--verify` requires it to be a
   byte-for-byte copy of the newest version.

## Data contract for Layer 3

The workflow commits **three** files under `data/ndrrma/`:

```
data/ndrrma/public/latest.json          # the artifact Layer 3 consumes statically (mutable pointer)
data/ndrrma/versions/<stamp>-<hash>.json # immutable history, same record shape
data/ndrrma/ledger.jsonl                # append-only provenance ledger
```

`public/latest.json` (and each version record) has this shape:

```json
{
  "schema_version": 1,
  "capture_date": "2026-09-21T09:00+07:00",
  "data_date": "2026-09-19",
  "last_successful_refresh": "2026-09-21T09:00+07:00",
  "success": true,
  "source": {
    "name": "NDRRMA 5Ws public Power BI dashboard",
    "report": "Rasuwa Flood Response",
    "access": "public embed semantic query; read-only; no account or token"
  },
  "aggregates": {
    "mhpss_reached": 5830,
    "response_headline": 61612,
    "mhpss_activities": 233
  },
  "publication": {
    "classification": "public",
    "scope": "figures already published on the public NDRRMA dashboard",
    "note": "Sector reach is non-additive; never sum sector rows."
  }
}
```

Publication rules this artifact **obeys**, aligned with (not redefining) the Layer 3
rule-gated publishing design:

- **Only what was already public on the source dashboard is written.** The three aggregate
  figures above are the dashboard's own published numbers. No unpublished operational
  figures, no per-actor rows, no geography rows, no person-level data.
  *Enforcement:* `--verify` accepts the `aggregates` map only if its keys are exactly those
  three (`mhpss_activities`, `mhpss_reached`, `response_headline`) — an allowlist, not a
  substring check, so a differently-named extra key fails rather than silently committing.
  Note the *control plane* (the query config) does name sectors, because the query filters on
  them; the *published* artifact does not.
- **The `success` flag is part of the contract.** Layer 3 must be able to render a failed or
  stale capture as "not refreshed" rather than showing the last good figure as current.
- **Both dates are always shown.** `data_date` is the source's own refresh date and often does
  not advance because the report's refresh is disabled; `capture_date` is when we looked.
- **No additive claims.** MHPSS sector reach is a max-per-location measure, so the artifact
  deliberately carries no sector breakdown and no derived total. Cross-dimension sums disagree
  by design; the response-wide headline is a separate, separately-published figure.
- **Versioning.** Each movement lands a new immutable `versions/<stamp>-<hash>.json`; the prior
  version is never overwritten or edited. `public/latest.json` is the single mutable pointer and
  must always be a byte-for-byte copy of the newest version (enforced by `--verify`).

Layer 3's own rules — who may publish, gating, suppression, and the deployed rollout — are
unchanged and remain `BLOCKED — DECISION`. This document specifies only the artifact that
Layer 3 *may* consume; it does not invent or relax any publishing rule.

## How to run it here (no network, no real source)

```bash
# Failing-first / regression tests (synthetic fixtures only)
python3 -m unittest tests.test_ndrrma_capture -v

# Offline dry run: unchanged run, moved run, and the UTC-runner WIB guard
TZ=UTC python3 scripts/ndrrma_dry_run.py

# Offline capture against synthetic fixtures, into a throwaway directory
mkdir -p /tmp/ndrrma-check
python3 scripts/ndrrma_capture.py --asset-dir /tmp/ndrrma-check \
  --sector-fixture /tmp/sector.json --date-fixture /tmp/date.json \
  --capture-time 2026-09-21T09:00:00+07:00

# Strict read-back validation of committed artifacts (this is the workflow's
# second step); exit 2 and a diagnostic on any mismatch, never a false pass
python3 scripts/ndrrma_capture.py --asset-dir data/ndrrma --verify
```

The real run (what the workflow does) needs the network:

```bash
mkdir -p data/ndrrma
python3 scripts/ndrrma_capture.py --asset-dir data/ndrrma
```

## What could NOT be verified from here

**Open question — can a GitHub-hosted runner reach the Power BI public endpoint at all?**

Everything on the GitHub side that can be checked without pushing has been checked: the
workflow is syntactically valid, permissions are least-privilege, the single `uses:` is pinned
to a full commit SHA, no `secrets.*` is referenced, and the commit-back step is fully
exercised locally against a throwaway repository (new file → commit, unchanged → no commit,
moved source → commit). The capture/parse/disk paths are covered by offline tests.

What is **not** verified — and cannot be from here — is outbound reachability from a GitHub-hosted
runner to:

```
POST https://wabi-north-europe-j-primary-api.analysis.windows.net/public/reports/querydata?synchronous=true
```

`analysis.windows.net` legitimately serves this endpoint with no credentials, and it is reached
from the Thar Lay server today, but a cloud egress IP range may be treated differently. This
cannot be settled by reading code, by a local `curl` (which would only prove *this* host can
reach it), or by inspection of the workflow. It requires one real run on real runner egress.

**The probe that would settle it** is the smallest possible one, and it needs an actual push to
a **test repository** (never `mhpss-nepal.github.io`):

1. Create a scratch repository under the `mhpss-nepal` organisation, e.g. `ndrrma-egress-probe`.
2. Add a `workflow_dispatch`-only workflow that runs a single bounded request to the endpoint
   above with the public embed headers (`X-PowerBI-ResourceKey`), with a 30-second timeout, and
   prints the HTTP status and the first 200 bytes of the body. No repository write, no commit.
3. Run it once. **HTTP 200 with a JSON body = reachable** (the capture can be enabled). A
   connection timeout, TLS/SNI failure, or an HTML/`403` body = **not reachable from
   GitHub-hosted runners**, in which case the fallback is either a GitHub self-hosted runner
   inside institution infrastructure, or keeping the capture where it already works.
4. Record the run URL and the observed status as the evidence.

That push is Phase 2 and is gated on Adib's go-ahead. Until the probe passes, **this change
must not be described as solving the handover**: it is the institution-owned, AI-free chain,
with one named, unverified network assumption.

## Phase 2 — push plan (needs Adib's explicit go-ahead; NOT executed)

**Step 0 — answer reachability first, in a scratch repository.**

Do not enable the real workflow on faith. Create `mhpss-nepal/ndrrma-egress-probe` and run the
probe above. If it does not return HTTP 200, stop: the fallback is a self-hosted runner inside
institution infrastructure, or leaving the capture where it already works. Only a passing probe
justifies Step 1.

**Step 1 — the real workflow (only after Step 0 passes).**

**Repository and path.**

- Repository: `mhpss-nepal/mhpss-nepal.github.io` (the public site's own repository, which is
  already the Layer 3 publication surface).
- Path: exactly the files in the "What is in this change" table above. No other paths.

**Permissions.**

- Workflow `permissions: contents: write` only; the `GITHUB_TOKEN` is used solely for the
  commit-back push. No PAT, no deploy key, no service account, no third-party secret.
- Branch protection: if the default branch is protected, the bypass that will actually be
  needed is for the **GitHub Actions bot** (`github-actions[bot]`, app id `41898282`), because
  that is the identity the commit-back uses with `github.token`. Without a bypass or an
  allowed push, the push is rejected — safely (no commit lands), but the automation is then
  dead and the probe passing would have been wasted.
- `persist-credentials: false`, and the token is passed only on the explicit `git push` URL.
  Note that a URL-embedded token is visible in the runner process's argv; acceptable on a
  hosted runner, but do not add `set -x` to that step.

**Evidence that a first run worked (all four, in order).**

1. The Actions run log shows the capture step exiting 0 and a `changed: true` JSON line.
2. Exactly one new commit `data: capture NDRRMA public aggregates` touching only `data/ndrrma/`.
3. `data/ndrrma/public/latest.json` carries today's `capture_date`, a `data_date` no later than
   it, `success: true`, and exactly the three aggregate keys.
4. A second, immediate manual `workflow_dispatch` run produces **no** new commit and logs
   "NDRRMA public source is unchanged; no commit required."

**Rollback.**

- Immediate: `workflow_dispatch` → *Disable workflow* in the Actions tab (or delete the workflow
  file in a reviewed commit). No data is lost; the last capture stays committed.
- Full: `git revert` the commit that added `.github/workflows/ndrrma-weekly.yml`. The artifacts
  left in `data/ndrrma/` are inert static files and can stay or be reverted separately.
- The capture is non-destructive and read-only, so rollback never needs to undo a source change.

**Explicitly still blocked and not part of Phase 2.** Firestore Rules, the staging domain, cache
activation, and the deployed site rollout remain `BLOCKED — DECISION`.

## Hard constraints honoured by this change

- No production ref touched (public `68bf197`, form `9032bb7`, hub `ff2d4e2`); no push, PR,
  merge, or deploy was performed.
- No credentials, tokens, or service accounts added to the repository. The only values written
  are the public embed's own public identifiers, already published in the source script.
- Synthetic data only in tests; no person-level data captured or stored.
- `dist/` remains generated and untracked; nothing here deploys or integrates the applications.
