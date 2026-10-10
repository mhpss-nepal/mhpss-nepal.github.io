#!/usr/bin/env python3
"""Draft structure checks only. Never a publication or clinical approval gate."""
from pathlib import Path
import argparse
import copy
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
SLUG = re.compile(r'^[a-z][a-z0-9-]*$')
VERSION = re.compile(r'^\d+\.\d+\.\d+$')
BAD_TEXT = re.compile(r'<[^>]*>|(?:javascript|data|vbscript)\s*:', re.I)
BLOCKS = {'text', 'steps', 'example', 'safety', 'reflection', 'job_aid', 'external_resource'}


def validate(data):
    errors = []

    def check(ok, location, message):
        if not ok:
            errors.append(f'{location}: {message}')
        return ok

    def obj(value, keys, location):
        if not check(type(value) is dict, location, 'must be an object'):
            return False
        return check(set(value) == set(keys.split()), location,
                     'keys must be exactly: ' + keys)

    def text(value, location):
        return check(type(value) is str and bool(value.strip()) and not BAD_TEXT.search(value),
                     location, 'must be nonempty plain text without HTML or executable URI schemes')

    def slug(value, location):
        return check(type(value) is str and bool(SLUG.fullmatch(value)), location, 'invalid stable ID')

    def array(value, location, required=True):
        return check(type(value) is list and (not required or len(value) > 0), location,
                     'must be a list' + (' with at least one item' if required else ''))

    def strings(value, location, required=True):
        if array(value, location, required):
            for i, item in enumerate(value):
                text(item, f'{location}[{i}]')

    def minutes(value, location):
        check(type(value) is int and value > 0, location, 'must be a positive integer (not boolean)')

    def unique(ids, location):
        check(len(ids) == len(set(ids)), location, 'duplicate IDs')

    top = ('schema_version module_id content_version language translation_source_version title audience '
           'objectives scope_limits prerequisites estimated_minutes approval sources lessons questions '
           'completion_policy job_aids open_questions')
    if not obj(data, top, '$'):
        return errors
    check(type(data['schema_version']) is int and data['schema_version'] == 1, 'schema_version', 'must be integer 1')
    slug(data['module_id'], 'module_id')
    check(type(data['content_version']) is str and bool(VERSION.fullmatch(data['content_version'])), 'content_version', 'expected x.y.z')
    check(data['language'] in ('en', 'ne'), 'language', 'must be en or ne')
    if data['language'] == 'en':
        check(data['translation_source_version'] is None, 'translation_source_version', 'English must use null')
    else:
        check(type(data['translation_source_version']) is str and bool(VERSION.fullmatch(data['translation_source_version'])),
              'translation_source_version', 'Nepali must name the English source version')
    text(data['title'], 'title')
    for key in ('audience', 'objectives', 'scope_limits'):
        strings(data[key], key)
    for key in ('prerequisites', 'open_questions'):
        strings(data[key], key, False)
    minutes(data['estimated_minutes'], 'estimated_minutes')
    ap = data['approval']
    if obj(ap, 'status technical_reviewer language_reviewer approver review_due', 'approval'):
        check(ap['status'] in ('draft', 'in-review'), 'approval.status', 'draft/in-review only; this tool cannot approve releases')
        for key in ('technical_reviewer', 'language_reviewer', 'approver', 'review_due'):
            if ap[key] is not None:
                text(ap[key], 'approval.' + key)
        if ap['review_due'] is not None:
            check(bool(re.fullmatch(r'\d{4}-\d{2}-\d{2}', str(ap['review_due']))), 'approval.review_due', 'expected YYYY-MM-DD; validity needs review')

    source_ids = []
    if array(data['sources'], 'sources'):
        for i, source in enumerate(data['sources']):
            loc = f'sources[{i}]'
            if obj(source, 'source_id title edition reference location rights', loc):
                if slug(source['source_id'], loc + '.source_id'):
                    source_ids.append(source['source_id'])
                for key in ('title', 'edition', 'reference', 'location', 'rights'):
                    text(source[key], loc + '.' + key)
    unique(source_ids, 'sources')

    def refs(value, location):
        if array(value, location):
            for ref in value:
                if slug(ref, location):
                    check(ref in source_ids, location, 'unknown source ID: ' + ref)
            if all(type(x) is str for x in value):
                unique(value, location)

    lesson_ids = []
    if array(data['lessons'], 'lessons'):
        for i, lesson in enumerate(data['lessons']):
            loc = f'lessons[{i}]'
            if not obj(lesson, 'lesson_id title objective estimated_minutes blocks', loc):
                continue
            if slug(lesson['lesson_id'], loc + '.lesson_id'):
                lesson_ids.append(lesson['lesson_id'])
            for key in ('title', 'objective'):
                text(lesson[key], loc + '.' + key)
            check(type(data['objectives']) is list and lesson['objective'] in data['objectives'], loc + '.objective', 'must match a declared objective')
            minutes(lesson['estimated_minutes'], loc + '.estimated_minutes')
            if array(lesson['blocks'], loc + '.blocks'):
                for j, block in enumerate(lesson['blocks']):
                    b = f'{loc}.blocks[{j}]'
                    if obj(block, 'type body source_ids', b):
                        check(type(block['type']) is str and block['type'] in BLOCKS, b + '.type', 'unsupported block type')
                        text(block['body'], b + '.body')
                        refs(block['source_ids'], b + '.source_ids')
    unique(lesson_ids, 'lessons')

    qids = []
    if array(data['questions'], 'questions'):
        for i, question in enumerate(data['questions']):
            loc = f'questions[{i}]'
            if not obj(question, 'question_id objective prompt options correct_option_id source_ids', loc):
                continue
            if slug(question['question_id'], loc + '.question_id'):
                qids.append(question['question_id'])
            text(question['objective'], loc + '.objective')
            check(type(data['objectives']) is list and question['objective'] in data['objectives'], loc + '.objective', 'must match a declared objective')
            text(question['prompt'], loc + '.prompt')
            ids = []
            if array(question['options'], loc + '.options'):
                check(len(question['options']) >= 2, loc + '.options', 'at least two options required')
                for j, option in enumerate(question['options']):
                    o = f'{loc}.options[{j}]'
                    if obj(option, 'option_id text rationale', o):
                        if slug(option['option_id'], o + '.option_id'):
                            ids.append(option['option_id'])
                        text(option['text'], o + '.text')
                        text(option['rationale'], o + '.rationale')
            unique(ids, loc + '.options')
            check(type(question['correct_option_id']) is str and question['correct_option_id'] in ids,
                  loc + '.correct_option_id', 'must name exactly one existing option')
            refs(question['source_ids'], loc + '.source_ids')
    unique(qids, 'questions')

    policy = data['completion_policy']
    if obj(policy, 'mode required_lesson_ids pass_percent', 'completion_policy'):
        check(policy['mode'] == 'formative_trial', 'completion_policy.mode', 'only formative_trial supported')
        check(policy['pass_percent'] is None, 'completion_policy.pass_percent', 'trial pass mark must remain null')
        if array(policy['required_lesson_ids'], 'completion_policy.required_lesson_ids'):
            valid = []
            for item in policy['required_lesson_ids']:
                if slug(item, 'completion_policy.required_lesson_ids'):
                    valid.append(item)
                    check(item in lesson_ids, 'completion_policy.required_lesson_ids', 'unknown lesson: ' + item)
            unique(valid, 'completion_policy.required_lesson_ids')

    aids = []
    if array(data['job_aids'], 'job_aids'):
        for i, aid in enumerate(data['job_aids']):
            loc = f'job_aids[{i}]'
            if obj(aid, 'aid_id title body source_ids', loc):
                if slug(aid['aid_id'], loc + '.aid_id'):
                    aids.append(aid['aid_id'])
                text(aid['title'], loc + '.title')
                text(aid['body'], loc + '.body')
                refs(aid['source_ids'], loc + '.source_ids')
    unique(aids, 'job_aids')
    return errors


