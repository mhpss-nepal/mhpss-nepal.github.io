# Form registry and output-home contract

Status: **DONE — REVIEW ARTIFACT**  
Task: `t_d3d2bbfb`  
Scope: local-only prototype; synthetic metadata; no production read or write; no live Hub page changed.

## Decision

`config/form-registry.yaml` is the proposed source-neutral declaration that answers two questions in one place:

1. What is this form?
2. Where is its output read?

The executable validator is `packages/form_registry/form_registry.py`. It fails closed when a form has no reading home, points to a home whose file or anchor does not exist, assigns a kind the home does not accept, weakens a privacy class, or tries to claim direct canonical authority. The generated artifact `prototypes/form-registry/generated-field-landing.html` demonstrates that the field landing list can be derived from the registry without editing the live `apps/form/index.html` in this task.

This is a review artifact, not a deployment decision. HMIS/DHIS2 mappings, indicator approval, retention, production server rules, and post-trial classifications remain **BLOCKED — DECISION**.

## Verified current system: the five-layer claim corrected

The original five layers are directionally right, with four corrections.

| Layer | Verified implementation | Correction / finding |
|---|---|---|
| Identity | `contact.html`, `referral.html`, `phq9.html`, and `selfreport.html` write `service_contact`, `referral`, `phq9`, and `self_report`. The 5Ws path writes `kind: activity` in `apps/hub/assets/store.js:137-145`. | The 5Ws kind is not an unspecified special value; it is `activity`. `apps/form/4ws-report.html` is only a redirect and records nothing. |
| Storage | `apps/hub/assets/fb.js:28-31,286-293` writes register copies to collection `submissions` by default. `watch()` reads all records; `watchKind()` can filter by `kind`. | The 5Ws also keeps a separate device-local source copy under `mhpss-np-4ws-v1` before submitting its reduced register copy. The other four forms pass through Layer-1 device storage and the shared queue. Therefore “one shared store” is incomplete: there is device authority/materialization plus the hosted register. |
| Reading home | `activity` is read by `apps/hub/index.html`, whose five visible panels are Overview, Who is where, Activities, Reports received, and Publish. `service_contact`, `referral`, `phq9`, and `self_report` are classified and rendered in `apps/hub/forms.html`. | The Hub does not have eleven authoritative top-level sections. It has five dashboard panels plus four per-form output homes. Several dashboard analyses are computed views inside those panels. The registry names the stable home, not every derived chart. |
| Validation / rules | Form validation is split: 5Ws validation and export shape live in `store.js`; the other forms use page/L1 validation; referral has extra save/queue safeguards in `l1.js` and `fb.js`. `store.js:129-145` deliberately removes empty fields to remain below an observed 60-key limit. | No Firestore Rules file exists in this repository. The 60-key value is a client-side design constraint described in source, not verified authoritative server policy. Server enforcement remains unverified. |
| Output | 5Ws has device CSV (`STORE.toCSV`), Hub CSV exports, and two public aggregate documents: `public_stats/flood_response` and `public_stats/coordination_full`. The four other form homes have restricted CSV exports. `FB.publish()` is the only in-repository `public_stats` writer. | CSV is not one global output path. Each form/home owns a shape. Only coordination aggregates have a public route; clinical, safeguarding, anonymous free text, and restricted person records do not. |

Current registry mapping:

| Form | Kind | Trial status in prototype | Reading home | Privacy | Public route |
|---|---|---|---|---|---|
| MHPSS Activity Report (5Ws) | `activity` | `approved-for-trial` | `hub.dashboard.reports` | `coordination-aggregate` | named rule-gated aggregate route to `flood_response` and `coordination_full` |
| Service Contact Record | `service_contact` | `dummy` | `hub.forms.contact` | `restricted-person-record` | never |
| Referral Out / In | `referral` | `dummy` | `hub.forms.referral` | `safeguarding` | never |
| PHQ-9 Follow-up | `phq9` | `dummy` | `hub.forms.phq9` | `clinical` | never |
| Anonymous Self-report | `self_report` | `dummy` | `hub.forms.selfreport` | `anonymous-free-text` | never |

The `dummy` and landing-page values reflect the trial-scope requirement that only the 5Ws form be generated into the fixture. They do not change the live landing page in this task.

## Registry schema

Each entry requires:

- `id`: stable registry identifier, never reused;
- `file_path`: source path of the form;
- `kind`: V1 routing discriminator written on the register copy;
- `title`: human-readable title;
- `trial_status`: exactly `approved-for-trial`, `dummy`, or `retired`;
- `field_landing`: whether an approved form is generated into the field landing surface;
- `reading_home`: mandatory key into the top-level `homes` map;
- `privacy_class`: enforced output class;
- `schema_versions`: every still-readable record schema for the form;
- `public_output.route`: `never` or `rule-gated-aggregate`;
- `public_output.documents`: named public aggregate documents, empty when route is `never`.

Each reading home declares its real file, a literal selector that must exist in that file, the URL a reader reaches it at, and the kinds it accepts. Validation reads the repository and rejects a missing file or selector, or a form whose kind the home does not accept. This makes “stored but never read” an executable defect: a form cannot invent a home, and a home cannot silently drop a form.

Registry policy also carries the closed allowlist `policy.public_documents`. A form cannot name a public document that is not on that list, so inventing a new public aggregate is not something a form entry can do on its own.

### Privacy enforcement

The policy class is structural in the registry validator:

- `clinical` (`phq9`) can only use `public_output.route: never`;
- `safeguarding` (`referral`) can only use `never`;
- `anonymous-free-text` and `restricted-person-record` also use `never` in this prototype;
- only `coordination-aggregate` can use `rule-gated-aggregate`.

