import unittest, sys, copy, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/learning-release'))
import validate_content as validator
FIXTURE=ROOT/'tests/fixtures/skill-loop-v2.fixture.mjs'
def fixture():
 raw=FIXTURE.read_text().split('export default ',1)[1].rsplit(';',1)[0]
 return json.loads(raw)
class Compatibility(unittest.TestCase):
 def test_draft_v2_supported_without_approving(self):
  d=fixture()
  self.assertEqual(validator.validate(d),[])
  d['approval']['status']='approved'
  self.assertTrue(validator.validate(d))
 def test_public_structure_distinct_and_assets_required(self):
  import public_package
  d=fixture();d['approval']['status']='approved'
  self.assertTrue(public_package.validate_public_structure(d,asset_root=ROOT/'tests/fixtures/skill-loop-v2/assets'))
  for s in d['scenes']:s['status']='approved'
  self.assertEqual(public_package.validate_public_structure(d,asset_root=ROOT/'tests/fixtures/skill-loop-v2/assets'),[])
  self.assertTrue(public_package.validate_public_structure(d,asset_root=ROOT/'missing-assets'))
  d['approval']['status']='draft'
  self.assertTrue(public_package.validate_public_structure(d,asset_root=ROOT/'tests/fixtures/skill-loop-v2/assets'))
 def test_public_authority_not_package_flags(self):
  import public_package
  raw=FIXTURE.read_bytes()
  with self.assertRaises(ValueError):public_package.validate_authorized_public(raw,receipt={},registry=None,asset_root=ROOT/'tests/fixtures/skill-loop-v2/assets')
if __name__=='__main__':unittest.main()
