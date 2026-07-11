import unittest

from digital_twin import (
    InterventionPlan,
    TwinState,
    assimilate_observation,
    simulate_parallel,
    twin_events,
)


class DigitalTwinTests(unittest.TestCase):
    def test_parallel_paths_share_baseline_then_diverge(self):
        rows = simulate_parallel(TwinState(), InterventionPlan(), 36)
        self.assertEqual(len(rows), 74)
        usual = [row for row in rows if row["Path"] == "Usual path"]
        planned = [row for row in rows if row["Path"] == "Intervention twin"]
        self.assertEqual(usual[0]["Twin index"], planned[0]["Twin index"])
        self.assertGreater(planned[-1]["Twin index"], usual[-1]["Twin index"])
        self.assertLess(planned[-1]["Weight"], usual[-1]["Weight"])

    def test_zero_adherence_does_not_create_large_benefit(self):
        plan = InterventionPlan(adherence=0)
        rows = simulate_parallel(TwinState(), plan, 12)
        usual = [row for row in rows if row["Path"] == "Usual path"][-1]
        planned = [row for row in rows if row["Path"] == "Intervention twin"][-1]
        self.assertAlmostEqual(usual["Weight"], planned["Weight"], places=1)

    def test_observation_reanchors_only_supplied_fields(self):
        state = TwinState()
        updated = assimilate_observation(state, weight_kg=88, sbp=135)
        self.assertEqual(updated.weight_kg, 88)
        self.assertEqual(updated.sbp, 135)
        self.assertEqual(updated.egfr, state.egfr)

    def test_events_include_plan_and_smoking_goal(self):
        plan = InterventionPlan(start_month=2, quit_smoking_month=4)
        events = twin_events(simulate_parallel(TwinState(), plan, 12), plan)
        self.assertTrue(any(event["Month"] == 2 for event in events))
        self.assertTrue(any(event["Month"] == 4 for event in events))


if __name__ == "__main__":
    unittest.main()
