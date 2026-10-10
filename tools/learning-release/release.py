#!/usr/bin/env python3
"""Trusted content importer; private fixtures or explicitly authorized protected-PR publication."""
import argparse
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('draft_validator', HERE / 'validate_content.py')
assert spec and spec.loader
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)


class ReleaseError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise ReleaseError(message)


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False) + '\n').encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def parse_json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'duplicate JSON key')
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=lambda _: require(False, 'non-finite JSON'))


def no_symlink_path(path):
    """Inspect lexical path components before resolving, including absent leaves."""
    path = Path(path).absolute()
    require(all(not part.is_symlink() for part in (path, *path.parents)), 'path/parent symlink refused')
    return path.resolve()


def disjoint_paths(left, right):
    left, right = no_symlink_path(left), no_symlink_path(right)
    require(left != right and left not in right.parents and right not in left.parents,
            'paths must be canonically disjoint')


def read_json(path):
    no_symlink_path(path)
    require(Path(path).stat().st_size <= 1024 * 1024, 'JSON exceeds size limit')
    value = parse_json(Path(path).read_bytes())
    if isinstance(value, dict) and value.get('broker_state_version') == 1:
        import base64
        require(set(value) == {'broker_state_version', 'blob_ancestor', 'record'} and
                type(value['blob_ancestor']) is int and 0 <= value['blob_ancestor'] <= 1, 'invalid broker state envelope')
        root = Path(path).parent
        for _ in range(value['blob_ancestor']):
            root = root.parent
        root = root / '.broker-blobs'
        total = 0
        def hydrate(item):
            nonlocal total
            if isinstance(item, dict) and set(item) == {'broker_blob_sha256'}:
                digest = item['broker_blob_sha256']
                require(isinstance(digest, str) and re.fullmatch(r'[a-f0-9]{64}', digest), 'invalid broker artifact ID')
                blob = root / digest
                require(not root.is_symlink() and not blob.is_symlink() and blob.stat().st_size <= 8 * 1024 * 1024, 'unsafe/oversized broker artifact')
                raw = blob.read_bytes()
                total += len(raw)
                require(total <= 256 * 1024 * 1024 and sha(raw) == digest, 'broker artifact corrupt/oversized')
                return base64.b64encode(raw).decode()
            if isinstance(item, dict):
                return {k: hydrate(v) for k, v in item.items()}
            if isinstance(item, list):
                return [hydrate(v) for v in item]
            return item
        return hydrate(value['record'])
    return value


def atomic_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.writing')
    with temporary.open('wb') as stream:
        stream.write(canonical(data))
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)
    directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def tree_manifest(root):
    return [{'path': p.relative_to(root).as_posix(), 'sha256': sha(p.read_bytes()), 'bytes': p.stat().st_size}
            for p in sorted(Path(root).rglob('*')) if p.is_file()]


def walk_strings(value):
    if isinstance(value, str):
        require(len(value) <= 50000, 'text exceeds UI limit')
        yield value
    elif isinstance(value, list):
        require(len(value) <= 500, 'list exceeds UI limit')
        for item in value:
            yield from walk_strings(item)
    elif isinstance(value, dict):
        for item in value.values():
            yield from walk_strings(item)


def copy_site(site, dest):
    require(not any(p.is_symlink() for p in Path(site).rglob('*')), 'source symlinks rejected')
    shutil.copytree(site, dest, ignore=shutil.ignore_patterns('.git', '__pycache__', '*.pyc', 'node_modules'))


