#!/usr/bin/env python3
"""Protected-PR/legacy Pages broker. No credentials accepted; gh owns authentication.

All mutating operations require explicit execute authorization and durable local state.
Fixture injection is constructor-only; the operator CLI always uses real gh/HTTPS.
"""
import base64
import fcntl
import json
from pathlib import Path
import re
import subprocess
import tempfile
import time
import os
import copy
from urllib.parse import quote, urlsplit
from urllib.request import build_opener, HTTPRedirectHandler, Request

from release import (ReleaseError, atomic_json, canonical, prepare, read_json,
                     require, sha, verify_authorization, no_symlink_path, disjoint_paths)


class ProviderError(ReleaseError):
    pass


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise ProviderError('readback redirect refused')


class GitHub:
    def __init__(self, repository, gh_command=None, http=None):
        require(bool(re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repository)), 'invalid repository')
        self.repository = repository
        self.command = gh_command or ['gh']
        self.http = http or self.https

    def api(self, endpoint, method='GET', payload=None, missing=False):
        argv = [*self.command, 'api', 'repos/' + self.repository + '/' + endpoint,
                '--method', method, '-H', 'Accept: application/vnd.github+json',
                '-H', 'X-GitHub-Api-Version: 2022-11-28']
        if payload is not None:
            argv += ['--input', '-']
        try:
            result = subprocess.run(argv, input=canonical(payload) if payload is not None else None,
                                    capture_output=True, timeout=60)
        except (subprocess.TimeoutExpired, OSError) as exc:
            raise ProviderError('provider effect unknown; reconcile durable intent') from exc
        if missing and result.returncode and b'HTTP 404' in result.stderr:
            return None
        if result.returncode != 0:
            raise ProviderError('provider request failed/ambiguous: ' + method + ' ' + endpoint)
        try:
            return json.loads(result.stdout)
        except ValueError as exc:
            raise ProviderError('invalid provider response; reconcile intent') from exc

    def https(self, url):
        with build_opener(NoRedirect).open(Request(url, headers={'Cache-Control': 'no-cache'}), timeout=30) as response:
            require(response.status == 200, 'readback HTTP status')
            raw = response.read(8 * 1024 * 1024 + 1)
            require(len(raw) <= 8 * 1024 * 1024, 'readback exceeds bound')
            return raw

    def main(self):
        return self.api('git/ref/heads/main')['object']['sha']

    def snapshot(self, commit):
        obj = self.api('git/commits/' + commit)
        tree = self.api('git/trees/' + obj['tree']['sha'] + '?recursive=1')
        require(tree.get('truncated') is False and len(tree['tree']) <= 10000, 'provider tree incomplete/oversized')
        files = {}
        for item in tree['tree']:
            if item['type'] == 'tree':
                continue
            require(item['type'] == 'blob' and item['mode'] in ('100644', '100755'), 'symlink/submodule rejected')
            safe_path(item['path'])
            require(item.get('size', 0) <= 8 * 1024 * 1024, 'remote blob oversized')
            blob = self.api('git/blobs/' + item['sha'])
            require(blob['encoding'] == 'base64', 'unsupported blob encoding')
            files[item['path']] = base64.b64decode(blob['content'])
        require(sum(map(len, files.values())) <= 64 * 1024 * 1024, 'site size bound')
        return obj['tree']['sha'], files


def safe_path(path):
    require(isinstance(path, str) and path and not path.startswith('/') and
            all(p not in ('', '.', '..', '.git') for p in path.split('/')) and
            not any(c in path for c in ('\\', '?', '#', '\x00')), 'unsafe target path')
    return path


def scoped(path):
    return path == 'learning-release.json' or path.startswith('learn/content/')


def encoded(files):
    return {p: base64.b64encode(b).decode() if b is not None else None for p, b in files.items()}


def decoded(files):
    return {p: base64.b64decode(b) if b is not None else None for p, b in files.items()}


