/* =====================================================================
   Firebase configuration — MHPSS Nepal
   ---------------------------------------------------------------------
   Project: mhpss-nepal-hub. Written from the Firebase console on
   15 September 2026.

   This file is public, and that is expected: a Firebase web config is
   not a secret. It identifies the project; it does not grant access.
   Authorization must be enforced by authoritative Firestore security Rules.
   Those Rules are external to this monorepo and are not yet versioned or
   verified here, so server enforcement is unverified and this branch must not
   be deployed. See infra/README.md.

   NEVER put a service-account key or any private key in this file.
   ===================================================================== */
window.FB_CONFIG = {
  apiKey: "AIzaSyBa0Z1SPwkP-vwA6-icqmC1gIfI0aLOaI8",
  authDomain: "mhpss-nepal-hub.firebaseapp.com",
  projectId: "mhpss-nepal-hub",
  storageBucket: "mhpss-nepal-hub.firebasestorage.app",
  messagingSenderId: "39288227570",
  appId: "1:39288227570:web:4259bf73ceedbda16e326b"
};

/* One collection, one document per record, keyed by a deterministic id
   so a retried write overwrites itself instead of duplicating. */
window.FB_COLLECTION = "submissions";
