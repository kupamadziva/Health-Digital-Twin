import unittest

from health_metrics import condition_assessments


class ConditionHealthScoreTests(unittest.TestCase):
    def test_healthy_readings_receive_full_scores(self):
        results = condition_assessments(
            height_cm=172, weight_kg=68, sbp=115, dbp=75,
            hba1c=5.4, egfr=100, diabetes_risk=4,
        )
        self.assertTrue(all(item["Score"] == 100 or item["Condition"] == "Type 2 diabetes" for item in results))
        self.assertEqual(results[0]["Score"], 96)

    def test_unhealthy_distance_is_explicit_and_score_falls(self):
        results = condition_assessments(
            height_cm=172, weight_kg=92, sbp=148, dbp=94,
            hba1c=6.1, egfr=86, diabetes_risk=50,
        )
        by_name = {item["Condition"]: item for item in results}
        self.assertLess(by_name["Blood pressure"]["Score"], 100)
        self.assertIn("above", by_name["Blood pressure"]["Difference"])
        self.assertIn("below", by_name["Kidney function"]["Difference"])
        self.assertEqual(by_name["Type 2 diabetes"]["Score"], 50)

    def test_exact_boundaries_are_not_called_normal(self):
        results = condition_assessments(
            height_cm=172, weight_kg=68, sbp=120, dbp=79,
            hba1c=5.7, egfr=90,
        )
        by_name = {item["Condition"]: item for item in results}
        self.assertEqual(by_name["Blood pressure"]["Status"], "Monitor")
        self.assertIn("boundary", by_name["Blood pressure"]["Difference"])
        self.assertEqual(by_name["Average blood sugar"]["Status"], "Monitor")
        self.assertIn("boundary", by_name["Average blood sugar"]["Difference"])

    def test_scores_worsen_monotonically_as_readings_move_away(self):
        near = condition_assessments(height_cm=172,weight_kg=78,sbp=130,dbp=82,hba1c=5.8,egfr=85)
        far = condition_assessments(height_cm=172,weight_kg=100,sbp=160,dbp=100,hba1c=7.0,egfr=55)
        near_scores = {item["Condition"]: item["Score"] for item in near}
        far_scores = {item["Condition"]: item["Score"] for item in far}
        self.assertTrue(all(far_scores[name] < near_scores[name] for name in near_scores))


if __name__ == "__main__":
    unittest.main()
