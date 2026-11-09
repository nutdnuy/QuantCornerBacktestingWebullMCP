import copy
import importlib.util
from pathlib import Path
import tempfile
import unittest

SPEC=importlib.util.spec_from_file_location('report',Path(__file__).resolve().parents[1]/'scripts'/'report.py')
report=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(report)

class ReportTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.assets=Path(self.temp.name)
        (self.assets/'quantcorner-mark-light.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"><path d="M0 0L10 10"/></svg>')
        self.data={'equity':[{'date':'2025-01-02','equity':100.,'benchmark_equity':100.,'drawdown':0.},{'date':'2025-01-03','equity':90.,'benchmark_equity':95.,'drawdown':-.1}], 'metrics':{'total_return':-.1,'max_drawdown':-.1,'closed_trades':0,'sharpe':None},'config':{'currency':'USD'},'trades':[]}
    def render(self, data=None, **kwargs):return report.render_report(data or self.data,asset_dir=self.assets,**kwargs)
    def test_provenance_and_units(self):
        page=self.render()
        for value in ['Data provenance unknown','Portfolio value (USD)','Drawdown (%)','N/A','−20%','0 observed']:
            if value != '0 observed':self.assertIn(value,page)
        self.assertNotIn('<script',page)
        self.assertNotIn('https://',page)
        self.assertIn('No closed trades',page)
    def test_synthetic_disclosure(self):
        self.data['provenance']={'data_kind':'synthetic','source':'deterministic fixture'}
        page=self.render();self.assertIn('Synthetic demonstration — not Webull market data',page)
    def test_escaping(self):
        payload='</script><img src="https://attacker.test" onerror="alert(1)">'
        self.data['provenance']={'data_kind':'unknown','source':payload}
        self.data['warnings']=[payload]
        page=self.render(title=payload)
        self.assertNotIn(payload,page)
        self.assertIn('&lt;/script&gt;',page)
        self.assertNotIn('<img src="https://attacker.test"',page)
    def test_constant_and_single_series(self):
        self.data['equity']=self.data['equity'][:1]
        self.assertIn('<circle',self.render())
        self.data['equity'].append(dict(self.data['equity'][0],date='2025-01-03'))
        self.assertIn('<polyline',self.render())
    def test_bad_series_rejected(self):
        for rows in [[],list(reversed(self.data['equity'])),[dict(self.data['equity'][0],equity=float('nan'))],[dict(self.data['equity'][0],drawdown=1)]]:
            data=copy.deepcopy(self.data);data['equity']=rows
            with self.assertRaises(ValueError):self.render(data)
    def test_bad_metric_rejected(self):
        self.data['metrics']['sharpe']=float('inf')
        with self.assertRaises(ValueError):self.render()
    def test_embedded_font_weights_are_distinct(self):
        fonts=self.assets/'fonts';fonts.mkdir()
        (fonts/'roboto-400.woff2').write_bytes(b'regular')
        (fonts/'roboto-600.woff2').write_bytes(b'semibold')
        page=self.render()
        self.assertIn('font-weight:400;font-display:swap',page)
        self.assertIn('font-weight:600;font-display:swap',page)
    def test_responsive_chart_and_visible_metric_labels(self):
        page=self.render()
        self.assertEqual(page.count('class="chart-compact"'),2)
        self.assertEqual(page.count('class="chart-wide"'),2)
        self.assertIn('data-label="Benchmark"',page)
        self.assertIn('text-anchor="end" class="axis-label">2025-01-03',page)
        self.assertIn('k = thousand',page)
    def test_research_record_visible(self):
        self.data['research']={'phase':'development','trial_id':'trial-01'}
        page=self.render()
        self.assertIn('Research record',page)
        self.assertIn('trial-01',page)
    def test_missing_logo_rejected(self):
        (self.assets/'quantcorner-mark-light.svg').unlink()
        with self.assertRaises(ValueError):self.render()

if __name__=='__main__':unittest.main()
