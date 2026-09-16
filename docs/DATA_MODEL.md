# Data model

Draft, 15 September 2026; corrected 16 September 2026 against the IASC manual
itself and the data workstream's code lists. Not agreed with EDCD or the MHPSS
Technical Working Group.

## The rule the model exists to enforce

**This is a coordination system. It holds service-level information. It does
not hold individual-level information.**

The coordination function needs to know which organisation provides which
service where. It has no case-management mandate, no clinical role, and
therefore no lawful purpose for individual records. That single rule disposes
of the GBV, unaccompanied-children, suicide and clinical-case scenarios before
they arise rather than after.

## Mapping to the IASC 4Ws model

The IASC MHPSS 4Ws manual (2012), Table 1, lists 22 items: A to Q, then five
marked *Optional* (R to V). The manual does not call any of them "core". The
fields here map onto A to Q. The additions are marked; they come from defects
observed in the current reporting workbook rather than from the manual.

| IASC item | Field | Notes |
|---|---|---|
| A · Date | `dateAD` | Gregorian. The field the system sorts and groups on. |
| — | `dateBS` | **Addition.** Bikram Sambat as reported, typed. Not converted automatically — see below. |
| B · Implementing agency | `org`, `orgOther` | Coded. The manual says B is the agency implementing the activity, *rather than the donor*. `OTHER` requires a name and is flagged for reconciliation. |
| C · Other organisation(s) with whom the activity is done | *(not yet a field)* | The manual's item C is the joint-activity partner. Two partners are written that way in the current reports. A `partners` field is the next schema change; until then the names sit in `codes.js` against the organisation. |
| — | `donor` | **Addition.** A funding tag. Donor has no IASC item. It distinguishes one organisation reporting under two funding lines from two organisations. One record in the current reports carries two tags; allowing several is a pending schema change. |
| D · Focal point name | `focalName` | A professional, not a service user. The only personal data in the model. |
| E · Focal point phone | `focalPhone` | As above. |
| F · Focal point email | `focalEmail` | As above. Optional. |
| G · Region / district | `district` | Coded. |
| H · Town / neighbourhood | `site`, `siteOther` | Coded against the site list. A report that names only a palika and no site is coded at palika level (see *Site list*). |
| I · Geographical code | `site` → palika P-code | Every site carries the OCHA COD-AB P-code of its palika. No GPS is collected — see granularity below. |
| J · Activity code | `activity` | Coded. |
| K · Activity subcode | via `codes.js` | The 2012 code list (Table 2: 11 codes, 45 subcodes) is now in hand. Where the match is direct the subcode sits on the activity in `codes.js`; where it depends on the cadre or the content (specialised care, medication, referral, IEC, assessment) a rule is recorded and no subcode is written yet. |
| L · One-sentence description | `description` | Capped at 220 characters. No names, no clinical detail. |
| M · Target groups | `targetGroups` | Category codes, multiple. Never a description of a person. |
| N · Number of people in the target group directly supported in the previous 30 days | `reachedTotal`, `countBasis`, `distinctPeople` | The manual's N is a 30-day count of *people*. The current workbook counts contacts per activity-day, so this model records the total together with what it counts — service contacts, distinct people, or not sure — and a distinct-people figure where the reporter has one. How a 30-day people count is derived from daily contact counts is an open ruling. |
| — | twelve band fields, see *Disaggregation* | **Addition.** Sex and age disaggregation in four age bands. |
| O · Implementation status | `status` | The manual's three states are: currently being implemented; funded but not yet implemented; unfunded and not yet implemented. The form's Ongoing / Completed / Planned is a working rendering and does not carry the funded–unfunded distinction. |
| P · Start date | `dateAD` | This model reports per activity-day, so start and end collapse into the report date. |
| Q · End date | `dateAD` | As above. |
| — | `modality` | **Addition.** In person at a site, outreach, telephone. Helpline contacts were otherwise unrecordable. |
| — | `cadre` | **Addition.** Counsellor, psychologist, psychiatrist. Absent from the current form, which is why the three cannot be counted apart. |

## Fields that do not exist, and are not to be added

Beneficiary name · nickname · identity number · phone number · date of birth ·
address · diagnosis · assessment score against a person · photograph of a
service user · anything from which an individual could be identified.

## The two calendars

Dates in the current workbook are Bikram Sambat values stored as Gregorian
datetime objects — a BS date such as `2083-05-07` sitting in a date cell —
with stray years in the same column and one free-text range. Excel is
interpreting BS dates as AD dates silently, which corrupts every sort and
every period filter. (The dates above are illustrations, not values from the
workbook.)

