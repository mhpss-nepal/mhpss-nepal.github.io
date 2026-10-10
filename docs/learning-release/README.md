# Learning release: operational boundary and runbook

## What works now

One operation imports an explicitly synthetic approved-package roleplay, checks every input, creates immutable versioned module paths, regenerates the catalogue without removing other topics, runs the existing website guards, builds byte-reproducible ZIPs, deploys into a **private filesystem fixture**, reads back every file/hash, and only then advances last-good. Updates, duplicate attempts, interrupted deployment reconciliation, and exact-byte rollback are exercised.

This is **not** ministry approval, a live LMS/admin upload screen, or an online deployment. Actual PFA remains QC-blocked and cannot enter an imported candidate. No clinical translations are invented. Content can remain `in-review` in the schema: a separate trusted signed review is required for production preparation.

## Operator: one synthetic exercise

No AI session or developer-owned host is required; Python 3, OpenSSL, and Git are standard institutional runner dependencies.

```sh
python3 tools/learning-release/roleplay.py --site . --output /institution/private/new-release-exercise
```

Use a new private output directory **outside** the source repository. The command snapshots the site, makes deterministic synthetic packages, publishes a new navigation lesson/quiz, updates it, then restores and verifies the prior exact bytes. It saves `report.json`, input ZIPs/receipts, private deployment, content-addressed release ZIPs, and full file/hash manifests. These contain navigation test content only, not clinical or learner information. Synthetic receipts have `mode: SYNTHETIC`, no trust signatures, and the GitHub adapter rejects them.

To exercise a supplied synthetic package with one action:

```sh
python3 tools/learning-release/release.py publish --synthetic \
  --package /institution/private/approved-SYNTHETIC-1.0.0.zip \
  --approval /institution/private/SYNTHETIC-review-1.0.0.json \
  --site . --state /institution/private/release-state --target /institution/private/released-site
```

Initial target must not exist; untracked target content is never overwritten. State/source/target must be disjoint. Do not point this fixture adapter at real hosting directories.

```sh
python3 tools/learning-release/release.py rollback \
  --state /institution/private/release-state --target /institution/private/released-site
```

## Production candidate preparation, not publication

The institution supplies a reviewed ZIP and receipt, and commissions a separately controlled public-key registry. **No default trust key or production registry is shipped.** An arbitrary `approved: true` JSON object cannot authorize release.

```sh
python3 tools/learning-release/release.py prepare \
  --package /institution/reviewed/approved-package.zip \
  --approval /institution/reviewed/approval.json \
  --registry /institution/trust/registry.json \
  --site . --candidate /institution/private/new-candidate
```

Preparation fails closed without all trusted role signatures, a permitted explicit locale profile, exact content hashes, and website checks. Candidate is never written into the source tree. A sidecar `<candidate>.release/` contains a reproducible `site.zip`, file manifest, and check evidence. Only complete candidates become visible; no source or last-good mutation happens on pre-deploy failure.

Create the offline GitHub adapter output:

```sh
python3 tools/learning-release/release.py github-adapter \
  --site . --candidate /institution/private/new-candidate \
  --output /institution/private/new-github-adapter \
  --repository INSTITUTION/WEBSITE --base-url https://INSTITUTION.github.io/WEBSITE/
```

It makes and actually checks a Git-applicable patch in an isolated local Git fixture. Only `learn/content/**` and `learning-release.json` enter that patch. The real repository's history, index, branches, remotes and production settings remain untouched. Output is `prepared-not-deployed`, never `live`.

## One production publish action (implemented; online commissioning NOT EXERCISED)

`.github/workflows/learning-release.yml` has a `workflow_dispatch` entry with **reviewed repository package name** and exact ZIP SHA-256. It does not fetch arbitrary URLs, accept credential-bearing URLs, interpolate input into shell source, or change Pages hosting.

