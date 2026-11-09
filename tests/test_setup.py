import json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import install,onboard

class SetupTests(unittest.TestCase):
    def test_onboarding_preserves_existing_and_does_not_claim_webull(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            state=onboard.setup(root)
            self.assertEqual(state['webull_connection'],'not_checked')
            self.assertFalse(json.loads((root/'plan.json').read_text())['approved'])
            (root/'plan.json').write_text('{"owner_edit":true}')
            onboard.setup(root)
            self.assertEqual(json.loads((root/'plan.json').read_text()),{'owner_edit':True})
            self.assertEqual((root/'.gitignore').read_text(),'*\n')
    def test_install_is_portable_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            target=install.install(d)
            self.assertTrue((target/'SKILL.md').is_file())
            self.assertTrue((target/'assets/quantcorner-mark-light.svg').is_file())
            self.assertTrue((target/'scripts/engine.py').is_file())
            self.assertFalse((target/'.git').exists())
            with self.assertRaises(ValueError):install.install(d)
    def test_installer_excludes_arbitrary_local_files(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'source';(root/'scripts').mkdir(parents=True)
            (root/'SKILL.md').write_text('public')
            (root/'.env').write_text('private fixture')
            (root/'private.csv').write_text('private fixture')
            (root/'scripts/cache.json').write_text('private fixture')
            (root/'scripts/tool.py').write_text('pass')
            outside=Path(d)/'outside.py';outside.write_text('private fixture')
            (root/'scripts/linked.py').symlink_to(outside)
            with patch.object(install,'__file__',str(root/'scripts/install.py')):
                target=install.install(Path(d)/'host')
            self.assertEqual(sorted(str(p.relative_to(target)) for p in target.rglob('*') if p.is_file()),['SKILL.md','scripts/tool.py'])

if __name__=='__main__':unittest.main()