def run_checks(source, candidate):
    reports = []
    for script in ('tools/i18n-check.py', 'tools/text-setting-check.py'):
        if (Path(source) / script).exists():
            baseline = subprocess.run([sys.executable, str(Path(source) / script)], cwd=source, capture_output=True, timeout=60)
            result = subprocess.run([sys.executable, str(Path(candidate) / script)], cwd=candidate, capture_output=True, timeout=60)
            require(baseline.returncode == 0 and result.returncode == 0, 'website guard failed: ' + script)
            reports.append({'check': script, 'baseline': baseline.returncode, 'candidate': result.returncode,
                            'output_sha256': sha(result.stdout + result.stderr)})
    catalogue_path = Path(candidate) / 'learn/content/catalogue.json'
    catalogue = read_json(catalogue_path)
    require(set(catalogue) == {'schema_version', 'modules'} and type(catalogue['schema_version']) is int and catalogue['schema_version'] == 1, 'catalogue schema')
    seen = set()
    for entry in catalogue['modules']:
        require(set(entry) == {'module_id', 'content_version', 'language', 'path', 'sha256'}, 'catalogue entry schema')
        require(bool(re.fullmatch(r'modules/[a-z][a-z0-9-]*/[0-9]+\.[0-9]+\.[0-9]+/(en|ne)\.json', entry['path'])), 'unsafe catalogue path')
        identity = (entry['module_id'], entry['language'])
        require(identity not in seen, 'duplicate catalogue identity')
        seen.add(identity)
        path = catalogue_path.parent / entry['path']
        raw = path.read_bytes()
        require(sha(raw) == entry['sha256'], 'catalogue content hash mismatch')
        data = parse_json(raw)
        require(not validator.validate(data), 'catalogue module schema')
        require(all(data[k] == entry[k] for k in ('module_id', 'content_version', 'language')), 'catalogue identity mismatch')
    require((Path(candidate) / 'learn/index.html').is_file(), 'learning UI missing')
    reports.append({'check': 'catalogue-schema-hash-and-quiz', 'modules': len(seen), 'status': 'pass'})
    return reports


def verify_authorization(receipt, registry):
    import base64
    require(receipt.get('mode') == 'PRODUCTION' and registry, 'trusted production authorization not configured')
    policy = parse_json(registry) if isinstance(registry, bytes) else read_json(registry)
    require(policy.get('schema_version') == 1 and policy.get('trust_status') == 'institution-configured', 'trust registry not commissioned')
    require(receipt['locale_profile'] in policy['locale_profiles'], 'locale profile not institution-authorized')
    approvers = policy['approvers']
    require(0 < len(approvers) <= 32, 'approver registry bound')
    require(len({a['key_id'] for a in approvers}) == len(approvers), 'duplicate approver key')
    require(0 < len(receipt['signatures']) <= 32, 'missing or excessive signatures')
    payload = dict(receipt)
    payload['signatures'] = []
    covered = {tuple(m[k] for k in ('module_id', 'content_version', 'language')): set() for m in receipt['modules']}
    scratch = Path(os.environ.get('TMPDIR', '/root/.hermes/cache/scratch'))
    with tempfile.TemporaryDirectory(prefix='review-verify-', dir=scratch) as folder:
        folder = Path(folder)
        (folder / 'body').write_bytes(canonical(payload))
        seen = set()
        for signature in receipt['signatures']:
            require(set(signature) == {'key_id', 'signature_base64'}, 'signature schema')
            require(signature['key_id'] not in seen, 'duplicate signing key')
            seen.add(signature['key_id'])
            matching = [a for a in approvers if a['key_id'] == signature['key_id']]
            require(len(matching) == 1, 'untrusted signing key')
            approver = matching[0]
            (folder / 'public.pem').write_text(approver['public_key'])
            try:
                (folder / 'signature').write_bytes(base64.b64decode(signature['signature_base64'], validate=True))
            except ValueError as exc:
                raise ReleaseError('invalid signature encoding') from exc
            verified = subprocess.run(['openssl', 'pkeyutl', '-verify', '-pubin', '-inkey', str(folder / 'public.pem'),
                                      '-rawin', '-in', str(folder / 'body'), '-sigfile', str(folder / 'signature')],
                                      capture_output=True, timeout=15)
            require(verified.returncode == 0, 'review signature invalid')
            for identity in covered:
                module_id, version, language = identity
                require(module_id not in policy['blocked_module_ids'], 'institution-blocked module')
                if module_id in approver['module_ids'] and language in approver['languages']:
                    covered[identity].update(approver['roles'])
    for (module_id, version, language), roles in covered.items():
        require({'clinical-safety', 'source-rights', 'release-owner', 'language-' + language} <= roles,
                'missing authorized clinical/source/language/owner review')
    return sha(canonical(policy))


