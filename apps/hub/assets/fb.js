/* =====================================================================
   MHPSS Nepal — Firestore bridge
   ---------------------------------------------------------------------
   Modelled on the Sadar Hati hub module (saha-shared.js): dynamic import
   of the Firebase 10.13.0 modular SDK from gstatic, initialiseApp, then
   a thin push function. Two deliberate differences, both because field
   workers in Rasuwa will often have no signal at all:

   1. LOCAL FIRST, ALWAYS. Every record is written to this device before
      any network call. Sadar Hati is online-first; that is fine in
      Malang and wrong in a holding centre above Dhunche. A record must
      never depend on the network to survive.

   2. DETERMINISTIC DOCUMENT IDs, via setDoc rather than addDoc. A queued
      record may be retried many times — on reconnect, on reload, on a
      second device that has the same export. addDoc would create a new
      document every time and silently inflate the count. setDoc with an
      id derived from the record's own content writes the same document
      again instead, so retrying is safe and de-duplication happens for
      free at the database.

   Nothing here logs record content to the console. Never add that: a
   phone screen in a shelter is not a private place.
   ===================================================================== */
(function () {
  "use strict";

  var SDK = "https://www.gstatic.com/firebasejs/10.13.0/";
  var cfg = window.FB_CONFIG || {};
  var COLL = window.FB_COLLECTION || "submissions";
  var QKEY = "mhpss-np-queue-v1";
  var LKEY = "mhpss-np-linkmail";
  /* These are client-interface intentions, not authorization guarantees.
     The authoritative Rules are not versioned here; server enforcement is
     unverified and this branch must not be deployed. */
  var ROLE_LIST = [
    ["admin",       "Client intent: request record administration and role-management operations."],
    ["coordinator", "Client intent: request record reads and publication operations."],
    ["im_officer",  "Client intent: the coordinator workflow under a distinct audit label."],
    ["viewer",      "Client intent: request record reads without publication or administration controls."]
  ];

  var state = {
    configured: !!(cfg.projectId && cfg.apiKey),
    ready: false,
    error: "",
    user: null
  };
  var db = null, auth = null, api = {};
  var userCbs = [], stateCbs = [];

  function announce() {
    stateCbs.forEach(function (f) { try { f(status()); } catch (e) { /* ignore */ } });
  }
  function status() {
    return {
      configured: state.configured,
      ready: state.ready,
      error: state.error,
      online: navigator.onLine,
      user: state.user ? { email: state.user.email, uid: state.user.uid } : null,
      pending: queue().length
    };
  }

  /* ---------- local queue ---------------------------------------------
     The queue is the record of truth until the server confirms. An entry
     leaves the queue only once Firestore has acknowledged the write. */
  function queue() {
    try { return JSON.parse(localStorage.getItem(QKEY) || "[]"); } catch (e) { return []; }
  }
  function setQueue(q) {
    try { localStorage.setItem(QKEY, JSON.stringify(q)); return true; }
    catch (e) { window.__fbq = q; return false; }
  }

  /* ---------- safeguarding gate (independent of l1.js) ----------------
     A referral whose safeguarding check is not ticked may be a GBV case,
     an unaccompanied or separated child, or an immediate risk to life: it
     must never enter the coordination register. l1.js refuses it at the
     device write boundary; this is the same rule enforced again at the
     queue, so any caller that reaches the queue directly -- a retry after
     reconnect, a re-import, another script -- is refused too, and nothing
     is written or transmitted.

     Deliberately self-contained: if l1.js is absent (the hub loads this
     file without it) or its check is ever weakened, this still fails
     closed. Safe means the safeguard is explicitly ticked in the record
     itself, never inferred from its absence. */
  var SAFEGUARDING_FALLBACK =
    "STOP. Do not record this case here. The referral's safeguarding check is not ticked; " +
    "it may be a GBV case, an unaccompanied or separated child, or an immediate risk to life. " +
    "Close the form and use the specialised pathway.";
  function isUnsafeReferral(rec) {
    if (!rec) return false;
    var referral = rec.kind === "referral" ||
      (typeof rec.schema === "string" && /referral/.test(rec.schema));
    if (!referral) return false;
    return !(rec.safeguarding_confirmed === true && rec.excludes_gbv_uasc_lifethreat === true);
  }
  function queueRefusal(rec) {
    if (!isUnsafeReferral(rec)) return "";
    if (window.L1 && typeof window.L1.safeguardingRefusal === "function") {
      /* one wording, owned by l1.js, when it is present */
      return window.L1.safeguardingRefusal(rec) || SAFEGUARDING_FALLBACK;
    }
    return SAFEGUARDING_FALLBACK;
  }

  /* ---------- deterministic id ----------------------------------------
     FNV-1a over the fields that make a record what it is. Two exports of
     the same record produce the same id; two genuinely different records
     do not. Timestamps added by the device are excluded on purpose. */
  function rid(rec) {
    /* The 4Ws activity report names its fields dateAD / activity / modality
       (camelCase, from store.js), not date_ad / service like the l1.js
       forms. Until 16 Sep 2026 this basis read only the snake_case names,
       so every activity report from one organisation at one site hashed to
       the SAME document id -- each new day's report overwrote the last in
       the register. The report's own deterministic id (store.js recordId,
       over org, site, palika, date, activity, modality) is the identity, so
       it is the first thing in the basis; the camelCase fields follow for a
       record that arrives without one. */
    var basis = [
      rec.kind || "", rec.id || "", rec.org || "", rec.date_ad || rec.dateAD || "", rec.site || "",
      rec.palika || "", rec.activity || "", rec.modality || "",
      rec.contact_code || "", rec.service || rec.reason || rec.instrument || "",
      rec.focal_name || "", rec.administration || "", rec.direction || "",
      rec.q1 === undefined ? "" : String(rec.q1),
      rec.coping === undefined ? "" : String(rec.coping),
      rec.minutes || "", rec.total === undefined || rec.total === null ? "" : String(rec.total)
    ].join("|");
    var h1 = 0x811c9dc5 >>> 0, h2 = 0x01000193 >>> 0, i;
    for (i = 0; i < basis.length; i++) {
      h1 ^= basis.charCodeAt(i); h1 = Math.imul(h1, 0x01000193) >>> 0;
    }
    for (i = basis.length - 1; i >= 0; i--) {
      h2 ^= basis.charCodeAt(i); h2 = Math.imul(h2, 0x01000193) >>> 0;
    }
    function p(n) { var s = n.toString(36).toUpperCase(); while (s.length < 7) s = "0" + s; return s; }
    return (rec.kind || "rec") + "_" + p(h1) + p(h2);
  }

  /* ---------- init ---------------------------------------------------- */
  if (!state.configured) {
    state.error = "not configured";
  } else {
    (async function () {
      try {
        var appMod = await import(SDK + "firebase-app.js");
        var fsMod  = await import(SDK + "firebase-firestore.js");
        var auMod  = await import(SDK + "firebase-auth.js");
        var app = appMod.initializeApp(cfg);
        db = fsMod.getFirestore(app);
        auth = auMod.getAuth(app);
        api = {
          doc: fsMod.doc, setDoc: fsMod.setDoc, collection: fsMod.collection,
          query: fsMod.query, where: fsMod.where, orderBy: fsMod.orderBy,
          limit: fsMod.limit, onSnapshot: fsMod.onSnapshot, getDocs: fsMod.getDocs,
          getDoc: fsMod.getDoc, deleteDoc: fsMod.deleteDoc,
          serverTimestamp: fsMod.serverTimestamp,
          signIn: auMod.signInWithEmailAndPassword, signOut: auMod.signOut,
          onAuth: auMod.onAuthStateChanged,
          sendLink: auMod.sendSignInLinkToEmail,
          isLink: auMod.isSignInWithEmailLink,
          signInLink: auMod.signInWithEmailLink
        };
        /* An email link arrives as a URL on this same page. Finish the
           sign-in before wiring anything else up, so the page renders once
           in its final state rather than flashing a sign-in form first. */
        try {
          if (api.isLink(auth, window.location.href)) {
            var pending = "";
            try { pending = localStorage.getItem(LKEY) || ""; } catch (e) { /* ignore */ }
            if (!pending) {
              /* The link was opened in a different browser from the one that
                 asked for it, so the address is not on this device. Asking
                 for it again is the documented flow, not a failure. */
              pending = window.prompt(
                "To finish signing in, type the email address this link was sent to:") || "";
            }
            if (pending) {
              await api.signInLink(auth, pending, window.location.href);
              try { localStorage.removeItem(LKEY); } catch (e) { /* ignore */ }
              /* Strip the credential out of the address bar so it is not left
                 in history, bookmarks or a screenshot. */
              if (window.history && window.history.replaceState) {
                window.history.replaceState({}, document.title,
                  window.location.pathname + window.location.search);
              }
            }
          }
        } catch (e) {
          state.error = "sign-in link failed: " +
            (e && e.message ? e.message.replace(/^Firebase:\s*/, "") : String(e));
        }

        api.onAuth(auth, function (u) {
          state.user = u || null;
          userCbs.forEach(function (f) { try { f(state.user); } catch (e) { /* ignore */ } });
          announce();
        });
        state.ready = true; state.error = "";
        announce();
        flush();
      } catch (e) {
        state.ready = false;
        state.error = "could not reach Firebase: " + (e && e.message ? e.message : String(e));
        announce();
      }
    })();
  }

  /* ---------- submit --------------------------------------------------
     Returns immediately once the record is safe on this device. The
     network attempt continues in the background; the caller is told the
     truth either way, never "sent" when it was not.

     A referral that fails the safeguarding gate is refused here, before
     the queue: nothing is written and nothing is transmitted. The refusal
     surfaces to the caller's promise rejection, so a retry or a direct
     caller cannot slip an unsafe record past the form. The queue is also
     pruned of any such entry that reached it before the gate existed. */
  function submit(rec) {
    var refusal = queueRefusal(rec);
    if (refusal) {
      purgeUnsafeQueue();
      return Promise.reject(new Error(refusal));
    }
    var r = JSON.parse(JSON.stringify(rec || {}));
    r._rid = rid(r);
    r._device_ts = new Date().toISOString();
    var q = queue();
    /* already queued and unsent? replace rather than add a second copy */
    var at = -1;
    for (var i = 0; i < q.length; i++) { if (q[i]._rid === r._rid) { at = i; break; } }
    if (at >= 0) q[at] = r; else q.push(r);
    var persisted = setQueue(q);

    var out = { local: true, persisted: persisted, rid: r._rid, remote: false, error: "" };
    if (!state.ready) {
      out.error = state.configured ? (state.error || "not connected yet") : "not configured";
      announce();
      return Promise.resolve(out);
    }
    return push(r).then(function () {
      out.remote = true; drop(r._rid); announce(); return out;
    }).catch(function (e) {
      out.error = e && e.message ? e.message : String(e);
      announce(); return out;
    });
  }

  /* ---------- what never crosses the network -------------------------
     A 4Ws report names a focal point so a figure can be queried later.
     That is normal humanitarian practice and the detail is useful -- but
     it is a named professional's mobile number, and the rule the data
     workstream set is that professionals' contact details stay in the
     source file and "do not go into any deliverable, any repository, or
     any hosted system".

     So the focal point stays on the handset and in the private export a
     worker sends to coordination, and is stripped before the record is
     pushed. Coordination still gets it, through the file; the hosted
     database never holds it.

     This client strips these keys. Server enforcement is unverified until
     the authoritative Rules are reviewed and versioned. If the Technical
     Working Group later decides the hosted copy should carry a focal point,
     the client and reviewed server policy must change together. */
  var NEVER_SENT = ["focalName", "focalPhone", "focalEmail",
                    "focal_name", "focal_phone", "focal_email"];

  function push(r) {
    var body = JSON.parse(JSON.stringify(r));
    delete body._device_ts;
    for (var i = 0; i < NEVER_SENT.length; i++) delete body[NEVER_SENT[i]];
    body.server_ts = api.serverTimestamp();
    body.device_ts = r._device_ts;
    return api.setDoc(api.doc(db, COLL, r._rid), body);
  }

  function drop(id) {
    setQueue(queue().filter(function (x) { return x._rid !== id; }));
  }

  /* Nothing unsafe may leave the device, and nothing unsafe may sit in the
     queue waiting to. This is called before every flush and before a
     refused submit. An entry queued before the gate existed -- for
     example on an offline handset whose form was precached earlier -- is
     removed rather than transmitted. Returns the number removed, so a
     caller can report it. */
  function purgeUnsafeQueue() {
    var q = queue(), kept = [], removed = 0, i;
    for (i = 0; i < q.length; i++) {
      if (isUnsafeReferral(q[i])) { removed++; continue; }
      kept.push(q[i]);
    }
    if (removed) {
      setQueue(kept);
      announce();
    }
    return removed;
  }

  /* ---------- flush ---------------------------------------------------
     Sequential, not parallel: a phone on one bar of signal handles one
     write at a time far better than twenty at once. */
  function flush() {
    /* Fail closed first: drop anything unsafe before any attempt to send. */
    purgeUnsafeQueue();
    if (!state.ready || !navigator.onLine) return Promise.resolve({ sent: 0, left: queue().length });
    var q = queue().slice(), sent = 0;
    return q.reduce(function (chain, r) {
      return chain.then(function () {
        return push(r).then(function () { sent++; drop(r._rid); })
                      .catch(function () { /* stays queued */ });
      });
    }, Promise.resolve()).then(function () {
      announce();
      return { sent: sent, left: queue().length };
    });
  }

  window.addEventListener("online", function () { flush(); announce(); });
  window.addEventListener("offline", announce);

  /* ---------- read (coordination side, needs a signed-in user) -------- */
  function watch(cb, onErr) {
    if (!state.ready) { if (onErr) onErr("not connected"); return function () {}; }
    var qq = api.query(api.collection(db, COLL), api.orderBy("server_ts", "desc"), api.limit(2000));
    return api.onSnapshot(qq, function (snap) {
      var rows = [];
      snap.forEach(function (d) { var o = d.data(); o._id = d.id; rows.push(o); });
      cb(rows);
    }, function (e) { if (onErr) onErr(e && e.message ? e.message : String(e)); });
  }

  /* watchKind -- the client's intended unauthenticated read shape.
     It names the kind in the query so a future reviewed server policy can
     evaluate a bounded result set. The authoritative Rules are not versioned
     here, so anonymous-read behavior and server enforcement are unverified.

     No orderBy here, deliberately. Single-field indexes are automatic;
     combinations of fields are not, and an equality filter plus an orderBy on
     a different field is a combination. Dropping the sort keeps this path
     working with no composite index to create in the console, and costs
     nothing: every page that consumes these rows sorts them itself.
     If the collection ever outgrows the limit, the fix is the composite index
     on (kind, server_ts) -- Firestore returns the error with a link to build
     it -- not a larger limit. */
  function watchKind(kind, cb, onErr) {
    if (!state.ready) { if (onErr) onErr("not connected"); return function () {}; }
    var qq = api.query(api.collection(db, COLL), api.where("kind", "==", kind), api.limit(2000));
    return api.onSnapshot(qq, function (snap) {
      var rows = [];
      snap.forEach(function (d) { var o = d.data(); o._id = d.id; rows.push(o); });
      cb(rows);
    }, function (e) { if (onErr) onErr(e && e.message ? e.message : String(e)); });
  }

  function signIn(email, pass) {
    if (!state.ready) return Promise.reject(new Error("not connected"));
    return api.signIn(auth, email, pass);
  }
  function signOutNow() {
    if (!state.ready) return Promise.resolve();
    return api.signOut(auth);
  }

  /* ---------- the sync strip -------------------------------------------
     Auto-mounted on any page that loads this file. It states the actual
     situation and never implies more than is true: "saved on this phone"
     is not "sent", and a queue of 3 says 3. A field worker who believes
     a record reached coordination when it did not is worse off than one
     who knows it is still waiting. */
  (function () {
    var css = document.createElement("style");
    css.textContent =
      "#fbbar{position:sticky;top:0;z-index:39;display:flex;gap:9px;align-items:center;" +
      "flex-wrap:wrap;padding:8px 14px;font:600 12px/1.35 'Noto Sans',system-ui,sans-serif;" +
      "background:#eef5f1;color:#24543f;border-bottom:1px solid #bcd9c9}" +
      "#fbbar.warn{background:#fdf2ea;color:#8f420f;border-bottom-color:#e8c9b0}" +
      "#fbbar.off{background:#f4f7f9;color:#5b6b76;border-bottom-color:#d8dfe4}" +
      "#fbbar .m{flex:1 1 200px;min-width:0}" +
      "#fbbar button{font:700 11.5px/1.2 inherit;font-family:inherit;border:1.5px solid currentColor;" +
      "background:#fff;color:inherit;border-radius:6px;padding:6px 11px;cursor:pointer}";
    document.head.appendChild(css);

    var bar = document.createElement("div");
    bar.id = "fbbar";

    function mount() {
      var pb = document.getElementById("pwabar");
      if (pb && pb.parentNode) pb.parentNode.insertBefore(bar, pb.nextSibling);
      else document.body.insertBefore(bar, document.body.firstElementChild);
      paint(status());
    }

    function paint(st) {
      var cls = "", msg;
      if (!st.configured) {
        cls = "off";
        msg = "<b>Saving to this device only.</b> No database is connected yet, so records stay here " +
              "until you export them. Nothing is lost.";
      } else if (!st.ready) {
        cls = "warn";
        msg = "<b>Not connected to the database.</b> " +
              (st.online ? "Retrying. " : "No signal. ") +
              "Records are safe on this phone" + (st.pending ? " — " + st.pending + " waiting to send." : ".");
      } else if (st.pending) {
        cls = "warn";
        msg = "<b>" + st.pending + " record(s) still to send.</b> " +
              (st.online ? "Sending now." : "They go as soon as you have signal.");
      } else {
        msg = "<b>Connected.</b> Records reach coordination as you save them." +
              (st.user ? " Signed in as " + st.user.email + "." : "");
      }
      bar.className = cls;
      bar.innerHTML = '<span class="m">' + msg + "</span>";
      if (st.configured && st.pending && st.online) {
        var b = document.createElement("button");
        b.type = "button"; b.textContent = "Send now";
        b.onclick = function () { b.disabled = true; b.textContent = "Sending…"; flush(); };
        bar.appendChild(b);
      }
    }

    stateCbs.push(paint);
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", mount);
    } else { mount(); }
  })();

  /* ---------- roles ----------------------------------------------------
     This client derives a role-document reference from sign-in state. It does
     not claim an authoritative role-key scheme or authorization result. The
     real Rules must be reviewed and versioned before either can be stated. */
  function myRole() {
    if (!state.ready || !state.user) return Promise.resolve(null);
    var mail = (state.user.email || "").toLowerCase();
    return api.getDoc(api.doc(db, "roles", mail))
      .then(function (d) { return d.exists() ? d.data() : null; })
      .catch(function () { return null; });
  }

  function listRoles() {
    if (!state.ready) return Promise.reject(new Error("not connected"));
    return api.getDocs(api.collection(db, "roles")).then(function (snap) {
      var out = [];
      snap.forEach(function (d) { var o = d.data(); o._email = d.id; out.push(o); });
      out.sort(function (a, b) { return (a._email || "").localeCompare(b._email || ""); });
      return out;
    });
  }

  function grantRole(personEmail, role, note) {
    if (!state.ready || !state.user) return Promise.reject(new Error("not signed in"));
    var body = {
      role: role,
      added_by: state.user.email,
      added_at: api.serverTimestamp()
    };
    if (note) body.note = String(note).slice(0, 200);
    return api.setDoc(api.doc(db, "roles", personEmail), body);
  }

  function revokeRole(personEmail) {
    if (!state.ready) return Promise.reject(new Error("not connected"));
    return api.deleteDoc(api.doc(db, "roles", personEmail));
  }

  /* ---------- passwordless sign-in ------------------------------------
     The person types their address once and clicks a link. No password is
     ever chosen, typed, shared or stored -- which also means nobody is
     holding anybody else's password. */
  function sendLink(mail) {
    if (!state.ready) return Promise.reject(new Error("not connected"));
    try { localStorage.setItem(LKEY, mail); } catch (e) { /* ignore */ }
    return api.sendLink(auth, mail, {
      url: window.location.origin + window.location.pathname,
      handleCodeInApp: true
    });
  }

  /* ---------- the public shelf -----------------------------------------
     Client intent: public_stats contains previewed aggregates rather than
     register records. This client stamps computed_at, requires `basis`, and
     limits the document shape. Server read/write enforcement is unverified
     until the authoritative Rules are reviewed and versioned.

     SAFETY, ON THIS SIDE, BECAUSE A RAW VALUE IN THE COLLECTION IS ALREADY
     EXPOSED. Redaction is computed for the WHOLE document, once, before any
     value is emitted -- not per number. That is the finding: a floor applied
     to each number in turn still lets a hidden cell be recovered by
     subtracting the published parts from the published total, and still leaves
     the row, its category label, a zero-width bar and the bar scale pointing
     at it. So:

       - a below-floor row is DROPPED (never rendered as "fewer than N" with
         its category intact);
       - any total a dropped row contributed to is WITHHELD, so the hidden cell
         cannot be recovered by subtraction;
       - organisation and palika counts go through the SAME floor (no bypass);
       - a document may not DECLARE its own floor below the policy floor;
       - a document this code cannot fully redact is REFUSED, not written.

     The reader (the public site's public-read.js) applies the same decision
     again, as defence in depth, but the fix is here first: the publisher is
     the only place that can stop a raw value being written. */
  var PUBLIC_SUPPRESSION_FLOOR = 10;
  /* keys that are bookkeeping, not counts about people: never suppressed, and
     never treated as a leak by the verification sweep below */
  var NOT_A_COUNT = {
    schema: 1, schema_version: 1, suppressed_below: 1,
    period_from: 1, period_to: 1, codes_version: 1
  };

  function policyFloor(declared) {
    var n = (typeof declared === "number" && isFinite(declared)) ? Math.floor(declared) : 0;
    return n > PUBLIC_SUPPRESSION_FLOOR ? n : PUBLIC_SUPPRESSION_FLOOR;
  }
  function belowFloorValue(n, floor) {
    return typeof n === "number" && isFinite(n) && n > 0 && n < floor;
  }
  function isPlainObject(v) {
    return !!v && typeof v === "object" && !Array.isArray(v);
  }
  function isRowFamily(v) {
    return Array.isArray(v) && v.length > 0 && isPlainObject(v[0]);
  }
  /* Does this ROW carry a count below the floor? Every numeric field of a row
     in an aggregate document is a count, so any one of them puts the row
     below the floor and the whole row goes. */
  function rowHasBelowFloor(row, floor) {
    var keys = Object.keys(row);
    for (var i = 0; i < keys.length; i++) {
      if (NOT_A_COUNT[keys[i]]) continue;
      if (belowFloorValue(row[keys[i]], floor)) return true;
    }
    return false;
  }
  /* The whole-document decision: ONE suppression pass, before anything is
     sent. A "row" is an object inside a list of objects -- a district, a
     family, a site, an organisation:

       1. a row carrying a below-floor count is DROPPED whole (never published
          as "fewer than N" with its category label intact);
       2. when any row anywhere is dropped, every scalar count OUTSIDE a row is
          WITHHELD, so the hidden cell cannot be recovered by subtracting the
          published parts from a published total. The survivor rows keep their
          own figures, which are all at or above the floor;
       3. a style="..." geometry the reader draws is computed by the reader over
          the rows it is given, so it is a function of redacted values only;
       4. every scalar count anywhere passes the same floor.

     Rule 2 is deliberately blunt -- it withholds more than the minimum -- and
     the narrower rule is an open question for Adib. The trade is stated in the
     evidence document; this is the most protective option that keeps the
     document publishable. */
  function redactPublicBody(body) {
    var out = JSON.parse(JSON.stringify(body));
    var floor = policyFloor(out.suppressed_below);
    out.suppressed_below = floor;
    var state = { dropped: false };
    return nullAggregates(dropRows(out, floor, state), floor, state, false);
  }
  /* pass 1: drop every row that carries a below-floor count */
  function dropRows(node, floor, state) {
    if (Array.isArray(node)) {
      var rowFamily = isRowFamily(node);
      var kept = [];
      node.forEach(function (item) {
        if (rowFamily && isPlainObject(item)) {
          if (rowHasBelowFloor(item, floor)) { state.dropped = true; return; }
          kept.push(dropRows(item, floor, state));
        } else {
          kept.push(dropRows(item, floor, state));
        }
      });
      return kept;
    }
    if (isPlainObject(node)) {
      Object.keys(node).forEach(function (k) { node[k] = dropRows(node[k], floor, state); });
      return node;
    }
    return node;
  }
  /* pass 2: withhold every scalar count outside a row once anything was
     dropped, and withhold any scalar count below the floor anywhere. */
  function nullAggregates(node, floor, state, inRow) {
    if (Array.isArray(node)) {
      var rowFamily = isRowFamily(node);
      node.forEach(function (item) { nullAggregates(item, floor, state, rowFamily); });
      return node;
    }
    if (isPlainObject(node)) {
      Object.keys(node).forEach(function (k) {
        var v = node[k];
        if (NOT_A_COUNT[k]) return;
        if (typeof v === "number") {
          if (belowFloorValue(v, floor) || (state.dropped && !inRow)) node[k] = null;
        } else {
          nullAggregates(v, floor, state, false);
        }
      });
    }
    return node;
  }
  /* Fail closed. A below-floor count that survived the pass above is a shape
     this code does not know how to redact (a row held as an array, say), so
     the document is refused rather than written. Returns the field path; never
     the value. */
  function firstBelowFloorCount(node, floor, path) {
    if (node === null || typeof node === "boolean" || node === undefined) return "";
    if (typeof node === "number") {
      return (isFinite(node) && node > 0 && node < floor) ? (path || "$") : "";
    }
    if (Array.isArray(node)) {
      for (var i = 0; i < node.length; i++) {
        var hit = firstBelowFloorCount(node[i], floor, (path || "$") + "[" + i + "]");
        if (hit) return hit;
      }
      return "";
    }
    if (typeof node === "object") {
      var keys = Object.keys(node);
      for (var j = 0; j < keys.length; j++) {
        if (NOT_A_COUNT[keys[j]]) continue;
        var found = firstBelowFloorCount(node[keys[j]], floor, (path || "$") + "." + keys[j]);
        if (found) return found;
      }
    }
    return "";
  }

  function publish(docId, body) {
    /* Fail closed before connection/auth checks so restricted data is refused
       by this real public_stats sink under every runtime state. */
    var restrictedKinds = { referral: true, phq9: true };
    var restrictedPrivacy = {
      "restricted-referral-person-list": true,
      "clinical": true,
      "safeguarding": true
    };
    function containsRestricted(value) {
      if (!value || typeof value !== "object") return false;
      if (restrictedKinds[value.kind] || restrictedPrivacy[value.privacy_class]) return true;
      var keys = Object.keys(value);
      for (var i = 0; i < keys.length; i++) {
        if (containsRestricted(value[keys[i]])) return true;
      }
      return false;
    }
    if (containsRestricted(body)) {
      return Promise.reject(new Error("restricted or clinical records cannot be published to public_stats"));
    }
    /* public_stats is a public aggregate shelf, never a staging destination.
       The browser is not the authoritative policy boundary, but this exact
       sink must still refuse a document-declared floor that disables policy. */
    if (docId === "referral_directory") {
      return Promise.reject(new Error("referral_directory cannot be published to public_stats"));
    }
    if (!body || body.mode !== "production") {
      return Promise.reject(new Error("non-public mode cannot be published to public_stats"));
    }
    if (typeof body.suppressed_below !== "number" ||
        !isFinite(body.suppressed_below) ||
        body.suppressed_below < PUBLIC_SUPPRESSION_FLOOR) {
      return Promise.reject(new Error("public_stats requires a suppression floor of at least " + PUBLIC_SUPPRESSION_FLOOR));
    }
    if (!state.ready) return Promise.reject(new Error("not connected"));
    if (!state.user) return Promise.reject(new Error("not signed in"));
    if (!body || typeof body.basis !== "string" || !body.basis.trim()) {
      return Promise.reject(new Error("a published document must say in `basis` what it counts"));
    }
    /* ONE redaction for the whole document, before a single value is written. */
    var out = redactPublicBody(body);
    /* Fail closed: whatever the redaction pass could not make safe, this sink
       refuses rather than writing. The path is named; the value never is. */
    var leak = firstBelowFloorCount(out, PUBLIC_SUPPRESSION_FLOOR, "$");
    if (leak) {
      return Promise.reject(new Error(
        "a below-floor count survived redaction at " + leak + "; refusing to publish"));
    }
    for (var i = 0; i < NEVER_SENT.length; i++) delete out[NEVER_SENT[i]];
    if (Object.keys(out).length + 1 >= 40) return Promise.reject(new Error("too many top-level fields for the client publication limit (< 40)"));
    out.computed_at = api.serverTimestamp();
    out.published_by_role = "coordinator";
    return api.setDoc(api.doc(db, "public_stats", docId), out).then(function () { return docId; });
  }
  /* the published copy, as anyone would see it (no account needed) */
  function readPublic(docId) {
    if (!state.ready) return Promise.reject(new Error("not connected"));
    return api.getDoc(api.doc(db, "public_stats", docId)).then(function (d) { return d.exists() ? d.data() : null; });
  }

  window.FB = {
    status: status,
    myRole: myRole, listRoles: listRoles, grantRole: grantRole, revokeRole: revokeRole,
    publish: publish, readPublic: readPublic,
    /* the whole-document redaction, exposed so the hub preview and the tests can
       show exactly what would be written, and assert on it, without publishing */
    redactPublicBody: redactPublicBody, belowFloorCount: firstBelowFloorCount,
    REDACTION_FLOOR: PUBLIC_SUPPRESSION_FLOOR,
    sendLink: sendLink, ROLES: ROLE_LIST,
    onStatus: function (f) { stateCbs.push(f); f(status()); },
    onUser: function (f) { userCbs.push(f); f(state.user); },
    submit: submit, flush: flush, queue: queue, rid: rid,
    safeguardingRefusal: function (rec) { return queueRefusal(rec); },
    purgeUnsafeQueue: purgeUnsafeQueue,
    watch: watch, watchKind: watchKind, signIn: signIn, signOut: signOutNow,
    clearQueue: function () { setQueue([]); announce(); }
  };
})();
