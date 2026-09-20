#!/usr/bin/env python3
"""Runtime proof that restricted form records cannot enter public_stats.

Runs the real fb.js publication boundary in Node with a stubbed Firebase API.
Synthetic payloads only; no network access.
"""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FB_PATH = ROOT / "apps" / "hub" / "assets" / "fb.js"

NODE_HARNESS = r"""
const fs = require("fs");
const vm = require("vm");
function stubEl() { return {className:"",innerHTML:"",textContent:"",appendChild(){},insertBefore(){},parentNode:null}; }
const writes = [];
const api = {
  doc(_db, collection, id) { return {collection, id}; },
  setDoc(ref, body) { writes.push({ref, body}); return Promise.resolve(); },
  serverTimestamp() { return "SERVER_TIME"; },
  getDoc() { return Promise.resolve({exists(){return false;}}); },
  collection(){return {};}, query(){return {};}, where(){return {};}, orderBy(){return {};},
  limit(){return {};}, onSnapshot(){return function(){};}, getDocs(){return Promise.resolve({forEach(){}});},
  deleteDoc(){return Promise.resolve();}, signIn(){return Promise.resolve();}, signOut(){return Promise.resolve();},
  onAuth(_auth, cb){cb({email:"reviewer@example.invalid",uid:"u1"});},
  sendLink(){return Promise.resolve();}, isLink(){return false;}, signInLink(){return Promise.resolve();}
};
const localStorage = {getItem(){return null;},setItem(){},removeItem(){}};
const document = {title:"test",readyState:"complete",head:stubEl(),body:Object.assign(stubEl(),{firstElementChild:null}),createElement(){return stubEl();},getElementById(){return null;},addEventListener(){}};
const window = {FB_CONFIG:{projectId:"test",apiKey:"test"},FB_COLLECTION:"submissions",addEventListener(){},location:{href:"http://test/hub",origin:"http://test",pathname:"/hub",search:""},history:{replaceState(){}},prompt(){return "";}};
const context = {window,document,localStorage,navigator:{onLine:false},console,Promise,Date,JSON,setTimeout,clearTimeout,CustomEvent:function(){}};
window.window=window; window.document=document; window.localStorage=localStorage;
context.importModuleDynamically = async function(specifier) {
  if (specifier.endsWith("firebase-app.js")) return {initializeApp(){return {};}};
  if (specifier.endsWith("firebase-firestore.js")) return {getFirestore(){return {};},...api};
  return {getAuth(){return {};},signInWithEmailAndPassword:api.signIn,signOut:api.signOut,onAuthStateChanged:api.onAuth,sendSignInLinkToEmail:api.sendLink,isSignInWithEmailLink:api.isLink,signInWithEmailLink:api.signInLink};
};
(async () => {
  const script = new vm.Script(fs.readFileSync(process.argv[1],"utf8"), {filename:"fb.js", importModuleDynamically:context.importModuleDynamically});
  script.runInContext(vm.createContext(context));
  await new Promise(resolve => setTimeout(resolve, 100));
  const body = JSON.parse(process.argv[2]);
  let error = "";
  try { await window.FB.publish("synthetic", body); } catch (e) { error = e.message; }
  process.stdout.write(JSON.stringify({error,writes}));
})().catch(e => { console.error(e); process.exit(1); });
"""


def publish(body: dict[str, object]) -> dict[str, object]:
    completed = subprocess.run(
        ["node", "--experimental-vm-modules", "-e", NODE_HARNESS, str(FB_PATH), json.dumps(body)],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(completed.stdout)


class PublicationPrivacyGateTests(unittest.TestCase):
    def test_referral_reconciliation_and_restricted_records_cannot_publish(self) -> None:
        for body in (
            {"basis": "synthetic", "privacy_class": "restricted-referral-person-list", "counts": {"raw": 2}},
            {"basis": "synthetic", "analysis": {"privacy_class": "restricted-referral-person-list"}},
            {"basis": "synthetic", "kind": "referral", "contact_code": "NP-ABCDE-12345"},
            {"basis": "synthetic", "kind": "phq9", "total": 9},
        ):
            with self.subTest(body=body):
                result = publish(body)
                self.assertEqual(result["writes"], [])
                self.assertIn("restricted", result["error"])

if __name__ == "__main__":
    unittest.main()
