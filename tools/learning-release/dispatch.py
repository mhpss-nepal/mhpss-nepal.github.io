#!/usr/bin/env python3
"""Read-only adapter: signed content-review receipt -> deterministic candidate/patch."""
import os
from pathlib import Path
import re
import sys

from release import github_artifacts, prepare, require, sha


def main():
    root = Path(__file__).resolve().parents[2]
    package_name = os.environ.get('LEARNING_PACKAGE', '')
    expected = os.environ.get('LEARNING_PACKAGE_SHA256', '')
    require(bool(re.fullmatch(r'[a-z][a-z0-9-]{0,63}', package_name)), 'invalid reviewed package name')
    require(bool(re.fullmatch(r'[a-f0-9]{64}', expected)), 'exact package SHA-256 required')
    approved = root / 'docs/learning-release/approved-packages'
    package = approved / (package_name + '.zip')
    receipt = approved / (package_name + '.approval.json')
    registry = root / 'docs/learning-release/institution-registry.json'
    # Out-of-band variable managed by institution, NOT attacker-provided dispatch data.
    trust_hash = os.environ.get('LEARNING_REGISTRY_SHA256', '')
    require(bool(re.fullmatch(r'[a-f0-9]{64}', trust_hash)), 'institution has not pinned a trust registry')
    require(sha(registry.read_bytes()) == trust_hash, 'registry does not match protected institutional trust pin')
    require(sha(package.read_bytes()) == expected, 'package does not match dispatch hash')
    # Deliberately fails if no independent signer registry or owner/content signatures.
    output = Path(os.environ['RUNNER_TEMP']) / 'learning-release-output'
    output.mkdir(mode=0o700)
    candidate = output / 'candidate'
    prepare(package, receipt, root, candidate, synthetic=False, registry=registry)
    github_artifacts(root, candidate, output / 'github-adapter', os.environ['GITHUB_REPOSITORY'],
                     os.environ.get('LEARNING_READBACK_BASE_URL', ''))
    print('PREPARED ONLY: signed reproducible candidate + protected PR patch; no remote writes or hosting changes.')


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print('REJECTED: ' + str(exc), file=sys.stderr)
        sys.exit(1)
