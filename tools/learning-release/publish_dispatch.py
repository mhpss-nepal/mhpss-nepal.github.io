#!/usr/bin/env python3
"""Single commissioned workflow action; dispatch carries only package identity and consent."""
import os
from pathlib import Path
import re
import sys

from github_broker import Broker
from release import read_json, require, sha, no_symlink_path, disjoint_paths


def main():
    root = Path(__file__).resolve().parents[2]
    require(os.environ.get('GITHUB_REF') == 'refs/heads/main', 'broker runs trusted main only')
    require(os.environ.get('LEARNING_EXECUTE_DEPLOYMENT') == 'true', 'explicit deployment consent required')
    name = os.environ.get('LEARNING_PACKAGE', '')
    expected = os.environ.get('LEARNING_PACKAGE_SHA256', '')
    require(bool(re.fullmatch(r'[a-z][a-z0-9-]{0,63}', name)), 'invalid package identity')
    require(bool(re.fullmatch(r'[a-f0-9]{64}', expected)), 'exact package hash required')
    policy_path = root / 'docs/learning-release/provider-policy.json'
    policy_pin = os.environ.get('LEARNING_PROVIDER_POLICY_SHA256', '')
    require(bool(re.fullmatch(r'[a-f0-9]{64}', policy_pin)) and sha(policy_path.read_bytes()) == policy_pin,
            'provider policy differs from independently protected pin')
    policy = read_json(policy_path)
    require(policy['repository'] == os.environ['GITHUB_REPOSITORY'], 'repository policy mismatch')
    require(policy['registry_sha256'] == os.environ.get('LEARNING_REGISTRY_SHA256'), 'registry pin mismatch')
    registry = root / 'docs/learning-release/institution-registry.json'
    approved = root / 'docs/learning-release/approved-packages'
    package = approved / (name + '.zip')
    approval = approved / (name + '.approval.json')
    require(sha(package.read_bytes()) == expected, 'dispatch package hash mismatch')
    state = Path(os.environ['LEARNING_BROKER_STATE_ROOT'])
    require(state.is_absolute(), 'persistent private broker state must be absolute and disjoint from checkout')
    state = no_symlink_path(state)
    for boundary in (root, approved, package, approval, registry):
        disjoint_paths(state, boundary)
    require(bool(os.environ.get('GH_TOKEN')), 'commissioned provider credential unavailable')
    result = Broker(state, policy, registry).publish(package, approval, execute=True)
    print('PROVIDER RESULT: ' + result['status'] + '; release=' + result['release_id'])


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print('REJECTED / MANUAL ATTENTION IF PENDING: ' + str(exc), file=sys.stderr)
        sys.exit(1)
