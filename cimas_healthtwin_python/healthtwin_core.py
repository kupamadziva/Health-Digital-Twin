"""Transparent screening rules for the HealthTwin demonstration.

This module deliberately separates deterministic screening logic from the UI.
It does not diagnose disease or estimate treatment effects.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


MODEL_VERSION = "screening-rules-2.0.0"
UNKNOWN = "Unknown"
YES = "Yes"
NO = "No"


@dataclass(frozen=True)
class ScreeningResult:
    status: str
    label: str
    detail: str
    level: int


def bmi(weight_kg: float, height_cm: float) -> float:
    if height_cm <= 0:
        raise ValueError("Height must be greater than zero.")
    return weight_kg / ((height_cm / 100) ** 2)


def findrisc_points(profile: Mapping[str, Any]) -> int | None:
    """Return FINDRISC points, or None when a required answer is unknown.

    FINDRISC is not applicable to a person who reports diagnosed diabetes.
    """
    if profile.get("diagnosed_diabetes") == YES:
        return None

    required = (
        "age",
        "sex",
        "height_cm",
        "weight_kg",
        "waist_cm",
        "daily_activity",
        "daily_fruit_veg",
        "on_bp_meds",
        "history_high_glucose",
        "family_history_diabetes",
    )
    if any(profile.get(key) in (None, UNKNOWN) for key in required):
        return None

    points = 0
    age = int(profile["age"])
    if age >= 65:
        points += 4
    elif age >= 55:
        points += 3
    elif age >= 45:
        points += 2

    body_mass_index = bmi(profile["weight_kg"], profile["height_cm"])
    if body_mass_index > 30:
        points += 3
    elif body_mass_index >= 25:
        points += 1

    waist = float(profile["waist_cm"])
    if profile["sex"] == "Male":
        points += 4 if waist > 102 else 3 if waist >= 94 else 0
    elif profile["sex"] == "Female":
        points += 4 if waist > 88 else 3 if waist >= 80 else 0
    else:
        return None

    if profile["daily_activity"] == NO:
        points += 2
    if profile["daily_fruit_veg"] == NO:
        points += 1
    if profile["on_bp_meds"] == YES:
        points += 2
    if profile["history_high_glucose"] == YES:
        points += 5

    family_history = profile["family_history_diabetes"]
    if family_history == "First-degree relative":
        points += 5
    elif family_history == "Distant relative":
        points += 3

    return points


def findrisc_result(profile: Mapping[str, Any]) -> ScreeningResult:
    if profile.get("diagnosed_diabetes") == YES:
        return ScreeningResult(
            "not-applicable",
            "Not applicable",
            "FINDRISC is intended for people without diagnosed diabetes.",
            1,
        )

    points = findrisc_points(profile)
    if points is None:
        return ScreeningResult(
            "incomplete",
            "Incomplete",
            "Complete every required FINDRISC answer to calculate the score.",
            1,
        )

    if points <= 6:
        label, frequency, level = "Low", "about 1 in 100 over 10 years", 0
    elif points <= 11:
        label, frequency, level = "Slightly elevated", "about 1 in 25 over 10 years", 1
    elif points <= 14:
        label, frequency, level = "Moderate", "about 1 in 6 over 10 years", 2
    elif points <= 20:
        label, frequency, level = "High", "about 1 in 3 over 10 years", 3
    else:
        label, frequency, level = "Very high", "about 1 in 2 over 10 years", 3

    return ScreeningResult(
        "complete",
        label,
        f"FINDRISC {points}/26; published category: {frequency}.",
        level,
    )


def blood_pressure_result(profile: Mapping[str, Any]) -> ScreeningResult:
    if not profile.get("bp_available"):
        return ScreeningResult(
            "incomplete", "Not recorded", "Add a recent BP reading.", 1
        )

    sbp = int(profile["sbp"])
    dbp = int(profile["dbp"])
    symptoms = profile.get("severe_bp_symptoms", UNKNOWN)
    reading = f"Recorded reading: {sbp}/{dbp} mmHg."

    if sbp > 180 or dbp > 120:
        if symptoms == YES:
            return ScreeningResult(
                "urgent",
                "Urgent help",
                f"{reading} Emergency symptoms were reported; seek emergency care now.",
                4,
            )
        return ScreeningResult(
            "urgent",
            "Repeat and contact care",
            f"{reading} Repeat after at least one minute; if still this high, contact a clinician immediately.",
            4,
        )
    if sbp >= 140 or dbp >= 90:
        return ScreeningResult(
            "review",
            "Clinical review",
            f"{reading} One reading does not confirm hypertension; repeat measurements are needed.",
            3,
        )
    if sbp >= 120 or dbp >= 80:
        return ScreeningResult(
            "monitor",
            "Repeat and monitor",
            f"{reading} Record multiple correctly taken readings and discuss them during routine care.",
            2,
        )
    return ScreeningResult(
        "within-range",
        "Within displayed reference range",
        f"{reading} This is a screening observation, not a diagnosis.",
        0,
    )


def kidney_result(profile: Mapping[str, Any]) -> ScreeningResult:
    egfr = profile.get("egfr")
    uacr = profile.get("uacr")
    if egfr is None and uacr is None:
        return ScreeningResult(
            "incomplete",
            "Labs not available",
            "Kidney screening needs eGFR and urine albumin-to-creatinine ratio (uACR).",
            1,
        )
    if egfr is None or uacr is None:
        return ScreeningResult(
            "incomplete",
            "One lab missing",
            "Both eGFR and uACR are needed for a useful kidney review.",
            2,
        )

    if float(egfr) < 60 or float(uacr) >= 30:
        return ScreeningResult(
            "review",
            "Clinical review",
            "At least one kidney marker is outside the displayed screening threshold. Persistence for 3+ months is needed to establish chronic kidney disease.",
            3,
        )
    return ScreeningResult(
        "within-range",
        "No marker flagged",
        "Neither entered marker crosses the displayed screening threshold; interpret with a clinician and clinical context.",
        0,
    )


def cvd_result(profile: Mapping[str, Any]) -> ScreeningResult:
    return ScreeningResult(
        "unavailable",
        "Not calculated",
        "A validated, region-specific WHO cardiovascular risk chart has not been integrated. No substitute percentage is shown.",
        1,
    )


def review_priority(profile: Mapping[str, Any]) -> ScreeningResult:
    results = [
        blood_pressure_result(profile),
        kidney_result(profile),
        findrisc_result(profile),
    ]
    highest = max((item.level for item in results), default=0)
    if highest >= 4:
        return ScreeningResult(
            "urgent", "Urgent attention", "A very high BP reading requires the action shown below.", 4
        )
    if highest >= 3:
        return ScreeningResult(
            "review", "Clinical review suggested", "One or more transparent screening rules were flagged.", 3
        )
    if highest >= 2:
        return ScreeningResult(
            "monitor", "Monitor / complete review", "Repeat measurements or missing information may change the result.", 2
        )
    if any(item.status in {"incomplete", "unavailable"} for item in results):
        return ScreeningResult(
            "incomplete", "Incomplete screening", "No overall health score is generated from incomplete or incomparable measures.", 1
        )
    return ScreeningResult(
        "routine", "Routine prevention", "No entered screening measure triggered a higher review level.", 0
    )


def goal_summary(profile: Mapping[str, Any], goals: Mapping[str, Any]) -> list[str]:
    """Describe user-selected goals without estimating causal risk reduction."""
    messages: list[str] = []
    if goals.get("target_weight") is not None and goals["target_weight"] < profile["weight_kg"]:
        messages.append(
            f"Weight goal: {profile['weight_kg']:.0f} kg to {goals['target_weight']:.0f} kg"
        )
    if goals.get("daily_activity") == YES and profile.get("daily_activity") != YES:
        messages.append("Goal: at least 30 minutes of daily physical activity")
    if goals.get("daily_fruit_veg") == YES and profile.get("daily_fruit_veg") != YES:
        messages.append("Goal: fruit or vegetables every day")
    if goals.get("smoke_free") == YES and profile.get("smoker") == YES:
        messages.append("Goal: become smoke-free with appropriate support")
    return messages


def demo_wellness_index(profile: Mapping[str, Any]) -> tuple[int, list[dict[str, Any]]]:
    """Return a transparent synthetic index and its point deductions.

    This is a product-demonstration device, not a clinical risk score. Every
    deduction is exposed so the number cannot masquerade as a black-box model.
    Unknown values are not penalised.
    """
    deductions: list[dict[str, Any]] = []

    def deduct(driver: str, points: int, explanation: str) -> None:
        if points:
            deductions.append(
                {"Driver": driver, "Points": points, "Why": explanation}
            )

    body_mass_index = bmi(profile["weight_kg"], profile["height_cm"])
    deduct(
        "Weight range",
        10 if body_mass_index >= 30 else 5 if body_mass_index >= 25 else 0,
        f"BMI entered: {body_mass_index:.1f}",
    )

    sex = profile.get("sex")
    waist = float(profile["waist_cm"])
    if sex == "Male":
        deduct("Waist circumference", 6 if waist > 102 else 3 if waist >= 94 else 0, f"Waist entered: {waist:.0f} cm")
    elif sex == "Female":
        deduct("Waist circumference", 6 if waist > 88 else 3 if waist >= 80 else 0, f"Waist entered: {waist:.0f} cm")

    deduct("Daily activity", 8 if profile.get("daily_activity") == NO else 0, "Daily 30-minute activity was not reported")
    deduct("Fruit and vegetables", 4 if profile.get("daily_fruit_veg") == NO else 0, "Daily fruit or vegetables were not reported")
    deduct("Smoking", 15 if profile.get("smoker") == YES else 0, "Current smoking was reported")
    deduct("Previous high glucose", 8 if profile.get("history_high_glucose") == YES else 0, "Previous high glucose was reported")

    if profile.get("bp_available"):
        sbp, dbp = int(profile["sbp"]), int(profile["dbp"])
        bp_points = 14 if (sbp >= 140 or dbp >= 90) else 6 if (sbp >= 120 or dbp >= 80) else 0
        deduct("Blood-pressure observation", bp_points, f"Single entered reading: {sbp}/{dbp} mmHg")

    score = max(0, 100 - sum(item["Points"] for item in deductions))
    return score, sorted(deductions, key=lambda item: item["Points"], reverse=True)


def apply_demo_goals(profile: Mapping[str, Any], goals: Mapping[str, Any]) -> dict[str, Any]:
    """Create a scenario profile without claiming that the goals will occur."""
    scenario = dict(profile)
    original_weight = float(profile["weight_kg"])
    target_weight = float(goals.get("target_weight", original_weight))
    scenario["weight_kg"] = target_weight
    if original_weight > 0 and target_weight < original_weight:
        scenario["waist_cm"] = float(profile["waist_cm"]) * target_weight / original_weight
    if goals.get("daily_activity") == YES:
        scenario["daily_activity"] = YES
    if goals.get("daily_fruit_veg") == YES:
        scenario["daily_fruit_veg"] = YES
    if goals.get("smoke_free") == YES:
        scenario["smoker"] = NO
    if profile.get("bp_available") and goals.get("target_sbp") is not None:
        scenario["sbp"] = min(int(profile["sbp"]), int(goals["target_sbp"]))
    return scenario


def demo_trajectory(current_index: int, scenario_index: int) -> list[dict[str, Any]]:
    """Build a visibly hypothetical three-year product-demo trajectory."""
    rows: list[dict[str, Any]] = []
    for year in range(4):
        progress = min(1.0, year / 2)
        rows.append(
            {
                "Year": "Now" if year == 0 else f"Year {year}",
                "No goals modelled": max(0, current_index - year),
                "If all selected goals are achieved": round(
                    current_index + (scenario_index - current_index) * progress
                ),
            }
        )
    return rows
