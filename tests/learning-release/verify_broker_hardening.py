#!/usr/bin/env python3
"""Offline verification; preserves original review assertions and raw outcomes."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / 'tests/learning-release/evidence/broker-hardening'
REVIEW = ROOT.parent / 'broker-independent-review'
SCOPES = ('tools/learning-release', 'tests/learning-release', 'docs/learning-release', '.github/workflows')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def manifest():
    return [{'path': p.relative_to(ROOT).as_posix(), 'sha256': digest(p), 'size': p.stat().st_size}
            for scope in SCOPES for p in sorted((ROOT / scope).rglob('*'))
            if p.is_file() and '__pycache__' not in p.parts and 'evidence' not in p.parts]


def main():
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    before = manifest()
    baseline = json.loads((REVIEW / 'manifest-before.json').read_text())
    current = {e['path']: e for e in before}
    preserved = [e['path'] for e in baseline if current[e['path']]['sha256'] == e['sha256']]
    assert all(p in preserved for p in ('tests/learning-release/test_release.py', 'tests/learning-release/test_github_broker.py', 'tests/learning-release/fake_gh.py'))
    target = EVIDENCE / 'original-adversarial'
    target.mkdir(exist_ok=True)
    runner = target / 'adversarial_probes.py'
    shutil.copyfile(REVIEW / 'adversarial_probes.py', runner)
    assert digest(runner) == digest(REVIEW / 'adversarial_probes.py')
    for entry in before:
        source = ROOT / entry['path']
        dest = target / 'source-snapshot' / entry['path']
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, dest)
    env = os.environ | {'PYTHONDONTWRITEBYTECODE': '1'}
    runs = []
    commands = [
        ('full-existing-plus-regressions-final', [sys.executable, '-m', 'unittest', 'discover', '-s', 'tests/learning-release', '-p', 'test_*.py', '-v']),
        ('validator-final', [sys.executable, 'tools/learning-release/validate_content.py', '--self-test']),
        ('original-adversarial-final', [sys.executable, str(runner)]),
    ]
    for name, command in commands:
        result = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True, timeout=420)
        log = result.stdout + result.stderr
        path = EVIDENCE / (name + '.log')
        path.write_text(log)
        entry = {'name': name, 'command': command, 'exit_code': result.returncode,
                 'log': path.relative_to(ROOT).as_posix(), 'log_sha256': digest(path)}
        counts = re.search(r'Ran (\d+) tests', log)
        if counts:
            entry['tests_run'] = int(counts[1])
        runs.append(entry)
        print(json.dumps(entry), flush=True)
    assert before == manifest(), 'scoped source changed while verifying'
    adversarial = json.loads((target / 'adversarial-results.json').read_text())
    assert adversarial['probe_count'] == len(adversarial['results']) == 15
    assert adversarial['pass_count'] == sum(r['passed'] for r in adversarial['results'])
    outcome = {'runs': runs, 'original_adversarial_verdict': adversarial,
               'original_runner_sha256': digest(runner), 'original_files_preserved': preserved,
               'source_preserved_during_verification': True, 'candidate_files': before,
               'test_files': sorted(p.relative_to(ROOT).as_posix() for p in (ROOT / 'tests/learning-release').glob('test_*.py')),
               'limitations': ['Original runner records expected symlink and registry-pin ReleaseError rejections as harness errors; raw verdict is not green.',
                               'No real provider operations, credentials, Luna or content modifications; independent rereview remains required.']}
    (EVIDENCE / 'FINAL-MANIFEST.json').write_text(json.dumps(before, indent=2) + '\n')
    (EVIDENCE / 'FINAL-RESULTS.json').write_text(json.dumps(outcome, indent=2) + '\n')
    assert runs[0]['exit_code'] == runs[1]['exit_code'] == 0
    assert adversarial['pass_count'] == 13 and adversarial['fail_count'] == 2
    expected = {'state_symlink_is_rejected_before_resolve': 'symlink refused',
                'registry_pin_is_rechecked_when_publish_executes': 'independent institutional pin'}
    failures = [r for r in adversarial['results'] if not r['passed']]
    assert {r['name'] for r in failures} == set(expected)
    assert all(expected[r['name']] in r.get('harness_error', '') for r in failures)
    print('Verified exact source preservation, green unittest/validator, and raw unchanged runner 13 pass / 2 expected rejection harness failures.')


if __name__ == '__main__':
    main()
