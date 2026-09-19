# Deployment gate

This branch is a build and repository foundation only. It is not approved for deployment.

The authoritative Firestore rules are not yet versioned or verified in this monorepo. Their effective server-side authorization remains unverified, and the Firebase client configuration is not an authorization control.

This monorepo branch **must not be deployed** until the institution-owned rules in the authoritative environment have been:

1. exported into an institution-controlled review artifact without accessing or copying production data;
2. reviewed for least-privilege access and removal of personal exceptions;
3. emulator-tested with allow and deny cases;
4. coordinated with the institutional owner and the application rollout; and
5. versioned through the normal reviewed pull-request process.

Until those steps have evidence and approval, Firestore authorization remains an explicit merge/deploy blocker. This branch must not fabricate replacement rules or claim production authorization has been remediated.
