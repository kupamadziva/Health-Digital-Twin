"""Synthetic care-management operations and claims-book data for the demo.

No values in this module represent a real Cimas member or actual Cimas claims.
The structures are deliberately explicit so production integrations can replace
the demo records without changing the user experience.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Iterable

import pandas as pd


CARE_CASES = {
    "T. Moyo": {"owner": "Rudo N.", "last_contact": 16, "due": -1, "status": "Needs action", "contact": "WhatsApp", "programme": "Blood-pressure support", "barrier": "Shift work makes weekday visits difficult"},
    "R. Chikwava": {"owner": "Tariro K.", "last_contact": 6, "due": 4, "status": "In progress", "contact": "Phone", "programme": "Healthy living", "barrier": "None recorded"},
    "S. Ndoro": {"owner": "Rudo N.", "last_contact": 24, "due": -3, "status": "Urgent", "contact": "Phone", "programme": "Diabetes support", "barrier": "Transport to the preferred clinic"},
    "P. Gumbo": {"owner": "Unassigned", "last_contact": 35, "due": 21, "status": "Monitoring", "contact": "SMS", "programme": "Routine prevention", "barrier": "None recorded"},
    "F. Sibanda": {"owner": "Tariro K.", "last_contact": 11, "due": 1, "status": "Needs action", "contact": "WhatsApp", "programme": "Blood-pressure support", "barrier": "Medication collection hours"},
    "N. Mutasa": {"owner": "Nyasha P.", "last_contact": 9, "due": 7, "status": "In progress", "contact": "SMS", "programme": "Stop-smoking support", "barrier": "None recorded"},
    "C. Dube": {"owner": "Nyasha P.", "last_contact": 19, "due": 0, "status": "Urgent", "contact": "Phone", "programme": "Kidney and BP review", "barrier": "Lives far from contracted provider"},
    "L. Mhlanga": {"owner": "Unassigned", "last_contact": 42, "due": 30, "status": "Monitoring", "contact": "Email", "programme": "Routine prevention", "barrier": "None recorded"},
    "B. Chirwa": {"owner": "Tariro K.", "last_contact": 13, "due": 2, "status": "Needs action", "contact": "Phone", "programme": "Blood-pressure support", "barrier": "Caregiving responsibilities"},
}


# Paid amounts are synthetic USD-equivalent demo values for the latest 12 months.
# Attribution is a rules-based demo allocation, not clinical or actuarial causality.
CLAIMS_BOOK = {
    "T. Moyo": [("Blood pressure", "Consultations", 4, 260), ("Blood pressure", "Medication", 8, 610), ("Type 2 diabetes", "Laboratory", 3, 285), ("Other care", "Other", 2, 190)],
    "R. Chikwava": [("Blood pressure", "Consultations", 2, 140), ("Blood pressure", "Medication", 5, 330), ("Other care", "Other", 2, 120)],
    "S. Ndoro": [("Type 2 diabetes", "Medication", 10, 940), ("Type 2 diabetes", "Laboratory", 5, 510), ("Blood pressure", "Consultations", 5, 380), ("Kidney function", "Hospital and specialist", 2, 1880), ("Other care", "Other", 2, 160)],
    "P. Gumbo": [("Other care", "Prevention", 2, 120), ("Other care", "Other", 1, 75)],
    "F. Sibanda": [("Blood pressure", "Medication", 8, 580), ("Blood pressure", "Consultations", 3, 220), ("Type 2 diabetes", "Laboratory", 2, 190), ("Other care", "Other", 1, 95)],
    "N. Mutasa": [("Blood pressure", "Consultations", 2, 145), ("Respiratory risk", "Consultations", 2, 210), ("Other care", "Other", 2, 130)],
    "C. Dube": [("Kidney function", "Hospital and specialist", 3, 2440), ("Blood pressure", "Medication", 9, 690), ("Type 2 diabetes", "Laboratory", 4, 430), ("Other care", "Other", 2, 175)],
    "L. Mhlanga": [("Other care", "Prevention", 2, 110), ("Other care", "Other", 1, 55)],
    "B. Chirwa": [("Blood pressure", "Medication", 7, 510), ("Blood pressure", "Consultations", 3, 240), ("Kidney function", "Laboratory", 3, 310), ("Other care", "Other", 1, 90)],
}


def care_reason(state) -> str:
    """Return a plain-language, explainable reason for queue placement."""
    reasons = []
    if state.sbp >= 160 or state.dbp >= 100:
        reasons.append("very high blood-pressure reading")
    elif state.sbp >= 140 or state.dbp >= 90:
        reasons.append("blood pressure above the displayed healthy range")
    if state.hba1c >= 6.5:
        reasons.append("average blood sugar in the diabetes screening range")
    elif state.hba1c >= 6.0:
        reasons.append("average blood sugar has room to improve")
    if state.egfr < 60:
        reasons.append("kidney result needs clinical review")
    elif state.egfr < 75:
        reasons.append("kidney result should be monitored")
    if state.smoking_exposure:
        reasons.append("smoking support may reduce risk")
    # Keep every clinically important flag visible; hiding a third severe result
    # behind a generic priority score would make the queue less explainable.
    return "; ".join(reasons[:3]) or "routine preventive follow-up"


def urgency(state, case: dict) -> str:
    if state.sbp >= 160 or state.dbp >= 100 or state.hba1c >= 7 or state.egfr < 60:
        return "Urgent"
    if case["due"] < 0 or state.sbp >= 140 or state.hba1c >= 6:
        return "High"
    if state.sbp >= 130 or state.activity_days < 3:
        return "Medium"
    return "Routine"


def recommended_action(state) -> str:
    if state.egfr < 60:
        return "Arrange kidney and medication review"
    if state.hba1c >= 6.5:
        return "Book diabetes review and repeat test"
    if state.sbp >= 160 or state.dbp >= 100:
        return "Contact today and arrange BP review"
    if state.sbp >= 140 or state.dbp >= 90:
        return "Check treatment and book BP follow-up"
    if state.smoking_exposure:
        return "Offer stop-smoking support"
    return "Continue routine monitoring"


def due_label(offset: int) -> str:
    if offset < 0:
        return f"{abs(offset)}d overdue"
    if offset == 0:
        return "Today"
    return f"In {offset}d"


def queue_rows(fleet: Iterable[tuple], score_by_name: dict[str, int]) -> pd.DataFrame:
    rows = []
    rank = {"Urgent": 0, "High": 1, "Medium": 2, "Routine": 3}
    for name, region, state in fleet:
        case = CARE_CASES[name]
        level = urgency(state, case)
        rows.append({
            "Priority": level,
            "Member": name,
            "Why flagged": care_reason(state),
            "Health score": score_by_name[name],
            "Last contact": f"{case['last_contact']}d ago",
            "Owner": case["owner"],
            "Due": due_label(case["due"]),
            "Next action": recommended_action(state),
            "Status": case["status"],
            "_rank": rank[level],
            "_due": case["due"],
            "Region": region,
        })
    return pd.DataFrame(rows).sort_values(["_rank", "_due", "Health score"])


def claims_for(member: str) -> pd.DataFrame:
    rows = []
    for condition, category, count, paid in CLAIMS_BOOK[member]:
        rows.append({"Condition attribution": condition, "Claim category": category, "Claims": count, "Paid amount": float(paid)})
    return pd.DataFrame(rows)


def member_claim_summary(member: str) -> dict:
    claims = claims_for(member)
    chronic = claims[claims["Condition attribution"] != "Other care"]
    total = float(claims["Paid amount"].sum())
    chronic_total = float(chronic["Paid amount"].sum())
    previous = round(total * {"T. Moyo": .83, "R. Chikwava": .91, "S. Ndoro": .72, "P. Gumbo": 1.08, "F. Sibanda": .88, "N. Mutasa": .79, "C. Dube": .66, "L. Mhlanga": 1.04, "B. Chirwa": .86}[member], 2)
    return {
        "total": total,
        "chronic": chronic_total,
        "chronic_share": chronic_total / total if total else 0,
        "previous": previous,
        "change": (total - previous) / previous if previous else 0,
        "claim_count": int(claims["Claims"].sum()),
    }


def scheme_claim_summary() -> pd.DataFrame:
    parts = []
    for member in CLAIMS_BOOK:
        df = claims_for(member)
        df["Member"] = member
        parts.append(df)
    return pd.concat(parts, ignore_index=True)


def initial_tasks() -> list[dict]:
    today = date.today()
    return [
        {"Member": "S. Ndoro", "Task": "Arrange diabetes and kidney review", "Owner": "Rudo N.", "Due": today - timedelta(days=3), "Status": "Overdue"},
        {"Member": "T. Moyo", "Task": "Call about recent BP reading", "Owner": "Rudo N.", "Due": today, "Status": "Open"},
        {"Member": "C. Dube", "Task": "Confirm specialist appointment", "Owner": "Nyasha P.", "Due": today, "Status": "Open"},
        {"Member": "F. Sibanda", "Task": "Check medication collection", "Owner": "Tariro K.", "Due": today + timedelta(days=1), "Status": "Open"},
    ]


def initial_contacts() -> list[dict]:
    return [
        {"Member": "T. Moyo", "Date": date.today() - timedelta(days=16), "Channel": "WhatsApp", "Outcome": "Reached", "Note": "Agreed to repeat BP check."},
        {"Member": "S. Ndoro", "Date": date.today() - timedelta(days=24), "Channel": "Phone", "Outcome": "Reached", "Note": "Transport remains a barrier."},
        {"Member": "C. Dube", "Date": date.today() - timedelta(days=19), "Channel": "Phone", "Outcome": "No answer", "Note": "Try again in the morning."},
    ]
