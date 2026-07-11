"""Longitudinal synthetic digital-twin engine for the product demonstration.

The transition equations are intentionally transparent and illustrative. They
demonstrate twin behaviour (state, time, interventions, observations, parallel
futures) but are not validated clinical prediction equations.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from math import sqrt
from typing import Any


ENGINE_VERSION = "synthetic-twin-1.0.0"


@dataclass(frozen=True)
class TwinState:
    age: float = 47
    height_cm: float = 172
    weight_kg: float = 92
    waist_cm: float = 104
    sbp: float = 148
    dbp: float = 94
    hba1c: float = 6.1
    egfr: float = 86
    activity_days: float = 1
    diet_score: float = 2
    smoking_exposure: float = 1


@dataclass(frozen=True)
class InterventionPlan:
    start_month: int = 1
    weight_loss_kg: float = 10
    activity_target: float = 5
    diet_target: float = 7
    quit_smoking_month: int | None = 3
    bp_support_effect: float = 12
    adherence: float = 0.75


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def twin_index(state: TwinState) -> int:
    """Synthetic 0–100 state summary used only to visualise divergence."""
    bmi = state.weight_kg / ((state.height_cm / 100) ** 2)
    penalty = 0.0
    penalty += clamp((bmi - 22) * 1.4, 0, 18)
    penalty += clamp((state.sbp - 115) * 0.35, 0, 20)
    penalty += clamp((state.dbp - 75) * 0.25, 0, 8)
    penalty += clamp((state.hba1c - 5.2) * 9, 0, 18)
    penalty += clamp((90 - state.egfr) * 0.18, 0, 12)
    penalty += clamp((5 - state.activity_days) * 2, 0, 10)
    penalty += clamp((6 - state.diet_score) * 1.2, 0, 7)
    penalty += state.smoking_exposure * 12
    return round(clamp(100 - penalty, 0, 100))


def _usual_step(state: TwinState) -> TwinState:
    bmi = state.weight_kg / ((state.height_cm / 100) ** 2)
    weight_drift = 0.045 if state.activity_days < 3 else 0.01
    weight = state.weight_kg + weight_drift
    waist = state.waist_cm + weight_drift * 0.65
    sbp = state.sbp + 0.045 + max(0, bmi - 25) * 0.004
    dbp = state.dbp + 0.018
    hba1c = state.hba1c + (0.008 if bmi >= 30 else 0.004)
    decline = 0.055
    decline += 0.025 if state.sbp >= 140 else 0
    decline += 0.025 if state.hba1c >= 6.5 else 0
    return replace(
        state,
        age=state.age + 1 / 12,
        weight_kg=weight,
        waist_cm=waist,
        sbp=sbp,
        dbp=dbp,
        hba1c=hba1c,
        egfr=max(1, state.egfr - decline),
    )


def _plan_step(
    state: TwinState,
    baseline: TwinState,
    plan: InterventionPlan,
    month: int,
) -> TwinState:
    if month < plan.start_month:
        return _usual_step(state)

    adherence = clamp(plan.adherence, 0, 1)
    if adherence == 0:
        return _usual_step(state)
    activity = state.activity_days + (plan.activity_target - state.activity_days) * 0.16 * adherence
    diet = state.diet_score + (plan.diet_target - state.diet_score) * 0.14 * adherence
    smoking = state.smoking_exposure
    if plan.quit_smoking_month is not None and month >= plan.quit_smoking_month:
        smoking = max(0, 1 - adherence)

    weight_target = max(40, baseline.weight_kg - plan.weight_loss_kg)
    weight = state.weight_kg + (weight_target - state.weight_kg) * 0.075 * adherence
    waist_target = baseline.waist_cm * weight_target / baseline.weight_kg
    waist = state.waist_cm + (waist_target - state.waist_cm) * 0.075 * adherence

    weight_lost = baseline.weight_kg - weight
    activity_gain = activity - baseline.activity_days
    desired_sbp = baseline.sbp - plan.bp_support_effect * adherence - weight_lost * 0.35 - activity_gain * 0.65
    desired_dbp = baseline.dbp - plan.bp_support_effect * 0.45 * adherence - weight_lost * 0.12
    sbp = state.sbp + (desired_sbp - state.sbp) * 0.18
    dbp = state.dbp + (desired_dbp - state.dbp) * 0.16

    diet_gain = diet - baseline.diet_score
    desired_hba1c = baseline.hba1c - weight_lost * 0.025 - activity_gain * 0.035 - diet_gain * 0.025 - (1 - smoking) * 0.06
    hba1c = state.hba1c + (desired_hba1c - state.hba1c) * 0.10

    decline = 0.045
    decline += 0.018 if sbp >= 140 else 0
    decline += 0.018 if hba1c >= 6.5 else 0
    return TwinState(
        age=state.age + 1 / 12,
        height_cm=state.height_cm,
        weight_kg=weight,
        waist_cm=waist,
        sbp=sbp,
        dbp=dbp,
        hba1c=hba1c,
        egfr=max(1, state.egfr - decline),
        activity_days=activity,
        diet_score=diet,
        smoking_exposure=smoking,
    )


def _row(state: TwinState, month: int, path: str) -> dict[str, Any]:
    growth = sqrt(month / 12) if month else 0
    return {
        "Month": month,
        "Path": path,
        "Age": round(state.age, 2),
        "Weight": round(state.weight_kg, 1),
        "Waist": round(state.waist_cm, 1),
        "Systolic BP": round(state.sbp),
        "Diastolic BP": round(state.dbp),
        "HbA1c": round(state.hba1c, 2),
        "eGFR": round(state.egfr, 1),
        "Activity days": round(state.activity_days, 1),
        "Diet score": round(state.diet_score, 1),
        "Smoking exposure": round(state.smoking_exposure, 2),
        "Twin index": twin_index(state),
        "Weight uncertainty": round(0.7 + 0.6 * growth, 1),
        "BP uncertainty": round(3 + 2.5 * growth, 1),
        "HbA1c uncertainty": round(0.12 + 0.1 * growth, 2),
        "eGFR uncertainty": round(2 + 1.5 * growth, 1),
    }


def simulate_parallel(
    baseline: TwinState,
    plan: InterventionPlan,
    months: int = 36,
) -> list[dict[str, Any]]:
    usual = baseline
    planned = baseline
    rows = [_row(usual, 0, "Usual path"), _row(planned, 0, "Intervention twin")]
    for month in range(1, months + 1):
        usual = _usual_step(usual)
        planned = _plan_step(planned, baseline, plan, month)
        rows.extend((_row(usual, month, "Usual path"), _row(planned, month, "Intervention twin")))
    return rows


def assimilate_observation(state: TwinState, **observed: float) -> TwinState:
    """Re-anchor state fields to newly observed measurements."""
    allowed = {"weight_kg", "waist_cm", "sbp", "dbp", "hba1c", "egfr"}
    updates = {key: float(value) for key, value in observed.items() if key in allowed and value is not None}
    return replace(state, **updates)


def twin_events(rows: list[dict[str, Any]], plan: InterventionPlan) -> list[dict[str, Any]]:
    planned = [row for row in rows if row["Path"] == "Intervention twin"]
    events = [
        {"Month": plan.start_month, "Event": "Intervention plan starts", "Type": "Plan"},
    ]
    if plan.quit_smoking_month is not None:
        events.append({"Month": plan.quit_smoking_month, "Event": "Smoke-free goal begins", "Type": "Goal"})
    for field, threshold, event in (
        ("Systolic BP", 140, "Modelled systolic BP moves below 140"),
        ("HbA1c", 6.0, "Modelled HbA1c moves below 6.0"),
    ):
        match = next((row for row in planned[1:] if row[field] < threshold), None)
        if match:
            events.append({"Month": match["Month"], "Event": event, "Type": "Modelled milestone"})
    return sorted(events, key=lambda item: (item["Month"], item["Event"]))
