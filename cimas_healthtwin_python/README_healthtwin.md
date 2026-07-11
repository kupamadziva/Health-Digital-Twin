# Cimas HealthTwin — longitudinal digital-twin demonstration

This Streamlit demo maintains a synthetic member state and evolves two copies of
that state through time:

- **Usual path:** the state continues without the selected intervention plan.
- **Intervention twin:** timed weight, activity, nutrition, smoking, BP-support,
  and adherence assumptions change the monthly state transitions.

The model follows weight, waist, systolic and diastolic pressure, HbA1c, eGFR,
activity, nutrition consistency, smoking exposure, and a synthetic state index.
Forecast uncertainty grows with time. New follow-up observations can re-anchor
the state and trigger a new simulation, completing the twin feedback loop.

The **Twin Fleet** view runs the same engine across synthetic members, ranks
members by the divergence between their parallel futures, exposes primary
intervention levers, and supports outreach-capacity planning.

The member view maintains a persistent SQLite longitudinal record containing
complete check-up snapshots, past illnesses, diagnoses, care plans, visits,
medicines, allergies, and historic readings. Users can compare any two check-ups,
see what improved or needs attention, inspect events between those visits, and
follow every measure across time. A newly saved check-up becomes the twin's
current state. A QR workflow creates a 15-minute read-only clinician link backed
by an ephemeral server-side share; the QR contains only the access link, not the
medical history itself.

Medication records follow the shape of a medication statement: current and past
medicines are stored individually with dose, unit, route, frequency, effective
dates, status, reason, prescriber, instructions, reported adherence, information
source, and last-review date. Medication starts and stops also appear in the
health journey, and active medicines are included in the clinician QR summary.
This records reported use; it is not an electronic prescription or dispensing
system.

## Condition graphs and displayed references

The member graphs show raw readings, a displayed screening boundary, the exact
distance from that boundary, a plain-language status, and a synthetic 0–100
condition score. The scores help visual comparison only; they are not validated
clinical scores or diagnoses. Future values are labelled as modelled projections.

- Adult BMI range: [CDC adult BMI categories](https://www.cdc.gov/bmi/adult-calculator/bmi-categories.html)
- Blood pressure: [American Heart Association categories](https://www.heart.org/en/health-topics/high-blood-pressure/blood-pressure-explained)
- Average blood sugar: [CDC A1C ranges](https://www.cdc.gov/diabetes/diabetes-testing/prediabetes-a1c-test.html)
- Kidney function: [National Kidney Foundation eGFR information](https://www.kidney.org/kidney-topics/estimated-glomerular-filtration-rate-egfr)

## Run

```powershell
pip install -r requirements_healthtwin.txt
streamlit run cimas_healthtwin_app.py
```

## Test

```powershell
python -m unittest discover -s tests -v
```

## Architecture

- `digital_twin.py` — state, intervention protocol, monthly transition engine,
  parallel simulation, observation assimilation, uncertainty, and events.
- `cimas_healthtwin_app.py` — Digital Twin Studio and Twin Fleet experience.
- `healthtwin_core.py` — supporting transparent screening rules retained for
  future integration.
- `healthtwin_db.py` — SQLite schema and persistence for members, complete
  check-ups, illnesses, diagnoses, and care plans.
- `healthtwin_demo.db` — seeded synthetic longitudinal demonstration database.
- `tests/` — simulation and safety regression tests.

## Important boundary

The software demonstrates genuine digital-twin mechanics, but its transition
equations and uncertainty envelopes are synthetic—not validated physiological or
clinical forecasts. Production use requires calibration against longitudinal
Cimas data, external validation, model monitoring, security, privacy controls,
auditability, and clinical governance. Production QR sharing must additionally
verify the receiving clinician, capture patient consent, use short-lived access,
and log every record view.
