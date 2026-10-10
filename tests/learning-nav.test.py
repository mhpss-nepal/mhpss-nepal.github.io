import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class LearningNav(unittest.TestCase):
 def test_all_current_root_pages_link_learning(self):
  for name in ['index.html','flood-response.html','iec.html','referral-directory.html','resources.html','videos.html','contact-us.html']:
   with self.subTest(name=name):
    self.assertIn('href="learn/"',(ROOT/name).read_text())
 def test_dictionary_has_learning_key_in_both_languages(self):
  text=(ROOT/'assets/i18n-strings.js').read_text()
  self.assertEqual(text.count('"nav.band.learning":'),2)
 def test_existing_public_copy_not_changed(self):
  import subprocess,re
  for name in ['index.html','referral-directory.html','resources.html']:
   baseline=subprocess.check_output(['git','show','HEAD:'+name],cwd=ROOT,text=True)
   strip=lambda s:re.sub(r'<!--NAV:(top|foot|help) [a-z0-9]+-->.*?<!--/NAV-->','',s,flags=re.S)
   self.assertEqual(strip(baseline),strip((ROOT/name).read_text()))
if __name__=='__main__':unittest.main()