def self_test():
    sample = json.loads((Path(__file__).resolve().parent / 'module.template.json').read_text())
    assert not validate(sample), validate(sample)
    tests = [
        ('boolean schema version', lambda x: x.update(schema_version=True)),
        ('unknown top-level field', lambda x: x.update(secret='x')),
        ('claimed approval', lambda x: x['approval'].update(status='approved')),
        ('script body', lambda x: x['lessons'][0]['blocks'][0].update(body='<script>alert(1)</script>')),
        ('executable URI', lambda x: x['sources'][0].update(reference='javascript:alert(1)')),
        ('unknown source', lambda x: x['questions'][0].update(source_ids=['missing'])),
        ('unknown correct answer', lambda x: x['questions'][0].update(correct_option_id='z')),
        ('duplicate option', lambda x: x['questions'][0]['options'].append(copy.deepcopy(x['questions'][0]['options'][0]))),
        ('duplicate lesson', lambda x: x['lessons'].append(copy.deepcopy(x['lessons'][0]))),
        ('unknown required lesson', lambda x: x['completion_policy'].update(required_lesson_ids=['missing'])),
        ('invented trial pass mark', lambda x: x['completion_policy'].update(pass_percent=80)),
        ('Nepali without source version', lambda x: x.update(language='ne')),
        ('unsupported block', lambda x: x['lessons'][0]['blocks'][0].update(type='iframe')),
        ('boolean effort', lambda x: x.update(estimated_minutes=True)),
        ('objective mismatch', lambda x: x['questions'][0].update(objective='unknown')),
        ('missing rationale', lambda x: x['questions'][0]['options'][0].pop('rationale')),
        ('non-object root', lambda x: None),
    ]
    passed = 1
    for name, mutate in tests:
        candidate = copy.deepcopy(sample)
        mutate(candidate)
        if name == 'non-object root':
            candidate = []
        assert validate(candidate), name + ' unexpectedly accepted'
        passed += 1
    print(f'PASS: {passed} synthetic checks (valid template + {len(tests)} rejected mutations). Not clinical or application acceptance.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('files', nargs='*')
    parser.add_argument('--self-test', action='store_true')
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    files = [Path(p) for p in args.files] if args.files else sorted((ROOT / 'content/modules').rglob('*.json'))
    if not files:
        print('INFO: no module JSON packages yet. No completed modules are claimed. Use --self-test to test the validator.')
        return 0
    failed = 0
    seen = set()
    for path in files:
        try:
            data = json.loads(path.read_text())
            errors = validate(data)
            if type(data) is dict and type(data.get('module_id')) is str:
                identity = (data['module_id'], data.get('content_version'), data.get('language'))
                if all(type(x) is str for x in identity):
                    if identity in seen:
                        errors.append('duplicate module/revision/language package in input files')
                    seen.add(identity)
        except (OSError, ValueError, TypeError) as exc:
            errors = [str(exc)]
        if errors:
            failed += 1
            print('FAIL:', path)
            for error in errors:
                print(' -', error)
        else:
            print('PASS draft structure only:', path)
    print(f'Checked {len(files)} package(s); failed {failed}. No publication, clinical, language or rights approval implied.')
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
