import tempfile
import unittest
from pathlib import Path

from healthtwin_db import (
    add_medication,
    add_checkup,
    checkups,
    health_events,
    latest_checkup,
    medications,
    seed_demo_data,
    update_medication_status,
)


class HealthTwinDatabaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "test.db"
        seed_demo_data(self.path)

    def tearDown(self):
        self.temp.cleanup()

    def test_seed_creates_longitudinal_record(self):
        rows = checkups("HT-001", self.path)
        self.assertGreaterEqual(len(rows), 6)
        self.assertLess(rows[0]["weight_kg"], rows[-1]["weight_kg"])
        self.assertGreaterEqual(len(health_events("HT-001", self.path)), 5)

    def test_new_checkup_persists_and_becomes_latest(self):
        previous = latest_checkup("HT-001", self.path)
        new_row = {key: previous[key] for key in (
            "member_id","age","height_cm","weight_kg","waist_cm","sbp","dbp",
            "hba1c","egfr","activity_days","diet_score","smoker","on_bp_meds",
            "history_high_glucose","family_history_diabetes","twin_score",
            "medications","allergies","notes",
        )}
        new_row["checkup_date"] = "2026-12-01"
        new_row["weight_kg"] = 88
        add_checkup(new_row, self.path)
        self.assertEqual(latest_checkup("HT-001", self.path)["weight_kg"], 88)

    def test_seed_includes_current_medication_and_dose(self):
        active = [item for item in medications("HT-001", self.path) if item["status"] == "Active"]
        self.assertEqual(active[0]["medication_name"], "Amlodipine")
        self.assertEqual(active[0]["dose_value"], "5")
        self.assertEqual(active[0]["dose_unit"], "mg")

    def test_medication_can_be_added_then_stopped(self):
        medication_id = add_medication(
            {"member_id":"HT-001","medication_name":"Demo medicine","dose_value":"1","dose_unit":"tablet","route":"By mouth","frequency":"Twice daily","start_date":"2026-08-01","end_date":None,"status":"Active","reason":"Test","prescriber":"Test clinician","instructions":"Test only","adherence":"Not reviewed","information_source":"Clinician record","last_reviewed":"2026-08-01"},
            self.path,
        )
        update_medication_status(medication_id,"Stopped","2026-08-10","2026-08-10",self.path)
        item = next(row for row in medications("HT-001",self.path) if row["medication_id"] == medication_id)
        self.assertEqual(item["status"], "Stopped")
        self.assertEqual(item["end_date"], "2026-08-10")


if __name__ == "__main__":
    unittest.main()
