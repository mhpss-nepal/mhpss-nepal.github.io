"""Synthetic-only release acceptance; no clinical content or network."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[2]
TOOL = ROOT / 'tools/learning-release/release.py'
SCRATCH = Path(os.environ.get('TMPDIR', '/root/.hermes/cache/scratch'))


def canonical(x):
    return (json.dumps(x, sort_keys=True, separators=(',', ':'), ensure_ascii=False) + '\n').encode()


def digest(x):
    return hashlib.sha256(x).hexdigest()


def load_tool():
    spec = importlib.util.spec_from_file_location('learning_release', TOOL)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='learning-release-', dir=SCRATCH)
        self.root = Path(self.tmp.name)
        self.site = self.root / 'site'
        self.site.mkdir()
        (self.site / 'index.html').write_text('<!doctype html><title>Existing history</title>')
        (self.site / 'learn').mkdir()
        (self.site / 'learn/index.html').write_text('<!doctype html><title>Learning fixture</title>')
        self.state = self.root / 'state'
        self.target = self.root / 'private-target'
        self.assertTrue(TOOL.exists(), 'release implementation is missing')
        self.mod = load_tool()
        self.data = json.loads((ROOT / 'tools/learning-release/synthetic.module.json').read_text())

    def tearDown(self):
        self.tmp.cleanup()

    def package(self, version='1.0.0', mutate=None, extra=None):
        data = json.loads(json.dumps(self.data))
        data['content_version'] = version
        if mutate:
            mutate(data)
        raw = canonical(data)
        manifest = {'schema_version': 1, 'files': [{'path': 'modules/demo.json', 'sha256': digest(raw)}]}
        manifest_raw = canonical(manifest)
        package = self.root / ('package-' + version + '.zip')
        with zipfile.ZipFile(package, 'w', zipfile.ZIP_DEFLATED) as z:
            z.writestr('manifest.json', manifest_raw)
            z.writestr('modules/demo.json', raw)
            if extra:
                z.writestr(*extra)
        receipt = {'schema_version': 1, 'mode': 'SYNTHETIC', 'release_id': 'demo-' + version.replace('.', '-'),
                   'package_sha256': digest(package.read_bytes()), 'manifest_sha256': digest(manifest_raw),
                   'locale_profile': 'en-only-trial',
                   'modules': [{'module_id': data['module_id'], 'content_version': version,
                                'language': data['language'], 'sha256': digest(raw)}],
                   'attestations': ['clinical-safety-reviewed', 'source-and-rights-reviewed'], 'signatures': []}
        review = self.root / ('receipt-' + version + '.json')
        review.write_bytes(canonical(receipt))
        return package, review

    def release(self, package, receipt, **kw):
        return self.mod.publish(package=package, approval=receipt, site=self.site,
                                state=self.state, target=self.target, synthetic=True, **kw)

    def test_one_operation_private_release_is_reproducible(self):
        package, receipt = self.package()
        original = (self.site / 'index.html').read_bytes()
        result = self.release(package, receipt)
        self.assertEqual(result['status'], 'verified')
        self.assertTrue(result['synthetic'])
        catalogue = json.loads((self.target / 'learn/content/catalogue.json').read_text())
        self.assertEqual(len(catalogue['modules']), 1)
        entry = catalogue['modules'][0]
        installed = self.target / 'learn/content' / entry['path']
        self.assertEqual(digest(installed.read_bytes()), entry['sha256'])
        data = json.loads(installed.read_text())
        self.assertEqual(len(data['lessons']), 1)
        self.assertEqual(len(data['questions']), 1)
        self.assertEqual((self.target / 'index.html').read_bytes(), original)
        self.assertEqual((self.site / 'index.html').read_bytes(), original)
        self.assertFalse((self.site / 'learn/content').exists())
        self.assertEqual(self.release(package, receipt)['status'], 'already-verified')
        self.assertEqual(self.mod.tree_manifest(self.target), result['files'])

    def assert_rejected(self, package, receipt, **kw):
        before = self.mod.tree_manifest(self.site)
        with self.assertRaises((self.mod.ReleaseError, ValueError, KeyError, zipfile.BadZipFile)):
            self.release(package, receipt, **kw)
        self.assertEqual(before, self.mod.tree_manifest(self.site))
        self.assertFalse(self.target.exists())
        self.assertFalse((self.state / 'last-good.json').exists())

    def test_package_gates(self):
        cases = {
            'duplicate lesson': lambda d: d['lessons'].append(d['lessons'][0]),
            'unsupported block': lambda d: d['lessons'][0]['blocks'][0].update(type='iframe'),
            'unknown source': lambda d: d['questions'][0].update(source_ids=['missing']),
            'invalid quiz': lambda d: d['questions'][0].update(correct_option_id='missing'),
            'pfa blocked': lambda d: d.update(module_id='pfa'),
            'credential URL': lambda d: d['sources'][0].update(reference='https://name:secret@example.org/source'),
            'http URL': lambda d: d['sources'][0].update(reference='http://example.org/source'),
            'pending review': lambda d: d.update(open_questions=['Unresolved review']),
        }
        for name, mutate in cases.items():
            with self.subTest(name=name):
                package, receipt = self.package(mutate=mutate)
                self.assert_rejected(package, receipt)
        for name in ('../escape.json', 'MODULES/DEMO.JSON', 'unlisted.json', 'modules/café.json'):
            with self.subTest(path=name):
                package, receipt = self.package(extra=(name, '{}'))
                self.assert_rejected(package, receipt)

    def test_receipt_cannot_self_approve(self):
        for mutation in (
            lambda r: r.update(package_sha256='0' * 64),
            lambda r: r.update(modules=[]),
            lambda r: r.update(locale_profile='bilingual-production'),
            lambda r: r.update(attestations=[]),
            lambda r: r.update(mode='approved'),
        ):
            package, receipt = self.package()
            review = json.loads(receipt.read_text())
            mutation(review)
            receipt.write_bytes(canonical(review))
            self.assert_rejected(package, receipt)
        package, receipt = self.package()
        with self.assertRaises(self.mod.ReleaseError):
            self.mod.prepare(package, receipt, self.site, self.root / 'production', synthetic=False)

    def test_corrupt_package(self):
        package, receipt = self.package()
        package.write_bytes(b'not a zip')
        self.assert_rejected(package, receipt)

    def test_failed_check_preserves_last_good(self):
        package, receipt = self.package()
        self.release(package, receipt)
        old = self.mod.tree_manifest(self.target)
        last = (self.state / 'last-good.json').read_bytes()
        package, receipt = self.package('1.0.1')
        with self.assertRaises(self.mod.ReleaseError):
            self.release(package, receipt, failure='checks')
        self.assertEqual(self.mod.tree_manifest(self.target), old)
        self.assertEqual((self.state / 'last-good.json').read_bytes(), last)

    def test_update_and_rollback_exact_bytes(self):
        package, receipt = self.package()
        self.release(package, receipt)
        old = self.mod.tree_manifest(self.target)
        package, receipt = self.package('1.0.1')
        self.release(package, receipt)
        self.assertNotEqual(self.mod.tree_manifest(self.target), old)
        result = self.mod.rollback(self.state, self.target)
        self.assertEqual(result['status'], 'rolled-back-verified')
        self.assertEqual(self.mod.tree_manifest(self.target), old)

    def test_post_deploy_failures_restore_verified_previous(self):
        package, receipt = self.package()
        self.release(package, receipt)
        old = self.mod.tree_manifest(self.target)
        last = (self.state / 'last-good.json').read_bytes()
        for failure in ('after-deploy', 'readback'):
            package, receipt = self.package('1.0.1')
            with self.assertRaises(self.mod.ReleaseError):
                self.release(package, receipt, failure=failure)
            self.assertEqual(self.mod.tree_manifest(self.target), old)
            self.assertEqual((self.state / 'last-good.json').read_bytes(), last)

    def test_interrupted_deploy_reconciles_before_retry(self):
        package, receipt = self.package()
        self.release(package, receipt)
        package, receipt = self.package('1.0.1')
        with self.assertRaises(KeyboardInterrupt):
            self.release(package, receipt, failure='interrupt')
        self.assertTrue((self.state / 'pending.json').exists())
        result = self.release(package, receipt)
        self.assertEqual(result['status'], 'reconciled-verified')
        self.assertFalse((self.state / 'pending.json').exists())

    def test_reproducible_artifact_and_id_collision(self):
        package, receipt = self.package()
        result = self.release(package, receipt)
        artifact = self.state / 'releases' / result['artifact_sha256'] / 'site.zip'
        self.assertEqual(digest(artifact.read_bytes()), result['artifact_sha256'])
        other = self.root / 'other.zip'
        self.mod.archive_tree(self.target, other)
        self.assertEqual(other.read_bytes(), artifact.read_bytes())
        package.write_bytes(package.read_bytes() + b'collision')
        with self.assertRaises(self.mod.ReleaseError):
            self.release(package, receipt)

    def test_trusted_signed_production_candidate_and_forgery(self):
        import base64
        import subprocess
        package, receipt = self.package()
        review = json.loads(receipt.read_text())
        review['mode'] = 'PRODUCTION'
        review['signatures'] = []
        key = self.root / 'fixture-private.pem'
        public = self.root / 'fixture-public.pem'
        # Ephemeral synthetic test trust only; never a production trust key.
        subprocess.run(['openssl', 'genpkey', '-algorithm', 'ED25519', '-out', str(key)], check=True, capture_output=True)
        subprocess.run(['openssl', 'pkey', '-in', str(key), '-pubout', '-out', str(public)], check=True, capture_output=True)
        policy = {'schema_version': 1, 'trust_status': 'institution-configured', 'locale_profiles': ['en-only-trial'],
                  'approvers': [{'key_id': 'fixture', 'public_key': public.read_text(),
                                 'roles': ['clinical-safety', 'source-rights', 'language-en', 'release-owner'],
                                 'module_ids': ['synthetic-navigation'], 'languages': ['en']}],
                  'blocked_module_ids': ['pfa', 'psychological-first-aid']}
        registry = self.root / 'registry.json'
        registry.write_bytes(canonical(policy))
        body = self.root / 'body.json'
        body.write_bytes(canonical(review))
        signature = self.root / 'signature.bin'
        subprocess.run(['openssl', 'pkeyutl', '-sign', '-rawin', '-inkey', str(key), '-in', str(body), '-out', str(signature)], check=True, capture_output=True)
        review['signatures'] = [{'key_id': 'fixture', 'signature_base64': base64.b64encode(signature.read_bytes()).decode()}]
        receipt.write_bytes(canonical(review))
        candidate = self.root / 'production-candidate'
        result = self.mod.prepare(package, receipt, self.site, candidate, synthetic=False, registry=registry)
        self.assertEqual(result['mode'], 'PRODUCTION')
        self.assertFalse(json.loads((candidate / 'learning-release.json').read_text())['synthetic'])
        plan = self.mod.github_plan(candidate, 'institution/site', 'https://institution.github.io/site/')
        self.assertEqual(plan['status'], 'prepared-not-deployed')
        self.assertFalse(plan['merge']['direct_main_push'])
        adapter = self.root / 'adapter'
        self.mod.github_artifacts(self.site, candidate, adapter, 'institution/site', 'https://institution.github.io/site/')
        self.assertTrue((adapter / 'candidate.patch').stat().st_size > 0)
        self.assertTrue((adapter / 'provider-plan.json').is_file())
        review['locale_profile'] = 'bilingual-production'
        receipt.write_bytes(canonical(review))
        with self.assertRaises(self.mod.ReleaseError):
            self.mod.prepare(package, receipt, self.site, self.root / 'forged', synthetic=False, registry=registry)
        self.assertFalse((self.root / 'forged').exists())

    def test_provider_adapter_never_deploys_from_synthetic(self):
        package, receipt = self.package()
        self.release(package, receipt)
        with self.assertRaises(self.mod.ReleaseError):
            self.mod.github_plan(self.target, 'institution/site', 'https://institution.github.io/site/')

    def test_same_version_changed_bytes_rejected(self):
        package, receipt = self.package()
        self.release(package, receipt)
        old = self.mod.tree_manifest(self.target)
        package, receipt = self.package(mutate=lambda d: d.update(title='Changed synthetic title'))
        r = json.loads(receipt.read_text())
        r['release_id'] = 'other-release'
        receipt.write_bytes(canonical(r))
        with self.assertRaises(self.mod.ReleaseError):
            self.release(package, receipt)
        self.assertEqual(self.mod.tree_manifest(self.target), old)

    def test_symlink_and_duplicate_json_keys_rejected(self):
        package, receipt = self.package()
        link = self.site / 'link.txt'
        link.symlink_to(self.site / 'index.html')
        self.assert_rejected(package, receipt)
        link.unlink()
        receipt.write_text('{"mode":"SYNTHETIC","mode":"PRODUCTION"}')
        self.assert_rejected(package, receipt)

    def test_archive_duplicates_symlinks_bombs_and_duplicate_ids(self):
        import warnings
        for mode in ('duplicate', 'symlink', 'bomb', 'duplicate-id', 'wrong-module-hash'):
            package, receipt = self.package()
            with zipfile.ZipFile(package) as z:
                module = z.read('modules/demo.json')
            with warnings.catch_warnings():
                warnings.simplefilter('ignore')
                with zipfile.ZipFile(package, 'w', zipfile.ZIP_DEFLATED) as z:
                    files = [{'path': 'modules/demo.json', 'sha256': digest(module)}]
                    if mode == 'wrong-module-hash':
                        files[0]['sha256'] = '0' * 64
                    manifest = canonical({'schema_version': 1, 'files': files})
                    if mode == 'duplicate-id':
                        files.append({'path': 'modules/other.json', 'sha256': digest(module)})
                        manifest = canonical({'schema_version': 1, 'files': files})
                        z.writestr('modules/other.json', module)
                    z.writestr('manifest.json', manifest)
                    z.writestr('modules/demo.json', module)
                    if mode == 'duplicate':
                        z.writestr('modules/demo.json', module)
                    if mode == 'symlink':
                        info = zipfile.ZipInfo('modules/link.json')
                        info.external_attr = 0o120777 << 16
                        z.writestr(info, '../outside')
                    if mode == 'bomb':
                        z.writestr('modules/bomb.json', b'x' * (513 * 1024))
            r = json.loads(receipt.read_text())
            r.update(package_sha256=digest(package.read_bytes()), manifest_sha256=digest(manifest))
            receipt.write_bytes(canonical(r))
            with self.subTest(mode=mode):
                self.assert_rejected(package, receipt)

    def test_real_guard_failure_preserves_candidate_atomicity(self):
        package, receipt = self.package()
        tools = self.site / 'tools'
        tools.mkdir()
        (tools / 'i18n-check.py').write_text('raise SystemExit(1)\n')
        candidate = self.root / 'failed-candidate'
        with self.assertRaises(self.mod.ReleaseError):
            self.mod.prepare(package, receipt, self.site, candidate, synthetic=True)
        self.assertFalse(candidate.exists())

    def test_roleplay_entrypoint(self):
        import subprocess
        script = ROOT / 'tools/learning-release/roleplay.py'
        self.assertTrue(script.exists(), 'one-operation roleplay entrypoint missing')
        output = self.root / 'roleplay'
        result = subprocess.run([sys.executable, str(script), '--site', str(self.site), '--output', str(output)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads((output / 'report.json').read_text())
        self.assertTrue(report['rollback_exact_bytes'])
        self.assertEqual(report['provider_deployment'], 'NOT RUN')


if __name__ == '__main__':
    unittest.main(verbosity=2)
