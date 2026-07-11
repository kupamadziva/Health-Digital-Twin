"""SQLite persistence for longitudinal HealthTwin demonstration records."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import sqlite3
from typing import Any


DEFAULT_DB_PATH = Path(__file__).with_name("healthtwin_demo.db")


CHECKUP_FIELDS = (
    "member_id", "checkup_date", "age", "height_cm", "weight_kg", "waist_cm",
    "sbp", "dbp", "hba1c", "egfr", "activity_days", "diet_score", "smoker",
    "on_bp_meds", "history_high_glucose", "family_history_diabetes",
    "twin_score", "medications", "allergies", "notes",
)


def connect(path: str | Path = DEFAULT_DB_PATH) -> sqlite3.Connection:
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


@contextmanager
def database(path: str | Path = DEFAULT_DB_PATH):
    connection = connect(path)
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


def initialise_database(path: str | Path = DEFAULT_DB_PATH) -> None:
    with database(path) as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS members (
                member_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                sex TEXT NOT NULL,
                region TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS checkups (
                checkup_id INTEGER PRIMARY KEY AUTOINCREMENT,
                member_id TEXT NOT NULL REFERENCES members(member_id),
                checkup_date TEXT NOT NULL,
                age INTEGER NOT NULL,
                height_cm REAL NOT NULL,
                weight_kg REAL NOT NULL,
                waist_cm REAL NOT NULL,
                sbp REAL NOT NULL,
                dbp REAL NOT NULL,
                hba1c REAL NOT NULL,
                egfr REAL NOT NULL,
                activity_days REAL NOT NULL,
                diet_score REAL NOT NULL,
                smoker INTEGER NOT NULL,
                on_bp_meds INTEGER NOT NULL,
                history_high_glucose INTEGER NOT NULL,
                family_history_diabetes TEXT NOT NULL,
                twin_score INTEGER NOT NULL,
                medications TEXT NOT NULL DEFAULT '',
                allergies TEXT NOT NULL DEFAULT '',
                notes TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(member_id, checkup_date)
            );

            CREATE TABLE IF NOT EXISTS health_events (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                member_id TEXT NOT NULL REFERENCES members(member_id),
                event_date TEXT NOT NULL,
                event_type TEXT NOT NULL,
                title TEXT NOT NULL,
                details TEXT NOT NULL DEFAULT '',
                provider TEXT NOT NULL DEFAULT '',
                outcome TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS care_plans (
                plan_id INTEGER PRIMARY KEY AUTOINCREMENT,
                member_id TEXT NOT NULL REFERENCES members(member_id),
                plan_date TEXT NOT NULL,
                weight_loss_goal REAL NOT NULL,
                activity_target REAL NOT NULL,
                diet_target REAL NOT NULL,
                smoke_free INTEGER NOT NULL,
                bp_support INTEGER NOT NULL,
                adherence REAL NOT NULL,
                horizon_months INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'Active',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS medications (
                medication_id INTEGER PRIMARY KEY AUTOINCREMENT,
                member_id TEXT NOT NULL REFERENCES members(member_id),
                medication_name TEXT NOT NULL,
                dose_value TEXT NOT NULL,
                dose_unit TEXT NOT NULL,
                route TEXT NOT NULL,
                frequency TEXT NOT NULL,
                start_date TEXT NOT NULL,
                end_date TEXT,
                status TEXT NOT NULL,
                reason TEXT NOT NULL DEFAULT '',
                prescriber TEXT NOT NULL DEFAULT '',
                instructions TEXT NOT NULL DEFAULT '',
                adherence TEXT NOT NULL DEFAULT 'Not reviewed',
                information_source TEXT NOT NULL DEFAULT 'Patient reported',
                last_reviewed TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """
        )


def add_member(member_id: str, name: str, sex: str, region: str, path: str | Path = DEFAULT_DB_PATH) -> None:
    with database(path) as db:
        db.execute(
            "INSERT OR IGNORE INTO members(member_id,name,sex,region) VALUES(?,?,?,?)",
            (member_id, name, sex, region),
        )


def add_checkup(checkup: dict[str, Any], path: str | Path = DEFAULT_DB_PATH) -> int:
    values = [checkup[field] for field in CHECKUP_FIELDS]
    placeholders = ",".join("?" for _ in CHECKUP_FIELDS)
    with database(path) as db:
        cursor = db.execute(
            f"INSERT OR REPLACE INTO checkups({','.join(CHECKUP_FIELDS)}) VALUES({placeholders})",
            values,
        )
        return int(cursor.lastrowid)