def prepare(package, approval, site, candidate, synthetic=False, registry=None):
    candidate, site = no_symlink_path(candidate), no_symlink_path(site)
    for input_path in (package, approval):
        no_symlink_path(input_path)
        disjoint_paths(candidate, input_path)
    if registry and not isinstance(registry, bytes):
        no_symlink_path(registry)
    require(candidate != site and site not in candidate.parents and candidate not in site.parents, 'candidate must be disjoint from source')
    require(not candidate.exists() and not candidate.with_name(candidate.name + '.release').exists(), 'candidate destination already exists')
    candidate.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix='.release-preparing-', dir=candidate.parent))
    try:
        receipt = _prepare(package, approval, site, stage / 'site', synthetic, registry)
        atomic_json(stage / 'source-manifest.json', {'schema_version': 1, 'files': tree_manifest(site)})
        atomic_json(stage / 'approval.json', receipt)
        with zipfile.ZipFile(package) as archive:
            (stage / 'input-manifest.json').write_bytes(archive.read('manifest.json'))
        checks = run_checks(site, stage / 'site')
        files = tree_manifest(stage / 'site')
        archive_tree(stage / 'site', stage / 'site.zip')
        atomic_json(stage / 'manifest.json', {'schema_version': 1, 'files': files, 'checks': checks,
                                             'artifact_sha256': sha((stage / 'site.zip').read_bytes())})
        # Publish audit/artifact first, then candidate visibility in one final rename.
        # A crash can leave an orphan sidecar, never a visible candidate without its manifest.
        sidecar = candidate.with_name(candidate.name + '.release')
        os.replace(stage, sidecar)
        os.replace(sidecar / 'site', candidate)
        return receipt
    finally:
        if stage.exists():
            shutil.rmtree(stage)


