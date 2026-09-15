import unittest
import publish_artifacts as p

class PublicationChecks(unittest.TestCase):
    def test_rejects_synthetic_secret_patterns(self):
        self.assertTrue(p.secret_hit("github_" + "pat_" + "x" * 30))
        self.assertTrue(p.secret_hit("d" + "b-" + "x" * 30))

    def test_permits_named_projection(self):
        self.assertFalse(p.json_row_risk({"columns": ["cusip", "anndats", "analys"], "raw_values_read": False}))

    def test_rejects_observation_payload(self):
        self.assertTrue(p.json_row_risk({"rows": [{"permno": 0, "anndats": "EXAMPLE"}]}))
        self.assertTrue(p.json_row_risk({"price": 0}))

    def test_receipt_is_not_effect_data(self):
        self.assertFalse(p.json_row_risk({"candidate_denominator": 2794, "forecast_values_read": False}))

if __name__ == "__main__": unittest.main()