def add_event(event: dict[str, Any], path: str | Path = DEFAULT_DB_PATH) -> int:
    fields = ("member_id", "event_date", "event_type", "title", "details", "provider", "outcome")
    with database(path) as db:
        cursor = db.execute(
            f"INSERT INTO health_events({','.join(fields)}) VALUES(?,?,?,?,?,?,?)",
            [event.get(field, "") for field in fields],
        )
        return int(cursor.lastrowid)


def add_care_plan(plan: dict[str, Any], path: str | Path = DEFAULT_DB_PATH) -> int:
    fields = ("member_id", "plan_date", "weight_loss_goal", "activity_target", "diet_target", "smoke_free", "bp_support", "adherence", "horizon_months", "status")
    with database(path) as db:
        cursor = db.execute(
            f"INSERT INTO care_plans({','.join(fields)}) VALUES(?,?,?,?,?,?,?,?,?,?)",
            [plan[field] for field in fields],
        )
        return int(cursor.lastrowid)


def members(path: str | Path = DEFAULT_DB_PATH) -> list[dict[str, Any]]:
    with database(path) as db:
        return [dict(row) for row in db.execute("SELECT * FROM members ORDER BY name")]


def checkups(member_id: str, path: str | Path = DEFAULT_DB_PATH) -> list[dict[str, Any]]:
    with database(path) as db:
        rows = db.execute("SELECT * FROM checkups WHERE member_id=? ORDER BY checkup_date", (member_id,))
        return [dict(row) for row in rows]


def latest_checkup(member_id: str, path: str | Path = DEFAULT_DB_PATH) -> dict[str, Any] | None:
    with database(path) as db:
        row = db.execute("SELECT * FROM checkups WHERE member_id=? ORDER BY checkup_date DESC LIMIT 1", (member_id,)).fetchone()
        return dict(row) if row else None


def health_events(member_id: str, path: str | Path = DEFAULT_DB_PATH) -> list[dict[str, Any]]:
    with database(path) as db:
        rows = db.execute("SELECT * FROM health_events WHERE member_id=? ORDER BY event_date", (member_id,))
        return [dict(row) for row in rows]


def care_plans(member_id: str, path: str | Path = DEFAULT_DB_PATH) -> list[dict[str, Any]]:
    with database(path) as db:
        rows = db.execute("SELECT * FROM care_plans WHERE member_id=? ORDER BY plan_date", (member_id,))
        return [dict(row) for row in rows]


def add_medication(medication: dict[str, Any], path: str | Path = DEFAULT_DB_PATH) -> int:
    fields = (
        "member_id", "medication_name", "dose_value", "dose_unit", "route",
        "frequency", "start_date", "end_date", "status", "reason", "prescriber",
        "instructions", "adherence", "information_source", "last_reviewed",
    )
    with database(path) as db:
        cursor = db.execute(
            f"INSERT INTO medications({','.join(fields)}) VALUES({','.join('?' for _ in fields)})",
            [medication.get(field) for field in fields],
        )
        return int(cursor.lastrowid)


def medications(member_id: str, path: str | Path = DEFAULT_DB_PATH) -> list[dict[str, Any]]:
    with database(path) as db:
        rows = db.execute(
            "SELECT * FROM medications WHERE member_id=? ORDER BY CASE status WHEN 'Active' THEN 0 ELSE 1 END, start_date DESC",
            (member_id,),
        )
        return [dict(row) for row in rows]


def update_medication_status(
    medication_id: int,
    status: str,
    end_date: str | None,
    last_reviewed: str,
    path: str | Path = DEFAULT_DB_PATH,
) -> None:
    with database(path) as db:
        db.execute(
            "UPDATE medications SET status=?, end_date=?, last_reviewed=? WHERE medication_id=?",
            (status, end_date, last_reviewed, medication_id),
        )


def _seed_demo_medications(path: str | Path) -> None:
    if medications("HT-001", path):
        return
    add_medication(
        {
            "member_id":"HT-001", "medication_name":"Amlodipine", "dose_value":"5",
            "dose_unit":"mg", "route":"By mouth", "frequency":"Once daily",
            "start_date":"2026-06-20", "end_date":None, "status":"Active",
            "reason":"Blood-pressure management", "prescriber":"Cimas clinic",
            "instructions":"Take at approximately the same time each day.",
            "adherence":"Usually takes as directed", "information_source":"Clinician record",
            "last_reviewed":"2026-07-11",
        }, path,
    )
    add_medication(
        {
            "member_id":"HT-001", "medication_name":"Paracetamol", "dose_value":"500",
            "dose_unit":"mg", "route":"By mouth", "frequency":"As needed",
            "start_date":"2023-01-22", "end_date":"2023-01-26", "status":"Completed",
            "reason":"Fever and respiratory symptoms", "prescriber":"Primary care",
            "instructions":"Short outpatient course recorded in the synthetic history.",
            "adherence":"Course completed", "information_source":"Patient reported",
            "last_reviewed":"2023-01-26",
        }, path,
    )