class Broker:
    def __init__(self, state, policy, registry, provider=None, max_polls=60, poll_seconds=10):
        self.state_original = Path(state).absolute()
        self.state = no_symlink_path(state)
        self.policy = copy.deepcopy(policy)
        self.registry_path = Path(registry)
        self.registry = self.registry_path.read_bytes()
        self.gh = provider or GitHub(policy['repository'])
        self.max_polls, self.poll_seconds = max_polls, poll_seconds
        require(1 <= max_polls <= 180 and 0 <= poll_seconds <= 30, 'invalid bounded polling')
        require(sha(self.registry) == policy['registry_sha256'], 'registry differs from independent institutional pin')
        require(self.gh.repository == policy['repository'], 'provider repository mismatch')
        url = urlsplit(policy['base_url'])
        require(url.scheme == 'https' and url.hostname and not url.username and not url.password and
                not url.query and not url.fragment and url.port in (None, 443), 'invalid pinned HTTPS base origin')
        require(policy.get('stable_assets') and all(safe_path(p) for p in policy['stable_assets']), 'explicit stable asset scope required')
        require(type(policy.get('allow_rollback')) is bool, 'explicit rollback authorization required')
        self.base = policy['base_url'].rstrip('/') + '/'
        self.binding = sha(canonical(policy))

    def check_registry_pin(self):
        require(sha(self.registry_path.read_bytes()) == self.policy['registry_sha256'] == sha(self.registry),
                'registry differs from independent institutional pin')

    def state_envelope(self, record, ancestor=0, store=False):
        def pack(item):
            if isinstance(item, dict):
                result = {}
                for key, value in item.items():
                    if key in ('content', 'changes'):
                        result[key] = {}
                        for path, value64 in value.items():
                            safe_path(path)
                            if value64 is None:
                                result[key][path] = None
                                continue
                            raw = base64.b64decode(value64, validate=True)
                            require(len(raw) <= 8 * 1024 * 1024, 'broker artifact exceeds bound')
                            digest = sha(raw)
                            result[key][path] = {'broker_blob_sha256': digest}
                            if store:
                                directory = self.state / '.broker-blobs'
                                directory.mkdir(parents=True, exist_ok=True)
                                target = directory / digest
                                if target.exists():
                                    require(not target.is_symlink() and sha(target.read_bytes()) == digest, 'broker artifact corrupt')
                                else:
                                    temporary = directory / (digest + '.writing')
                                    with temporary.open('wb') as stream:
                                        stream.write(raw)
                                        stream.flush()
                                        os.fsync(stream.fileno())
                                    os.replace(temporary, target)
                                    fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
                                    try:
                                        os.fsync(fd)
                                    finally:
                                        os.close(fd)
                    else:
                        result[key] = pack(value)
                return result
            if isinstance(item, list):
                return [pack(v) for v in item]
            return item
        envelope = {'broker_state_version': 1, 'blob_ancestor': ancestor, 'record': pack(record)}
        require(len(canonical(envelope)) <= 1024 * 1024, 'broker manifest exceeds durable reader bound')
        return envelope

    def write_record(self, path, record):
        ancestor = 0 if Path(path).parent == self.state else 1
        # Validate manifest size before writing even local artifact data.
        self.state_envelope(record, ancestor)
        atomic_json(path, self.state_envelope(record, ancestor, store=True))

    def save(self, pending):
        # Reserve room for prior+failed records, rollback deletions and cursors.
        # Refuse unsupported manifests before the first provider mutation.
        if pending['kind'] == 'publish':
            require(len(canonical(self.state_envelope(pending))) <= 128 * 1024,
                    'broker manifest exceeds supported publish bound')
        self.write_record(self.state / 'pending.json', pending)

    def poll(self, observe, ready):
        for attempt in range(self.max_polls):
            value = observe()
            if ready(value):
                return value
            if attempt + 1 < self.max_polls:
                time.sleep(self.poll_seconds)
        raise ProviderError('provider still pending; durable intent retained, retry reads/reconciles only')

    def gates(self):
        protection = self.gh.api('branches/main/protection')
        require(protection.get('required_pull_request_reviews') is not None, 'protected PR main required')
        require(protection.get('enforce_admins', {}).get('enabled') is True, 'admin bypass must be disabled')
        checks = protection.get('required_status_checks') or {}
        require(checks.get('strict') is True, 'strict up-to-date protected checks required')
        contexts = {name: None for name in checks.get('contexts', [])}
        for check in checks.get('checks', []):
            app_id = check.get('app_id')
            require(app_id is None or type(app_id) is int and app_id >= -1, 'invalid required check App identity')
            contexts[check['context']] = app_id if app_id not in (None, -1) else None
        require(contexts, 'provider required checks not commissioned')
        pages = self.gh.api('pages')
        require(pages.get('build_type') == 'legacy' and pages.get('source') == {'branch': 'main', 'path': '/'}, 'legacy main-root Pages required; no hosting changes allowed')
        require(pages['html_url'].rstrip('/') + '/' == self.base, 'provider Pages URL differs from pinned target')
        return contexts

    def readback(self, pending):
        for path, digest in pending['readback'].items():
            url = self.base + quote(safe_path(path), safe='/') + '?learning_readback=' + pending['head']
            require(sha(self.gh.http(url)) == digest, 'exact deployed bytes mismatch: ' + path)

    def expected_publish(self, package, approval, base):
        """Derive authority anew: signed package over immutable provider base.

        Work trees and state JSON are caches, never approval authorities.
        """
        receipt = read_json(approval)
        self.check_registry_pin()
        verify_authorization(receipt, self.registry)
        release_id = receipt['release_id']
        require(bool(re.fullmatch(r'[a-z][a-z0-9-]{0,63}', release_id)), 'invalid release ID')
        require(bool(re.fullmatch(r'[a-f0-9]{40}', base)), 'invalid immutable base identity')
        tree, files = self.gh.snapshot(base)
        scratch = Path(os.environ.get('TMPDIR', '/root/.hermes/cache/scratch'))
        with tempfile.TemporaryDirectory(prefix='broker-expected-', dir=scratch) as folder:
            source = Path(folder) / 'source'
            source.mkdir()
            for path, raw in files.items():
                target = source / safe_path(path)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(raw)
            candidate = Path(folder) / 'candidate'
            prepare(package, approval, source, candidate, registry=self.registry)
            content = {p.relative_to(candidate).as_posix(): p.read_bytes() for p in candidate.rglob('*') if p.is_file() and scoped(p.relative_to(candidate).as_posix())}
        changed = {p: b for p, b in content.items() if files.get(p) != b}
        require(changed and all(scoped(p) for p in changed), 'empty/out-of-scope content patch')
        return self.intent(release_id, receipt, base, tree, files, content, changed,
                           sha(Path(approval).read_bytes()), 'publish')

    def prepare_intent(self, package, approval):
        return self.expected_publish(package, approval, self.gh.main())

    def reconstruct_publish(self, pending, package, approval):
        expected = self.expected_publish(package, approval, pending['base'])
        # Only reconciliation cursors survive. Every write and readback target is
        # regenerated, including catalogue, marker, stable assets and retained bytes.
        return expected | {k: pending[k] for k in ('phase', 'head', 'pr', 'merged', 'status') if k in pending}

    def intent(self, release_id, receipt, base, tree, files, content, changed, approval_hash, kind):
        require(sum(len(raw) for raw in content.values()) <= 32 * 1024 * 1024,
                'scoped content exceeds supported durable rollback bound')
        deployed = files | changed
        read_paths = set(content) | set(self.policy['stable_assets'])
        require(all(p in deployed and deployed[p] is not None for p in read_paths), 'readback target missing')
        require(all(len(p) <= 1024 for p in read_paths), 'readback path exceeds supported bound')
        require(len(self.policy['stable_assets']) <= 256, 'stable asset scope exceeds supported bound')
        # Leave bounded room for reconciliation cursor values and nested rollback.
        require(len(canonical(receipt)) <= 64 * 1024, 'receipt exceeds supported broker bound')
        # Verify every released immutable module plus exact catalogue/marker, not only updated modules.
        require('learning-release.json' in read_paths and 'learn/content/catalogue.json' in read_paths, 'missing release catalogue/marker')
        return {'release_id': release_id, 'receipt': receipt, 'approval_sha256': approval_hash,
                'package_sha256': receipt['package_sha256'], 'manifest_sha256': receipt['manifest_sha256'],
                'binding': self.binding, 'repository': self.gh.repository, 'base': base, 'tree': tree,
                'branch': 'learning-release/' + release_id + ('-rollback' if kind == 'rollback' else ''),
                'content': encoded(content), 'changes': encoded(changed),
                'readback': {p: sha(deployed[p]) for p in sorted(read_paths)},
                'approved_manifest_sha256': sha(canonical(encoded(content))), 'kind': kind,
                'phase': 'prepared', 'head': None, 'pr': None}

    def publish(self, package, approval, execute=False):
        require(execute is True, 'deliberate --execute-deployment authorization required')
        require(no_symlink_path(self.state_original) == self.state, 'state canonical boundary changed')
        for input_path in (package, approval, self.registry_path):
            disjoint_paths(self.state, input_path)
        require(not self.state.exists() or not any(p.is_symlink() for p in self.state.rglob('*')), 'state descendant symlink refused')
        self.state.mkdir(parents=True, exist_ok=True)
        with (self.state / 'lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            receipt = read_json(approval)
            self.check_registry_pin()
            verify_authorization(receipt, self.registry)
            require(receipt['package_sha256'] == sha(Path(package).read_bytes()), 'package hash mismatch')
            contexts = self.gates()
            last_path = self.state / 'last-good.json'
            if last_path.exists():
                prior = self.verified_prior(read_json(last_path))
                require(len(canonical(self.state_envelope(prior))) <= 128 * 1024,
                        'prior broker manifest exceeds supported rollback bound')
            path = self.state / 'pending.json'
            if path.exists():
                pending = read_json(path)
                require(pending['binding'] == self.binding and pending['repository'] == self.gh.repository, 'pending provider/authority mismatch')
                require(pending['receipt'] == receipt and pending['approval_sha256'] == sha(Path(approval).read_bytes()), 'different release pending; manual reconciliation required')
                require(pending['kind'] in ('publish', 'rollback'), 'unknown pending intent kind')
                if pending['kind'] == 'publish':
                    pending = self.reconstruct_publish(pending, package, approval)
                    self.save(pending)
            else:
                history = self.state / 'history' / (receipt['release_id'] + '.json')
                if history.exists():
                    old = read_json(history)
                    require(old['receipt'] == receipt and old['approval_sha256'] == sha(Path(approval).read_bytes()), 'release ID collision')
                    current = read_json(self.state / 'last-good.json')
                    require(current['release_id'] == receipt['release_id'] and old['status'] == 'verified', 'old release replay forbidden; protected rollback only')
                    old = self.reconstruct_publish(old, package, approval)
                    self.verified_prior(old)
                    self.readback(old)
                    return old | {'status': 'already-verified'}
                pending = self.prepare_intent(package, approval)
                self.save(pending)
            if pending['kind'] == 'rollback':
                failed = self.reconstruct_publish(pending['failed'], package, approval)
                pr = self.validate_pr(failed, self.gh.api('pulls/' + str(failed['pr'])))
                require(pr['merged'] and pr['merge_commit_sha'] == failed.get('merged'), 'rollback failed merge proof mismatch')
                _, rollback_base = self.gh.snapshot(pending['base'])
                require({p: b for p, b in rollback_base.items() if scoped(p)} == decoded(failed['content']),
                        'rollback base differs from authenticated failed release')
                pending['failed'] = failed
                return self.drive_rollback(pending, contexts)
            try:
                return self.drive(pending, contexts)
            except ProviderError:
                # Pending/ambiguous provider effects must reconcile before any new writes.
                raise
            except Exception:
                # Only a positively observed merged release can trigger a scoped authorized rollback.
                # Unknown effects remain pending; no blind reversal or last-good advancement.
                if pending.get('merged') and self.policy['allow_rollback'] and (self.state / 'last-good.json').exists():
                    self.start_rollback(pending, contexts)
                raise

    def validate_pr(self, pending, pr):
        require(pr['number'] == pending['pr'] and pr['head']['sha'] == pending['head'] and
                pr['head']['ref'] == pending['branch'] and pr['base']['ref'] == 'main' and
                pr['head']['repo']['full_name'] == self.gh.repository and
                pr['base']['repo']['full_name'] == self.gh.repository and
                pr.get('body') == self.pr_body(pending), 'remote PR identity/approved manifest mismatch')
        return pr

    def pr_body(self, p):
        return 'Institution-authorized content receipt; not independently attested provenance.\n' + canonical({k: p[k] for k in ('release_id', 'package_sha256', 'manifest_sha256', 'approved_manifest_sha256', 'approval_sha256', 'binding', 'kind')}).decode()

    def drive(self, p, contexts):
        if p['head'] is None:
            require(p['phase'] == 'prepared', 'unknown immutable commit creation; manual attention required')
            require(self.gh.main() == p['base'], 'concurrent base drift; refuse publish')
            tree_entries = []
            for path, raw in decoded(p['changes']).items():
                require(scoped(path), 'out-of-scope remote write refused')
                blob_sha = None
                if raw is not None:
                    blob = self.gh.api('git/blobs', 'POST', {'content': base64.b64encode(raw).decode(), 'encoding': 'base64'})
                    blob_sha = blob['sha']
                tree_entries.append({'path': path, 'mode': '100644', 'type': 'blob', 'sha': blob_sha})
            tree = self.gh.api('git/trees', 'POST', {'base_tree': p['tree'], 'tree': tree_entries})
            p['phase'] = 'commit-requested'
            self.save(p)
            commit = self.gh.api('git/commits', 'POST', {'message': 'Authorized learning content ' + p['release_id'],
                'tree': tree['sha'], 'parents': [p['base']]})
            p['head'] = commit['sha']
            p['phase'] = 'commit-created'
            self.save(p)
        # Re-read exact remote tree before any ref/PR/merge writes, not merely branch name.
        remote_commit = self.gh.api('git/commits/' + p['head'])
        require([x['sha'] for x in remote_commit['parents']] == [p['base']], 'remote commit parent differs from pinned fresh main')
        _, remote_files = self.gh.snapshot(p['head'])
        require({path: raw for path, raw in remote_files.items() if scoped(path)} == decoded(p['content']), 'remote commit approved manifest mismatch')
        original_tree, original = self.gh.snapshot(p['base'])
        require({k: b for k, b in remote_files.items() if not scoped(k)} == {k: b for k, b in original.items() if not scoped(k)}, 'remote commit changed unrelated site assets')
        branch = self.gh.api('git/ref/heads/' + p['branch'], missing=True)
        if branch:
            require(branch['object']['sha'] == p['head'], 'feature branch drift; manual attention required')
        else:
            require(p['phase'] == 'commit-created' and self.gh.main() == p['base'], 'unknown push effect/base drift; manual attention required')
            p['phase'] = 'branch-requested'
            self.save(p)
            self.gh.api('git/refs', 'POST', {'ref': 'refs/heads/' + p['branch'], 'sha': p['head']})
            branch = self.gh.api('git/ref/heads/' + p['branch'])
            require(branch['object']['sha'] == p['head'], 'feature ref readback mismatch')
            p['phase'] = 'branch-created'
            self.save(p)
        if not p['pr']:
            prs = self.gh.api('pulls?state=all&head=' + quote(self.gh.repository.split('/')[0] + ':' + p['branch'], safe='') + '&base=main&per_page=100')
            require(len(prs) <= 1, 'duplicate PRs; manual attention required')
            if prs:
                p['pr'] = prs[0]['number']
                self.validate_pr(p, prs[0])
                self.save(p)
            else:
                require(p['phase'] in ('branch-created', 'branch-requested') and self.gh.main() == p['base'], 'unknown PR creation/base drift; no replay')
                p['phase'] = 'pr-requested'
                self.save(p)
                pr = self.gh.api('pulls', 'POST', {'title': 'Learning content ' + p['release_id'],
                    'body': self.pr_body(p), 'head': p['branch'], 'base': 'main', 'draft': False,
                    'maintainer_can_modify': False})
                p['pr'] = pr['number']
                self.save(p)
        pr = self.validate_pr(p, self.gh.api('pulls/' + str(p['pr'])))
        if not pr['merged']:
            require(pr['state'] == 'open', 'PR closed without merge; manual attention required')
            require(self.gh.main() == p['base'], 'concurrent main drift; do not merge stale candidate')
            if p['phase'] != 'merge-requested':
                self.poll(lambda: self.checks(p['head'], contexts), bool)
                p['phase'] = 'merge-requested'
                self.save(p)
                self.gh.api('pulls/' + str(p['pr']) + '/merge', 'PUT', {'sha': p['head'], 'merge_method': 'squash',
                                                                 'commit_title': 'Learning content ' + p['release_id']})
            pr = self.poll(lambda: self.validate_pr(p, self.gh.api('pulls/' + str(p['pr']))), lambda x: x['merged'])
        require(pr['merge_commit_sha'], 'merged SHA missing')
        p['merged'] = pr['merge_commit_sha']
        self.save(p)
        require(self.gh.main() == p['merged'], 'postmerge main drift; manual reconciliation required')
        _, merged_files = self.gh.snapshot(p['merged'])
        require(all(sha(merged_files[path]) == digest for path, digest in p['readback'].items()), 'merged tree differs from approved target')
        self.pages(p)
        self.readback(p)
        require(self.gh.main() == p['merged'], 'main changed during readback; manual reconciliation required')
        p['status'] = 'verified'
        self.save(p)
        if p['kind'] == 'rollback':
            return p
        last = self.state / 'last-good.json'
        if last.exists() and read_json(last)['release_id'] != p['release_id']:
            self.write_record(self.state / 'previous-good.json', read_json(last))
        self.write_record(self.state / 'history' / (p['release_id'] + '.json'), p)
        self.write_record(last, p)
        (self.state / 'pending.json').unlink()
        return p

    def checks(self, head, required):
        runs = self.gh.api('commits/' + head + '/check-runs?per_page=100')
        status = self.gh.api('commits/' + head + '/status?per_page=100')
        require(runs['total_count'] <= 100 and status['total_count'] <= 100, 'check pagination exceeds safe bound')
        observed = {}
        for run in runs['check_runs']:
            name = run['name']
            if name in required and (required[name] is None or run.get('app', {}).get('id') == required[name]):
                observed.setdefault(name, run['conclusion'] if run['status'] == 'completed' else 'pending')
        for check in status['statuses']:
            name = check['context']
            # Legacy statuses do not carry the App identity required by an
            # app-bound check, even when the context name happens to match.
            if name in required and required[name] is None:
                observed.setdefault(name, check['state'])
        for name in required:
            require(observed.get(name) not in ('failure', 'error', 'cancelled', 'timed_out', 'action_required', 'startup_failure', 'stale'), 'required provider check failed: ' + name)
        return all(observed.get(name) in ('success', 'neutral', 'skipped') for name in required)

    def pages(self, p):
        def builds():
            result = self.gh.api('pages/builds?per_page=100')
            return [b for b in result if b['commit'] == p['merged']]
        found = builds()
        if not found:
            if p['phase'] == 'pages-requested':
                raise ProviderError('Pages request effect unknown; manual attention required')
            p['phase'] = 'pages-requested'
            self.save(p)
            self.gh.api('pages/builds', 'POST', {})
        def ready(items):
            if not items:
                return False
            require(items[0]['status'] != 'errored', 'Pages build failed')
            return items[0]['status'] == 'built'
        self.poll(builds, ready)

    def verified_prior(self, prior):
        """Resolve a receipt-matched protected merge, not a locally hashed tree.

        The institution-trusted provider PR/immutable commit is the provenance
        authority for retained content. Local checksums are merely cache IDs.
        """
        from release import run_checks, parse_json
        require(prior['binding'] == self.binding and prior['status'] == 'verified', 'rollback prior authority mismatch')
        self.check_registry_pin()
        verify_authorization(prior['receipt'], self.registry)
        pr = self.gh.api('pulls/' + str(prior['pr']))
        require(pr['merged'] and pr['merge_commit_sha'] == prior['merged'], 'rollback prior protected merge mismatch')
        _, files = self.gh.snapshot(pr['merge_commit_sha'])
        _, head_files = self.gh.snapshot(pr['head']['sha'])
        content = {p: b for p, b in files.items() if scoped(p)}
        require(content == {p: b for p, b in head_files.items() if scoped(p)}, 'rollback prior merge content mismatch')
        expected = dict(prior, head=pr['head']['sha'], branch='learning-release/' + prior['receipt']['release_id'],
                        kind='publish', release_id=prior['receipt']['release_id'], content=encoded(content),
                        approved_manifest_sha256=sha(canonical(encoded(content))),
                        package_sha256=prior['receipt']['package_sha256'], manifest_sha256=prior['receipt']['manifest_sha256'])
        self.validate_pr(expected, pr)
        marker = parse_json(content['learning-release.json'])
        require(marker == {'release_id': prior['receipt']['release_id'], 'synthetic': False,
                'package_sha256': prior['receipt']['package_sha256'], 'manifest_sha256': prior['receipt']['manifest_sha256'],
                'trust_registry_sha256': verify_authorization(prior['receipt'], self.registry),
                'approval_sha256': prior['approval_sha256'], 'locale_profile': prior['receipt']['locale_profile'],
                'modules': prior['receipt']['modules']}, 'rollback prior manifest receipt mismatch')
        for module in prior['receipt']['modules']:
            path = 'learn/content/modules/{module_id}/{content_version}/{language}.json'.format(**module)
            require(path in content and sha(content[path]) == module['sha256'], 'rollback prior manifest module mismatch')
        scratch = Path(os.environ.get('TMPDIR', '/root/.hermes/cache/scratch'))
        with tempfile.TemporaryDirectory(prefix='broker-prior-', dir=scratch) as folder:
            root = Path(folder)
            for path, raw in content.items():
                target = root / safe_path(path)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(raw)
            (root / 'learn/index.html').write_bytes(b'validation-only')
            run_checks(root, root)
        return expected

    def start_rollback(self, failed, contexts):
        prior = self.verified_prior(read_json(self.state / 'last-good.json'))
        base = self.gh.main()
        tree, files = self.gh.snapshot(base)
        # Concurrent unrelated changes are preserved; concurrent content changes require manual attention.
        require({p: b for p, b in files.items() if scoped(p)} == decoded(failed['content']), 'rollback content drift; manual attention required')
        content = decoded(prior['content'])
        changes = {p: b for p, b in content.items() if files.get(p) != b}
        changes.update({p: None for p in failed['content'] if p not in content})
        require(changes, 'no rollback content changes')
        rollback = self.intent(failed['release_id'], failed['receipt'], base, tree, files, content, changes,
                               failed['approval_sha256'], 'rollback')
        rollback['failed'] = failed
        rollback['prior'] = prior
        self.write_record(self.state / 'rollback-intent.json', rollback)
        self.save(rollback)
        return self.drive_rollback(rollback, contexts)

    def drive_rollback(self, rollback, contexts):
        require(self.policy['allow_rollback'], 'rollback authorization revoked')
        prior = self.verified_prior(rollback['prior'])
        require(prior['content'] == rollback['prior']['content'] and
                prior['content'] == rollback['content'], 'rollback prior manifest corrupt')
        tree, files = self.gh.snapshot(rollback['base'])
        content = decoded(prior['content'])
        changes = {p: b for p, b in content.items() if files.get(p) != b}
        changes.update({p: None for p in files if scoped(p) and p not in content})
        expected = self.intent(rollback['release_id'], rollback['receipt'], rollback['base'], tree,
                               files, content, changes, rollback['approval_sha256'], 'rollback')
        rollback.update({k: v for k, v in expected.items() if k not in ('phase', 'head', 'pr')})
        content = decoded(prior['content'])
        marker = json.loads(content['learning-release.json'])
        require(marker['release_id'] == prior['receipt']['release_id'] and
                marker['modules'] == prior['receipt']['modules'] and
                marker['package_sha256'] == prior['receipt']['package_sha256'] and
                marker['manifest_sha256'] == prior['receipt']['manifest_sha256'], 'rollback prior manifest receipt mismatch')
        for module in prior['receipt']['modules']:
            path = 'learn/content/modules/{module_id}/{content_version}/{language}.json'.format(**module)
            require(path in content and sha(content[path]) == module['sha256'], 'rollback prior manifest module mismatch')
        self.drive(rollback, contexts)
        rollback['status'] = 'rolled-back-verified'
        self.write_record(self.state / 'rollback-records' / (rollback['release_id'] + '.json'), rollback)
        failed = rollback['failed'] | {'status': 'rolled-back-verified'}
        self.write_record(self.state / 'history' / (failed['release_id'] + '.json'), failed)
        # last-good remains the previous approved release; update its remote proof/readback only.
        # Keep the original receipt-matched protected PR/merge proof; the
        # rollback PR carries the failed receipt, not the prior receipt.
        current = prior | {'readback': rollback['readback']}
        self.write_record(self.state / 'last-good.json', current)
        (self.state / 'pending.json').unlink()
        return rollback
