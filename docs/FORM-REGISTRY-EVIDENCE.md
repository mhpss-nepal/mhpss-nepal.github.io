# Form registry — executable evidence

Status: **DONE — REVIEW ARTIFACT** (held pending independent review)
Task: `t_abf0b818` (recovery card; supersedes `t_d3d2bbfb`, which stalled on a
provider-judge infrastructure fault and was escalated to triage — the work itself
was never found defective).
Design under test: `docs/FORM-REGISTRY-DESIGN.md`
Registry: `config/form-registry.yaml`
Validator: `packages/form_registry/form_registry.py`
WIP checkpoint preserved by the operator: `2184d5a` (unescaped fork parent of
this evidence; the four source files above were **not** rebuilt here).

Scope of this card was bounded to running the suites, confirming the design's
three claims, and committing the evidence. No hardening round, no new item
families, no production read/write, no network.

## 1. Suites — commands and actual results

Run from the repository root of this worktree
(`/root/mhpss-nepal-work/v2-authority-redesign`, branch
`architecture/v2-immutable-authority`).

| Command | Result |
|---|---|
| `python3 -m unittest tests.test_form_registry -v` | **Ran 10 tests … OK** (exit 0) |
| `PYTHONPATH=tests python3 -m unittest discover -s tests/v2_contract -p 'test_*.py' -v` | **Ran 59 tests … OK** (exit 0) |
| `python3 -m unittest discover -s tests -v` | **Ran 167 tests … OK** (exit 0) |

The `tests/v2_contract` suite is registered as a package (`tests/v2_contract/__init__.py`)
and is invoked both ways the repo documents it:
`discover -s tests/v2_contract -p 'test_*.py'` (README:55) and
`discover -s tests/v2_contract -t tests/v2_contract`, with `PYTHONPATH=tests`
so the shared `fixture_repo` helper resolves. Both forms report 59 passed.

Raw transcription (exact tail) captured locally under
`evidence/form-registry/` (`focused-registry.txt`, `v2-contract.txt`,
`full-suite.txt`); the results are reproduced verbatim below.

```
python3 -m unittest tests.test_form_registry -v
...
Ran 10 tests in 0.013s

OK

PYTHONPATH=tests python3 -m unittest discover -s tests/v2_contract -p 'test_*.py' -v
...
Ran 59 tests in 1.036s

OK

python3 -m unittest discover -s tests -v
...
Ran 167 tests in 238.756s

OK
```

## 2. The design's three claims, each made falsifiable

The full design (`docs/FORM-REGISTRY-DESIGN.md`) makes one executable guarantee,
stated three ways: *stored but never read* is a defect the validator must catch.
Each claim was tested by mutating the real registry in memory and re-running the
real `validate_registry`, not by reading source.

Probe: `/tmp/probe_claims.py` (baseline registry first accepted, then each
mutation). Actual output:

```
baseline (unmutated registry): ACCEPTED (valid)
  form invents a reading home key                         -> REJECTED: form activity-5ws: unknown reading_home hub.invented.home
  form routed to a home that does not accept its kind      -> REJECTED: form activity-5ws: reading_home does not accept kind activity
  home drops its only accepted kind (empty list)           -> REJECTED: home hub.dashboard.reports: accepted_kinds is required
  home file does not exist                                 -> REJECTED: home hub.dashboard.reports: path does not exist
  home selector does not exist                             -> REJECTED: home hub.dashboard.reports: selector id="no-such-anchor" does not exist
  form file does not exist                                 -> REJECTED: form activity-5ws: file_path does not exist
```

Mapping to the claims:

- **A form cannot invent a reading home** — a `reading_home` that is not a key in
  the top-level `homes` map is rejected (`unknown reading_home`). A form also
  cannot point at a real home whose `accepted_kinds` does not include its `kind`
  (`does not accept kind`).
- **A reading home cannot silently drop a form** — a home that stops accepting the
  kind becomes invalid (`accepted_kinds is required` when emptied; `does not accept
  kind` when mismatched), so the pairing is enforced from both directions rather
  than only on the form side.
- **A missing file or selector fails validation** — a home `path` that does not
  exist, a `file_path` that does not exist, or a `selector` string absent from the
  file all fail closed with a named error.

The checker is therefore **not vacuous**: three deliberately planted defects each
produce the specific failure the design promises, while the unmutated registry is
accepted.

## 3. Generator reproducibility

```
python3 packages/form_registry/form_registry.py config/form-registry.yaml --root . \
  --render /tmp/regen.html
# registry validation passed: 5 forms, 5 homes   (exit 0)

diff /tmp/regen.html prototypes/form-registry/generated-field-landing.html
# IDENTICAL (reproducible)
```

The committed fixture `prototypes/form-registry/generated-field-landing.html`
contains exactly the one `approved-for-trial` + `field_landing: true` card (the
5Ws form), and regenerating it is byte-identical. No live page, QR sheet, or
service-worker precache is touched.

