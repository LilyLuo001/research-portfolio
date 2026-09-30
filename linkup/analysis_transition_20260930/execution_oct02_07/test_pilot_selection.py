import unittest
import pilot_first_wave_3shards as pilot

class SelectionTest(unittest.TestCase):
    def test_fixed_regions_and_output_blind_selection(self):
        rows = [
            {"shard_id": "ks-a", "region": "kunshan", "candidate_count": 999},
            {"shard_id": "ks-b", "region": "kunshan", "candidate_count": 0},
            {"shard_id": "wz-a", "region": "wuzhen", "candidate_count": 999},
            {"shard_id": "wz-b", "region": "wuzhen", "candidate_count": 0},
        ]
        chosen = pilot.select(rows)
        self.assertEqual(len(chosen), 3)
        self.assertIn("kunshan", {r["region"] for r in chosen})
        self.assertIn("wuzhen", {r["region"] for r in chosen})
        stripped = [{k: v for k, v in r.items() if k != "candidate_count"} for r in rows]
        self.assertEqual([r["shard_id"] for r in chosen], [r["shard_id"] for r in pilot.select(stripped)])

if __name__ == "__main__": unittest.main()
