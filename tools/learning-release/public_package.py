"""Public interface adapter, distinct from draft validation. Flags are not authority.

validate_public_structure is NOT authorization. Parent release integration must call
validate_authorized_public with the already existing institution-bound signed receipt.
The browser additionally needs a reviewed exact-rendition executable release pin.
"""
import copy
import hashlib
import importlib.util
from pathlib import Path
HERE = Path(__file__).resolve().parent

def sibling(name):
    spec = importlib.util.spec_from_file_location('learning_public_' + name, HERE / (name + '.py'))
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def validate_public_structure(data, *, asset_root):
    """Validate approved public representation without relaxing draft validator."""
    if type(data) is not dict or type(data.get('approval')) is not dict or data['approval'].get('status') != 'approved':
        return ['public package requires approved authoring disposition; not authority']
    projected = copy.deepcopy(data)
    projected['approval']['status'] = 'in-review'
    return sibling('validate_content').validate(projected, mode='release', asset_root=asset_root, check_assets=True)

def validate_authorized_public(raw, *, receipt, registry, asset_root):
    """Fail before acceptance without genuine receipt/registry and exact byte binding."""
    release = sibling('release')
    release.verify_authorization(receipt, registry)
    data = release.parse_json(raw)
    errors = validate_public_structure(data, asset_root=asset_root)
    if errors:
        raise ValueError('; '.join(errors))
    identity = {k: data[k] for k in ('module_id', 'content_version', 'language')}
    identity['sha256'] = hashlib.sha256(raw).hexdigest()
    if not any(row == identity for row in receipt['modules']):
        raise ValueError('signed receipt does not bind exact public rendition')
    return data