def _prepare(package, approval, site, candidate, synthetic=False, registry=None):
    receipt = read_json(approval)
    require(type(receipt) is dict and set(receipt) == {'schema_version', 'mode', 'release_id', 'package_sha256', 'manifest_sha256', 'locale_profile', 'modules', 'attestations', 'signatures'}, 'receipt exact schema')
    if synthetic:
        require(receipt.get('mode') == 'SYNTHETIC', 'synthetic mode requires explicitly unpublishable receipt')
        trust_hash = None
    else:
        trust_hash = verify_authorization(receipt, registry)
    require(type(receipt.get('schema_version')) is int and receipt['schema_version'] == 1, 'receipt schema')
    require(bool(re.fullmatch(r'[a-z][a-z0-9-]{0,63}', receipt.get('release_id', ''))), 'invalid release ID')
    require(set(receipt['attestations']) == {'clinical-safety-reviewed', 'source-and-rights-reviewed'}, 'missing review attestations')
    require(receipt['locale_profile'] in ('en-only-trial', 'bilingual-production'), 'unknown locale profile')
    require(Path(package).stat().st_size <= 8 * 1024 * 1024, 'package exceeds size limit')
    require(receipt['package_sha256'] == sha(Path(package).read_bytes()), 'package hash mismatch')
    with zipfile.ZipFile(package) as archive:
        infos = archive.infolist()
        require(2 <= len(infos) <= 65, 'archive entry count')
        seen = set()
        for entry in infos:
            require(entry.filename == 'manifest.json' or bool(re.fullmatch(r'modules/[a-z][a-z0-9-]*\.json', entry.filename)), 'unsafe archive path')
            require(entry.filename.casefold() not in seen, 'archive name collision')
            seen.add(entry.filename.casefold())
            require((entry.external_attr >> 16) & 0o170000 in (0, 0o100000), 'archive symlink/nonregular entry')
            require(not entry.flag_bits & 1, 'encrypted archive')
            require(0 < entry.file_size <= 512 * 1024, 'archive entry size')
            require(entry.file_size / max(1, entry.compress_size) <= 100, 'archive compression ratio')
        require(sum(e.file_size for e in infos) <= 4 * 1024 * 1024, 'archive expanded size')
        manifest_raw = archive.read('manifest.json')
        require(receipt['manifest_sha256'] == sha(manifest_raw), 'manifest hash mismatch')
        manifest = parse_json(manifest_raw)
        require(set(manifest) == {'schema_version', 'files'} and type(manifest['schema_version']) is int and manifest['schema_version'] == 1, 'manifest schema')
        require(type(manifest['files']) is list and manifest['files'], 'empty manifest')
        paths = [e['path'] for e in manifest['files']]
        require(len(paths) == len(set(paths)) and set(paths) | {'manifest.json'} == set(e.filename for e in infos), 'manifest membership mismatch')
        modules = []
        identities = set()
        for entry in manifest['files']:
            require(set(entry) == {'path', 'sha256'}, 'manifest entry schema')
            raw = archive.read(entry['path'])
            require(sha(raw) == entry['sha256'], 'module hash mismatch')
            data = parse_json(raw)
            require(not validator.validate(data), 'invalid module schema')
            require('pfa' not in data['module_id'] and 'psychological-first-aid' not in data['module_id'], 'PFA content remains QC blocked')
            require(not data['open_questions'], 'unresolved content review')
            for text in walk_strings(data):
                for url in re.findall(r'[A-Za-z][A-Za-z0-9+.-]*://[^\s]+', text):
                    from urllib.parse import urlsplit
                    parsed = urlsplit(url)
                    require(parsed.scheme == 'https' and parsed.hostname in {'www.who.int', 'interagencystandingcommittee.org', 'www.mhpssmsp.org', 'spherestandards.org', 'campus.paho.org', 'whoacademy.org'} and not parsed.port and not parsed.username and not parsed.password and not parsed.query and not parsed.fragment, 'unsafe or nonallowlisted source URL')
            identity = (data['module_id'], data['content_version'], data['language'])
            require(identity not in identities, 'duplicate module identity')
            identities.add(identity)
            modules.append((data, raw))
        actual = sorted(({k: d[k] for k in ('module_id', 'content_version', 'language')} | {'sha256': sha(raw)} for d, raw in modules), key=lambda e: (e['module_id'], e['language']))
        require(sorted(receipt['modules'], key=lambda e: (e['module_id'], e['language'])) == actual, 'review binding mismatch')
        groups = {}
        for d, raw in modules:
            groups.setdefault((d['module_id'], d['content_version']), {})[d['language']] = d
        for locales in groups.values():
            if receipt['locale_profile'] == 'en-only-trial':
                require(set(locales) == {'en'}, 'English trial locale mismatch')
            else:
                require(set(locales) == {'en', 'ne'}, 'bilingual pair required')
                require(locales['ne']['translation_source_version'] == locales['en']['content_version'], 'translation source mismatch')
    copy_site(site, candidate)
    content = Path(candidate) / 'learn/content'
    content.mkdir(parents=True, exist_ok=True)
    catalogue_path = content / 'catalogue.json'
    catalogue = read_json(catalogue_path) if catalogue_path.exists() else {'schema_version': 1, 'modules': []}
    for data, raw in modules:
        rel = f"modules/{data['module_id']}/{data['content_version']}/{data['language']}.json"
        out = content / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        require(not out.exists() or out.read_bytes() == raw, 'immutable module version collision')
        out.write_bytes(raw)
        catalogue['modules'] = [e for e in catalogue['modules'] if (e['module_id'], e['language']) != (data['module_id'], data['language'])]
        catalogue['modules'].append({k: data[k] for k in ('module_id', 'content_version', 'language')} | {'path': rel, 'sha256': sha(raw)})
    catalogue['modules'].sort(key=lambda e: (e['module_id'], e['language']))
    atomic_json(catalogue_path, catalogue)
    atomic_json(Path(candidate) / 'learning-release.json', {'release_id': receipt['release_id'], 'synthetic': synthetic,
                'package_sha256': receipt['package_sha256'], 'manifest_sha256': receipt['manifest_sha256'],
                'trust_registry_sha256': trust_hash, 'approval_sha256': sha(Path(approval).read_bytes()),
                'locale_profile': receipt['locale_profile'], 'modules': receipt['modules']})
    return receipt


