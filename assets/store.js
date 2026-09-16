/* =====================================================================
   MHPSS Nepal — local store
   ---------------------------------------------------------------------
   Deliberately has NO backend. Records are held in this browser only,
   and leave it only when a person exports them. That is not a temporary
   shortcut: until the three governance questions have written answers,
   no operational data may sit on infrastructure that is not WHO's or
   the government's. A form with no server cannot breach that rule.

   When a backend is authorised, only `save()` and `all()` change. The
   record shape, the deterministic id and the validation stay as they are.
   ===================================================================== */

const KEY = "mhpss-np-4ws-v1";
const SCHEMA_VERSION = "4ws-np-0.2.0";  /* 0.2.0: four age bands, 16 Sep 2026 */

/* ---------------------------------------------------------------------
   Deterministic record id.
   The same report submitted twice — a double tap, a page reload, a
   re-sync after signal returns — produces the same id and therefore one
   record, not two. This is the anti-duplication guarantee at the record
   level; it is separate from the analytical de-duplication check, which
   looks for two different organisations reporting one site on one day.
   FNV-1a, 32-bit, rendered base36. Not a security hash; an identity hash.
   ------------------------------------------------------------------- */
function fnv1a(str) {
  let h = 0x811c9dc5;
  for (let i = 0; i < str.length; i++) {
    h ^= str.charCodeAt(i);
    h = (h + ((h << 1) + (h << 4) + (h << 7) + (h << 8) + (h << 24))) >>> 0;
  }
  return h >>> 0;
}
function recordId(r) {
  const parts = [r.org, r.orgOther || "", r.site, r.siteOther || "", r.dateAD, r.activity, r.modality].join("|");
  return "R" + fnv1a(parts).toString(36).toUpperCase().padStart(7, "0");
}

/* ---------------------------------------------------------------------
   Storage. Wrapped because localStorage throws in private windows and
   returns empty when site data is cleared. A form that breaks when
   storage is unavailable is a form that loses a day of field reporting.
   ------------------------------------------------------------------- */
function read() {
  try {
    const raw = localStorage.getItem(KEY);
    return raw ? JSON.parse(raw) : [];
  } catch (e) {
    console.warn("store: read failed, continuing in memory", e);
    return window.__mem || [];
  }
}
function write(list) {
  window.__mem = list;
  try {
    localStorage.setItem(KEY, JSON.stringify(list));
    return true;
  } catch (e) {
    console.warn("store: write failed, held in memory for this page only", e);
    return false;
  }
}

function all() {
  return read().sort((a, b) => (b.createdAt || "").localeCompare(a.createdAt || ""));
}

/* Today, on this device, as YYYY-MM-DD. Built from local components on
   purpose: toISOString() would give the UTC day and reject early-morning
   reports from Nepal. */
function todayLocal() {
  const d = new Date();
  const p = (n) => String(n).padStart(2, "0");
  return d.getFullYear() + "-" + p(d.getMonth() + 1) + "-" + p(d.getDate());
}

function save(rec) {
  const list = read();
  const id = recordId(rec);
  const now = new Date().toISOString();
  const idx = list.findIndex((x) => x.id === id);
  const out = { ...rec, id, schemaVersion: SCHEMA_VERSION };

  if (idx >= 0) {
    // Same report again: keep the original creation time, record the revision.
    out.createdAt = list[idx].createdAt;
    out.revisedAt = now;
    out.revision = (list[idx].revision || 0) + 1;
    out.previous = list[idx].previous ? [...list[idx].previous, stripHistory(list[idx])] : [stripHistory(list[idx])];
    list[idx] = out;
    const persistedRev = write(list);
    syncToRegister(out);   /* a corrected report must reach the register too */
    return { record: out, duplicateOf: id, persisted: persistedRev };
  }
  out.createdAt = now;
  out.revision = 0;
  list.push(out);
  const persisted = write(list);

  /* The device copy is written FIRST and unconditionally -- that is the
     record. Only then is a push attempted, and a failed push leaves the
     record queued rather than losing it.

     This was missing until 16 Sep 2026: the activity report is the only
     form that saves through this file rather than l1.js, so wiring the
     bridge into l1.js alone left the 4Ws report -- the form that feeds
     the 5W -- saving locally and never reaching the register. Found by
     submitting the real form and checking the queue. */
  syncToRegister(out);
  return { record: out, duplicateOf: null, persisted: persisted };
}

/* Shape an activity report for the register and hand it to the bridge.
   `kind` and `schema` are what the security rules match on; the bridge
   adds the server timestamp and strips the focal point. Silent when no
   bridge is loaded, so the form still works as a local-only instrument. */
