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

  /* ---------- deterministic id ----------------------------------------
     FNV-1a over the fields that make a record what it is. Two exports of
     the same record produce the same id; two genuinely different records
     do not. Timestamps added by the device are excluded on purpose. */
  function rid(rec) {
    var basis = [
      rec.kind || "", rec.org || "", rec.date_ad || "", rec.site || "",
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
          serverTimestamp: fsMod.serverTimestamp,
          signIn: auMod.signInWithEmailAndPassword, signOut: auMod.signOut,
          onAuth: auMod.onAuthStateChanged
        };
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
     truth either way, never "sent" when it was not. */
  function submit(rec) {
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

  function push(r) {
    var body = JSON.parse(JSON.stringify(r));
    delete body._device_ts;
    body.server_ts = api.serverTimestamp();
    body.device_ts = r._device_ts;
    return api.setDoc(api.doc(db, COLL, r._rid), body);
  }

  function drop(id) {
    setQueue(queue().filter(function (x) { return x._rid !== id; }));
  }

  /* ---------- flush ---------------------------------------------------
     Sequential, not parallel: a phone on one bar of signal handles one
     write at a time far better than twenty at once. */
  function flush() {
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

  window.FB = {
    status: status,
    onStatus: function (f) { stateCbs.push(f); f(status()); },
    onUser: function (f) { userCbs.push(f); f(state.user); },
    submit: submit, flush: flush, queue: queue, rid: rid,
    watch: watch, signIn: signIn, signOut: signOutNow,
    clearQueue: function () { setQueue([]); announce(); }
  };
})();
