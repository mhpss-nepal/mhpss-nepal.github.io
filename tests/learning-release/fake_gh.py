#!/usr/bin/env python3
"""Deterministic OFFLINE GitHub API process fixture. Never contacts a network."""
import base64
import hashlib
import json
from pathlib import Path
import sys

path = Path(sys.argv[1])
args = sys.argv[2:]
data = json.loads(path.read_text())
assert args[0] == 'api', args
method = args[args.index('--method') + 1] if '--method' in args else 'GET'
endpoint = args[1].split('repos/fixture/site/', 1)[-1]
payload = json.loads(sys.stdin.read()) if '--input' in args else {}
data['calls'].append(method + ' ' + endpoint)
result = None
fail = False

def oid(value):
    return hashlib.sha1(json.dumps(value, sort_keys=True).encode()).hexdigest()

def tree(files):
    entries = []
    for name, content in sorted(files.items()):
        blob = oid(content)
        data['blobs'][blob] = content
        entries.append({'path': name, 'mode': '100644', 'type': 'blob', 'sha': blob, 'size': len(base64.b64decode(content))})
    return {'sha': oid(entries), 'tree': entries, 'truncated': False}

if endpoint == 'branches/main/protection':
    result = {'required_pull_request_reviews': {'required_approving_review_count': 0},
              'required_status_checks': {'strict': True, 'contexts': ['fixture-dynamic-check']}, 'enforce_admins': {'enabled': True}}
elif endpoint == 'pages':
    result = {'build_type': 'legacy', 'source': {'branch': 'main', 'path': '/'}, 'html_url': 'https://fixture.invalid/'}
elif endpoint == 'git/ref/heads/main':
    result = {'object': {'sha': data['main']}}
elif endpoint.startswith('git/ref/heads/'):
    name = endpoint.removeprefix('git/ref/heads/')
    result = {'object': {'sha': data['refs'][name]}} if name in data['refs'] else None
    if result is None:
        fail = True
elif endpoint.startswith('git/commits/'):
    commit = endpoint.split('/')[-1]
    if commit not in data['commits']:
        initial = tree(data['files'])
        data.setdefault('trees', {})[initial['sha']] = initial
        data['commits'][commit] = {'sha': commit, 'tree': {'sha': initial['sha']}, 'parents': []}
    result = data['commits'][commit]
elif endpoint.startswith('git/trees/'):
    value = endpoint.split('/')[-1].split('?')[0]
    if value in data.get('trees', {}):
        result = data['trees'][value]
    else:
        result = tree(data['files'])
elif endpoint.startswith('git/blobs/'):
    result = {'encoding': 'base64', 'content': data['blobs'][endpoint.split('/')[-1]]}
elif endpoint == 'git/blobs':
    blob = oid(payload['content'])
    data['blobs'][blob] = payload['content']
    result = {'sha': blob}
elif endpoint == 'git/trees':
    current = {x['path']: x for x in tree(data['files'])['tree']}
    for item in payload['tree']:
        if item['sha'] is None:
            current.pop(item['path'], None)
        else:
            current[item['path']] = item
    result = {'tree': list(current.values()), 'truncated': False}
    result['sha'] = oid(result)
    data.setdefault('trees', {})[result['sha']] = result
elif endpoint == 'git/commits':
    result = {'sha': oid(payload), 'tree': {'sha': payload['tree']}, 'parents': [{'sha': s} for s in payload['parents']]}
    data['commits'][result['sha']] = result
    if data['fault'] == 'ambiguous-commit':
        data['fault'] = ''
        fail = True
elif endpoint == 'git/refs':
    name = payload['ref'].removeprefix('refs/heads/')
    data['refs'][name] = payload['sha']
    result = {'object': {'sha': payload['sha']}}
    if data['fault'] == 'drift':
        data['main'] = 'd' * 40
elif endpoint.startswith('pulls?'):
    from urllib.parse import parse_qs
    q = parse_qs(endpoint.split('?')[1])
    head = q['head'][0].split(':', 1)[1]
    result = [p for p in data['prs'] if p['head']['ref'] == head]
elif endpoint == 'pulls':
    number = len(data['prs']) + 1
    result = {'number': number, 'state': 'open', 'merged': False, 'merge_commit_sha': None,
              'head': {'sha': data['refs'][payload['head']], 'ref': payload['head'], 'repo': {'full_name': 'fixture/site'}},
              'base': {'sha': data['main'], 'ref': 'main', 'repo': {'full_name': 'fixture/site'}}, 'body': payload['body']}
    data['prs'].append(result)
    if data['fault'] == 'ambiguous-pr':
        data['fault'] = ''
        fail = True
elif endpoint.startswith('pulls/') and endpoint.endswith('/merge'):
    pr = data['prs'][int(endpoint.split('/')[1]) - 1]
    if data['fault'] != 'merge-pending':
        pr['merged'] = True
        pr['state'] = 'closed'
        pr['merge_commit_sha'] = pr['head']['sha']
        data['main'] = pr['head']['sha']
        entries = data['trees'][data['commits'][data['main']]['tree']['sha']]['tree']
        data['files'] = {e['path']: data['blobs'][e['sha']] for e in entries}
    result = {'merged': pr['merged'], 'sha': pr['merge_commit_sha']}
elif endpoint.startswith('pulls/'):
    result = data['prs'][int(endpoint.split('/')[1]) - 1]
elif endpoint.startswith('commits/') and endpoint.endswith('/check-runs?per_page=100'):
    result = {'total_count': 1, 'check_runs': [{'name': 'fixture-dynamic-check', 'status': 'completed',
               'conclusion': 'failure' if data['fault'] == 'checks' else 'success'}]}
elif endpoint.startswith('commits/') and endpoint.endswith('/status?per_page=100'):
    result = {'total_count': 0, 'statuses': [], 'state': 'pending'}
elif endpoint == 'pages/builds' and method == 'POST':
    result = {'url': 'fixture', 'status': 'queued'}
    data['builds'].insert(0, {'commit': data['main'], 'status': 'errored' if data['fault'] in ('pages', 'pages-once', 'pages-once-rollback-merge-pending') else 'built',
                           'error': {'message': 'fixture failure' if data['fault'] in ('pages', 'pages-once') else None}})
    if data['fault'] == 'pages-once':
        data['fault'] = ''
    elif data['fault'] == 'pages-once-rollback-merge-pending':
        data['fault'] = 'merge-pending'
    elif data['fault'] == 'ambiguous-pages':
        data['fault'] = ''
        fail = True
elif endpoint == 'pages/builds?per_page=100':
    result = data['builds']
else:
    raise AssertionError((method, endpoint, payload))
path.write_text(json.dumps(data))
if fail:
    print('gh: fixture ambiguous response' if result else 'gh: Not Found (HTTP 404)', file=sys.stderr)
    sys.exit(1)
print(json.dumps(result))
