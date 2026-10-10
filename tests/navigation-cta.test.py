import unittest,importlib.util,re,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('site_nav',ROOT/'tools/nav.py')
assert spec is not None and spec.loader is not None
nav=importlib.util.module_from_spec(spec);spec.loader.exec_module(nav)
class NavigationCTA(unittest.TestCase):
 def test_order_and_grouping(self):
  self.assertEqual([r[0] for r in nav.NAV],['home','contact','flood','iec','referral','resources','videos','learning'])
  html=nav.top_block('referral')
  self.assertIn('class="nav-middle"',html)
  self.assertIn('class="nav-home"',html)
  self.assertIn('class="nav-learning"',html)
  self.assertIn('aria-hidden="true"',html)
  self.assertEqual(html.count('href="learn/"'),1)
  self.assertIn('class="on" aria-current="page" href="referral-directory.html"',html)
 def test_old_content_outside_topnav_unchanged(self):
  for rel,_ in nav.pages():
   before=subprocess.check_output(['git','show','1dbf25fe7f16c8bebde97819fba848f5897cc2f6:'+rel],cwd=ROOT,text=True)
   strip=lambda s:re.sub(r'<!--NAV:top [a-z0-9]+-->.*?<!--/NAV-->','',s,flags=re.S)
   self.assertEqual(strip(before),strip((ROOT/rel).read_text()),rel)
 def test_learning_engine_unchanged(self):
  for rel in ['learn/assets/engine.js','learn/content/catalogue.json','assets/i18n-strings.js']:
   self.assertEqual(subprocess.check_output(['git','show','1dbf25fe7f16c8bebde97819fba848f5897cc2f6:'+rel],cwd=ROOT),(ROOT/rel).read_bytes())
if __name__=='__main__':unittest.main()
