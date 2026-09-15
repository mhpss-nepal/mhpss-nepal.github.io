# Data model

Draft, 15 September 2026. Not agreed with EDCD or the MHPSS sub-cluster.

## The rule the model exists to enforce

**This is a coordination system. It holds service-level information. It does
not hold individual-level information.**

The coordination function needs to know which organisation provides which
service where. It has no case-management mandate, no clinical role, and
therefore no lawful purpose for individual records. That single rule disposes
of the GBV, unaccompanied-children, suicide and clinical-case scenarios before
they arise rather than after.

## Mapping to the IASC 4Ws model

The IASC MHPSS 4Ws manual (2012), Table 1, defines seventeen core items. The
fields here map onto them. Two additions are marked; both come from defects
observed in the current reporting workbook rather than from the manual.

| IASC item | Field | Notes |
|---|---|---|
| A · Date | `dateAD` | Gregorian. The field the system sorts and groups on. |
| — | `dateBS` | **Addition.** Bikram Sambat as reported, typed. Not converted automatically — see below. |
| B · Implementing agency | `org`, `orgOther` | Coded. `OTHER` requires a name and is flagged for reconciliation. |
| C · Partner organisations | `donor` | Funding tag. Distinguishes one organisation reporting twice from two organisations. |
| D · Focal point name | `focalName` | A professional, not a service user. The only personal data in the model. |
| E · Focal point phone | `focalPhone` | As above. |
| F · Focal point email | `focalEmail` | As above. Optional. |
| G · Region / district | `district` | Coded. |
| H · Town / neighbourhood | `site`, `siteOther` | Coded against the holding-centre roster. |
| I · Geographical code | `site` code | The site code carries this. No GPS is collected — see granularity below. |
| J · Activity code | `activity` | Coded. |
| K · Activity subcode | *(not implemented)* | Waiting on the official IASC code list. |
| L · One-sentence description | `description` | Capped at 220 characters. No names, no clinical detail. |
| M · Target groups | `targetGroups` | Category codes, multiple. Never a description of a person. |
| N · Number directly supported | `reachedTotal` | A count, not a list. |
| — | `fU18` `mU18` `oU18` `f18` `m18` `o18` | **Addition.** Sex and age disaggregation. See below. |
| O · Implementation status | `status` | Ongoing / completed / planned. |
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
datetime objects — `2083-05-19` sitting in a date cell — with several stray
years (`2026-05-27`, `2082-05-18`) and one free-text range. Excel is
interpreting BS dates as AD dates silently, which corrupts every sort and
every period filter.

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

Six optional fields: female, male and other/not-recorded, each under 18 and
18 and over.

They exist because the current workbook has rows with `Women (18+)= 19, Men
(18+)= 28` and `Below 18 Male: 6, Female: 18` typed into the **provider**
column. Partners are already trying to report disaggregation and the form has
nowhere to put it, so it lands in whichever field is nearest.

The form enforces one rule: the parts must add to the total, or all be left
blank. Partly-filled disaggregation is worse than none, because it looks
complete in a summary and is not.

## Location granularity

Site-level, coded, and no finer. No GPS coordinates, no ward-level detail
below the site.

The 4Ws manual leaves granularity open — town names, neighbourhood names or
GPS. In a displacement setting, a precise location combined with a specific
target group becomes identifying even with no names attached: "three people in
this target group at this coordinate on this date" can be enough. The coarsest
level that still supports referral is the right level.

## Site list

`assets/codes.js` carries the list. Two kinds of entry:

- `source: "roster"` — on the official holding-centre roster sheet of the
  daily reporting workbook (Rasuwa 4 sites, Nuwakot 19). **These are the
  denominator for coverage-gap
  analysis.**
- `source: "reported"` — appears in submitted reports but is not on the
  roster. Recorded and flagged. A site nobody ever listed as a service point
  cannot be counted as one that was missed, so these are shown separately and
  never counted as gaps.

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
