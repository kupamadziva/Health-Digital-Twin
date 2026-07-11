import unittest

from healthtwin_core import (
    NO,
    UNKNOWN,
    YES,
    blood_pressure_result,
    apply_demo_goals,
    demo_wellness_index,
    findrisc_points,
    findrisc_result,
    kidney_result,
    review_priority,
)


def complete_profile():
    return {
        "age": 47,
        "sex": "Male",
        "height_cm": 172,
        "weight_kg": 92,
        "waist_cm": 104,
        "daily_activity": NO,
        "daily_fruit_veg": NO,
        "on_bp_meds": NO,
        "history_high_glucose": YES,
        "family_history_diabetes": "First-degree relative",
        "diagnosed_diabetes": NO,
        "bp_available": True,
        "sbp": 148,
        "dbp": 94,
        "severe_bp_symptoms": NO,
        "egfr": None,
        "uacr": None,
    }


class FindriscTests(unittest.TestCase):
    def test_known_profile_points(self):
        self.assertEqual(findrisc_points(complete_profile()), 22)

    def test_unknown_answer_makes_result_incomplete(self):
        profile = complete_profile()
        profile["daily_activity"] = UNKNOWN
        self.assertIsNone(findrisc_points(profile))
        self.assertEqual(findrisc_result(profile).status, "incomplete")

    def test_diagnosed_diabetes_is_not_applicable(self):
        profile = complete_profile()
        profile["diagnosed_diabetes"] = YES
        self.assertEqual(findrisc_result(profile).status, "not-applicable")


class SafetyRuleTests(unittest.TestCase):
    def test_very_high_bp_with_symptoms_is_urgent(self):
        profile = complete_profile()
        profile.update(sbp=185, dbp=121, severe_bp_symptoms=YES)
        self.assertEqual(blood_pressure_result(profile).label, "Urgent help")
        self.assertEqual(review_priority(profile).status, "urgent")

    def test_single_high_reading_does_not_claim_diagnosis(self):
        result = blood_pressure_result(complete_profile())
        self.assertEqual(result.status, "review")
        self.assertIn("does not confirm", result.detail)

    def test_kidney_requires_both_markers(self):
        profile = complete_profile()
        profile["egfr"] = 80
        self.assertEqual(kidney_result(profile).label, "One lab missing")

    def test_kidney_chronicity_is_disclosed(self):
        profile = complete_profile()
        profile.update(egfr=55, uacr=10)
        self.assertIn("3+ months", kidney_result(profile).detail)


class DemoIndexTests(unittest.TestCase):
    def test_index_exposes_every_deduction(self):
        profile = complete_profile()
        profile["smoker"] = YES
        score, drivers = demo_wellness_index(profile)
        self.assertEqual(score, 35)
        self.assertEqual(100 - score, sum(item["Points"] for item in drivers))

    def test_selected_goals_improve_demo_index(self):
        profile = complete_profile()
        profile["smoker"] = YES
        before, _ = demo_wellness_index(profile)
        scenario = apply_demo_goals(
            profile,
            {
                "target_weight": 80,
                "daily_activity": YES,
                "daily_fruit_veg": YES,
                "smoke_free": YES,
                "target_sbp": 125,
            },
        )
        after, _ = demo_wellness_index(scenario)
        self.assertGreater(after, before)


if __name__ == "__main__":
    unittest.main()