function syncToRegister(rec) {
  if (!window.FB || typeof window.FB.submit !== "function") return null;
  const body = { ...rec, kind: "activity", schema: "mhpss-np-4ws/" + SCHEMA_VERSION };
  return window.FB.submit(body);
}

/* Nothing is deleted. A removed record is archived with a reason, so the
   figure a report carried on a given date can always be reconstructed. */
function archive(id, reason) {
  const list = read();
  const i = list.findIndex((x) => x.id === id);
  if (i < 0) return false;
  list[i] = { ...list[i], archived: true, archivedAt: new Date().toISOString(), archiveReason: reason || "" };
  return write(list);
}

function stripHistory(r) {
  const { previous, ...rest } = r;
  return rest;
}

function active() {
  return all().filter((r) => !r.archived);
}

/* ---------------------------------------------------------------------
   AGE BANDS — the one place they are defined.
   The form collects four; the official Nepal 5Ws asks for two. The four
   were chosen so that no second collection is ever needed:
       0-4  +  5-17   = the official "under 18"
       18-59 + 60+    = the official "18 and over"
   so one grid satisfies the team's ask for an under-5 figure and the
   5Ws rollup at the same time. Any page that needs the official two
   bands calls fold(); nothing else knows both shapes.
   ------------------------------------------------------------------- */
const BANDS = [
  { key: "04",   lo: 0,  hi: 4,    label: "0–4",   f: "f04",   m: "m04",   o: "o04",   child: true  },
  { key: "517",  lo: 5,  hi: 17,   label: "5–17",  f: "f517",  m: "m517",  o: "o517",  child: true  },
  { key: "1859", lo: 18, hi: 59,   label: "18–59", f: "f1859", m: "m1859", o: "o1859", child: false },
  { key: "60",   lo: 60, hi: null, label: "60+",   f: "f60",   m: "m60",   o: "o60",   child: false },
];
const PART_IDS = BANDS.reduce((a, b) => a.concat([b.f, b.m, b.o]), []);

/* The two "of whom" counts. NOT additive: a person already counted in a
   band above can appear in either or both of these. They never enter the
   sum check -- a pregnant woman counted once as 18-59 female and once
   here is one person, not two. */
const OF_WHOM = ["ofPwd", "ofPreg"];

/* Fold a record to the official two bands.
   A record filed before 16 Sep 2026 carries only fU18/f18 and no band
   fields at all, so the fold reads the legacy pair when no band is
   filled. Both shapes therefore count in the same total, which is what
   lets the coordination view read the whole file rather than the part
   filed since the change. */
function fold(r) {
  const any = PART_IDS.some((k) => num(r[k]) !== null);
  if (!any) {
    return {
      fU18: num(r.fU18) || 0, mU18: num(r.mU18) || 0, oU18: num(r.oU18) || 0,
      f18:  num(r.f18)  || 0, m18:  num(r.m18)  || 0, o18:  num(r.o18)  || 0,
      banded: false,
    };
  }
  const g = (k) => num(r[k]) || 0;
  const kids = BANDS.filter((b) => b.child), adults = BANDS.filter((b) => !b.child);
  const s = (set, sex) => set.reduce((a, b) => a + g(b[sex]), 0);
  return {
    fU18: s(kids, "f"),   mU18: s(kids, "m"),   oU18: s(kids, "o"),
    f18:  s(adults, "f"), m18:  s(adults, "m"), o18:  s(adults, "o"),
    banded: true,
  };
}

/* Total disaggregated people in a record, either shape. */
function disaggTotal(r) {
  const d = fold(r);
  return d.fU18 + d.mU18 + d.oU18 + d.f18 + d.m18 + d.o18;
}

/* ---------------------------------------------------------------------
   Validation. Returns a list of problems; an empty list means valid.
   The disaggregation rule matters: in the current workbook several rows
   have sex and age breakdowns typed into the provider column because the
   form has nowhere to put them. Here they have somewhere, and the parts
   are checked against the total rather than trusted.
   ------------------------------------------------------------------- */
