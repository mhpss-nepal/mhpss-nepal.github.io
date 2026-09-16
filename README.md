# MHPSS Coordination Hub — Nepal

Draft information-management instruments for the **mental health and psychosocial
support (MHPSS)** side of the Rasuwa–Bhote Koshi flood response, for discussion
with the WHO Nepal mental health team, the Ministry of Health and Food Safety
and the Epidemiology and Disease Control Division (EDCD).

**→ [mhpss-nepal.github.io](https://mhpss-nepal.github.io/)**

---

> ## ⚠ Everything you see running is synthetic
>
> The hub is populated by a deterministic synthetic dataset generated on
> 15 September 2026 (`gen.js` → `data/demo.js`). **No figure, name, site total or
> date shown on the site is response data.** Nothing here may be quoted,
> screenshotted as evidence, or cited in any report.
>
> The charts carry a `SYNTHETIC` watermark inside the SVG so that a cropped
> screenshot still says so.

**No personal data, and none is to be added.** No names, telephone numbers or
email addresses of service users or of staff appear in this repository, in any
branch, however briefly. See [`data/README.md`](data/README.md).

**No unpublished operational figures.** The measured defect counts, partner reach
figures and duplication analysis of the current reporting workbook live in the
data inventory shared privately with WHO, the Ministry and EDCD. They are
deliberately absent here: they are unpublished figures attributed to named
partners, and they are not ours to publish.

---

## Why this exists

A national 5W already exists. It is run by NDRRMA, it is government-owned, and
Protection–MHPSS is already one of its clusters. The mental health side runs a
separate reporting sheet that does not feed it.

**So the gap is not the instrument. The gap is the connection.**

What the current sheet cannot do — and what a 4Ws exists to do — is say *which
sites are at zero*. It cannot, because the holding-centre roster is written in
Devanagari while every reported location is written in Roman script, and the two
have no key between them. That single missing key is what this repository is
built to supply.

## What is here

| Address | What it is | Layer |
|---|---|---|
| [`/`](index.html) | **Home** — the MHPSS Technical Working Group, its mission and membership (to be agreed), what it does, the helplines | 3 · public |
| [`flood-response.html`](flood-response.html) | **Flood Response** — the event as its sources state it, the published response summary, helplines, field tools, programme guidance (none yet), and how the response is coordinated | 3 · public |
| [`bps.html`](bps.html) · [`iec.html`](iec.html) · [`videos.html`](videos.html) | **BPS+ · IEC · Videos** — honestly empty until real, approved Nepal material exists | 3 · public |
| [`referral-directory.html`](referral-directory.html) | **Referral Directory** — helplines, the declared affected area on COD-AB boundaries, and the published palika-level directory | 3 · public |
| [`resources.html`](resources.html) · [`contact-us.html`](contact-us.html) | **Resources · Contact** — sourced items only; roles, names to be confirmed | 3 · public |
| [`form/`](form/index.html) | **Layer 1.** The field forms and the printable QR card sheet | 1 |
| [`hub/`](hub/index.html) | **Layer 2.** Coordination view, coverage and 4Ws, field inbox, access | 2 |
| [`architecture.html`](architecture.html) · [`method.html`](method.html) · [`access-explained.html`](access-explained.html) · [`layer3.html`](layer3.html) | How this system works — reached from the footer, not the menu | reference |
| [`assets/public-read.js`](assets/public-read.js) | The public pages' only read: `public_stats`, aggregates a coordinator publishes | 3 |
| [`assets/codes.js`](assets/codes.js) | Controlled vocabularies — sites, organisations, activities, cadres | 1–2 |
| [`assets/store.js`](assets/store.js) | Local storage, deterministic ids, validation, export | 1–2 |
| [`docs/DATA_MODEL.md`](docs/DATA_MODEL.md) | Field-by-field mapping to the IASC 4Ws model | 1–2 |
| [`gen.js`](gen.js) | Generates the synthetic demonstration dataset | 2 |
| [`tools/`](tools/) | The deploy gates: navigation, bilingual, offline, QR, figures, map, text setting, contrast | all |

### The form

One row per activity, per site, per day. Coded sites and activities; sex and age
disaggregation with a live cross-check against the total; both calendars stored
separately; works with no signal; exports CSV or JSON.

It has **no beneficiary fields and none are to be added.** Resubmitting the same
site, date, activity and organisation updates that report rather than creating a
second one, so a double tap or a re-sync cannot inflate a figure.

### The hub

Five doors following the pattern of the Sadar Hati Integrated Hub — one per
architecture layer, plus the architecture concept and the method register. The
layer badge on each door says who it is for, so nobody has to guess which page
they are supposed to open.

### The coordination view and the dashboard

- **Coverage gaps** — which roster sites have *no* report in the period. This is
  what a 4Ws is for: not who is present, but which sites are at zero.
- **Duplication check** — site-days with more than one organisation reporting,
  with the three readings distinguished: different activities, one organisation
  under two funding tags, or genuinely the same activity twice.
- **4Ws matrix** — by organisation: districts, sites, activities, reach, first
  and last report.
- **Workforce** — cadre by district. Cadre and district only; no contact details.

## Running it

No build step, no dependencies, no server, no network.

```bash
open index.html                 # macOS — or just double-click it
python3 -m http.server 8080     # if you prefer a local URL
```

Everything works offline, including from a USB stick. That is deliberate: upper
Rasuwa is helicopter-only and is not expected to change for two to three months,
so a tool that needs a connection is a tool that does not reach the north at all.

Scripts are classic `<script>` tags rather than ES modules, because browsers
refuse module imports over `file://` — and opening the file directly has to work.

To regenerate the demonstration data (deterministic — the same seed gives the
same dataset on every machine):

```bash
node gen.js
```

## The governance position

Three questions were raised on 14 September 2026 and remain open:

1. Hosting a prototype on a non-WHO account
2. AI assistance in development
3. The procurement route for a domain

**Until each has a written answer, this is an internal demonstration**, and the
demonstration runs on synthetic content only. That is not caution for its own
sake: placing WHO personal data with a third-party provider is a transfer
requiring a written agreement with specified security undertakings, and a
personal account has none.

A form with no backend cannot breach that rule, which is why this one has no
backend. When a backend is authorised, only two functions in `store.js` change —
the record shape, the deterministic id and the validation stay as they are.

### Where this is going

| Stage | | |
|---|---|---|
| **0** | Fix the form | The revised instrument on the government's own matrix. No infrastructure. |
| **1** | Offline demonstrator | *This repository.* Synthetic data, running from a laptop. |
| **2** | Proof of concept | Real submissions from a few partners, on WHO-provisioned infrastructure, one cycle. Then a decision. |
| **3** | Government handover | Public layer at EDCD, a named secretariat in writing, one full update cycle run by the owner. |

**This organisation account exists to make stage 3 possible.** A GitHub
Organization can add owners and be transferred; a personal account cannot. The
account is deliberately named for the function, not for a ministry — it does not
present itself as WHO, the Ministry of Health and Food Safety, or EDCD, and it
should not be made to.

## Known gaps

Stated rather than smoothed over.

- **IASC 4Ws activity codes are applied in part.** The 2012 code list (Table 2:
  11 codes, 45 subcodes) is in hand. Eight activities carry their subcode as a
  direct match; five carry a rule instead, because the subcode depends on the
  cadre or the content, and no subcode is written for them. Whether helpline
  contact and coordination meeting belong in a 4Ws activity list, and whether
  the 2012 codes or the updated set in a May 2024 draft toolkit (not obtained)
  should be the basis, are open.
- **No Bikram Sambat conversion.** Nepali month lengths vary year to year and
  cannot be computed from a formula. A verified calendar table for 2082–2085
  from a Government of Nepal source is needed first.
- **The site list is not agreed.** It is derived from the holding-centre roster
  sheet, the list of centres from the District Administration Office, Nuwakot,
  of 29 Bhadra 2083, and sites appearing in submitted reports. EDCD and the
  MHPSS Technical Working Group have not signed it off.
- **The activity list is not agreed.** Consolidated from what partners have
  actually submitted, not from an agreed taxonomy.
- **No accessibility audit** has been run beyond colour-contrast validation of
  the chart palette.
- **Most text is not yet in Nepali.** Pages carry a language switch and fall
  back to English where a Nepali string is still awaited; machine drafts are
  announced as such, and clinical wording stays in English.

## Attribution

Colours sampled from who.int on 15 September 2026. The chart palette is anchored
on that blue and validated for colour-vision deficiency separation and contrast
in both light and dark modes.

**No emblem is used.** WHO emblem use requires express written permission, and
the Nepal national emblem belongs to the Ministry. Institutional naming verified
against `mohp.gov.np` and `edcd.gov.np` on 15 September 2026 — Ministry of Health
and Food Safety · Department of Health Services · Epidemiology and Disease
Control Division · Non-Communicable Disease & Mental Health Section.

Prepared with AI assistance.