def seed_demo_data(path: str | Path = DEFAULT_DB_PATH) -> None:
    initialise_database(path)
    add_member("HT-001", "Tendai M.", "Male", "Harare", path)
    if checkups("HT-001", path):
        # Keep previously seeded snapshots aligned with the current demo engine,
        # without touching a same-day check-up that the user has edited.
        seeded_scores = {
            "Routine annual check-up.": 80,
            "Activity reduced during busy work period.": 72,
            "Smoking resumed; lifestyle support offered.": 55,
            "High glucose history added; BP follow-up recommended.": 48,
            "Nutrition and activity care plan agreed.": 46,
            "Latest comprehensive check-up.": 37,
        }
        with database(path) as db:
            for note, score in seeded_scores.items():
                db.execute(
                    "UPDATE checkups SET twin_score=? WHERE member_id='HT-001' AND notes=?",
                    (score, note),
                )
            db.execute(
                "UPDATE checkups SET on_bp_meds=1, medications='Amlodipine 5 mg once daily' WHERE member_id='HT-001' AND notes='Latest comprehensive check-up.'"
            )
        _seed_demo_medications(path)
        return

    snapshots = [
        ("2022-06-14",43,84,94,128,82,5.4,102,4,5,0,0,0,80,"None","No known allergies","Routine annual check-up."),
        ("2023-06-20",44,86,97,134,85,5.5,99,3,4,0,0,0,72,"None","No known allergies","Activity reduced during busy work period."),
        ("2024-05-16",45,88,99,139,88,5.7,95,3,4,1,0,0,55,"None","No known allergies","Smoking resumed; lifestyle support offered."),
        ("2025-02-18",46,89,101,142,90,5.8,92,2,3,1,0,1,48,"None","No known allergies","High glucose history added; BP follow-up recommended."),
        ("2025-11-03",46,90,102,144,91,5.9,89,2,3,1,0,1,46,"None","No known allergies","Nutrition and activity care plan agreed."),
        ("2026-07-11",47,92,104,148,94,6.1,86,1,2,1,1,1,37,"Amlodipine 5 mg once daily","No known allergies","Latest comprehensive check-up."),
    ]
    for row in snapshots:
        checkup_date, age, weight, waist, sbp, dbp, hba1c, egfr, activity, diet, smoker, meds, glucose, score, medications, allergies, notes = row
        add_checkup(
            {
                "member_id":"HT-001", "checkup_date":checkup_date, "age":age,
                "height_cm":172, "weight_kg":weight, "waist_cm":waist,
                "sbp":sbp, "dbp":dbp, "hba1c":hba1c, "egfr":egfr,
                "activity_days":activity, "diet_score":diet, "smoker":smoker,
                "on_bp_meds":meds, "history_high_glucose":glucose,
                "family_history_diabetes":"First-degree relative", "twin_score":score,
                "medications":medications, "allergies":allergies, "notes":notes,
            }, path,
        )

    for event in (
        ("2023-01-22","Illness","Respiratory infection","Fever and cough managed as an outpatient.","Primary care","Recovered"),
        ("2024-03-08","Illness","Malaria","Positive malaria test and full treatment course.","Local clinic","Recovered"),
        ("2024-09-12","Injury","Lower-back strain","Short course of pain relief and activity modification.","Primary care","Resolved"),
        ("2025-02-18","Clinical finding","Raised blood-pressure reading","Repeat measurements recommended.","Cimas clinic","Under review"),
        ("2025-11-03","Care plan","Lifestyle support started","Activity, nutrition, and smoke-free goals discussed.","Wellness team","Active"),
    ):
        event_date, event_type, title, details, provider, outcome = event
        add_event({"member_id":"HT-001","event_date":event_date,"event_type":event_type,"title":title,"details":details,"provider":provider,"outcome":outcome}, path)

    add_care_plan(
        {"member_id":"HT-001","plan_date":"2025-11-03","weight_loss_goal":8,"activity_target":5,"diet_target":6,"smoke_free":1,"bp_support":1,"adherence":0.7,"horizon_months":24,"status":"Active"},
        path,
    )
    _seed_demo_medications(path)