function validate(r) {
  const p = [];
  const need = { org: "Reporting organisation", site: "Site", dateAD: "Date", activity: "Activity", modality: "Modality", focalName: "Focal point name", focalPhone: "Focal point phone" };
  for (const [k, label] of Object.entries(need)) if (!r[k]) p.push(`${label} is required`);
  if (r.org === "OTHER" && !r.orgOther) p.push("Name the organisation");
  if (r.site === "OTHER" && !r.siteOther) p.push("Name the site");
  /* The DEVICE's date, not UTC. Nepal is UTC+05:45, so from midnight until
     05:45 local the UTC date is still yesterday -- a worker filing an early
     report with today's date was told it was in the future and could not
     submit at all. Found by test, 16 Sep 2026. */
  if (r.dateAD && r.dateAD > todayLocal()) p.push("Date is in the future");
  if (!(r.targetGroups || []).length) p.push("Select at least one target group");

  const t = num(r.reachedTotal);
  if (t === null) p.push("Total reached is required (enter 0 if none)");
  /* The counting basis is required because without it the figure cannot be
     used: the cleaned backlog is in service contacts, the form once said
     "people", and a series that mixes the two is not a series. R-U1
     (NDRRMA / EDCD) rules on what goes into the 5W; this field only records
     what the reporter actually counted. */
  if (!r.countBasis) p.push("Say what the total counts — service contacts, distinct people, or not sure");
  const dp = num(r.distinctPeople);
  if (dp !== null && r.countBasis !== "CONTACTS") p.push("Distinct people applies only when the total is a contact count");
  if (dp !== null && t !== null && dp > t) p.push(`Distinct people (${dp}) cannot exceed the contact count of ${t}`);
  const sum = disaggTotal(r);
  if (t !== null && sum > t) p.push(`Disaggregated figures add to ${sum}, more than the total of ${t}`);
  if (t !== null && sum > 0 && sum < t) p.push(`Disaggregated figures add to ${sum} of ${t} — ${t - sum} unaccounted. Leave all blank, or account for all.`);
  /* The "of whom" counts sit INSIDE the total, so each one can be at most
     the total -- but they are not added to it and not added to each other,
     because one person can be in both. */
  const ofLabel = { ofPwd: "Persons with disabilities", ofPreg: "Pregnant or postpartum" };
  for (const k of OF_WHOM) {
    const v = num(r[k]);
    if (v !== null && t !== null && v > t) p.push(`${ofLabel[k]} (${v}) is more than the total of ${t}`);
  }
  return p;
}
function num(v) {
  if (v === "" || v === null || v === undefined) return null;
  const n = Number(v);
  return Number.isFinite(n) && n >= 0 ? n : null;
}

/* ---------------------------------------------------------------------
   Export. CSV is one row per record, flat, with no subtotal rows.
   The largest defect in the current workbook comes from subtotals living
   in the same column as the data, so a plain sum counts a large share of
   the reach twice. Totals belong in the analysis, never in the dataset.
   ------------------------------------------------------------------- */
const CSV_COLUMNS = [
  "id", "createdAt", "revision", "dateAD", "dateBS", "district", "site", "siteOther", "siteSource",
  "org", "orgOther", "donor", "focalName", "focalPhone", "focalEmail", "cadre",
  "activity", "modality", "status", "targetGroups", "description",
  "reachedTotal", "countBasis", "distinctPeople",
  /* four bands as collected */
  "f04", "m04", "o04", "f517", "m517", "o517", "f1859", "m1859", "o1859", "f60", "m60", "o60",
  /* the official two, folded, so a 5Ws submission needs no arithmetic and
     a legacy record exports in the same columns as a new one */
  "fU18", "mU18", "oU18", "f18", "m18", "o18",
  /* counted inside the figures above, never added to them */
  "ofPwd", "ofPreg",
  "schemaVersion",
];

function toCSV(rows) {
  const esc = (v) => {
    const s = Array.isArray(v) ? v.join(";") : v === null || v === undefined ? "" : String(v);
    return /[",\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s;
  };
  const head = CSV_COLUMNS.join(",");
  /* The folded columns are computed at export, not stored on the record:
     one figure in two places is one figure that can disagree with itself. */
  const body = rows.map((r) => {
    const row = { ...r, ...fold(r) };
    return CSV_COLUMNS.map((c) => esc(row[c])).join(",");
  }).join("\n");
  return "﻿" + head + "\n" + body + "\n"; // BOM so Excel reads UTF-8
}

function download(filename, text, mime) {
  const blob = new Blob([text], { type: (mime || "text/plain") + ";charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  setTimeout(() => URL.revokeObjectURL(url), 1500);
}

function stamp() {
  const d = new Date();
  const p = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}${p(d.getMonth() + 1)}${p(d.getDate())}_${p(d.getHours())}${p(d.getMinutes())}`;
}

function clearAll() {
  try { localStorage.removeItem(KEY); } catch (e) { /* ignore */ }
  window.__mem = [];
}

/* Global for the same reason as codes.js — see the note there. */
window.STORE = {
  SCHEMA_VERSION, CSV_COLUMNS, BANDS, PART_IDS, OF_WHOM, fold, disaggTotal,
  recordId, all, active, save, archive,
  validate, toCSV, download, stamp, clearAll
};