## 4. Environment fault found and cleared (not a code defect)

The first `python3 -m unittest discover -s tests` run of this card **failed 1 of
167**:

```
FAIL: test_browser_helpers_serve_the_application_root_from_any_cwd
        (relative='apps/hub/tools/justify-sweep.py')
AssertionError: 1 != 0 : ... NOT FLUSH: 2
    forms.html   390px  p  align=start  Error code explanation: 404 - Nothing matches
    access.html  390px  p  align=start  Error code explanation: 404 - Nothing matches
FAILED (failures=1)
```

Root cause, established before repairing anything: the two QA helpers
`apps/public/tools/justify-sweep.py` and `apps/hub/tools/justify-sweep.py` both
hard-code `PORT = 9071`. A **leaked orphaned server** from a prior session
(`pid 922395`, started 2026-09-20 08:04, parent = the user systemd session, not
this run) was still listening on `127.0.0.1:9071`, serving
`…/v2-authority-redesign/apps/public`. The hub helper's `wait_for_server()` probe
is answered by that foreign server, so its Playwright load fetched the **public**
tree, where `forms.html` and `access.html` (and `id="p-raw"` etc.) do not exist —
hence the literal `http.server` 404 body landing inside an unstyled `<p>`.

Evidence (probe `/tmp/probe_env.py`), before the fix:

```
LISTEN  …  127.0.0.1:9071  users:(("python3",pid=922395,fd=3))
pid 922395  PPID 1229  /usr/local/lib/hermes-agent/venv/bin/python3 -m http.server 9071 \
            --bind 127.0.0.1 --directory /root/mhpss-nepal-work/v2-authority-redesign/apps/public

127.0.0.1:9071  /            -> HTTP 200  title='MHPSS Technical Working Group Nepal'
127.0.0.1:9071  /index.html  -> HTTP 200  title='MHPSS Technical Working Group Nepal'
127.0.0.1:9071  /forms.html  -> HTTP 404 File not found
127.0.0.1:9071  /access.html -> HTTP 404 File not found
```

`apps/hub/tools/justify-sweep.py` itself binds `127.0.0.1` and reaps its own
server (`srv.terminate()/wait()/kill()`), so it does not leak; the orphan came
from elsewhere. Confirmation that this was the environment and not the code:

- The only files this card's WIP commit touches are
  `config/`, `docs/`, `packages/form_registry/`, `prototypes/`,
  `tests/test_form_registry.py` — **no** `apps/` or `tests/test_third_review.py`
  change (`git diff --name-only 2184d5a^ 2184d5a` lists only those five).
- After `kill 922395` the same failing test passes standalone and the full suite
  is green (`Ran 167 tests … OK`), with `9071` free afterwards (the helpers reaped
  their own servers).
- A direct fetch of `127.0.0.1:9077/forms.html` from the real hub root returns
  HTTP 200; the 404s are exclusive to the leaked public-rooted server.

No source change was made to clear it — deliberately, because the card's scope
forbids editing the QA tools, and the defect's true home is the helpers'
shared fixed port, noted below under residual risk.

## 5. File change summary at final head

| Check | Command | Result |
|---|---|---|
| Base (WIP checkpoint) | `git rev-parse 2184d5a` | `2184d5a1b3570aa5af42909465f1b5092e8dc741` |
| Registry suite | `python3 -m unittest tests.test_form_registry -v` | 10 passed, 0 failed |
| V2 contract suite | `PYTHONPATH=tests python3 -m unittest discover -s tests/v2_contract -p 'test_*.py'` | 59 passed, 0 failed |
| Full suite | `python3 -m unittest discover -s tests` | 167 passed, 0 failed |
| `apps/` change | `git diff --name-only 2184d5a^ -- apps` (WIP) / unchanged here | 0 |
| Leaked QA server | `ss -ltnp \| grep 9071` | cleared (killed 922395) |

Head SHA and final `git status` are recorded in the task handoff comment.

## Residual risk (out of scope for this card — do not widen)

- **Shared fixed QA port.** `apps/public/tools/justify-sweep.py` and
  `apps/hub/tools/justify-sweep.py` both use `PORT = 9071`, so a leaked server
  from one app root can satisfy the other's readiness probe and make a suite
  report a false failure (or, worse, silently load the wrong tree). This is a
  QA-harness robustness gap, not a data or release gap, and belongs to whichever
  task owns the QA tools; it is recorded here, not fixed here.
- **Server enforcement remains unverified.** The registry is publisher-side
  metadata; authoritative production Rules are not versioned in this repository.
  The design already states this (`FORM-REGISTRY-DESIGN.md` §Privacy enforcement).

## BLOCKED — DECISION (unchanged)

Institutional ownership/controller roles; production Rules/indexes; retention and
legal basis; post-trial approval of the four dummy forms; whether anonymous free
text is collected at all; production V2 runtime and migration/cutover authority.
None is decided or invented by this evidence.
