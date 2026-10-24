"""Small synthetic method QA; contains no research data."""
import unittest
import numpy as np
import pandas as pd
from correction_core import (truth, conjunction, estimate_component, corrected_point,
                             known_domain_components, ht_envelope, design_variance)

class CorrectionTests(unittest.TestCase):
    def test_census_recovers_reference_and_denominator(self):
        i = pd.RangeIndex(4)
        ref = truth([1, 1, 0, 0], i); old = truth([0, 1, 1, 0], i)
        den = truth([1, 1, 1, 0], i); oldden = truth([1, 1, 0, 0], i)
        n = estimate_component(ref, old, np.ones(4), 2, 4)
        d = estimate_component(den, oldden, np.ones(4), 2, 4)
        self.assertEqual(n['corrected_total_point'], 2)
        self.assertEqual(d['corrected_total_point'], 3)
        self.assertAlmostEqual(corrected_point(n, d)[0], 2/3)

    def test_unknown_preserved_with_known_domain_distinct(self):
        i = pd.RangeIndex(4)
        domain = truth([1, 1, None, 0], i); outcome = truth([1, None, 0, None], i)
        n, d = known_domain_components(domain, outcome)
        self.assertEqual(n.tolist(), [True, False, False, False])
        self.assertEqual(d.tolist(), [True, False, False, False])
        bounds = ht_envelope(domain, outcome, np.ones(4))
        self.assertAlmostEqual(bounds['full_target_unknown_lower'], 1/3)
        self.assertEqual(bounds['full_target_unknown_upper'], 1)
        self.assertEqual(bounds['unknown_domain_ads'], 1)
        self.assertTrue(pd.isna(outcome.iloc[1]))

    def test_missing_auxiliary_fails_instead_of_zero(self):
        i = pd.RangeIndex(2)
        with self.assertRaises(ValueError):
            estimate_component(truth([1, 0], i), truth([None, 0], i), [1, 1], 0, 2)

    def test_srs_variance_uses_all_sample_rows(self):
        # N=4 n=2, residuals1,0 -> S2=.5, V=16*.5*.5/2=2.
        self.assertAlmostEqual(design_variance([1., 0.], [('a',), ('a',)], {('a',): 4}), 2.)
        self.assertEqual(design_variance([1., 0.], [('a',), ('a',)], {('a',): 2}), 0.)
        self.assertIsNone(design_variance([0.], [('b',)], {('b',): 2}))

    def test_invalid_corrected_totals_not_clipped(self):
        i = pd.RangeIndex(2)
        n = estimate_component(truth([0, 0], i), truth([1, 1], i), [3, 3], 1, 6)
        d = estimate_component(truth([1, 1], i), truth([0, 0], i), [3, 3], 0, 6)
        self.assertEqual(n['corrected_total_point'], -5.)
        self.assertIsNone(corrected_point(n, d)[0])

if __name__ == '__main__':
    unittest.main()
