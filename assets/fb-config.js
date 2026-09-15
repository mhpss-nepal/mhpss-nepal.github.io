/* =====================================================================
   Firebase configuration — MHPSS Nepal
   ---------------------------------------------------------------------
   PASTE THE CONFIG BLOCK FROM THE FIREBASE CONSOLE BELOW.
   Project settings → General → Your apps → Web app → firebaseConfig.

   This file is public, and that is expected: a Firebase web config is
   not a secret. It identifies the project; it does not grant access.
   Access is decided entirely by the Firestore security rules, which are
   kept in Information Management/firestore_rules_mhpss_nepal_v1.txt and
   published from the console.

   NEVER put a service-account key, a private key, or an API secret in
   this file or anywhere else in this repository.

   While projectId is empty the whole site falls back to local-only
   storage: forms still work and still export, nothing is lost, and the
   pages say plainly that they are not syncing.
   ===================================================================== */
window.FB_CONFIG = {
  apiKey: "",
  authDomain: "",
  projectId: "",
  storageBucket: "",
  messagingSenderId: "",
  appId: ""
};

/* Where records go. One collection, one document per record, keyed by a
   deterministic id — see assets/fb.js for why that matters. */
window.FB_COLLECTION = "submissions";
