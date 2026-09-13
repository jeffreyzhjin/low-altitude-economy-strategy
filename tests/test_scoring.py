import sys
import unittest
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "analysis"))

from scenario_scoring import CRITERIA, WEIGHT_SETS, score_scenarios, validate_weights


class ScenarioScoringTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.frame = pd.read_csv(ROOT / "data" / "scenario-scoring.csv")

    def test_base_weights_sum_to_one(self):
        validate_weights(WEIGHT_SETS["Base case"])

    def test_ranking_has_all_scenarios(self):
        ranked = score_scenarios(self.frame, WEIGHT_SETS["Base case"])
        self.assertEqual(len(ranked), 6)
        self.assertEqual(set(ranked["rank"]), {1, 2, 3, 5, 6})

    def test_instant_delivery_ranks_first(self):
        ranked = score_scenarios(self.frame, WEIGHT_SETS["Base case"])
        self.assertEqual(ranked.iloc[0]["scenario_id"], "S01")
        self.assertAlmostEqual(ranked.iloc[0]["weighted_score"], 4.4)

    def test_scores_outside_scale_raise(self):
        invalid = self.frame.copy()
        invalid.loc[0, next(iter(CRITERIA))] = 6
        with self.assertRaises(ValueError):
            score_scenarios(invalid, WEIGHT_SETS["Base case"])


if __name__ == "__main__":
    unittest.main()

