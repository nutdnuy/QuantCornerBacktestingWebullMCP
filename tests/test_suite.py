"""Installation, migration and private cross-skill handoff integration tests."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import install, onboard, handoff

class SuiteTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = Path(install.__file__).resolve().parents[1]
        self.names = [install.CORE] + handoff.members()
    def test_fresh_install_all_nine_and_one_engine(self):
        core = install.install(self.root/'host')
        for name in self.names:
            self.assertTrue(install.declared_name(core.parent/name, name))
        self.assertEqual(len(list(core.parent.rglob('engine.py'))),1)
        self.assertEqual(len(list(core.parent.rglob('quantcorner-mark-light.svg'))),1)
    def test_webull_install_preserves_existing_efin_suite(self):
        host = self.root / 'host'
        old_names = ['quantcorner-backtesting-efin-mcp', 'ask-quantcorner',
                     'qc-setup', 'qc-design-strategy', 'qc-audit-data', 'qc-backtest',
                     'qc-validate', 'qc-explain-results', 'qc-report']
        for name in old_names:
            folder = host / name
            folder.mkdir(parents=True)
            (folder / 'SKILL.md').write_text('original ' + name)
        install.install(host)
        self.assertEqual(len(list(host.iterdir())), 18)
        for name in old_names:
            self.assertEqual((host / name / 'SKILL.md').read_text(), 'original ' + name)
    def test_public_checkout_layout(self):
        checkout=self.root/'checkout'
        install.copy_public(self.source,checkout,True)
        for name,source in install.sources(self.source).items():
            if name!=install.CORE:
                (checkout/'skills').mkdir(exist_ok=True)
                install.copy_public(source,checkout/'skills'/name)
        with patch.object(install,'__file__',str(checkout/'scripts/install.py')):
            core=install.install(self.root/'public-host')
        self.assertEqual(set(p.name for p in core.parent.iterdir()),set(self.names))
    def test_installed_suite_can_be_copied_elsewhere(self):
        core=install.install(self.root/'one')
        with patch.object(install,'__file__',str(core/'scripts/install.py')):
            second=install.install(self.root/'two')
        self.assertTrue((second.parent/'qc-webull-validate/SKILL.md').exists())
    def test_conflict_preflight_installs_nothing(self):
        host=self.root/'host';(host/'qc-webull-report').mkdir(parents=True)
        (host/'qc-webull-report/owner.txt').write_text('keep')
        with self.assertRaises(ValueError):install.install(host)
        self.assertEqual(sorted(p.name for p in host.iterdir()),['qc-webull-report'])
        self.assertEqual((host/'qc-webull-report/owner.txt').read_text(),'keep')
    def test_upgrade_preserves_customizations_in_backup(self):
        core=install.install(self.root/'host');(core/'private-owner.txt').write_text('private fixture')
        install.install(core.parent,upgrade=True)
        saved=list((core.parent/'.quantcorner-backups').glob('*/'+install.CORE+'/private-owner.txt'))
        self.assertEqual(len(saved),1);self.assertEqual(saved[0].read_text(),'private fixture')
        self.assertFalse((core/'private-owner.txt').exists())
    def test_upgrade_recognizes_legacy_core(self):
        host=self.root/'host';old=host/install.CORE;old.mkdir(parents=True)
        (old/'SKILL.md').write_text('---\nname: '+install.CORE+'\n---\nold')
        install.install(host,upgrade=True)
        self.assertTrue((host/'ask-quantcorner-webull/SKILL.md').exists())
        self.assertEqual(len(list((host/'.quantcorner-backups').glob('*/'+install.CORE+'/SKILL.md'))),1)
    def test_symlink_and_unrecognized_upgrade_refused(self):
        host=self.root/'host';host.mkdir();outside=self.root/'outside';outside.mkdir()
        (host/'qc-webull-report').symlink_to(outside,target_is_directory=True)
        with self.assertRaises(ValueError):install.install(host,upgrade=True)
        self.assertTrue((host/'qc-webull-report').is_symlink());self.assertEqual(list(outside.iterdir()),[])
        (host/'qc-webull-report').unlink();(host/'qc-webull-report').mkdir()
        with self.assertRaises(ValueError):install.install(host,upgrade=True)
        self.assertFalse((host/install.CORE).exists())
    def test_upgrade_publication_failure_rolls_back(self):
        core=install.install(self.root/'host');(core/'owner.txt').write_text('keep')
        original=Path.rename
        def fail_once(path,target):
            if '.quantcorner-stage-' in str(path) and path.name=='qc-webull-report':
                raise OSError('simulated publication failure')
            return original(path,target)
        with patch.object(Path,'rename',fail_once):
            with self.assertRaises(OSError):install.install(core.parent,upgrade=True)
        self.assertEqual((core/'owner.txt').read_text(),'keep')
        for name in self.names:self.assertTrue((core.parent/name/'SKILL.md').is_file())
    def test_handoff_resume_retains_context_and_history(self):
        w=self.root/'research';onboard.setup(w)
        (w/'CONTEXT.md').write_text('owner decisions')
        handoff.record(w,'qc-webull-design-strategy','ready','qc-webull-audit-data',['plan.json'],'agreed')
        onboard.setup(w)
        self.assertEqual((w/'CONTEXT.md').read_text(),'owner decisions')
        self.assertEqual(json.loads((w/'handoff.json').read_text())['next_skill'],'qc-webull-audit-data')
        self.assertEqual(len((w/'handoffs.jsonl').read_text().splitlines()),1)
        self.assertFalse(json.loads((w/'plan.json').read_text())['approved'])
    def test_existing_root_registry_adopted_not_replaced(self):
        w=self.root/'research';w.mkdir();(w/'trials.jsonl').write_text('legacy evidence')
        onboard.setup(w)
        self.assertEqual(handoff.load_project(w)['research_directory'],'.')
        self.assertEqual((w/'trials.jsonl').read_text(),'legacy evidence')
        self.assertFalse((w/'runs').exists())
    def test_two_existing_registries_require_resolution(self):
        w=self.root/'research';(w/'runs').mkdir(parents=True)
        (w/'trials.jsonl').write_text('a');(w/'runs/trials.jsonl').write_text('b')
        with self.assertRaises(ValueError):onboard.setup(w)
        self.assertFalse((w/'project.json').exists())
    def test_invalid_artifact_and_skill_do_not_change_handoff(self):
        w=self.root/'research';onboard.setup(w);before=(w/'handoff.json').read_bytes()
        for artifact in ['missing.json','../outside.json',str(w/'plan.json')]:
            with self.assertRaises(ValueError):handoff.record(w,'qc-webull-report','ready',None,[artifact],'x')
        with self.assertRaises(ValueError):handoff.record(w,'not-a-skill','ready',None,[],'x')
        self.assertEqual((w/'handoff.json').read_bytes(),before)
        self.assertFalse((w/'handoffs.jsonl').exists())
    def test_handoff_lock_retained(self):
        w=self.root/'research';onboard.setup(w);(w/'.handoff.lock').touch()
        with self.assertRaises(FileExistsError):handoff.record(w,'qc-webull-report','complete',None,[],'x')
        self.assertTrue((w/'.handoff.lock').exists())
    def test_installed_runtime_demo_and_cross_skill_handoff(self):
        core=install.install(self.root/'host');w=self.root/'project'
        def call(script,*args):
            subprocess.run([sys.executable,str(core/'scripts'/script),*map(str,args)],check=True,capture_output=True)
        call('onboard.py','--workspace',w)
        call('demo.py','--output',w/'demo')
        call('handoff.py','--workspace',w,'--skill','qc-webull-report','--status','complete','--artifact','demo/report.html','--note','Synthetic installation smoke test')
        self.assertEqual(json.loads((w/'handoff.json').read_text())['artifacts'],['demo/report.html'])
        self.assertIn('Synthetic demonstration',(w/'demo/report.html').read_text())

if __name__=='__main__':unittest.main()