def archive_tree(root, output):
    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_STORED) as archive:
        for item in tree_manifest(root):
            info = zipfile.ZipInfo(item['path'], date_time=(1980, 1, 1, 0, 0, 0))
            info.external_attr = 0o100644 << 16
            archive.writestr(info, (Path(root) / item['path']).read_bytes())


def install_tree(source, target):
    """Fixture adapter only: durable pending state lets next invocation reconcile."""
    staging = target.with_name(target.name + '.staging')
    previous = target.with_name(target.name + '.previous')
    for p in (staging, previous):
        if p.exists():
            shutil.rmtree(p)
    shutil.copytree(source, staging)
    if target.exists():
        os.replace(target, previous)
    os.replace(staging, target)
    if previous.exists():
        shutil.rmtree(previous)


def commit_verified(state, result, previous):
    if previous:
        atomic_json(state / 'previous-good.json', previous)
    atomic_json(state / 'last-good.json', result)
    atomic_json(state / 'history' / (result['release_id'] + '.json'), result)
    (state / 'pending.json').unlink(missing_ok=True)


def restore(state, target, previous):
    if previous:
        source = state / 'releases' / previous['artifact_sha256'] / 'site'
        require(tree_manifest(source) == previous['files'], 'previous artifact corrupt; manual reconciliation required')
        install_tree(source, target)
        require(tree_manifest(target) == previous['files'], 'rollback readback failed')
    elif target.exists():
        shutil.rmtree(target)
    (state / 'pending.json').unlink(missing_ok=True)