This model stores both, separately:

- `dateAD` — a real Gregorian date from a date picker. Required. Everything
  sorts, groups and filters on this.
- `dateBS` — Bikram Sambat as the reporter wrote it. Optional, free text,
  validated only against the shape `YYYY-MM-DD`.

**There is no automatic conversion, deliberately.** Converting between the two
calendars requires a lookup table of days per month for each BS year, because
Nepali month lengths vary year to year and cannot be computed from a formula.
No verified table has been obtained. Guessing one would produce dates that
look right and are wrong, which is worse than not converting.

*Open item: obtain a verified BS calendar table for 2082–2085 from a
Government of Nepal source, then add conversion with the source cited.*

## Disaggregation

Four age bands — 0–4, 5–17, 18–59, 60 and over — each split female, male and
other or not recorded: twelve optional fields (`f04` … `o60`). Two "of whom"
counts sit beside them, people with disabilities and pregnant or postpartum
women; they are not additive and may not exceed the total. Exports also carry
the older six-field split (under 18 and 18 and over) folded from the bands, so
a sheet built on the first version still reads.

They exist because partners are already trying to report disaggregation and
the current form has nowhere to put it, so it lands in whichever field is
nearest — a total in the provider column, an age split in a remarks cell. An
illustration, not a workbook value: `women 18+ = 12, men 18+ = 9` typed where
an organisation name should be.

The form enforces one rule: the parts must add to the total, or all be left
blank. Partly-filled disaggregation is worse than none, because it looks
complete in a summary and is not.

## Location granularity

Site-level, coded, and no finer. No GPS coordinates. A ward is recorded
against a *site* in the code list, as sourced, never against a person or a
report.

The 4Ws manual leaves granularity open — town names, neighbourhood names or
GPS. In a displacement setting, a precise location combined with a specific
target group becomes identifying even with no names attached: "three people in
this target group at this coordinate on this date" can be enough. The coarsest
level that still supports referral is the right level.

## Site list

`assets/codes.js` carries the list, following the data workstream's code list
of 15 September 2026. Four kinds of entry, by `source`:

- `roster` — on the holding-centre roster sheet of the daily reporting
  workbook (Rasuwa 4 sites, Nuwakot 19). **These are the denominator for
  coverage-gap analysis.**
- `gov-list` — on the District Administration Office Nuwakot list of 29
  Bhadra 2083 and not on that roster (12). Offered on the forms. Whether
  they join the denominator is an open question for EDCD and the district
  health office; until it is ruled they are shown apart.
- `reported` — named in submitted reports and on neither list (31). Recorded
  and flagged. A site nobody ever listed as a service point cannot be counted
  as one that was missed, so these are shown separately and never counted as
  gaps.
- `retired` — a code merged into another, or one that named a palika or a
  ward rather than a place (8). Kept so that an old record still resolves;
  never offered for a new one.

Every site carries its palika as an OCHA COD-AB Nepal P-code (`palika`), the
key into the `PALIKAS` list of the sixteen local levels that appear in reports
or on the roster. The P-code is the join key any map or the NDRRMA 5W will
match on. A report that names only a palika is coded at palika level; a palika
is not a site and never enters the roster denominator.

## Record identity and de-duplication

Two different things, often confused:

**Record identity.** The record id is a hash of organisation, site, date,
activity and modality. Submitting the same report twice — a double tap, a page
reload, a re-sync after signal returns — produces the same id and therefore
one record with a revision history, not two records. This is what makes the
form safe to use on a bad connection.

**Analytical de-duplication.** A separate question: did two *different*
organisations report the same site on the same day, and if so did they reach
the same people? The dashboard flags these. It does not resolve them, because
it cannot — only the two organisations know. The flag distinguishes three
readings: different activities (likely different people), one organisation
under two funding tags (attribution, not duplication), and the same activity
by two organisations (needs a conversation).

## No subtotals in the dataset

The CSV export is one flat row per record. Totals are computed in the
dashboard and never stored as rows.

This is the direct fix for the largest defect in the current workbook: subtotal
rows sit in the same column as the data, so a plain sum of the service column
counts a substantial share of the reach twice. Anyone who opens the file and
sums the column gets a materially inflated figure without doing anything wrong.

*The measured size of that inflation, and the other defect counts, are set out in
the data inventory shared with the WHO Nepal mental health team, the Ministry of
Health and Food Safety and EDCD. They are deliberately not reproduced in this
public repository: they are unpublished operational figures attributed to named
partners, and they are not ours to publish.*
