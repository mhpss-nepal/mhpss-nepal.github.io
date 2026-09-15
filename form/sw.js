/* =====================================================================
   MHPSS Nepal — field forms service worker
   ---------------------------------------------------------------------
   Lives at /form/sw.js so its scope is /form/ — GitHub Pages will not
   let us set a Service-Worker-Allowed header, so the file's own location
   is what defines the scope.

   Strategy, chosen deliberately:
     - HTML pages   : network first, cache as fallback. A worker with
                      signal always gets the current questions; a worker
                      without signal still gets the form.
     - CSS/JS/icons : cache first, revalidated in the background, so the
                      form opens instantly and quietly updates.
   Bump CACHE when anything in PRECACHE changes, or phones keep the old copy.
   ===================================================================== */
const CACHE = "mhpss-np-field-v1";

const PRECACHE = [
  "./",
  "index.html",
  "4ws-report.html",
  "contact.html",
  "phq9.html",
  "referral.html",
  "selfreport.html",
  "manifest.webmanifest",
  "icons/icon-192.png",
  "icons/icon-512.png",
  "icons/maskable-512.png",
  "icons/apple-touch-icon.png",
  "../assets/app.css",
  "../assets/codes.js",
  "../assets/l1.js",
  "../assets/qr.js",
  "../assets/store.js"
];

self.addEventListener("install", (e) => {
  e.waitUntil((async () => {
    const c = await caches.open(CACHE);
    /* one at a time: a single 404 must not fail the whole install and
       leave the worker with no cache at all */
    await Promise.all(PRECACHE.map(async (u) => {
      try { await c.add(new Request(u, { cache: "reload" })); }
      catch (err) { /* keep going — logged below on first fetch miss */ }
    }));
    self.skipWaiting();
  })());
});

self.addEventListener("activate", (e) => {
  e.waitUntil((async () => {
    const keys = await caches.keys();
    await Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)));
    await self.clients.claim();
  })());
});

self.addEventListener("fetch", (e) => {
  const req = e.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;

  const isPage = req.mode === "navigate" ||
                 (req.headers.get("accept") || "").includes("text/html");

  if (isPage) {
    e.respondWith((async () => {
      try {
        const fresh = await fetch(req);
        const c = await caches.open(CACHE);
        c.put(req, fresh.clone());
        return fresh;
      } catch (err) {
        const hit = await caches.match(req, { ignoreSearch: true });
        if (hit) return hit;
        const list = await caches.match("index.html");
        if (list) return list;
        return new Response(
          "<!doctype html><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>" +
          "<title>Offline</title><body style=\"font:16px/1.5 system-ui;padding:28px;color:#20313b\">" +
          "<h1 style=\"font-size:20px\">This form has not been saved to the phone yet</h1>" +
          "<p>Open the form list once while you have signal. After that it works with no signal.</p>",
          { headers: { "Content-Type": "text/html; charset=utf-8" }, status: 200 }
        );
      }
    })());
    return;
  }

  /* static: cache first, refresh in the background */
  e.respondWith((async () => {
    const c = await caches.open(CACHE);
    const hit = await c.match(req, { ignoreSearch: true });
    if (hit) {
      fetch(req).then((r) => { if (r && r.ok) c.put(req, r.clone()); }).catch(() => {});
      return hit;
    }
    try {
      const fresh = await fetch(req);
      if (fresh && fresh.ok) c.put(req, fresh.clone());
      return fresh;
    } catch (err) {
      return new Response("", { status: 504, statusText: "Offline and not cached" });
    }
  })());
});
