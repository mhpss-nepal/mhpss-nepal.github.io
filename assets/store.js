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
const SCHEMA_VERSION = "4ws-np-0.1.0";

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
  if (t === null) p.push("Total people reached is required (enter 0 if none)");
  const parts = ["fU18", "mU18", "oU18", "f18", "m18", "o18"].map((k) => num(r[k]) || 0);
  const sum = parts.reduce((a, b) => a + b, 0);
  if (t !== null && sum > t) p.push(`Disaggregated figures add to ${sum}, more than the total of ${t}`);
  if (t !== null && sum > 0 && sum < t) p.push(`Disaggregated figures add to ${sum} of ${t} — ${t - sum} unaccounted. Leave all blank, or account for all.`);
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
  "reachedTotal", "fU18", "mU18", "oU18", "f18", "m18", "o18",
  "schemaVersion",
];

function toCSV(rows) {
  const esc = (v) => {
    const s = Array.isArray(v) ? v.join(";") : v === null || v === undefined ? "" : String(v);
    return /[",\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s;
  };
  const head = CSV_COLUMNS.join(",");
  const body = rows.map((r) => CSV_COLUMNS.map((c) => esc(r[c])).join(",")).join("\n");
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
  SCHEMA_VERSION, CSV_COLUMNS, recordId, all, active, save, archive,
  validate, toCSV, download, stamp, clearAll
};