def rollback(state, target):
    state, target = Path(state).resolve(), Path(target).resolve()
    with (state / 'lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        current = read_json(state / 'last-good.json')
        require(current['target'] == str(target), 'rollback target mismatch')
        require(tree_manifest(target) == current['files'], 'target drift; reconcile before rollback')
        require((state / 'previous-good.json').exists(), 'no previous verified artifact')
        previous = read_json(state / 'previous-good.json')
        restore(state, target, previous)
        atomic_json(state / 'last-good.json', previous)
        atomic_json(state / 'previous-good.json', current)
        return previous | {'status': 'rolled-back-verified'}


def publish(package, approval, site, state, target, synthetic=False, registry=None, failure=None):
    require(synthetic, 'private filesystem publish is synthetic only; production requires protected provider adapter')
    site, state, target = map(lambda p: Path(p).resolve(), (site, state, target))
    require(site != target and site not in target.parents and target not in site.parents, 'target must be disjoint from source')
    require(site != state and site not in state.parents and state not in site.parents, 'state must be disjoint from source')
    require(state != target and state not in target.parents and target not in state.parents, 'state and target must be disjoint')
    require(not target.is_symlink(), 'unsafe fixture target')
    state.mkdir(parents=True, exist_ok=True)
    with (state / 'lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        receipt = read_json(approval)
        require(receipt.get('mode') == 'SYNTHETIC', 'private fixture requires synthetic receipt')
        require(bool(re.fullmatch(r'[a-z][a-z0-9-]{0,63}', receipt.get('release_id', ''))), 'invalid release ID')
        current = read_json(state / 'last-good.json') if (state / 'last-good.json').exists() else None
        require(not current or current['target'] == str(target), 'state target mismatch')
        if (state / 'pending.json').exists():
            pending = read_json(state / 'pending.json')
            require(pending['target'] == str(target), 'pending target mismatch')
            if tree_manifest(target) == pending['files']:
                commit_verified(state, pending, current)
                if receipt['release_id'] == pending['release_id']:
                    require(pending['package_sha256'] == sha(Path(package).read_bytes()), 'release ID collision')
                    return pending | {'status': 'reconciled-verified'}
                current = pending
            elif current and tree_manifest(target) == current['files']:
                (state / 'pending.json').unlink()
            else:
                restore(state, target, current)
                raise ReleaseError('uncertain fixture effect reconciled by verified rollback; invoke again deliberately')
        if current:
            require(tree_manifest(target) == current['files'], 'target drift; reconcile required')
        else:
            require(not target.exists(), 'initial target must not exist; refuses to overwrite untracked content')
        history = state / 'history' / (receipt['release_id'] + '.json')
        if history.exists():
            prior = read_json(history)
            require(prior['package_sha256'] == sha(Path(package).read_bytes()), 'release ID collision')
            require(current and current['release_id'] == receipt['release_id'], 'release previously superseded; explicit rollback required')
            return current | {'status': 'already-verified'}
        work = Path(tempfile.mkdtemp(prefix='candidate-', dir=state))
        deployed = False
        try:
            candidate = work / 'site'
            # Updates start from last verified tree; all other topics and history remain.
            prepare(package, approval, state / 'releases' / current['artifact_sha256'] / 'site' if current else site,
                    candidate, synthetic, registry)
            require(failure != 'checks', 'injected fixture check failure')
            files = tree_manifest(candidate)
            archive_tree(candidate, work / 'site.zip')
            artifact_sha = sha((work / 'site.zip').read_bytes())
            artifact = state / 'releases' / artifact_sha
            if not artifact.exists():
                artifact.parent.mkdir(parents=True, exist_ok=True)
                os.replace(work, artifact)
                work = None
            else:
                require(tree_manifest(artifact / 'site') == files, 'artifact identity collision')
            result = {'status': 'verified', 'synthetic': True, 'release_id': receipt['release_id'],
                      'target': str(target), 'package_sha256': receipt['package_sha256'],
                      'manifest_sha256': receipt['manifest_sha256'], 'artifact_sha256': artifact_sha, 'files': files}
            atomic_json(state / 'pending.json', result)
            deployed = True
            install_tree(artifact / 'site', target)
            if failure == 'interrupt':
                raise KeyboardInterrupt('fixture interruption after side effect; pending state retained')
            require(failure != 'after-deploy', 'injected post-deploy failure')
            if failure == 'readback':
                (target / 'learning-release.json').write_text('corrupt readback fixture')
            require(tree_manifest(target) == files, 'readback mismatch')
            commit_verified(state, result, current)
            return result
        except Exception:
            if deployed:
                restore(state, target, current)
            raise
        finally:
            if work and work.exists():
                shutil.rmtree(work)


def github_plan(candidate, repository, base_url):
    """Offline protected-PR adapter. Deliberately never mutates GitHub/Pages."""
    from urllib.parse import urlsplit
    require(bool(re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repository)), 'invalid repository')
    parsed = urlsplit(base_url)
    require(parsed.scheme == 'https' and parsed.hostname and not parsed.username and not parsed.query and not parsed.fragment,
            'invalid exact readback URL')
    release = read_json(Path(candidate) / 'learning-release.json')
    require(release.get('synthetic') is False and release.get('trust_registry_sha256'), 'synthetic/untrusted artifacts cannot enter GitHub publish adapter')
    return {'adapter': 'github-protected-pr', 'status': 'prepared-not-deployed', 'repository': repository,
            'branch': 'learning-release/' + release['release_id'], 'base': 'main',
            'allowed_changes': ['learn/content/**', 'learning-release.json'],
            'required_checks': ['learning-release / checks'],
            'merge': {'method': 'squash', 'auto': True, 'force': False, 'direct_main_push': False,
                      'requires_provider_branch_rules': True},
            'publication': 'Existing legacy Pages main-root deployment only after protected PR merge; no hosting configuration change',
            'readback_url': base_url.rstrip('/') + '/learning-release.json',
            'release': release, 'authority_required': True,
            'remote_run': 'NOT RUN; apply via institutional broker with protected-main rules, app token, and exact-target readback'}


def github_artifacts(site, candidate, output, repository, base_url):
    """Exercise Git locally to prepare an applicable scoped patch; zero remote writes."""
    plan = github_plan(candidate, repository, base_url)
    site, candidate, output = map(Path, (site, candidate, output))
    require(not output.exists(), 'adapter output exists')
    output.mkdir(parents=True)
    scratch = Path(os.environ.get('TMPDIR', '/root/.hermes/cache/scratch'))
    with tempfile.TemporaryDirectory(prefix='github-adapter-', dir=scratch) as folder:
        folder = Path(folder)
        def git(*args):
            result = subprocess.run(['git', '-c', 'user.name=Learning release fixture', '-c', 'user.email=fixture@invalid',
                                     '-c', 'core.hooksPath=/dev/null', *args], cwd=folder, capture_output=True, timeout=30)
            require(result.returncode == 0, 'local Git adapter command failed')
            return result.stdout
        git('init', '-q')
        for rel in ('learn/content', 'learning-release.json'):
            src = site / rel
            dst = folder / rel
            if src.is_dir():
                shutil.copytree(src, dst)
            elif src.is_file():
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(src, dst)
        git('add', '.')
        git('commit', '-q', '--allow-empty', '-m', 'Fixture baseline; not production history')
        git('checkout', '-q', '-b', plan['branch'])
        for rel in ('learn/content', 'learning-release.json'):
            src = candidate / rel
            dst = folder / rel
            if dst.is_dir():
                shutil.rmtree(dst)
            elif dst.exists():
                dst.unlink()
            if src.is_dir():
                shutil.copytree(src, dst)
            else:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(src, dst)
        git('add', '.')
        patch = git('diff', '--cached', '--binary', '--full-index')
        require(bool(patch), 'empty release patch')
        (output / 'candidate.patch').write_bytes(patch)
        git('reset', '--hard', 'HEAD')
        checked = subprocess.run(['git', 'apply', '--check', str((output / 'candidate.patch').resolve())], cwd=folder, capture_output=True)
        require(checked.returncode == 0, 'candidate patch does not apply to baseline')
    atomic_json(output / 'provider-plan.json', plan | {'patch_sha256': sha(patch), 'local_git_apply_check': 'pass'})
    return plan


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=['publish', 'prepare', 'rollback', 'github-adapter', 'publish-github'])
    parser.add_argument('--policy', type=Path, help='independently pinned institutional provider policy')
    parser.add_argument('--execute-deployment', action='store_true', help='explicit authorization for protected feature PR and legacy Pages publication')
    for name in ('package', 'approval', 'site', 'state', 'target', 'candidate', 'registry', 'output'):
        parser.add_argument('--' + name, type=Path)
    parser.add_argument('--repository')
    parser.add_argument('--base-url')
    parser.add_argument('--synthetic', action='store_true')
    args = vars(parser.parse_args())
    operation = args.pop('operation')
    policy = args.pop('policy')
    execute = args.pop('execute_deployment')
    try:
        if operation == 'publish-github':
            from github_broker import Broker
            require(all(args[k] for k in ('package', 'approval', 'state', 'registry')) and policy,
                    '--package --approval --state --registry --policy required')
            require(not args['synthetic'], 'synthetic receipts cannot publish to GitHub')
            result = Broker(args['state'], read_json(policy), args['registry']).publish(
                args['package'], args['approval'], execute=execute)
        elif operation == 'rollback':
            require(args['state'] and args['target'], '--state and --target required')
            result = rollback(args['state'], args['target'])
        elif operation == 'github-adapter':
            require(all(args[k] for k in ('site', 'candidate', 'output', 'repository', 'base_url')), 'adapter arguments missing')
            result = github_artifacts(*(args[k] for k in ('site', 'candidate', 'output', 'repository', 'base_url')))
        else:
            require(all(args[k] for k in ('package', 'approval', 'site')), '--package --approval --site required')
            for key in ('output', 'repository', 'base_url'):
                args.pop(key)
            if operation == 'publish':
                args.pop('candidate')
                require(args['state'] and args['target'], '--state and --target required')
                result = publish(**args)
            else:
                args.pop('state'); args.pop('target')
                require(args['candidate'], '--candidate required')
                result = prepare(**args)
        print(json.dumps(result, sort_keys=True))
    except (ReleaseError, OSError, ValueError, KeyError, TypeError, zipfile.BadZipFile) as exc:
        print('REJECTED: ' + str(exc), file=sys.stderr)
        sys.exit(1)