Institutional operator places `NAME.zip` and `NAME.approval.json` under `docs/learning-release/approved-packages/` via a reviewed protected PR. Commission `docs/learning-release/institution-registry.json`; pin its exact SHA-256 as protected environment variable `LEARNING_REGISTRY_SHA256`, independently of PR/dispatch input, and set `LEARNING_READBACK_BASE_URL`. Protect environment `learning-release-authorization`. Without those settings the workflow deliberately fails closed. An institution-native admin/LMS could later upload to its reviewed staging service and invoke this same entry; none exists here today.

The original workflow stays read-only. Its candidate bytes are deterministic and bound to the **signed human content-review receipt**; the candidate itself is not a separately signed provenance attestation.

The separate `.github/workflows/learning-publish.yml` implements the write broker. One dispatch supplies package identity/hash and deliberate `execute_deployment=true`. No subsequent per-content branch/merge/deploy action is required. The operator CLI uses the same broker:

```sh
python3 tools/learning-release/release.py publish-github \
  --package /institution/reviewed/package.zip --approval /institution/reviewed/approval.json \
  --registry /institution/trust/registry.json --policy /institution/trust/provider-policy.json \
  --state /institution/private/persistent-release-state --execute-deployment
```

`github_broker.py` uses bounded `gh api` argv calls (no shell or accepted passwords). It snapshots fresh remote `main`, calls the existing trusted importer, creates immutable Git blobs/tree/commit with that main as sole parent, and pushes **only a new feature ref** using GitHub's Git refs API. This is the provider equivalent of a scoped feature-branch push, not local history/index mutation. It opens/reconciles one exact PR, discovers protected provider check names dynamically, polls them, submits a SHA-bound squash merge through the protected PR API, confirms actual merge, requests/reconciles legacy Pages builds, verifies exact deployed marker/catalogue/all retained module bytes and explicitly scoped stable assets, and only then records last-good. No direct main push, force, bypass, hosting switch, or fabricated receipt.

One-time institutional commissioning (not performed here):

1. Land the checked workflows/tools through an authorized PR. Require strict up-to-date protected-main PR checks, including the **actual observed check context**, with admin enforcement/no broker bypass. Zero required GitHub reviews is compatible with separate signed owner/content authorization. Broker fails closed if these provider gates are missing; ruleset-only installations must expose equivalent protection or use an audited adapter extension.
2. Commission the independently controlled signer registry and protect exact `LEARNING_REGISTRY_SHA256`. Also commission `docs/learning-release/provider-policy.json`; protect its exact raw-file hash as `LEARNING_PROVIDER_POLICY_SHA256`. No default production trust/policy is shipped. Direct CLI policy is a trusted institutional file, never content/dispatch input.
3. Policy fields: `repository`, exact HTTPS `base_url` matching provider Pages URL, exact `registry_sha256`, `stable_assets` list of static source paths (include every released reader JS/CSS/font/image that must remain stable), and explicit boolean `allow_rollback`. Set `allow_rollback=true` once to authorize automatic protected-PR rollback to the previous signed, verified content manifest; not an extra per-release human action.
4. Configure protected environment `learning-release-authorization`, dedicated institution-managed self-hosted runner label `learning-release-broker`, and absolute disjoint persistent `LEARNING_BROKER_STATE_ROOT`. Preserve this private directory across failures/reruns; never cache it as public site content. Only one broker host may own it; locking is local filesystem locking, not multi-host consensus. Environment approval policy is an institutional commissioning choice, not a new content-QC signature.
5. Supply environment secret `LEARNING_BROKER_TOKEN`: short-lived externally refreshed GitHub App token or institution-approved fine-grained token scoped to this repository with **Contents/Pull requests/Pages write; Checks/Commit statuses/Administration read**; no Administration write or bypass role. Pages write is required for `POST /pages/builds`, not to change hosting. Do not use the normal `GITHUB_TOKEN` for created PRs: its write events may suppress required check workflows. Dedicated runner must never execute untrusted PR code. Private signing keys stay elsewhere.

Durable `pending.json` binds release ID, PR number, approval/package/manifest hashes, exact content manifest, base/head SHA, policy and repository **before side effects**. A retry reads remote branch/commit/PR identity and approved bytes before continuing. Ambiguous PR creation reconciles a uniquely matching PR; no second create/push. Unknown commit/PR/Pages effects that cannot be positively reconciled stop for manual attention, not blind replay. Old/superseded releases cannot be replayed. A failed check never merges. Pending merge never reissues its mutation. Bounded waits may require rerunning the same action to observe completion, not a new content approval.

