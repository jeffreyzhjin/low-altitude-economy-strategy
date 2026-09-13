import sys
import unittest
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "analysis"))

from scenario_scoring import CRITERIA, WEIGHT_SETS, score_scenarios, validate_weights
from decision_support import build_decision_memo, normalize_weights, ranking_matrix


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

    def test_custom_weights_are_normalized(self):
        normalized = normalize_weights({key: 20 for key in CRITERIA})
        self.assertAlmostEqual(sum(normalized.values()), 1.0)
        self.assertTrue(all(value == 0.2 for value in normalized.values()))

    def test_zero_custom_weights_raise(self):
        with self.assertRaises(ValueError):
            normalize_weights({key: 0 for key in CRITERIA})

    def test_predefined_profiles_keep_same_top_two(self):
        matrix = ranking_matrix(self.frame, WEIGHT_SETS, score_scenarios)
        expected = {"Urban instant delivery", "Low-altitude digital infrastructure and services"}
        for profile in matrix.columns:
            self.assertEqual(set(matrix[profile].nsmallest(2).index), expected)

    def test_decision_memo_includes_ranking_and_caveat(self):
        ranked = score_scenarios(self.frame, WEIGHT_SETS["Base case"])
        memo = build_decision_memo(ranked, "Base case", WEIGHT_SETS["Base case"], CRITERIA)
        self.assertIn("Urban instant delivery", memo)
        self.assertIn("screening result, not an investment forecast", memo)


if __name__ == "__main__":
    unittest.main()
