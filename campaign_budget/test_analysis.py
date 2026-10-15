import unittest
import pandas as pd
from analysis import FEATURES, top_budget, scenario, split_ordered

class Tests(unittest.TestCase):
    def test_no_post_call_leakage(self):
        self.assertNotIn('duration',FEATURES);self.assertNotIn('campaign',FEATURES)
    def test_no_demographic_features(self):
        self.assertFalse(set(FEATURES)&{'age','job','marital','education','default','housing','loan'})
    def test_budget_cap(self):
        r=top_budget([0,1,0,1],[.1,.8,.2,.9],.5)
        self.assertEqual(r['contacts'],2);self.assertEqual(r['recall'],1)
    def test_invalid_budget(self):
        with self.assertRaises(ValueError):top_budget([1],[1],0)
    def test_empty(self):
        with self.assertRaises(ValueError):top_budget([],[],.2)
    def test_ties_are_stable(self):
        self.assertEqual(top_budget([0,1],[.5,.5],.5)['observed_positives'],0)
    def test_zero_positive(self):
        self.assertEqual(top_budget([0,0],[.2,.1],.5)['recall'],0)
    def test_scenario_math(self):self.assertEqual(scenario(100,10,20,1),100)
    def test_invalid_scenario(self):
        with self.assertRaises(ValueError):scenario(1,2,3,4)
    def test_chronological_disjoint(self):
        a,b,c=split_ordered(pd.DataFrame({'i':range(100)}))
        self.assertEqual((a.i.max(),b.i.min(),b.i.max(),c.i.min()),(59,60,79,80))

if __name__=='__main__':unittest.main()