After a known merged failure, configured rollback revalidates the prior signed receipt and exact saved content manifest, snapshots current main, preserves unrelated concurrent site assets, refuses concurrent content drift, creates a new protected rollback PR, and performs the same checks/Pages/exact-byte readback. It deletes only failed content additions absent from prior manifest, not an entire old site tree. Last-good stays prior until rollback verification; failure/unknown remote effect retains pending audit evidence. Rollback does **not** promise zero downtime. With rollback disabled or no verified prior release, manual attention is required.

All provider success/failure paths below are **deterministic offline gh-process and HTTP fixtures**, not online evidence. Actual institutional PR/merge/Pages/readback/rollback commissioning remains **NOT EXERCISED**. Real PFA stays QC HOLD. See `PROVIDER-TDD.md` for executed commands/results.

## Gate matrix

| Gate | Status |
|---|---|
| Input ZIP membership, size/count/ratio, collision/traversal/symlink rejection | Exercised locally |
| Exact JSON v1 contract, IDs, quiz, source references, type/URL scan | Exercised locally |
| Review hashes, bounded signing registry, module/language/role authorization | Real OpenSSL verification exercised with ephemeral **test-only** keys |
| PFA QC exclusion, unresolved review rejection | Exercised locally |
| `en-only-trial` vs explicit bilingual en/ne source-version pairing | Enforced; no translation generated |
| Immutable versions, preserved catalogue, deterministic release ZIP | Exercised locally |
| Existing i18n + text-setting guards baseline/candidate | Executed on real website snapshot; their scope is not clinical/language approval |
| Actual imported lesson + quiz/rationale in browser | Executed on private loopback fixture, not injected UI content |
| Failure/readback mismatch, update/rollback, interrupted state reconciliation | Exercised locally, exact previous bytes verified |
| GitHub adapter scoped patch + `git apply --check` | Executed in isolated local Git fixture |
| Protected-PR broker, reconcile/no duplicate effects, Pages, exact HTTPS, scoped rollback | Implemented and exercised with offline gh/HTTP fixtures; online commissioning **NOT EXERCISED** |

## Verification

```sh
python3 -m unittest discover -s tests/learning-release -v
python3 tools/learning-release/validate_content.py --self-test
python3 tools/i18n-check.py
python3 tools/text-setting-check.py
```

Optional imported-content browser smoke (Playwright/Chromium are external test dependencies; configure paths in your own environment):

```sh
PLAYWRIGHT_MODULE=/institution/test-tools/playwright/index.mjs \
CHROMIUM_EXECUTABLE=/institution/test-tools/chromium \
LEARNING_DEPLOYMENT=/institution/private/new-release-exercise/private-deployment \
node tests/learning-release/imported-ui-smoke.mjs
```

## Security and failure handling

- Private signing keys and broker credentials belong in the institutional vault/HSM, **never repository files**. Only public review keys go in the access-controlled registry. Test-generated keys are ephemeral scratch fixtures, not a production trust anchor.
- Source/rights review, qualified clinical/safety review, locale review and owner release authority are separate signer roles. The scanner validates shape and unsafe constructs; it does not assert clinical truth, provenance validity, rights permission, or human translation quality.
- `pending.json` is durable intent before fixture side effects. On retry, exact target readback either finalizes an already-applied candidate, recognizes the prior tree, or restores the verified prior tree and stops for deliberate retry. Do not delete state to bypass reconciliation.
- Pre-deploy failures preserve source and last-good. Post-deploy exceptions restore and verify prior files; interrupted processes retain pending state for reconciliation. Unknown external remote effects must never be replayed blindly.
- Keep private state on a reliable local filesystem. This fixture uses rename, not a distributed deployment transaction, and does not promise power-loss durability or multi-host locking. Filesystem write/restore failure requires operator intervention, never a fabricated success.