The prototype test demonstrates the registry decision, and `tests/test_publication_privacy_gate.py` independently drives the real `FB.publish()` sink to prove synthetic `phq9`, `referral`, clinical, safeguarding, and restricted bodies produce zero writes. This remains publisher-side protection; authoritative production Rules are not versioned here.

A form cannot grant itself a publication right. Four things must all hold for a form to reach `public_stats`: a policy class on the publishable list; route `rule-gated-aggregate`; documents drawn from `policy.public_documents`; and the existing sink checks (production mode, suppression floor, whole-document redaction, authentication). The registry removes the first three as choices a form can make for itself; it does not weaken the fourth.

## Landing-page generation

`render_landing_fixture()` includes an entry only when both are true:

- `trial_status == approved-for-trial`;
- `field_landing == true`.

The generated fixture currently contains exactly the 5Ws card. Retired and dummy forms remain resolvable in the registry but are not offered to field users. A later integration task can replace the hand-maintained cards in `apps/form/index.html` with this generated block after the trial-scope lane and service-worker/cache review are complete. This task deliberately does not edit the live page, QR sheet, QR data, or service-worker precache.

## Adding a genuinely new form

A contributor follows one sequence:

1. Add the form page, but do not give it a canonical `event_id` or `stream_id` API.
2. Define a versioned payload schema and synthetic fixtures.
3. Add or extend a real Hub reading home first. The home must name the new kind in `accepted_kinds` and provide review, export, and data-quality behavior appropriate to the privacy class.
4. Add one registry entry with a unique `id`, `file_path`, and `kind`; preserve every schema version that still has stored records.
5. Start as `dummy` and `field_landing: false` unless the trial authority has approved it.
6. Run registry validation and the focused tests. Add failing-first tests for the form’s validation, persistence path, reading home, export, and privacy/publication boundary.
7. Obtain independent review of the schema, privacy classification, reading home, service-worker/cache impact, and any publication aggregate.
8. Only after the review and the relevant owner decision, change the status or landing visibility. Deployment remains a separate release action.

A new form must not:

- declare browser-direct canonical writes;
- allocate or accept a caller-chosen canonical `event_id`;
- invent a `stream_id` independent of the trusted envelope;
- write a canonical record directly rather than through ingestion;
- publish raw or person-level records;
- choose its own `public_stats` document or weaken a privacy class;
- omit a reading home;
- silently replace a schema version or make retired records unresolvable.

The prototype rejects the fields `canonical_write`, `event_id_source`, and `stream_id_source` if they appear on a form entry. Production enforcement belongs in the shared ingestion and release contracts, not in metadata alone.

## Relationship to the V2 immutable-authority contract

The registry is routing and schema metadata, not authority.

- V1 uses `kind` to classify register copies and route them to a Hub home.
- V2 canonical identity remains the trusted envelope’s `event_id`; a root event has `stream_id == event_id`, and corrections/voids receive new trusted identities with exact predecessor lineage.
- The registry entry’s `kind` selects a form family, allowed schema versions, privacy policy, and projection/home adapter. It does not become `event_id`, `stream_id`, or a duplicate key.
- A V2 projection derives from rehashed immutable canonical events. The projection can attach the registry form id and route the current state to its declared reading home, but cannot use registry metadata to bypass lineage or reconciliation.
- A retired entry remains in the registry so historical envelopes and V1 rows still resolve. Retirement disables new entry/landing exposure; it does not delete identity or schema history.

The registry lives at repository root under `config/`, outside any one application. V1 static build tooling and future V2 ingestion/projection code can consume the same released file. In a production V2 release it must be included in the trusted release manifest and bound by hash like other contract assets; this prototype does not amend the already approved release-manifest implementation.

## Scaling and schema evolution

At 20 forms, the registry remains one bounded list while homes remain named adapters. Validation cost is linear in forms and homes. The landing page becomes a generated view grouped by status/privacy rather than another list maintained by hand. Hub navigation can likewise be generated later, but each home must still exist as executable code; metadata cannot substitute for a consumer.

When a form schema changes:

1. create a new versioned schema;
2. append it to `schema_versions` rather than replacing the old version;
3. make the declared home/projector read both versions or add an explicit reviewed migration adapter;
4. add fixtures for old and new versions, including correction lineage;
5. never rewrite old canonical event bytes.

When a form is retired, keep its entry, kind, schema versions, reading home, and projection/export support. Set `trial_status: retired` and `field_landing: false`. Old records continue to resolve; only new entry is disabled.

## Executable evidence

Failing-first RED, before `form_registry.py` existed:

```text
python3 -m unittest tests.test_form_registry -v
ModuleNotFoundError: No module named 'form_registry'
```

GREEN and fixture generation:

```text
python3 -m unittest tests.test_form_registry -v
python3 packages/form_registry/form_registry.py config/form-registry.yaml --root . --render prototypes/form-registry/generated-field-landing.html
python3 -m unittest tests.test_form_registry tests.test_publication_privacy_gate -v
```

The final exact outputs are recorded in `docs/FORM-REGISTRY-EVIDENCE.md` (card
`t_abf0b818`, which supersedes the judge-stalled `t_d3d2bbfb`) and in the task
handoff. No network or production endpoint is called by these commands.

## Open institutional decisions

The registry intentionally does not decide:

- Nepal HMIS/DHIS2 mappings or indicator acceptance;
- retention, archival duration, deletion, or legal basis;
- production data controller, system owner, administrator, or approver;
- authoritative server Rules and role discrimination;
- post-trial approval of the four dummy forms;
- whether anonymous free text should be collected at all and, if so, its restricted review/retention home;
- production V2 runtime and migration/cutover authority.

All remain **BLOCKED — DECISION**.
