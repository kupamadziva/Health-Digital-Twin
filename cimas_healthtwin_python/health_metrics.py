"""Explainable condition-level health scores for charts.

The reference boundaries are recognisable adult screening references. The
0–100 visual scores are product communication aids, not validated clinical
scores or diagnoses.
"""

from __future__ import annotations


def condition_assessments(
    *,
    height_cm: float,
    weight_kg: float,
    sbp: float,
    dbp: float,
    hba1c: float,
    egfr: float,
    diabetes_risk: float | None = None,
) -> list[dict]:
    bmi = weight_kg / ((height_cm / 100) ** 2)
    healthy_min_weight = 18.5 * (height_cm / 100) ** 2
    healthy_max_weight = 24.9 * (height_cm / 100) ** 2
    if weight_kg > healthy_max_weight:
        weight_distance = weight_kg - healthy_max_weight
        weight_deviation = f"BMI {bmi:.1f}; {weight_distance:.1f} kg above the upper weight corresponding to BMI 24.9"
        bmi_distance = bmi - 24.9
        weight_status = "Review" if bmi >= 30 else "Monitor"
    elif weight_kg < healthy_min_weight:
        weight_distance = healthy_min_weight - weight_kg
        weight_deviation = f"BMI {bmi:.1f}; {weight_distance:.1f} kg below the lower weight corresponding to BMI 18.5"
        bmi_distance = 18.5 - bmi
        weight_status = "Review"
    else:
        weight_deviation, bmi_distance = "Within the healthy BMI range", 0
        weight_status = "On track"

    upper_excess = max(0, sbp - 120)
    lower_excess = max(0, dbp - 80)
    crossed = []
    if sbp > 120:
        crossed.append(f"upper number {upper_excess:.0f} mmHg above 120")
    elif sbp == 120:
        crossed.append("upper number at the 120 boundary")
    if dbp > 80:
        crossed.append(f"lower number {lower_excess:.0f} mmHg above 80")
    elif dbp == 80:
        crossed.append("lower number at the 80 boundary")
    if crossed:
        bp_deviation = " and ".join(crossed)
    else:
        bp_deviation = "Within the displayed screening reference"
    if sbp > 180 or dbp > 120:
        bp_status = "Urgent"
    elif sbp >= 130 or dbp >= 80:
        bp_status = "Review"
    elif sbp >= 120:
        bp_status = "Monitor"
    else:
        bp_status = "On track"

    sugar_excess = max(0, hba1c - 5.7)
    if hba1c > 5.7:
        sugar_deviation = f"{sugar_excess:.1f} percentage points above the 5.7% boundary"
    elif hba1c == 5.7:
        sugar_deviation = "At the 5.7% boundary"
    else:
        sugar_deviation = "Within the displayed screening reference"
    sugar_status = "On track" if hba1c < 5.7 else "Monitor" if hba1c < 6.5 else "Review"
    kidney_gap = max(0, 90 - egfr)
    kidney_deviation = f"{kidney_gap:.0f} points below the displayed 90 reference; age, urine ACR, and repeated results affect interpretation" if kidney_gap else "At or above the displayed 90 reference"
    kidney_status = "On track" if egfr >= 90 else "Monitor" if egfr >= 60 else "Review"

    results = [
        {"Condition":"Weight range","Score":round(max(0,100-bmi_distance*7)),"Status":weight_status,"Current":f"BMI {bmi:.1f}","Healthy":"BMI 18.5–24.9","Difference":weight_deviation},
        {"Condition":"Blood pressure","Score":round(max(0,100-max(upper_excess*1.4,lower_excess*3))),"Status":bp_status,"Current":f"{sbp:.0f}/{dbp:.0f} mmHg","Healthy":"Below 120/80","Difference":bp_deviation},
        {"Condition":"Average blood sugar","Score":round(max(0,100-sugar_excess*35)),"Status":sugar_status,"Current":f"{hba1c:.1f}%","Healthy":"Below 5.7%","Difference":sugar_deviation},
        {"Condition":"Kidney function","Score":round(min(100,max(0,egfr/90*100))),"Status":kidney_status,"Current":f"{egfr:.0f}","Healthy":"90 or higher","Difference":kidney_deviation},
    ]
    if diabetes_risk is not None:
        diabetes_gap = max(0, diabetes_risk - 11)
        diabetes_status = "On track" if diabetes_risk < 12 else "Monitor" if diabetes_risk < 25 else "Review"
        results.insert(0,{"Condition":"Type 2 diabetes","Score":round(max(0,100-diabetes_risk)),"Status":diabetes_status,"Current":f"{diabetes_risk:.0f}% screening risk","Healthy":"Low category: below 12%","Difference":f"{diabetes_gap:.0f} percentage points above the low category" if diabetes_gap else "Within the low screening category"})
    return results
