"""OFFLINE provider fixtures only; ephemeral test signatures are NOT institutional trust."""
import base64
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/learning-release'))
import release


class BrokerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='broker-fixture-', dir=os.environ['TMPDIR'])
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.remote = self.root / 'remote.json'
        self.state = self.root / 'state'
        site = {'index.html': b'Existing site', 'learn/index.html': b'Learning UI',
                'learn/content/catalogue.json': release.canonical({'schema_version': 1, 'modules': []})}
        self.remote.write_text(json.dumps({'files': {p: base64.b64encode(b).decode() for p, b in site.items()},
                                          'fault': '', 'calls': [], 'prs': [], 'refs': {}, 'commits': {}, 'blobs': {},
                                          'main': 'a' * 40, 'builds': []}))
        self.registry = self.root / 'registry.json'
        self.key = self.root / 'private.pem'
        public = self.root / 'public.pem'
        self.command('openssl', 'genpkey', '-algorithm', 'ED25519', '-out', str(self.key))
        self.command('openssl', 'pkey', '-in', str(self.key), '-pubout', '-out', str(public))
        release.atomic_json(self.registry, {'schema_version': 1, 'trust_status': 'institution-configured',
            'locale_profiles': ['en-only-trial'], 'blocked_module_ids': ['pfa', 'psychological-first-aid'],
            'approvers': [{'key_id': 'OFFLINE-FIXTURE', 'public_key': public.read_text(),
                          'roles': ['clinical-safety', 'source-rights', 'language-en', 'release-owner'],
                          'module_ids': ['synthetic-navigation'], 'languages': ['en']}]})
        self.policy = {'repository': 'fixture/site', 'base_url': 'https://fixture.invalid/',
                       'registry_sha256': release.sha(self.registry.read_bytes()),
                       'stable_assets': ['index.html', 'learn/index.html'], 'allow_rollback': True}

    def command(self, *args):
        return subprocess.run(args, check=True, capture_output=True, timeout=15).stdout

    def package(self, version='1.0.0'):
        module = release.read_json(ROOT / 'tools/learning-release/synthetic.module.json')
        module['content_version'] = version
        raw = release.canonical(module)
        manifest = release.canonical({'schema_version': 1, 'files': [{'path': 'modules/demo.json', 'sha256': release.sha(raw)}]})
        package = self.root / ('package-' + version + '.zip')
        with zipfile.ZipFile(package, 'w') as archive:
            archive.writestr('manifest.json', manifest)
            archive.writestr('modules/demo.json', raw)
        receipt = {'schema_version': 1, 'mode': 'PRODUCTION', 'release_id': 'fixture-' + version.replace('.', '-'),
                   'package_sha256': release.sha(package.read_bytes()), 'manifest_sha256': release.sha(manifest),
                   'locale_profile': 'en-only-trial', 'modules': [{k: module[k] for k in ('module_id', 'content_version', 'language')} | {'sha256': release.sha(raw)}],
                   'attestations': ['clinical-safety-reviewed', 'source-and-rights-reviewed'], 'signatures': []}
        body = self.root / 'body'
        body.write_bytes(release.canonical(receipt))
        signature = self.command('openssl', 'pkeyutl', '-sign', '-rawin', '-inkey', str(self.key), '-in', str(body))
        receipt['signatures'] = [{'key_id': 'OFFLINE-FIXTURE', 'signature_base64': base64.b64encode(signature).decode()}]
        approval = self.root / ('approval-' + version + '.json')
        release.atomic_json(approval, receipt)
        return package, approval

    def data(self):
        return json.loads(self.remote.read_text())

    def fault(self, name):
        data = self.data()
        data['fault'] = name
        self.remote.write_text(json.dumps(data))

    def broker(self):
        self.assertTrue((ROOT / 'tools/learning-release/github_broker.py').exists(), 'functional provider broker missing')
        import github_broker
        def http(url):
            from urllib.parse import urlsplit, unquote
            parsed = urlsplit(url)
            self.assertEqual(parsed.hostname, 'fixture.invalid')
            self.assertIn('learning_readback=', parsed.query)
            data = self.data()
            if data['fault'] == 'readback':
                return b'FIXTURE mismatched deployed bytes'
            if data['fault'] == 'readback-once-with-unrelated-drift':
                data['fault'] = ''
                data['files']['unrelated-new.html'] = base64.b64encode(b'Concurrent unrelated asset').decode()
                data['main'] = 'c' * 40
                self.remote.write_text(json.dumps(data))
                return b'FIXTURE one failed readback'
            return base64.b64decode(data['files'][unquote(parsed.path.lstrip('/'))])
        provider = github_broker.GitHub('fixture/site', gh_command=[sys.executable, str(Path(__file__).with_name('fake_gh.py')), str(self.remote)], http=http)
        return github_broker.Broker(self.state, self.policy, self.registry, provider, max_polls=2, poll_seconds=0)

    def test_one_action_imports_merges_reads_back_then_advances_last_good(self):
        package, approval = self.package()
        result = self.broker().publish(package, approval, execute=True)
        self.assertEqual(result['status'], 'verified')
        self.assertEqual(release.read_json(self.state / 'last-good.json')['release_id'], 'fixture-1-0-0')
        data = self.data()
        self.assertEqual(len(data['prs']), 1)
        self.assertTrue(data['prs'][0]['merged'])
        self.assertEqual(base64.b64decode(data['files']['index.html']), b'Existing site')
        self.assertFalse(any('refs/heads/main' in c and 'POST' in c for c in data['calls']))
        calls = len(data['calls'])
        self.assertEqual(self.broker().publish(package, approval, execute=True)['status'], 'already-verified')
        self.assertFalse(any(c.startswith(('POST ', 'PUT ', 'PATCH ')) for c in self.data()['calls'][calls:]))

    def test_required_checks_fail_without_merge_or_last_good(self):
        self.fault('checks')
        with self.assertRaisesRegex(release.ReleaseError, 'check failed'):
            self.broker().publish(*self.package(), execute=True)
        self.assertFalse(self.data()['prs'][0]['merged'])
        self.assertFalse((self.state / 'last-good.json').exists())

    def test_ambiguous_pr_create_retry_reconciles_without_duplicate_writes(self):
        self.fault('ambiguous-pr')
        package, approval = self.package()
        with self.assertRaisesRegex(release.ReleaseError, 'ambiguous'):
            self.broker().publish(package, approval, execute=True)
        self.assertEqual(len(self.data()['prs']), 1)
        self.assertEqual(self.broker().publish(package, approval, execute=True)['status'], 'verified')
        calls = self.data()['calls']
        self.assertEqual(calls.count('POST pulls'), 1)
        self.assertEqual(calls.count('POST git/refs'), 1)

    def test_merge_pending_retry_never_replays_merge(self):
        self.fault('merge-pending')
        package, approval = self.package()
        for _ in range(2):
            with self.assertRaisesRegex(release.ReleaseError, 'still pending'):
                self.broker().publish(package, approval, execute=True)
        self.assertEqual(self.data()['calls'].count('PUT pulls/1/merge'), 1)
        self.assertFalse((self.state / 'last-good.json').exists())

    def test_pages_failure_cannot_advance_last_good(self):
        self.fault('pages')
        with self.assertRaisesRegex(release.ReleaseError, 'Pages build failed'):
            self.broker().publish(*self.package(), execute=True)
        self.assertTrue(self.data()['prs'][0]['merged'])
        self.assertFalse((self.state / 'last-good.json').exists())
        self.assertTrue((self.state / 'pending.json').exists())

    def test_mismatched_readback_cannot_advance_last_good(self):
        self.fault('readback')
        with self.assertRaisesRegex(release.ReleaseError, 'bytes mismatch'):
            self.broker().publish(*self.package(), execute=True)
        self.assertFalse((self.state / 'last-good.json').exists())

    def test_drifted_base_never_creates_or_merges_pr(self):
        self.fault('drift')
        with self.assertRaisesRegex(release.ReleaseError, 'base drift'):
            self.broker().publish(*self.package(), execute=True)
        self.assertEqual(self.data()['prs'], [])

    def test_old_release_replay_refused(self):
        first = self.package()
        self.broker().publish(*first, execute=True)
        self.broker().publish(*self.package('1.0.1'), execute=True)
        calls = len(self.data()['calls'])
        with self.assertRaisesRegex(release.ReleaseError, 'old release replay'):
            self.broker().publish(*first, execute=True)
        self.assertFalse(any(c.startswith(('POST ', 'PUT ')) for c in self.data()['calls'][calls:]))

    def test_invalid_registry_or_receipt_cannot_self_approve(self):
        self.policy['registry_sha256'] = '0' * 64
        with self.assertRaisesRegex(release.ReleaseError, 'independent institutional pin'):
            self.broker()
        self.policy['registry_sha256'] = release.sha(self.registry.read_bytes())
        package, approval = self.package()
        receipt = release.read_json(approval)
        receipt['signatures'] = []
        release.atomic_json(approval, receipt)
        with self.assertRaisesRegex(release.ReleaseError, 'signatures'):
            self.broker().publish(package, approval, execute=True)
        self.assertEqual(self.data()['calls'], [])

    def test_no_execute_flag_has_zero_remote_calls(self):
        with self.assertRaisesRegex(release.ReleaseError, 'deliberate'):
            self.broker().publish(*self.package())
        self.assertEqual(self.data()['calls'], [])

    def test_failed_new_release_rolls_back_prior_content_via_protected_pr(self):
        self.broker().publish(*self.package(), execute=True)
        prior = release.read_json(self.state / 'last-good.json')
        self.fault('pages-once')
        second = self.package('1.0.1')
        with self.assertRaisesRegex(release.ReleaseError, 'Pages build failed'):
            self.broker().publish(*second, execute=True)
        data = self.data()
        self.assertEqual(len(data['prs']), 3)
        self.assertTrue(all(p['merged'] for p in data['prs']))
        self.assertEqual(base64.b64decode(data['files']['index.html']), b'Existing site')
        self.assertEqual(base64.b64decode(data['files']['learning-release.json']), base64.b64decode(prior['content']['learning-release.json']))
        self.assertFalse(any('/1.0.1/' in p for p in data['files']), 'rollback removes only failed release additions')
        self.assertEqual(release.read_json(self.state / 'last-good.json')['release_id'], prior['release_id'])
        record = release.read_json(self.state / 'rollback-records/fixture-1-0-1.json')
        self.assertEqual(record['status'], 'rolled-back-verified')
        calls = len(data['calls'])
        with self.assertRaisesRegex(release.ReleaseError, 'old release replay'):
            self.broker().publish(*second, execute=True)
        self.assertFalse(any(c.startswith(('POST ', 'PUT ')) for c in self.data()['calls'][calls:]))

    def test_rollback_without_authority_only_retains_pending_evidence(self):
        self.policy['allow_rollback'] = False
        self.broker().publish(*self.package(), execute=True)
        old = (self.state / 'last-good.json').read_bytes()
        self.fault('pages')
        with self.assertRaisesRegex(release.ReleaseError, 'Pages build failed'):
            self.broker().publish(*self.package('1.0.1'), execute=True)
        self.assertEqual((self.state / 'last-good.json').read_bytes(), old)
        self.assertEqual(len(self.data()['prs']), 2)
        self.assertTrue((self.state / 'pending.json').exists())

    def test_changed_remote_manifest_retry_fails_closed(self):
        self.fault('ambiguous-pr')
        package, approval = self.package()
        with self.assertRaises(release.ReleaseError):
            self.broker().publish(package, approval, execute=True)
        data = self.data()
        data['prs'][0]['body'] = 'untrusted replacement approval'
        self.remote.write_text(json.dumps(data))
        with self.assertRaisesRegex(release.ReleaseError, 'identity/approved manifest'):
            self.broker().publish(package, approval, execute=True)
        self.assertFalse(self.data()['prs'][0]['merged'])

    def test_unknown_pr_effect_is_not_blindly_replayed(self):
        self.fault('ambiguous-pr')
        package, approval = self.package()
        with self.assertRaises(release.ReleaseError):
            self.broker().publish(package, approval, execute=True)
        data = self.data()
        data['prs'] = []  # provider cannot positively reconcile effect
        self.remote.write_text(json.dumps(data))
        with self.assertRaisesRegex(release.ReleaseError, 'no replay'):
            self.broker().publish(package, approval, execute=True)
        self.assertEqual(self.data()['calls'].count('POST pulls'), 1)

    def test_unknown_commit_effect_is_not_replayed(self):
        self.fault('ambiguous-commit')
        package, approval = self.package()
        with self.assertRaises(release.ReleaseError):
            self.broker().publish(package, approval, execute=True)
        with self.assertRaisesRegex(release.ReleaseError, 'unknown immutable commit'):
            self.broker().publish(package, approval, execute=True)
        self.assertEqual(self.data()['calls'].count('POST git/commits'), 1)
        self.assertEqual(self.data()['prs'], [])

    def test_extra_remote_content_or_parent_drift_rejected(self):
        self.fault('ambiguous-pr')
        package, approval = self.package()
        with self.assertRaises(release.ReleaseError):
            self.broker().publish(package, approval, execute=True)
        data = self.data()
        head = data['prs'][0]['head']['sha']
        data['commits'][head]['parents'] = [{'sha': 'e' * 40}]
        self.remote.write_text(json.dumps(data))
        with self.assertRaisesRegex(release.ReleaseError, 'parent'):
            self.broker().publish(package, approval, execute=True)
        self.assertFalse(self.data()['prs'][0]['merged'])

    def test_https_redirect_policy_refuses_off_origin(self):
        import github_broker
        from urllib.request import Request
        with self.assertRaisesRegex(release.ReleaseError, 'redirect refused'):
            github_broker.NoRedirect().redirect_request(Request('https://fixture.invalid/a'), None, 302, 'redirect', {}, 'https://evil.invalid/a')

    def test_provider_workflow_is_separate_environment_gated_no_pr_write_trigger(self):
        workflow = ROOT / '.github/workflows/learning-publish.yml'
        self.assertTrue(workflow.exists(), 'explicit protected broker workflow missing')
        text = workflow.read_text()
        self.assertIn('workflow_dispatch:', text)
        self.assertIn('environment: learning-release-authorization', text)
        self.assertIn('contents: write', text)
        self.assertIn('pull-requests: write', text)
        self.assertIn('LEARNING_BROKER_TOKEN', text)
        self.assertNotIn('pull_request:', text)
        self.assertNotIn('pull_request_target:', text)

    def test_readback_retry_then_authorized_rollback_preserves_unrelated_concurrent_asset(self):
        self.broker().publish(*self.package(), execute=True)
        self.fault('readback-once-with-unrelated-drift')
        with self.assertRaisesRegex(release.ReleaseError, 'bytes mismatch'):
            self.broker().publish(*self.package('1.0.1'), execute=True)
        data = self.data()
        self.assertEqual(base64.b64decode(data['files']['unrelated-new.html']), b'Concurrent unrelated asset')
        self.assertEqual(release.read_json(self.state / 'rollback-records/fixture-1-0-1.json')['status'], 'rolled-back-verified')

    def test_rollback_resumption_revalidates_prior_manifest_against_its_receipt(self):
        self.broker().publish(*self.package(), execute=True)
        self.fault('pages-once-rollback-merge-pending')
        package, approval = self.package('1.0.1')
        with self.assertRaises(release.ReleaseError):
            self.broker().publish(package, approval, execute=True)
        pending = release.read_json(self.state / 'pending.json')
        self.assertEqual(pending['kind'], 'rollback')
        pending['prior']['content']['learning-release.json'] = base64.b64encode(b'FORGED prior').decode()
        release.atomic_json(self.state / 'pending.json', pending)
        calls = len(self.data()['calls'])
        with self.assertRaisesRegex(release.ReleaseError, 'prior manifest'):
            self.broker().publish(package, approval, execute=True)
        self.assertFalse(any(c.startswith(('POST ', 'PUT ')) for c in self.data()['calls'][calls:]))

    def test_dispatch_binds_trust_policy_and_explicit_consent(self):
        import publish_dispatch
        from unittest.mock import patch
        with patch.dict(os.environ, {'GITHUB_REF': 'refs/heads/main', 'LEARNING_EXECUTE_DEPLOYMENT': 'false'}):
            with self.assertRaisesRegex(release.ReleaseError, 'explicit deployment consent'):
                publish_dispatch.main()

    def test_main_drift_during_readback_does_not_advance_last_good(self):
        broker = self.broker()
        original_http = broker.gh.http
        def http(url):
            raw = original_http(url)
            data = self.data()
            data['main'] = 'f' * 40
            self.remote.write_text(json.dumps(data))
            return raw
        broker.gh.http = http
        with self.assertRaisesRegex(release.ReleaseError, 'during readback'):
            broker.publish(*self.package(), execute=True)
        self.assertFalse((self.state / 'last-good.json').exists())

    def test_cli_one_action_exercises_real_importer_and_fake_provider(self):
        # CLI uses real default gh argv. Only the offline executable and HTTPS transport
        # are replaced in a private child interpreter; no production trust defaults.
        package, approval = self.package()
        policy = self.root / 'provider-policy.json'
        release.atomic_json(policy, self.policy)
        binary = self.root / 'bin'
        binary.mkdir()
        shim = binary / 'gh'
        shim.write_text('#!' + sys.executable + '\nimport os, runpy, sys\nsys.argv = [os.environ["FIXTURE_GH_SCRIPT"], os.environ["FIXTURE_GH_STATE"], *sys.argv[1:]]\nrunpy.run_path(sys.argv[0], run_name="__main__")\n')
        shim.chmod(0o700)
        driver = self.root / 'offline-cli.py'
        driver.write_text('import base64, json, os, runpy, sys\nfrom pathlib import Path\nfrom urllib.parse import urlsplit, unquote\nsys.path.insert(0, os.environ["FIXTURE_TOOL_DIR"])\nimport github_broker\ndef http(self, url):\n p=urlsplit(url)\n assert p.scheme == "https" and p.hostname == "fixture.invalid" and "learning_readback=" in p.query\n d=json.loads(Path(os.environ["FIXTURE_GH_STATE"]).read_text())\n return base64.b64decode(d["files"][unquote(p.path.lstrip("/"))])\ngithub_broker.GitHub.https=http\nsys.argv = [os.environ["FIXTURE_RELEASE"], *sys.argv[1:]]\nrunpy.run_path(sys.argv[0], run_name="__main__")\n')
        env = os.environ | {'PATH': str(binary) + os.pathsep + os.environ['PATH'],
            'FIXTURE_GH_STATE': str(self.remote), 'FIXTURE_GH_SCRIPT': str(Path(__file__).with_name('fake_gh.py')),
            'FIXTURE_TOOL_DIR': str(ROOT / 'tools/learning-release'), 'FIXTURE_RELEASE': str(ROOT / 'tools/learning-release/release.py')}
        command = [sys.executable, str(driver), 'publish-github', '--package', str(package), '--approval', str(approval),
                   '--registry', str(self.registry), '--policy', str(policy), '--state', str(self.state), '--execute-deployment']
        result = subprocess.run(command, env=env, capture_output=True, text=True, timeout=90)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['status'], 'verified')
        self.assertEqual(len(self.data()['prs']), 1)

    def test_unknown_postmerge_provider_effect_does_not_trigger_rollback(self):
        self.broker().publish(*self.package(), execute=True)
        self.fault('ambiguous-pages')
        package, approval = self.package('1.0.1')
        with self.assertRaisesRegex(release.ReleaseError, 'ambiguous'):
            self.broker().publish(package, approval, execute=True)
        self.assertEqual(len(self.data()['prs']), 2, 'unknown Pages response cannot authorize a new rollback write')
        self.assertEqual(release.read_json(self.state / 'last-good.json')['release_id'], 'fixture-1-0-0')
        self.assertEqual(self.broker().publish(package, approval, execute=True)['status'], 'verified')
        self.assertEqual(self.data()['calls'].count('POST pages/builds'), 2)

    def test_unreconciled_pages_effect_never_replays_or_rolls_back(self):
        self.broker().publish(*self.package(), execute=True)
        self.fault('ambiguous-pages')
        package, approval = self.package('1.0.1')
        with self.assertRaises(release.ReleaseError):
            self.broker().publish(package, approval, execute=True)
        data = self.data()
        data['builds'] = []
        self.remote.write_text(json.dumps(data))
        with self.assertRaisesRegex(release.ReleaseError, 'effect unknown'):
            self.broker().publish(package, approval, execute=True)
        self.assertEqual(len(self.data()['prs']), 2)
        self.assertEqual(self.data()['calls'].count('POST pages/builds'), 2)

    def test_intent_json_flushes_file_and_directory_before_side_effect(self):
        from unittest.mock import patch
        original = os.fsync
        with patch.object(os, 'fsync', wraps=original) as flush:
            release.atomic_json(self.root / 'durable-intent.json', {'pending': True})
        self.assertEqual(flush.call_count, 2, 'file and rename directory require fsync')

    def test_cli_exposes_single_explicit_operator_entry(self):
        result = subprocess.run([sys.executable, str(ROOT / 'tools/learning-release/release.py'), '--help'], capture_output=True, text=True)
        self.assertIn('publish-github', result.stdout)
        self.assertIn('--execute-deployment', result.stdout)


if __name__ == '__main__':
    unittest.main(verbosity=2)
