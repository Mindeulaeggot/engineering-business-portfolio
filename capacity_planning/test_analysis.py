import unittest
import numpy as np
import pandas as pd
from analysis import asymmetric_loss,summarize,features,FEATURES

class Tests(unittest.TestCase):
    def test_shortage_cost(self):self.assertEqual(asymmetric_loss([10],[8],5),10)
    def test_idle_cost(self):self.assertEqual(asymmetric_loss([8],[10],5),2)
    def test_exact(self):self.assertEqual(asymmetric_loss([10],[10],5),0)
    def test_asymmetric_quantile(self):self.assertGreater(5/6,.5)
    def test_negative_capacity(self):
        with self.assertRaises(ValueError):asymmetric_loss([1],[-1],5)
    def test_invalid_cost(self):
        with self.assertRaises(ValueError):asymmetric_loss([1],[1],0)
    def test_coverage(self):self.assertEqual(summarize(np.array([2,4]),np.array([3,3]),5)['hour_coverage_rate'],.5)
    def test_no_target_leakage(self):self.assertFalse(set(FEATURES)&{'cnt','casual','registered','temp','weathersit'})
    def test_feature_order(self):
        df=pd.DataFrame({k:[0] for k in reversed(FEATURES)})
        self.assertEqual(list(features(df)),FEATURES)

if __name__=='__main__':unittest.main()
