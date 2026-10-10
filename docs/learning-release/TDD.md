# Executed acceptance record

Commands were run in the candidate checkout, with real private scratch directories under `/root/.hermes/cache/scratch`, never a fabricated cloud deployment.

## Red → green tracer slices

1. New-topic single operation: initial test failed `release implementation is missing`; implemented importer/private deploy; 1 test passed.
2. Fail-closed package/receipt gates: mutation run failed 9 subtests (PFA exclusion, malformed/unsafe packages, missing receipt binding/locale attestation); implemented validation gates; 4 tests passed.
3. Artifact/history/rollback/reconciliation: 5 failures showed missing failure injection, artifact SHA, rollback, interruption handling; implemented content-addressed ZIPs, last-good/previous-good, pending-state reconciliation and verified restore; 9 tests passed.
4. Trusted review: real ephemeral Ed25519 signing test initially rejected because production authorization was absent; implemented bounded scope/role verification with OpenSSL, no shipped trust key; 10 passed.
5. Provider boundary: adapter absent and same-version overwrite unexpectedly accepted; implemented immutable version collision gate and GitHub protected-PR preparation. Adapter output test failed until isolated local Git patch/applicability check existed; 13 passed.
6. Operator roleplay: entrypoint initially missing; implemented one-operation synthetic exercise. 14 passed.
7. Extended rejection coverage: archive duplicate/symlink/bomb/duplicate-identity/hash tests, real website guard failure and candidate nonvisibility; final suite 16 passed.

## Integration findings and corrections

- The UI worker finalized catalogue paths as `modules/<id>/<version>/<locale>.json`; release importer uses that exact contract. An early private browser smoke failed while concurrent UI work still used a different path. Updated importer and reran actual rendered-content smoke successfully.
- Source checkout was being edited by another worker during the first full-site exercise; its final source comparison failed rather than asserting false immutability. Roleplay now freezes a source snapshot before exercising it. No checkout source mutation is performed by the release code.
- Rationale is rendered outside `#course-content`; corrected browser smoke selector to check real rendered body text rather than treating absent rationale in the lesson section as a release failure.
- Vendored draft validator's original self-test used shared-foundation-relative paths; adapted the self-test fixture path to its colocated template. Draft validation behavior is unchanged.

## Full website roleplay evidence

Executed:

```
python3 tools/learning-release/roleplay.py --site . --output /root/.hermes/cache/scratch/learning-release-site-roleplay-final
```

That snapshot produced **120 files / 39,012,335 bytes**, one catalogue module, one lesson, one quiz question. First artifact SHA-256: `f9b9b21689eb34e9bc9943fe89b5ec3e6d497fdc9f1e62db3ead41403e3c2bbb`. Updated artifact SHA-256: `3b2ff51641123ec8fc2cca66be8b6a2c45adaf1b821cb77945bba2cb1e3b4c0b`. First target manifest SHA-256: `eb39bc526bc9265edd1668432bcaa8f6c94b5e77b249fe0ae5e1cebc41a6b083`. Duplicate returned `already-verified`; rollback returned `rolled-back-verified`; exact prior bytes and source-snapshot preservation both verified true.

These hashes refer to that precise snapshot, not any later edits to documentation/tools. Same-tree determinism is separately asserted by byte-equal ZIP rebuilding in the unit suite.

Optional Playwright smoke against that **actual imported private deployment** returned:

```json
{"status":"PASS","mode":"actual imported synthetic content on loopback","lesson_and_quiz_rendered":true,"rationale_rendered":true,"browser_errors":[]}
```

Existing i18n/text-setting checks were run against baseline and candidate as part of this exercise. Their existing migration scope is unchanged and is not full bilingual clinical approval.

## Provider boundary

Actions pins were verified read-only with `git ls-remote` against upstream tags:

- checkout v4.2.2: `11bd71901bbe5b1630ceea73d27597364c9af683`
- upload-artifact v4.6.2: `ea165f8d65b6e75b540449e92b4886f43607fa02`

`dispatch.py` without commissioning/configuration returned `REJECTED: invalid reviewed package name` as expected. No production registry/key was fabricated. No live deployment, push, commit, PR, remote write, branch/main/remotes/cloud/Pages configuration change was performed. Candidate Git HEAD remained `d4867b1ae41de749ea68a01bccc51376b5379c5c` at verification.

Provider PR broker/auto-merge/publication/readback/cloud rollback are explicitly **not implemented/run** by this safe offline adapter. A real authorized institutional provider run remains necessary; local success is not a claim of online deployment.
