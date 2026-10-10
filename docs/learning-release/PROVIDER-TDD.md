# Protected-PR broker: execution evidence and limits

## Scope

Implemented `github_broker.py`, `publish_dispatch.py`, single `release.py publish-github --execute-deployment` entry, separate environment-gated `learning-publish.yml`, deterministic process fixture `fake_gh.py`, and provider acceptance tests. No actual GitHub mutation, provider deployment, credential change, production signer registry, or policy commissioning was performed. Main/site assets were not locally edited by this lane.

## RED → GREEN evidence

Actual terminal runs, in order:

1. `python3 -m unittest discover -s tests/learning-release -p test_github_broker.py -v`: first new end-to-end acceptance FAILED (`functional provider broker missing`), before implementation. After functional broker and fake process implementation: 1 test PASS.
2. Same command after failure/reconcile/rollback/CLI scenarios: 14 tests, FAILED missing CLI entry and fixture package re-creation (ZIP byte hash changed). Wired CLI; fixed test to reuse the exact approved package rather than mint a different archive under one release ID. 14 PASS.
3. Same command after parent/unknown-effects/workflow cases: 19 tests, FAILED remote parent drift was accepted and separate broker workflow missing. Added exact sole-parent/whole-content comparison and gated workflow. 19 PASS.
4. Scoped rollback exact content test FAILED after stronger whole-content comparison exposed retained failed-release module additions. Added only-scoped deletion entries; preserve unrelated assets. PASS in full suite.
5. Rollback-resumption test FAILED because prior saved manifest corruption was not rechecked. Added prior receipt signature, manifest identity, marker/module binding revalidation. PASS in full suite.
6. Readback-time main drift test FAILED (`ReleaseError not raised`). Added final provider-main recheck before last-good; PASS.
7. Ambiguous Pages response test FAILED because broker attempted rollback on an unknown provider effect. Classified unknown/pending provider errors separately and retained pending intent; PASS.
8. `python3 -m unittest discover -s tests/learning-release -p test_github_broker.py -k unreconciled_pages -v`: FAILED (3 PRs instead of 2). Exact captured failing output is `provider-red.log`. Fixed unresolved Pages retry to stop with provider-unknown status instead of initiating rollback. PASS in final suite.
9. `python3 -m unittest discover -s tests/learning-release -p test_github_broker.py -k flushes -v`: FAILED (0 fsync calls instead of file + directory). Added file flush/fsync before atomic rename and directory fsync after rename. PASS in final suite.

This was iterative test-first implementation. Not every later acceptance test failed on introduction: already-implemented failure gates were regression tests, not claimed as fresh RED evidence. The one-action CLI was executed in a child interpreter with a private fake `gh` executable on PATH and injected HTTPS byte transport; it used the real importer/OpenSSL verifier and returned `status=verified`. These are fixture results, never online evidence.

## Final executed commands

```sh
python3 -m unittest discover -s tests/learning-release -v
python3 tools/learning-release/validate_content.py --self-test
python3 tools/i18n-check.py
python3 tools/text-setting-check.py
python3 -m py_compile tools/learning-release/github_broker.py tools/learning-release/publish_dispatch.py tools/learning-release/release.py tests/learning-release/fake_gh.py tests/learning-release/test_github_broker.py
```

- Final acceptance: **43 tests PASS** (existing importer/private roleplay and new provider fixture tests); exit 0. Final run recorded 90.881 seconds.
- Validator: **18 synthetic checks PASS**, explicitly not clinical/application acceptance.
- Existing i18n/static text-setting gates: exit 0. Their existing translation gaps remain reported, not approved by the broker.
- Python compilation: exit 0.
- Captured full green outputs: `provider-green.log` (includes earlier 41-test green run and final 43-test run).

## Exercised provider scenarios (all OFFLINE)

Happy path/import/check/feature ref/PR/merge/Pages/exact marker/catalogue/modules/stable bytes/last-good; same-release read-only retry; check failure without merge; ambiguous PR creation without duplicate create/ref; unknown PR or immutable commit effect without replay; pending merge without duplicate mutation; Pages failure; Pages ambiguous completion reconciliation and unknown-effect stop; mismatched HTTP readback; parent/manifest/base drift; final readback main drift; superseded release replay; invalid trust pin or unsigned self-approval; missing deliberate flag; off-origin redirect refusal; scoped protected rollback to prior approved manifest; preservation of unrelated concurrent site assets; rollback disabled retaining pending evidence; corrupted rollback prior state rejected; workflow separation and dispatch consent; actual one-action CLI through fake provider.

## Commissioning limitations (NOT EXERCISED)

- No live push, PR, merge, build, HTTPS production readback or cloud rollback. This is implemented/tested provider automation, not proof the institution has commissioned it.
- Institution must configure strict protected main/no bypass, observed check context, independent signer registry and policy pins, repository-scoped App/token permissions, persistent dedicated runner/state and rollback authorization once. No default production trust key is supplied.
- Provider branch protection is the ultimate merge gate. Classic protection API is required by this implementation; ruleset-only protection fails closed instead of assuming equivalence.
- Direct GitHub Git object/ref API is used through gh; local checkout/index/history are untouched. Git objects are content-addressed, feature-ref creation is never force/update-main.
- HTTPS reads reject all redirects and bound response size/time; real CDN propagation/TLS outage behavior is not represented by fixture success. Readback errors retain last-good or invoke authorized rollback only for known effects; zero downtime is not claimed.
- Private local state is a trusted audit/control boundary. One owning broker host with reliable persistent filesystem is required. File and directory fsync improve intent durability; no distributed transaction or multi-host lock is claimed. Unreconciled effects stop for manual attention and never discard pending state.
- Real PFA remains QC HOLD. Human content-review signatures do not fabricate source provenance, clinical correctness or translation quality.
