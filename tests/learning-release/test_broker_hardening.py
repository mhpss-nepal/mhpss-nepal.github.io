"""Regression contracts for independent B1-B4/W1-W2, offline only."""
import base64
import json
import unittest
from pathlib import Path
import test_github_broker as fixtures
import release
import github_broker


class HardeningTests(unittest.TestCase):
    setUp = fixtures.BrokerTests.setUp
    command = fixtures.BrokerTests.command
    package = fixtures.BrokerTests.package
    data = fixtures.BrokerTests.data
    fault = fixtures.BrokerTests.fault
    broker = fixtures.BrokerTests.broker

    def writes(self):
        return [c for c in self.data()['calls'] if c.startswith(('POST ', 'PUT ', 'PATCH '))]

    def test_B1_resume_reconstructs_signed_content_not_self_hash(self):
        args = self.package()
        broker = self.broker()
        pending = broker.prepare_intent(*args)
        path = next(p for p in pending['content'] if '/modules/' in p)
        forged = release.canonical(dict(json.loads(base64.b64decode(pending['content'][path])), title='UNSIGNED'))
        pending['changes'][path] = pending['content'][path] = base64.b64encode(forged).decode()
        pending['readback'][path] = release.sha(forged)
        pending['approved_manifest_sha256'] = release.sha(release.canonical(pending['content']))
        broker.save(pending)
        result = self.broker().publish(*args, execute=True)
        self.assertEqual(result['status'], 'verified')
        self.assertEqual(release.sha(base64.b64decode(self.data()['files'][path])), release.read_json(args[1])['modules'][0]['sha256'])

    def test_B1_unknown_pending_kind_cannot_bypass_reconstruction(self):
        args = self.package()
        broker = self.broker()
        pending = broker.prepare_intent(*args)
        pending['kind'] = 'unsigned'
        pending['changes']['learning-release.json'] = base64.b64encode(b'UNSIGNED').decode()
        broker.save(pending)
        with self.assertRaises(release.ReleaseError):
            broker.publish(*args, execute=True)
        self.assertEqual(self.writes(), [])

    def test_B1_history_retry_reconstructs_readback_not_self_hash(self):
        args = self.package()
        result = self.broker().publish(*args, execute=True)
        history_path = self.state / 'history' / (result['release_id'] + '.json')
        saved = release.read_json(history_path)
        saved['readback'] = {}
        release.atomic_json(history_path, saved)
        broker = self.broker()
        broker.gh.http = lambda url: b'not approved deployed bytes'
        with self.assertRaisesRegex(release.ReleaseError, 'bytes mismatch'):
            broker.publish(*args, execute=True)

    def test_B2_rollback_uses_verified_remote_catalogue_not_saved_hash(self):
        self.broker().publish(*self.package(), execute=True)
        prior = release.read_json(self.state / 'last-good.json')
        original = prior['content']['learn/content/catalogue.json']
        prior['content']['learn/content/catalogue.json'] = base64.b64encode(b'{"malicious":true}\n').decode()
        prior['approved_manifest_sha256'] = release.sha(release.canonical(prior['content']))
        release.atomic_json(self.state / 'last-good.json', prior)
        self.fault('pages-once')
        with self.assertRaises(release.ReleaseError):
            self.broker().publish(*self.package('1.0.1'), execute=True)
        self.assertEqual(self.data()['files']['learn/content/catalogue.json'], original)
        self.assertEqual(release.read_json(self.state / 'rollback-records/fixture-1-0-1.json')['status'], 'rolled-back-verified')

    def test_B3_large_retained_content_restart_and_rollback(self):
        old = release.read_json(fixtures.ROOT / 'tools/learning-release/synthetic.module.json')
        old['content_version'] = '0.9.0'
        old['lessons'][0]['blocks'] = [dict(old['lessons'][0]['blocks'][0], body='Navigation fixture long text. ' * 1200) for _ in range(13)]
        entries = []
        data = self.data()
        for module_id in ('synthetic-navigation', 'another-navigation'):
            module = dict(old, module_id=module_id)
            raw = release.canonical(module)
            self.assertLess(len(raw), 512 * 1024)
            self.assertFalse(release.validator.validate(module))
            path = 'modules/' + module_id + '/0.9.0/en.json'
            data['files']['learn/content/' + path] = base64.b64encode(raw).decode()
            entries.append({k: module[k] for k in ('module_id', 'content_version', 'language')} | {'path': path, 'sha256': release.sha(raw)})
        data['files']['learn/content/catalogue.json'] = base64.b64encode(release.canonical({'schema_version': 1, 'modules': entries})).decode()
        self.remote.write_text(json.dumps(data))
        args = self.package()
        self.broker().publish(*args, execute=True)
        self.assertEqual(self.broker().publish(*args, execute=True)['status'], 'already-verified')
        self.fault('pages-once-rollback-merge-pending')
        next_args = self.package('1.0.1')
        with self.assertRaises(release.ReleaseError):
            self.broker().publish(*next_args, execute=True)
        self.assertEqual(release.read_json(self.state / 'pending.json')['kind'], 'rollback')
        self.fault('')
        # Fixture supplies a positive reconciliation of the prior merge request.
        data = self.data()
        pr = data['prs'][-1]
        pr.update(merged=True, state='closed', merge_commit_sha=pr['head']['sha'])
        data['main'] = pr['head']['sha']
        tree = data['trees'][data['commits'][data['main']]['tree']['sha']]['tree']
        data['files'] = {e['path']: data['blobs'][e['sha']] for e in tree}
        self.remote.write_text(json.dumps(data))
        self.assertEqual(self.broker().publish(*next_args, execute=True)['status'], 'rolled-back-verified')
        self.assertTrue(all(p.stat().st_size <= 1024 * 1024 for p in self.state.rglob('*.json')))

    def test_B4_registry_replacement_after_constructor_rejects(self):
        args = self.package()
        broker = self.broker()
        registry = release.read_json(self.registry)
        replacement = self.root / 'replacement.pem'
        public = self.root / 'replacement.pub'
        self.command('openssl', 'genpkey', '-algorithm', 'ED25519', '-out', str(replacement))
        self.command('openssl', 'pkey', '-in', str(replacement), '-pubout', '-out', str(public))
        registry['approvers'][0]['public_key'] = public.read_text()
        release.atomic_json(self.registry, registry)
        receipt = release.read_json(args[1])
        receipt['signatures'] = []
        body = self.root / 'resign-body'
        body.write_bytes(release.canonical(receipt))
        signed = self.command('openssl', 'pkeyutl', '-sign', '-rawin', '-inkey', str(replacement), '-in', str(body))
        receipt['signatures'] = [{'key_id': 'OFFLINE-FIXTURE', 'signature_base64': base64.b64encode(signed).decode()}]
        release.atomic_json(args[1], receipt)
        with self.assertRaises(release.ReleaseError):
            broker.publish(*args, execute=True)
        self.assertEqual(self.data()['calls'], [])

    def test_W1_required_check_honors_app_provenance(self):
        broker = self.broker()
        api = broker.gh.api
        def wrapped(endpoint, method='GET', payload=None, missing=False):
            if endpoint == 'branches/main/protection':
                return {'required_pull_request_reviews': {}, 'enforce_admins': {'enabled': True},
                        'required_status_checks': {'strict': True, 'contexts': ['required'], 'checks': [{'context': 'required', 'app_id': 123}]}}
            if endpoint.endswith('/check-runs?per_page=100'):
                return {'total_count': 1, 'check_runs': [{'name': 'required', 'app': {'id': 999}, 'status': 'completed', 'conclusion': 'success'}]}
            if endpoint.endswith('/status?per_page=100'):
                return {'total_count': 1, 'statuses': [{'context': 'required', 'state': 'success'}]}
            return api(endpoint, method, payload, missing)
        broker.gh.api = wrapped
        self.assertFalse(broker.checks('a' * 40, broker.gates()))

    def test_W2_state_symlink_and_parent_symlink_reject_before_calls(self):
        args = self.package()
        real = self.root / 'real-state'
        real.mkdir()
        self.state.symlink_to(real, target_is_directory=True)
        with self.assertRaisesRegex(release.ReleaseError, 'symlink'):
            self.broker().publish(*args, execute=True)
        self.state.unlink()
        parent = self.root / 'link-parent'
        parent.symlink_to(real, target_is_directory=True)
        self.state = parent / 'child'
        with self.assertRaisesRegex(release.ReleaseError, 'symlink'):
            self.broker().publish(*args, execute=True)
        self.assertEqual(self.data()['calls'], [])

    def test_W2_prepare_rejects_original_source_parent_link(self):
        args = self.package()
        source = self.root / 'source'
        source.mkdir()
        (source / 'learn').mkdir()
        (source / 'learn/index.html').write_bytes(b'UI')
        link = self.root / 'source-link'
        link.symlink_to(source, target_is_directory=True)
        with self.assertRaisesRegex(release.ReleaseError, 'symlink'):
            release.prepare(*args, link, self.root / 'candidate', registry=self.registry)

    def test_W2_state_and_package_boundaries_are_disjoint(self):
        args = self.package()
        self.state = args[0].parent
        with self.assertRaisesRegex(release.ReleaseError, 'disjoint'):
            self.broker().publish(*args, execute=True)
        self.assertEqual(self.data()['calls'], [])

    def test_B3_unreadable_prior_fails_before_new_release_writes(self):
        self.broker().publish(*self.package(), execute=True)
        (self.state / 'last-good.json').write_bytes(b' ' * (1024 * 1024 + 1))
        before = self.writes()
        with self.assertRaisesRegex(release.ReleaseError, 'size limit'):
            self.broker().publish(*self.package('1.0.1'), execute=True)
        self.assertEqual(self.writes(), before)

    def test_B3_unsupported_manifest_fails_before_provider_writes(self):
        args = self.package()
        broker = self.broker()
        original = broker.prepare_intent
        def oversized(*args):
            intent = original(*args)
            intent['readback']['oversized-fixture'] = 'x' * (129 * 1024)
            return intent
        broker.prepare_intent = oversized
        with self.assertRaisesRegex(release.ReleaseError, 'manifest exceeds'):
            broker.publish(*args, execute=True)
        self.assertEqual(self.writes(), [])

    def test_B2_distinct_squash_merge_identity_preserves_prior_authority(self):
        args = self.package()
        broker = self.broker()
        api = broker.gh.api
        def wrapped(endpoint, method='GET', payload=None, missing=False):
            result = api(endpoint, method, payload, missing)
            if endpoint == 'pulls/1/merge' and method == 'PUT':
                data = self.data()
                head = data['main']
                merged = 'b' * 40
                data['commits'][merged] = dict(data['commits'][head], sha=merged)
                data['main'] = merged
                data['prs'][0]['merge_commit_sha'] = merged
                self.remote.write_text(json.dumps(data))
            return result
        broker.gh.api = wrapped
        prior = broker.publish(*args, execute=True)
        self.assertNotEqual(prior['head'], prior['merged'])
        self.fault('pages-once')
        with self.assertRaisesRegex(release.ReleaseError, 'Pages build failed'):
            self.broker().publish(*self.package('1.0.1'), execute=True)
        self.assertEqual(release.read_json(self.state / 'rollback-records/fixture-1-0-1.json')['status'], 'rolled-back-verified')


if __name__ == '__main__':
    unittest.main(verbosity=2)
