import sys, unittest
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import price_monitor as M
import inventory_ui as UI

class SettlementTests(unittest.TestCase):
 def test_credit_preserves_target_and_details_reconcile(self):
  for target in [100000,1000000,10000000]:
   for override in [{},{'processing_min':22500,'processing_max':180000}]:
    data={'profitRate':25,'digiFees':dict(processing_percent=7,processing_min=36000,processing_max=240000,label_cost=6000,tax_percent=10)}
    p={'targetPriceOverride':target,'purchasePrice':target*.75,'commission':7,'platformRate':8,'digiFeeOverride':override}
    app=SimpleNamespace(data=data,target=lambda p:target,price=lambda p,c:UI.settlement_price(app,vars(M),p,c,'cash'))
    cash,cashparts=UI.breakdown(app,vars(M),p,'digikala','cash')
    credit,parts=UI.breakdown(app,vars(M),p,'digikala','credit')
    self.assertGreater(credit,cash)
    for mode,price,rows in [('cash',cash,cashparts),('credit',credit,parts)]:
     self.assertAlmostEqual(sum(v for _,v,_ in rows),price)
     self.assertLessEqual(abs(rows[-1][1]-target*.25),2)
     cfg=UI.E.fees(data,p);rate=8 if mode=='credit' else 0
     self.assertGreaterEqual(M.net(price,7,rate,cfg),target)
     self.assertLess(M.net(price-1,7,rate,cfg),target)
    self.assertGreater(dict((name,value) for name,value,_ in parts)['اضافه اعتباری'],0)
 def test_non_digi_and_missing_commission(self):
  app=SimpleNamespace(price=lambda p,c:12345)
  self.assertEqual(UI.settlement_price(app,{}, {},'arazman','credit'),12345)
  self.assertIsNone(UI.settlement_price(app,{}, {},'digikala','credit'))
if __name__=='__main__':unittest.main()
