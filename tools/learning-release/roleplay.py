#!/usr/bin/env python3
"""One operation: synthetic new-topic -> update -> exact rollback, private filesystem only."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import zipfile

from release import atomic_json, canonical, publish, require, rollback, sha, tree_manifest

HERE = Path(__file__).resolve().parent


def package(output, version):
    data = json.loads((HERE / 'synthetic.module.json').read_text())
    data['content_version'] = version
    raw = canonical(data)
    manifest_raw = canonical({'schema_version': 1, 'files': [{'path': 'modules/navigation.json', 'sha256': sha(raw)}]})
    archive = output / ('approved-SYNTHETIC-' + version + '.zip')
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_STORED) as z:
        for name, content in (('manifest.json', manifest_raw), ('modules/navigation.json', raw)):
            info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            info.external_attr = 0o100644 << 16
            z.writestr(info, content)
    receipt = {'schema_version': 1, 'mode': 'SYNTHETIC', 'release_id': 'synthetic-navigation-' + version.replace('.', '-'),
               'package_sha256': sha(archive.read_bytes()), 'manifest_sha256': sha(manifest_raw),
               'locale_profile': 'en-only-trial',
               'modules': [{k: data[k] for k in ('module_id', 'content_version', 'language')} | {'sha256': sha(raw)}],
               'attestations': ['clinical-safety-reviewed', 'source-and-rights-reviewed'], 'signatures': []}
    review = output / ('SYNTHETIC-review-' + version + '.json')
    atomic_json(review, receipt)
    return archive, review


def run(site, output):
    site, output = Path(site).resolve(), Path(output).resolve()
    require(not output.exists(), 'roleplay output must be new; never overwrites evidence')
    require(site not in output.parents and output not in site.parents and site != output, 'output must be disjoint from site')
    output.mkdir(parents=True, mode=0o700)
    # Freeze the candidate once: other workers may be editing its UI concurrently.
    from release import copy_site
    input_site = site
    site = output / 'source-snapshot'
    copy_site(input_site, site)
    original = tree_manifest(site)
    state, target = output / 'state', output / 'private-deployment'
    archive, review = package(output, '1.0.0')
    first = publish(archive, review, site, state, target, synthetic=True)
    duplicate = publish(archive, review, site, state, target, synthetic=True)
    catalogue = json.loads((target / 'learn/content/catalogue.json').read_text())
    first_bytes = tree_manifest(target)
    archive2, review2 = package(output, '1.0.1')
    second = publish(archive2, review2, site, state, target, synthetic=True)
    require(tree_manifest(target) != first_bytes, 'update must change target bytes')
    rolled = rollback(state, target)
    require(tree_manifest(target) == first_bytes, 'rollback did not restore exact bytes')
    require(tree_manifest(site) == original, 'source site changed')
    data = json.loads((target / 'learn/content' / catalogue['modules'][0]['path']).read_text())
    report = {'mode': 'SYNTHETIC PRIVATE FILESYSTEM ROLEPLAY; NOT MINISTRY APPROVAL',
              'provider_deployment': 'NOT RUN', 'first_release': first['release_id'], 'first_artifact_sha256': first['artifact_sha256'],
              'updated_release': second['release_id'], 'updated_artifact_sha256': second['artifact_sha256'],
              'duplicate_status': duplicate['status'], 'rollback_status': rolled['status'], 'rollback_exact_bytes': True,
              'source_unchanged': True, 'target_file_count': len(first_bytes),
              'target_total_bytes': sum(item['bytes'] for item in first_bytes),
              'catalogue_modules': len(catalogue['modules']), 'lessons': len(data['lessons']), 'quiz_questions': len(data['questions']),
              'first_target_manifest_sha256': sha(canonical(first_bytes)), 'target': str(target)}
    atomic_json(output / 'report.json', report)
    print(json.dumps(report, sort_keys=True, indent=2))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--site', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    run(args.site, args.output)
