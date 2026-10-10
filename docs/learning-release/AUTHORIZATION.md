# Package and independent review contract

All JSON is UTF-8, disallows duplicate keys and non-finite numbers, and is bounded. Module JSON preserves the exact shared-foundation schema v1 (`module.template.json`, draft validator vendored with provenance). A release does not change draft schema approval status into a claim of clinical approval.

## ZIP

Only `manifest.json` and one to 64 `modules/SLUG.json` files. Exact membership is mandatory, no unlisted file, directories, symlink/nonregular entry, duplicate/case-colliding name, Unicode path, absolute/traversal/backslash path or encryption. ZIP maximum 8 MiB; total expanded maximum 4 MiB; each member maximum 512 KiB; expansion ratio at most 100. No archive paths are extracted to disk.

`manifest.json` exact keys:

```json
{"schema_version":1,"files":[{"path":"modules/topic.json","sha256":"EXACT_LOWERCASE_SHA256"}]}
```

Module identities are unique per module/version/language. Lists/text are bounded to UI limits. Stable IDs/version/quiz/options/source references/type allowlists use the shared schema; unknown keys reject. Sources may use plain bibliographic references; linked URLs must use HTTPS, no user/password/query/fragment/port, and the UI source host allowlist: `www.who.int`, `interagencystandingcommittee.org`, `www.mhpssmsp.org`, `spherestandards.org`, `campus.paho.org`, `whoacademy.org`. Host acceptance never asserts that the source or clinical claim is correct. New source hosts require an institution-reviewed policy change.

## Receipt

Exact top-level keys:

```json
{
  "schema_version": 1,
  "mode": "PRODUCTION",
  "release_id": "topic-release-1",
  "package_sha256": "EXACT_ZIP_SHA256",
  "manifest_sha256": "EXACT_MANIFEST_BYTES_SHA256",
  "locale_profile": "bilingual-production",
  "modules": [
    {"module_id":"topic","content_version":"1.0.0","language":"en","sha256":"EXACT_MODULE_BYTES_SHA256"},
    {"module_id":"topic","content_version":"1.0.0","language":"ne","sha256":"EXACT_MODULE_BYTES_SHA256"}
  ],
  "attestations": ["clinical-safety-reviewed", "source-and-rights-reviewed"],
  "signatures": [{"key_id":"INSTITUTION_REGISTERED_KEY","signature_base64":"DETACHED_SIGNATURE"}]
}
```

This is a format illustration; placeholder hashes/signatures do not pass. Release ID must match `[a-z][a-z0-9-]{0,63}`. `en-only-trial` authorizes only English packages; `bilingual-production` requires English and Nepali for each module/version, and Nepali must name the exact English translation source version. No machine-generated translation is required or produced.

Signers attest to **the whole receipt**: canonical JSON with `signatures: []`, sorted keys, compact comma/colon separators, UTF-8 unescaped Unicode and one trailing LF. `canonical()` in `release.py` defines exact bytes. Verify using OpenSSL `pkeyutl -verify -pubin -rawin`; use compatible institution-generated signing keys such as Ed25519. Store private keys in the institutional vault/HSM; signing itself is outside this importer.

## Public-key registry

```json
{
  "schema_version":1,
  "trust_status":"institution-configured",
  "locale_profiles":["en-only-trial","bilingual-production"],
  "blocked_module_ids":["pfa","psychological-first-aid"],
  "approvers":[
    {
      "key_id":"INSTITUTION_REGISTERED_KEY",
      "public_key":"PEM PUBLIC KEY FROM INSTITUTION",
      "roles":["clinical-safety","source-rights","language-en","release-owner"],
      "module_ids":["topic"],
      "languages":["en"]
    }
  ]
}
```

Again, no working key is supplied. Registry has at most 32 explicitly scoped approvers; no module/language wildcard. Every module/version/language needs verified signer coverage for `clinical-safety`, `source-rights`, `language-<locale>`, and `release-owner`. Institutions should assign distinct responsible humans and separate keys; the current verifier permits one authorized person to hold several roles and does not impose separation-of-duties counts. Duplicate/untrusted/invalid signatures reject, not silently ignore. Invalid scope or missing roles rejects. Receipt's module list must match input hashes exactly, not a subset.

The registry is the trust root. It must be access-controlled independently of uploaded content; do not let an uploader choose their own registry. The Actions adapter independently pins its exact file SHA in a protected environment variable. The local CLI assumes its operator supplies a trusted registry path. There is no key-expiry/revocation service: removing/restricting an approver and rotating the protected registry pin is required for subsequent releases. Explicit institutional source/rights and clinical review remains a human responsibility.

The shipped roleplay uses `mode: SYNTHETIC` and cannot pass the production adapter. Tests generate ephemeral keys solely to exercise real verification; they are never installed as an institutional trust root.
