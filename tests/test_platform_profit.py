import copy,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import inventory_engine as E
import inventory_ui as U
import price_monitor as M
class PlatformProfitTests(unittest.TestCase):
 def setUp(self):
  self.app=object.__new__(type('Prices',(),{}));self.app.data={'profitRate':25,'digiFees':M.FEES};self.app.target=lambda p,c=None:E.channel_target(self.app.data,p,c) if c else E.target(self.app.data,p)
  self.p={'purchasePrice':1000000,'commission':7,'platformRate':8,'basalamCommission':9,'platformProfitOverrides':{'digikala':{'rate':10},'arazman':{'rate':20},'basalam':{'rate':30}}}
 def test_three_independent_targets(self):
  self.assertEqual([E.channel_target(self.app.data,self.p,c) for c in ['digikala','arazman','basalam']],[1100000,1200000,1300000]);self.assertEqual(E.target(self.app.data,self.p),1250000)
 def test_credit_uses_platform_target(self):
  for mode in ['cash','credit']:
   price=U.settlement_price(self.app,vars(M),self.p,'digikala',mode);rate=8 if mode=='credit' else 0
   self.assertLessEqual(abs(M.net(price,7,rate,M.FEES)-1100000),2)
 def test_amount_and_inheritance(self):
  self.p['platformProfitOverrides']['digikala']={'amount':1400000};self.assertAlmostEqual(E.channel_rate(self.app.data,self.p,'digikala'),40)
  self.p['purchasePrice']=1200000;self.assertEqual(E.channel_target(self.app.data,self.p,'digikala'),1400000);self.assertEqual(E.channel_target(self.app.data,self.p,'arazman'),1440000)
  self.p['platformProfitOverrides'].pop('basalam');self.p['profitRateOverride']=15;self.assertEqual(E.channel_target(self.app.data,self.p,'basalam'),1380000)
