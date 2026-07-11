"""Cimas HealthTwin — polished product demo powered by a longitudinal twin."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from html import escape
from io import BytesIO
import secrets
from textwrap import dedent
from urllib.parse import urlsplit, urlunsplit

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

try:
    import qrcode
except ImportError:  # The UI provides the install command if dependencies are stale.
    qrcode = None

from digital_twin import (
    ENGINE_VERSION,
    InterventionPlan,
    TwinState,
    assimilate_observation,
    simulate_parallel,
    twin_index,
)
from healthtwin_core import NO, YES, findrisc_points
from health_metrics import condition_assessments
from healthtwin_db import (
    add_care_plan,
    add_checkup,
    add_event,
    add_medication,
    care_plans,
    checkups,
    health_events,
    latest_checkup,
    medications,
    seed_demo_data,
    update_medication_status,
)


st.set_page_config(
    page_title="Cimas HealthTwin AI",
    page_icon="🫀",
    layout="wide",
    initial_sidebar_state="collapsed",
)

seed_demo_data()

st.markdown(
    """
    <style>
      :root { color-scheme: light; }
      .stApp { background:#fafaf9; color:#1e293b; }
      [data-testid="stHeader"] { background:#fafaf9; }
      .block-container {
        max-width:1120px;
        padding-top:4.5rem;
        padding-bottom:2rem;
      }
      .stApp p,.stApp label,.stApp [data-testid="stWidgetLabel"],
      .stApp [data-testid="stMarkdownContainer"],
      .stApp [data-testid="stCaptionContainer"] { color:#334155; }
      .stApp h1,.stApp h2,.stApp h3,.stApp h4 { color:#1e293b; }
      .brand { display:flex; align-items:center; gap:.55rem; }
      .brand-name { color:#0f172a; font-size:1.35rem; font-weight:800; }
      .tagline { color:#64748b; font-size:.85rem; font-style:italic; margin-top:.1rem; }
      .section-label { color:#64748b; font-size:.7rem; font-weight:700;
        text-transform:uppercase; letter-spacing:.08em; margin:.8rem 0 .25rem; }
      .score-panel { background:#fff; border:1px solid #e2e8f0; border-radius:1rem;
        padding:1.15rem; box-shadow:0 1px 2px rgba(15,23,42,.03); }
      .score-kicker { color:#64748b; font-size:.72rem; text-transform:uppercase;
        letter-spacing:.08em; }
      .score { color:#065f46; font-size:3.35rem; font-weight:800; line-height:1; }
      .score-outof { color:#64748b; font-size:.88rem; }
      .score-change { color:#047857; font-size:.85rem; margin-left:.45rem; }
      .risk-card { background:#fff; border:1px solid; border-radius:1rem;
        padding:1rem; min-height:165px; }
      .risk-head { display:flex; align-items:center; justify-content:space-between; gap:.4rem; }
      .risk-title { color:#334155; font-size:.86rem; font-weight:700; }
      .tier { border:1px solid; border-radius:999px; padding:.12rem .48rem;
        font-size:.66rem; font-weight:700; }
      .risk-value { font-size:2rem; font-weight:800; line-height:1.2; margin-top:.35rem; }
      .risk-caption { color:#475569; font-size:.73rem; }
      .risk-change { color:#047857; font-size:.75rem; margin-top:.45rem; }
      .risk-note { color:#64748b; font-size:.7rem; margin-top:.65rem; }
      .condition-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr));
        gap:.85rem; margin:.7rem 0 1rem; }
      .condition-card { --accent:#64748b; background:#fff; border:1px solid #e2e8f0;
        border-top:4px solid var(--accent); border-radius:1rem; padding:1rem;
        box-shadow:0 1px 3px rgba(15,23,42,.05); }
      .condition-card:last-child:nth-child(odd) { grid-column:1 / -1; }
      .condition-card-head { display:flex; align-items:center; justify-content:space-between;
        gap:.5rem; margin-bottom:.8rem; }
      .condition-card-name { color:#0f172a; font-size:.92rem; font-weight:800; }
      .condition-status { color:var(--accent); background:color-mix(in srgb,var(--accent) 10%,white);
        border:1px solid color-mix(in srgb,var(--accent) 30%,white); border-radius:999px;
        padding:.16rem .52rem; font-size:.67rem; font-weight:800; }
      .condition-score-row { display:grid; grid-template-columns:1fr auto 1fr;
        align-items:center; gap:.7rem; }
      .condition-score-block { min-width:0; }
      .condition-score-block:last-child { text-align:right; }
      .condition-score-label { color:#64748b; font-size:.66rem; font-weight:700;
        text-transform:uppercase; letter-spacing:.05em; }
      .condition-score-number { color:#0f172a; font-size:2rem; line-height:1.05; font-weight:850; }
      .condition-score-number.future { color:#047857; }
      .condition-arrow { color:#94a3b8; font-size:1.25rem; }
      .condition-change { display:inline-block; margin-top:.2rem; color:#047857;
        background:#ecfdf5; border-radius:999px; padding:.12rem .42rem;
        font-size:.68rem; font-weight:800; }
      .condition-track { position:relative; height:.48rem; background:#e2e8f0;
        border-radius:999px; margin:1rem .28rem .9rem; }
      .condition-track-fill { position:absolute; inset:0 auto 0 0; border-radius:999px;
        background:color-mix(in srgb,var(--accent) 72%,white); }
      .condition-marker { position:absolute; top:50%; width:.82rem; height:.82rem;
        background:#fff; border:3px solid var(--accent); border-radius:50%;
        transform:translate(-50%,-50%); z-index:2; }
      .condition-marker.future { border-color:#047857; border-radius:2px;
        transform:translate(-50%,-50%) rotate(45deg); z-index:3; }
      .condition-reading { display:flex; justify-content:space-between; gap:1rem;
        color:#475569; font-size:.72rem; margin-bottom:.38rem; }
      .condition-reading strong { color:#1e293b; }
      .condition-gap { color:#475569; background:#f8fafc; border-radius:.55rem;
        padding:.48rem .6rem; font-size:.7rem; line-height:1.35; }
      .low { background:#ecfdf5; border-color:#a7f3d0; color:#047857; }
      .moderate { background:#fffbeb; border-color:#fde68a; color:#a16207; }
      .high { background:#fff7ed; border-color:#fed7aa; color:#c2410c; }
      .very-high { background:#fff1f2; border-color:#fecdd3; color:#be123c; }
      .neutral { background:#f8fafc; border-color:#cbd5e1; color:#475569; }
      .lever { display:flex; justify-content:space-between; gap:1rem; padding:.48rem 0;
        border-bottom:1px solid #f1f5f9; color:#334155; font-size:.84rem; }
      .lever:last-child { border-bottom:0; }
      .lever-impact { color:#047857; font-weight:800; white-space:nowrap; }
      .st-key-profile_panel { background:#fff; border:1px solid #e2e8f0;
        border-radius:1rem; padding:1rem; }
      .st-key-sim_panel { background:#064e3b; border-radius:1rem; padding:1rem; }
      .st-key-sim_panel p,.st-key-sim_panel label,
      .st-key-sim_panel [data-testid="stWidgetLabel"],
      .st-key-sim_panel [data-testid="stMarkdownContainer"] { color:#ecfdf5 !important; }
      .sim-title { color:#fff; font-weight:800; font-size:.95rem; }
      .sim-help { color:#a7f3d0; font-size:.72rem; margin-bottom:.3rem; }
      .stat-card { background:#fff; border:1px solid #e2e8f0; border-radius:1rem;
        padding:1rem; min-height:110px; }
      .stat-label { color:#64748b; font-size:.68rem; text-transform:uppercase; letter-spacing:.05em; }
      .stat-value { color:#1e293b; font-size:1.65rem; font-weight:800; margin:.2rem 0; }
      .stat-hint { color:#64748b; font-size:.69rem; }
      .footer { color:#64748b; font-size:.7rem; text-align:center;
        max-width:780px; margin:2rem auto 0; }
      div[data-testid="stMetric"] { background:#fff; border:1px solid #e2e8f0;
        padding:.75rem .9rem; border-radius:1rem; }
      div[data-testid="stMetric"] [data-testid="stMetricLabel"],
      div[data-testid="stMetric"] [data-testid="stMetricLabel"] p {
        color:#334155 !important;
        opacity:1 !important;
      }
      div[data-testid="stMetric"] [data-testid="stMetricValue"],
      div[data-testid="stMetric"] [data-testid="stMetricValue"] > div {
        color:#0f172a !important;
        opacity:1 !important;
      }
      div[data-testid="stMetric"] [data-testid="stMetricValue"] {
        font-size:clamp(1.25rem, 2.2vw, 1.75rem) !important;
        line-height:1.2 !important;
        white-space:normal !important;
        overflow:visible !important;
        text-overflow:clip !important;
      }
      div[data-testid="stMetric"] [data-testid="stMetricDelta"] {
        color:#047857 !important;
        opacity:1 !important;
      }
      @media (max-width: 768px) {
        .block-container { padding-top:5rem; }
        .condition-grid { grid-template-columns:1fr; }
        .condition-card:last-child:nth-child(odd) { grid-column:auto; }
      }
    </style>
    """,
    unsafe_allow_html=True,
)


def findrisc_pct(points: int | None) -> int | None:
    if points is None:
        return None
    if points <= 6: return 1
    if points <= 11: return 4
    if points <= 14: return 17
    if points <= 20: return 33
    return 50


def risk_tier(value: float | None, kind: str, secondary: float | None = None) -> tuple[str, str]:
    if value is None:
        return "Not calculated", "neutral"
    if kind == "diabetes":
        if value < 12: return "Low", "low"
        if value < 25: return "Moderate", "moderate"
        if value < 40: return "High", "high"
        return "Very High", "very-high"
    if kind == "bp":
        lower = secondary if secondary is not None else 0
        if value > 180 or lower > 120: return "Urgent", "very-high"
        if value >= 130 or lower >= 80: return "Review", "high"
        if value >= 120: return "Monitor", "moderate"
        if lower < 80: return "On track", "low"
        return "Urgent", "very-high"
    if kind == "hba1c":
        if value < 5.7: return "On track", "low"
        if value < 6.5: return "Monitor", "moderate"
        return "Review", "high"
    if value >= 90: return "On track", "low"
    if value >= 60: return "Monitor", "moderate"
    return "Review", "high"


def risk_card(title: str, value: str, numeric: float | None, goal_value: str, delta: str, kind: str, note: str, secondary: float | None = None) -> None:
    tier, css = risk_tier(numeric, kind, secondary)
    st.markdown(
        f"""
        <div class="risk-card {css}">
          <div class="risk-head"><div class="risk-title">{escape(title)}</div><div class="tier {css}">{tier}</div></div>
          <div class="risk-value">{escape(value)}</div>
          <div class="risk-caption">today</div>
          <div class="risk-change">→ {escape(goal_value)} with selected plan {escape(delta)}</div>
          <div class="risk-note">ⓘ {escape(note)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def stat_card(label: str, value: str, hint: str) -> None:
    st.markdown(f'<div class="stat-card"><div class="stat-label">{escape(label)}</div><div class="stat-value">{escape(value)}</div><div class="stat-hint">{escape(hint)}</div></div>', unsafe_allow_html=True)


@st.cache_resource
def clinician_share_store() -> dict:
    """Ephemeral server-memory store used only for the QR demonstration."""
    return {}


def current_app_address() -> str:
    """Return the current app URL without query parameters for QR sharing."""
    try:
        current_url = str(st.context.url or "").strip()
    except Exception:
        current_url = ""
    if not current_url:
        return "http://localhost:8501"
    parsed = urlsplit(current_url)
    clean_path = parsed.path.rstrip("/")
    return urlunsplit((parsed.scheme, parsed.netloc, clean_path, "", ""))


def patient_summary(name: str, current: TwinState, events: list[dict], checkup_rows: list[dict], medication_rows: list[dict]) -> dict:
    recent = sorted(events, key=lambda item: item["event_date"], reverse=True)[:5]
    illnesses = [item for item in events if item["event_type"] in {"Illness", "Hospital stay", "Diagnosis", "Clinical finding"}]
    latest = checkup_rows[-1] if checkup_rows else {}
    return {
        "name": name,
        "generated": datetime.now().strftime("%d %b %Y, %H:%M"),
        "latest": {
            "Weight": f"{current.weight_kg:.1f} kg",
            "Blood pressure": f"{current.sbp:.0f}/{current.dbp:.0f} mmHg",
            "Average blood sugar": f"{current.hba1c:.1f}%",
            "Kidney function": f"{current.egfr:.0f}",
        },
        "allergies": latest.get("allergies") or "No allergies recorded",
        "medicines": [item for item in medication_rows if item["status"] == "Active"],
        "illnesses": illnesses,
        "recent": recent,
    }


def render_clinician_record(token: str) -> None:
    record = clinician_share_store().get(token)
    if not record or datetime.now() >= record["expires"]:
        st.error("This health-record link is invalid or has expired.")
        st.stop()
    summary = record["summary"]
    st.markdown(f"## 🫀 Health summary — {escape(summary['name'])}")
    st.caption(f"Shared for clinical review · generated {summary['generated']} · read-only")
    latest = st.columns(4)
    for column, (label, value) in zip(latest, summary["latest"].items()):
        column.metric(label, value)
    st.markdown("### Important information")
    st.write(f"**Medicine allergies:** {summary['allergies']}")
    st.markdown("**Current medicines**")
    if summary["medicines"]:
        medicine_df = pd.DataFrame(summary["medicines"]).rename(columns={"medication_name":"Medicine","dose_value":"Dose","dose_unit":"Unit","route":"How taken","frequency":"Frequency","reason":"Reason","prescriber":"Prescriber","instructions":"Instructions","adherence":"Taking status"})
        st.dataframe(medicine_df[["Medicine","Dose","Unit","How taken","Frequency","Reason","Prescriber","Instructions","Taking status"]],width="stretch",hide_index=True)
    else:
        st.write("No current medicines recorded.")
    st.markdown("### Past illnesses and diagnoses")
    illness_df = pd.DataFrame(summary["illnesses"])
    if illness_df.empty:
        st.info("No past illnesses or diagnoses are recorded.")
    else:
        illness_df = illness_df.rename(columns={"event_date":"Date","event_type":"Type","title":"Event","details":"Details","provider":"Provider","outcome":"Outcome"})
        st.dataframe(illness_df[["Date","Type","Event","Details","Provider","Outcome"]], width="stretch", hide_index=True)
    st.markdown("### Recent health record")
    recent_df = pd.DataFrame(summary["recent"]).rename(columns={"event_date":"Date","event_type":"Type","title":"Event","details":"Details","provider":"Provider","outcome":"Outcome"})
    st.dataframe(recent_df[["Date","Type","Event","Details","Provider","Outcome"]], width="stretch", hide_index=True)
    st.warning("Demonstration record. Confirm all information with the patient and the source clinical system before making decisions.")
    st.stop()


def profile_and_plan(saved: dict) -> tuple[str, dict, TwinState, InterventionPlan, int]:
    with st.container(key="profile_panel"):
        st.markdown("#### 📋 Member profile")
        name = st.text_input("Member name", "Tendai M.")
        st.caption(f"Latest saved check-up: {saved['checkup_date']}")
        st.markdown('<div class="section-label">Vitals</div>', unsafe_allow_html=True)
        age = st.slider("Age", 18, 80, int(saved["age"]), format="%d years")
        sex = st.radio("Sex", ["Male", "Female"], horizontal=True)
        height = st.slider("Height", 140, 200, int(saved["height_cm"]), format="%d cm")
        weight = st.slider("Weight", 40, 150, int(saved["weight_kg"]), format="%d kg")
        waist = st.slider("Waist circumference", 60, 140, int(saved["waist_cm"]), format="%d cm")
        bp_cols = st.columns(2)
        sbp = bp_cols[0].number_input("Upper BP number", 80, 240, int(saved["sbp"]), help="The first number in a blood-pressure reading")
        dbp = bp_cols[1].number_input("Lower BP number", 40, 150, int(saved["dbp"]), help="The second number in a blood-pressure reading")
        hba1c = st.slider("Average blood sugar (HbA1c)", 4.0, 14.0, float(saved["hba1c"]), .1, format="%.1f%%", help="A blood test showing average blood sugar over roughly three months")
        egfr = st.slider("Kidney function (eGFR)", 10, 140, int(saved["egfr"]), help="An estimate of how well the kidneys filter blood")
        st.markdown('<div class="section-label">Lifestyle & history</div>', unsafe_allow_html=True)
        activity = st.slider("Physical activity", 0, 7, int(saved["activity_days"]), format="%d days/week")
        diet = st.slider("Healthy nutrition", 0, 7, int(saved["diet_score"]), format="%d days/week")
        smoker = st.checkbox("Smoker", bool(saved["smoker"]))
        on_bp_meds = st.checkbox("On BP medication", bool(saved["on_bp_meds"]))
        high_glucose = st.checkbox("History of high glucose", bool(saved["history_high_glucose"]))
        family_options = ["None", "Distant relative", "First-degree relative"]
        family = st.selectbox("Family history of diabetes", family_options, index=family_options.index(saved["family_history_diabetes"]))

    with st.container(key="sim_panel"):
        st.markdown('<div class="sim-title">✨ What if…?</div><div class="sim-help">Choose achievable changes and compare where they could lead.</div>', unsafe_allow_html=True)
        loss = st.slider("Target weight loss", 0, min(30, weight - 40), 10, format="%d kg", key="plan_loss")
        activity_target = st.slider("Activity target", 0, 7, 5, format="%d days/week", key="plan_activity")
        diet_target = st.slider("Nutrition target", 0, 7, 6, format="%d days/week", key="plan_diet")
        quit_smoking = st.checkbox("Smoke-free", value=smoker, key="plan_smoking")
        bp_support = st.checkbox("Improve blood-pressure control", True, key="plan_bp")
        adherence = st.slider("How closely the plan is followed", 0, 100, 75, format="%d%%", key="plan_adherence") / 100
        horizon = st.select_slider("How far ahead to look", [12, 24, 36, 48, 60], 36, format_func=lambda x: f"{x} months", key="plan_horizon")

    profile = {
        "age": age, "sex": sex, "height_cm": height, "weight_kg": weight,
        "waist_cm": waist, "daily_activity": YES if activity >= 5 else NO,
        "daily_fruit_veg": YES if diet >= 5 else NO, "on_bp_meds": YES if on_bp_meds else NO,
        "history_high_glucose": YES if high_glucose else NO,
        "family_history_diabetes": family, "diagnosed_diabetes": NO,
    }
    state = TwinState(age=age, height_cm=height, weight_kg=weight, waist_cm=waist, sbp=sbp, dbp=dbp, hba1c=hba1c, egfr=egfr, activity_days=activity, diet_score=diet, smoking_exposure=1 if smoker else 0)
    plan = InterventionPlan(weight_loss_kg=loss, activity_target=activity_target, diet_target=diet_target, quit_smoking_month=3 if quit_smoking else None, bp_support_effect=12 if bp_support else 0, adherence=adherence)
    return name, profile, state, plan, horizon


def chart_for(data: pd.DataFrame, metric: str, height_cm: float) -> go.Figure:
    mapping = {
        "Overall": ("Twin index", "Overall health score"),
        "Weight": ("Weight", "Weight (kg)"),
        "Blood pressure": ("Systolic BP", "Upper blood-pressure number"),
        "Average blood sugar": ("HbA1c", "Average blood sugar (%)"),
        "Kidney function": ("eGFR", "Kidney function"),
    }
    field, axis_label = mapping[metric]
    figure = go.Figure()
    for path, color, dash in (("Usual path", "#94a3b8", "dot"), ("Intervention twin", "#047857", "solid")):
        subset = data[data["Path"] == path]
        figure.add_trace(go.Scatter(x=subset["Month"], y=subset[field], mode="lines", name="If nothing changes (modelled)" if path == "Usual path" else "With your plan (modelled)", line={"color":color,"width":3 if path == "Intervention twin" else 2,"dash":dash}, hovertemplate="Month %{x}: %{y}<extra></extra>"))
    if metric == "Weight":
        healthy_low = 18.5 * (height_cm / 100) ** 2
        healthy_high = 24.9 * (height_cm / 100) ** 2
        figure.add_hrect(y0=healthy_low,y1=healthy_high,fillcolor="rgba(16,185,129,.10)",line_width=0,annotation_text="Healthy BMI range",annotation_position="top left",annotation_font_color="#065f46")
    else:
        reference = {"Overall":80,"Blood pressure":120,"Average blood sugar":5.7,"Kidney function":90}[metric]
        figure.add_hline(y=reference,line_color="#10b981",line_dash="dash",annotation_text={"Overall":"Strong score: 80+","Blood pressure":"Normal boundary: below 120","Average blood sugar":"Normal boundary: below 5.7%","Kidney function":"Reference: 90+"}[metric],annotation_position="top left",annotation_font_color="#065f46")
    figure.update_layout(
        height=330,
        margin={"l":70,"r":25,"t":62,"b":62},
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        font={"color":"#334155","size":11},
        hovermode="x unified",
        legend={"orientation":"h","y":1.18,"x":0,"xanchor":"left","yanchor":"top","bgcolor":"rgba(255,255,255,.95)","bordercolor":"#cbd5e1","borderwidth":1,"font":{"color":"#0f172a","size":11},"title":{"text":"PATH","font":{"color":"#64748b","size":9}}},
        xaxis={"title":{"text":"Months from latest check-up","font":{"color":"#334155","size":11}},"tickfont":{"color":"#334155","size":10},"gridcolor":"#e2e8f0","linecolor":"#94a3b8","linewidth":1,"showline":True,"ticks":"outside","tickcolor":"#94a3b8","dtick":6,"zeroline":False},
        yaxis={"title":{"text":axis_label,"font":{"color":"#334155","size":11}},"tickfont":{"color":"#334155","size":10},"gridcolor":"#e2e8f0","linecolor":"#94a3b8","linewidth":1,"showline":True,"ticks":"outside","tickcolor":"#94a3b8","zeroline":False},
        hoverlabel={"bgcolor":"#ffffff","bordercolor":"#cbd5e1","font":{"color":"#0f172a"}},
    )
    return figure


def change_label(field: str, earlier: float, later: float, earlier_conditions: dict | None = None, later_conditions: dict | None = None) -> str:
    condition_map = {"Weight":"Weight range","Upper BP":"Blood pressure","Lower BP":"Blood pressure","Average blood sugar":"Average blood sugar","Kidney function":"Kidney function"}
    condition = condition_map.get(field)
    if condition and earlier_conditions and later_conditions:
        before = earlier_conditions[condition]
        after = later_conditions[condition]
        if before["Status"] == after["Status"] == "On track":
            return "Remained within reference"
        score_change = after["Score"] - before["Score"]
        if score_change > 1:
            return "Improved"
        if score_change < -1:
            return "Needs attention"
        return "Stable"
    difference = later - earlier
    if abs(difference) < 0.05:
        return "No meaningful change"
    higher_is_better = field in {"HealthTwin score", "Kidney function", "Active days", "Healthy-eating days"}
    improved = difference > 0 if higher_is_better else difference < 0
    return "Improved" if improved else "Needs attention"


def health_record_section(name: str, current: TwinState, plan: InterventionPlan, horizon: int) -> None:
    member_id = "HT-001"
    checkup_rows = checkups(member_id)
    event_rows = health_events(member_id)
    plan_rows = care_plans(member_id)
    medication_rows = medications(member_id)

    st.markdown("## Health record and check-up comparison")
    st.caption("See how the member changed between visits, what happened between them, and whether the care plan is working.")
    journey_tab, compare_tab, trends_tab, checkup_tab, medications_tab, events_tab, share_tab = st.tabs(
        ["Health journey", "Compare check-ups", "All trends", "Complete a check-up", "Medications", "Illnesses & care", "Share with a doctor"]
    )

    with journey_tab:
        timeline = []
        for row in checkup_rows:
            timeline.append({"Date":row["checkup_date"],"Type":"Complete check-up","What happened":f"HealthTwin score {row['twin_score']}/100","Details":row["notes"],"Outcome":f"BP {row['sbp']:.0f}/{row['dbp']:.0f} · Weight {row['weight_kg']:.1f} kg"})
        for row in event_rows:
            timeline.append({"Date":row["event_date"],"Type":row["event_type"],"What happened":row["title"],"Details":row["details"],"Outcome":row["outcome"]})
        timeline_df = pd.DataFrame(timeline).sort_values("Date", ascending=False)
        st.dataframe(timeline_df, width="stretch", hide_index=True)
        summary = st.columns(5)
        summary[0].metric("Years tracked", f"{(pd.to_datetime(checkup_rows[-1]['checkup_date'])-pd.to_datetime(checkup_rows[0]['checkup_date'])).days/365.25:.1f}")
        summary[1].metric("Complete check-ups", len(checkup_rows))
        summary[2].metric("Illnesses / findings", sum(row["event_type"] in {"Illness","Diagnosis","Clinical finding","Hospital stay"} for row in event_rows))
        summary[3].metric("Care plans", len(plan_rows))
        summary[4].metric("Current medicines", sum(row["status"] == "Active" for row in medication_rows))

    with compare_tab:
        labels = [f"{row['checkup_date']} · score {row['twin_score']}" for row in checkup_rows]
        selectors = st.columns(2)
        earlier_label = selectors[0].selectbox("Earlier check-up", labels, index=0)
        later_label = selectors[1].selectbox("Later check-up", labels, index=len(labels)-1)
        earlier = checkup_rows[labels.index(earlier_label)]
        later = checkup_rows[labels.index(later_label)]
        if earlier["checkup_date"] >= later["checkup_date"]:
            st.info("Choose an earlier visit on the left and a later visit on the right.")
        else:
            key_changes = st.columns(4)
            key_changes[0].metric("HealthTwin score", later["twin_score"], delta=later["twin_score"]-earlier["twin_score"])
            key_changes[1].metric("Weight", f"{later['weight_kg']:.1f} kg", delta=f"{later['weight_kg']-earlier['weight_kg']:+.1f} kg", delta_color="inverse")
            key_changes[2].metric("Blood pressure", f"{later['sbp']:.0f}/{later['dbp']:.0f}", delta=f"{later['sbp']-earlier['sbp']:+.0f} upper", delta_color="inverse")
            key_changes[3].metric("Average blood sugar", f"{later['hba1c']:.1f}%", delta=f"{later['hba1c']-earlier['hba1c']:+.1f}", delta_color="inverse")

            fields = [
                ("HealthTwin score","twin_score","points"),("Weight","weight_kg","kg"),("Waist","waist_cm","cm"),
                ("Upper BP","sbp","mmHg"),("Lower BP","dbp","mmHg"),("Average blood sugar","hba1c","%"),
                ("Kidney function","egfr",""),("Active days","activity_days","days/week"),("Healthy-eating days","diet_score","days/week"),
            ]
            earlier_conditions = {item["Condition"]:item for item in condition_assessments(height_cm=earlier["height_cm"],weight_kg=earlier["weight_kg"],sbp=earlier["sbp"],dbp=earlier["dbp"],hba1c=earlier["hba1c"],egfr=earlier["egfr"])}
            later_conditions = {item["Condition"]:item for item in condition_assessments(height_cm=later["height_cm"],weight_kg=later["weight_kg"],sbp=later["sbp"],dbp=later["dbp"],hba1c=later["hba1c"],egfr=later["egfr"])}
            comparison = []
            for label, field, unit in fields:
                old, new = float(earlier[field]), float(later[field])
                comparison.append({"Health measure":label,"Earlier":f"{old:g} {unit}".strip(),"Later":f"{new:g} {unit}".strip(),"Change":f"{new-old:+.1f}","What it means":change_label(label,old,new,earlier_conditions,later_conditions)})
            st.dataframe(pd.DataFrame(comparison), width="stretch", hide_index=True)
            improved = [item["Health measure"] for item in comparison if item["What it means"] == "Improved"]
            attention = [item["Health measure"] for item in comparison if item["What it means"] == "Needs attention"]
            if attention:
                st.warning(f"Between these visits, the main areas needing attention were: {', '.join(attention)}.")
            if improved:
                st.success(f"Improvements were recorded in: {', '.join(improved)}.")

            between = [row for row in event_rows if earlier["checkup_date"] < row["event_date"] <= later["checkup_date"]]
            st.markdown("#### What happened between these check-ups")
            if between:
                st.dataframe(pd.DataFrame(between).rename(columns={"event_date":"Date","event_type":"Type","title":"Event","details":"Details","outcome":"Outcome"})[["Date","Type","Event","Details","Outcome"]], width="stretch", hide_index=True)
            else:
                st.info("No illnesses, diagnoses, or care events were recorded between these visits.")

    with trends_tab:
        trend_data = pd.DataFrame(checkup_rows)
        trend_data["checkup_date"] = pd.to_datetime(trend_data["checkup_date"])
        choices = {
            "HealthTwin score":"twin_score","Weight":"weight_kg",
            "Blood pressure":None,"Average blood sugar":"hba1c","Kidney function":"egfr",
        }
        selected = st.selectbox("Health measure", list(choices))
        field = choices[selected]
        figure = go.Figure()
        if selected == "Blood pressure":
            figure.add_trace(go.Scatter(x=trend_data["checkup_date"],y=trend_data["sbp"],mode="lines+markers",name="Upper number",line={"color":"#047857","width":3},marker={"size":8},customdata=trend_data["dbp"],hovertemplate="%{x|%d %b %Y}<br>Reading: %{y}/%{customdata}<extra></extra>"))
            figure.add_trace(go.Scatter(x=trend_data["checkup_date"],y=trend_data["dbp"],mode="lines+markers",name="Lower number",line={"color":"#0f766e","width":2},marker={"size":7},showlegend=True,hovertemplate="%{x|%d %b %Y}<br>Lower: %{y}<extra></extra>"))
        else:
            figure.add_trace(go.Scatter(x=trend_data["checkup_date"],y=trend_data[field],mode="lines+markers",name=selected,line={"color":"#047857","width":3},marker={"size":8},hovertemplate="%{x|%d %b %Y}<br>%{y}<extra></extra>"))
        if selected == "Weight":
            low=18.5*(float(trend_data.iloc[-1]["height_cm"])/100)**2; high=24.9*(float(trend_data.iloc[-1]["height_cm"])/100)**2
            figure.add_hrect(y0=low,y1=high,fillcolor="rgba(16,185,129,.10)",line_width=0,annotation_text="Healthy BMI range",annotation_position="top left",annotation_font_color="#065f46")
        else:
            if selected == "Blood pressure":
                figure.add_hline(y=120,line_color="#10b981",line_dash="dash",annotation_text="Upper reference: below 120",annotation_position="top left",annotation_font_color="#065f46")
                figure.add_hline(y=80,line_color="#34d399",line_dash="dot",annotation_text="Lower reference: below 80",annotation_position="bottom left",annotation_font_color="#065f46")
            else:
                reference={"HealthTwin score":80,"Average blood sugar":5.7,"Kidney function":90}[selected]
                label={"HealthTwin score":"Strong score: 80+","Average blood sugar":"Normal boundary: below 5.7%","Kidney function":"Reference: 90+"}[selected]
                figure.add_hline(y=reference,line_color="#10b981",line_dash="dash",annotation_text=label,annotation_position="top left",annotation_font_color="#065f46")
        figure.update_layout(height=330,margin={"l":70,"r":25,"t":58,"b":60},paper_bgcolor="#ffffff",plot_bgcolor="#ffffff",font={"color":"#334155"},legend={"orientation":"h","y":1.16,"x":0,"bgcolor":"rgba(255,255,255,.95)","bordercolor":"#cbd5e1","borderwidth":1,"font":{"color":"#0f172a","size":11}},xaxis={"title":{"text":"Check-up date","font":{"color":"#334155","size":11}},"tickfont":{"color":"#334155","size":10},"gridcolor":"#e2e8f0","showline":True,"linecolor":"#94a3b8","ticks":"outside","tickcolor":"#94a3b8"},yaxis={"title":{"text":selected,"font":{"color":"#334155","size":11}},"tickfont":{"color":"#334155","size":10},"gridcolor":"#e2e8f0","showline":True,"linecolor":"#94a3b8","ticks":"outside","tickcolor":"#94a3b8"},hoverlabel={"bgcolor":"#ffffff","font":{"color":"#0f172a"}})
        st.plotly_chart(figure,width="stretch",config={"displayModeBar":False},theme=None)

        st.markdown("#### Individual condition scores over time")
        condition_history=[]
        for row in checkup_rows:
            assessments=condition_assessments(height_cm=row["height_cm"],weight_kg=row["weight_kg"],sbp=row["sbp"],dbp=row["dbp"],hba1c=row["hba1c"],egfr=row["egfr"])
            for item in assessments:
                condition_history.append({"Date":pd.to_datetime(row["checkup_date"]),"Condition":item["Condition"],"Score":item["Score"],"Status":item["Status"],"Current":item["Current"],"Reference":item["Healthy"],"Difference":item["Difference"]})
        condition_history_df=pd.DataFrame(condition_history)
        score_figure=go.Figure()
        for condition in condition_history_df["Condition"].unique():
            subset=condition_history_df[condition_history_df["Condition"]==condition]
            hover_data=list(zip(subset["Current"],subset["Reference"],subset["Difference"],subset["Status"]))
            score_figure.add_trace(go.Scatter(x=subset["Date"],y=subset["Score"],mode="lines+markers",name=condition,customdata=hover_data,hovertemplate="%{x|%d %b %Y}<br>Score: %{y}/100<br>Reading: %{customdata[0]}<br>Reference: %{customdata[1]}<br>Gap: %{customdata[2]}<br>Status: %{customdata[3]}<extra>"+condition+"</extra>"))
        score_figure.update_layout(height=390,margin={"l":70,"r":25,"t":78,"b":62},paper_bgcolor="#ffffff",plot_bgcolor="#ffffff",font={"color":"#334155"},legend={"orientation":"h","y":1.22,"x":0,"bgcolor":"rgba(255,255,255,.96)","bordercolor":"#cbd5e1","borderwidth":1,"font":{"color":"#0f172a","size":10},"title":{"text":"CONDITION","font":{"color":"#64748b","size":9}}},xaxis={"title":{"text":"Check-up date","font":{"color":"#334155","size":11}},"tickfont":{"color":"#334155","size":10},"gridcolor":"#e2e8f0","showline":True,"linecolor":"#94a3b8","ticks":"outside","tickcolor":"#94a3b8"},yaxis={"title":{"text":"Condition health score (0–100)","font":{"color":"#334155","size":11}},"tickfont":{"color":"#334155","size":10},"range":[0,100],"gridcolor":"#e2e8f0","showline":True,"linecolor":"#94a3b8","ticks":"outside","tickcolor":"#94a3b8"},hoverlabel={"bgcolor":"#ffffff","font":{"color":"#0f172a"}})
        st.plotly_chart(score_figure,width="stretch",config={"displayModeBar":False},theme=None)
        st.caption("Hover over any point to see exactly how far that reading was from the healthy reference at that check-up.")

    with checkup_tab:
        st.write("Save a complete snapshot. It becomes the new current state and can be compared with every earlier visit.")
        latest = checkup_rows[-1]
        with st.form("complete_checkup"):
            checkup_date = st.date_input("Check-up date", date.today())
            cols = st.columns(4)
            weight = cols[0].number_input("Weight (kg)",40.0,180.0,float(current.weight_kg),.1)
            waist = cols[1].number_input("Waist (cm)",50.0,180.0,float(current.waist_cm),.1)
            sbp = cols[2].number_input("Upper BP",80,240,int(current.sbp))
            dbp = cols[3].number_input("Lower BP",40,150,int(current.dbp))
            hba1c = cols[0].number_input("Average blood sugar",4.0,14.0,float(current.hba1c),.1)
            egfr = cols[1].number_input("Kidney function",1.0,180.0,float(current.egfr),.1)
            activity = cols[2].number_input("Active days",0,7,int(current.activity_days))
            diet = cols[3].number_input("Healthy-eating days",0,7,int(current.diet_score))
            smoker = st.checkbox("Currently smokes",bool(current.smoking_exposure),key="db_smoker")
            on_meds = st.checkbox("Taking blood-pressure medicine",bool(latest["on_bp_meds"]),key="db_meds")
            medication_summary = "; ".join(f"{item['medication_name']} {item['dose_value']} {item['dose_unit']} {item['frequency']}" for item in medication_rows if item["status"] == "Active") or "None recorded"
            medication_list_text = st.text_input("Current medications",medication_summary,disabled=True,help="Manage names and dosages in the Medications tab")
            allergies = st.text_input("Medicine allergies",latest["allergies"] or "No known allergies")
            notes = st.text_area("Check-up notes")
            save_checkup = st.form_submit_button("Save complete check-up",type="primary")
        if save_checkup:
            saved_state = TwinState(age=current.age,height_cm=current.height_cm,weight_kg=weight,waist_cm=waist,sbp=sbp,dbp=dbp,hba1c=hba1c,egfr=egfr,activity_days=activity,diet_score=diet,smoking_exposure=1 if smoker else 0)
            add_checkup({"member_id":member_id,"checkup_date":checkup_date.isoformat(),"age":round(current.age),"height_cm":current.height_cm,"weight_kg":weight,"waist_cm":waist,"sbp":sbp,"dbp":dbp,"hba1c":hba1c,"egfr":egfr,"activity_days":activity,"diet_score":diet,"smoker":int(smoker),"on_bp_meds":int(on_meds),"history_high_glucose":latest["history_high_glucose"],"family_history_diabetes":latest["family_history_diabetes"],"twin_score":twin_index(saved_state),"medications":medication_list_text,"allergies":allergies,"notes":notes or "Complete check-up."})
            add_care_plan({"member_id":member_id,"plan_date":checkup_date.isoformat(),"weight_loss_goal":plan.weight_loss_kg,"activity_target":plan.activity_target,"diet_target":plan.diet_target,"smoke_free":int(plan.quit_smoking_month is not None),"bp_support":int(plan.bp_support_effect>0),"adherence":plan.adherence,"horizon_months":horizon,"status":"Active"})
            st.session_state.observations = [{"Weight":weight,"Systolic BP":sbp,"Diastolic BP":dbp,"HbA1c":hba1c,"eGFR":egfr}]
            st.success("Complete check-up saved. The current twin has been updated.")

    with medications_tab:
        active_medications = [item for item in medication_rows if item["status"] == "Active"]
        past_medications = [item for item in medication_rows if item["status"] != "Active"]
        st.markdown("#### Current medications and dosages")
        st.caption("This is the reconciled list reported by the patient or clinician. Confirm it at every check-up.")
        if active_medications:
            active_df = pd.DataFrame(active_medications).rename(columns={"medication_name":"Medicine","dose_value":"Dose","dose_unit":"Unit","route":"How taken","frequency":"How often","start_date":"Started","reason":"Reason","prescriber":"Prescriber","instructions":"Instructions","adherence":"Taking status","last_reviewed":"Last reviewed"})
            st.dataframe(active_df[["Medicine","Dose","Unit","How taken","How often","Started","Reason","Prescriber","Instructions","Taking status","Last reviewed"]],width="stretch",hide_index=True)
        else:
            st.info("No current medications are recorded.")

        with st.expander("Add a medication",expanded=not active_medications):
            with st.form("add_medication_form",clear_on_submit=True):
                medication_cols=st.columns(3)
                medication_name=medication_cols[0].text_input("Medicine name")
                dose_value=medication_cols[1].text_input("Dose",placeholder="e.g. 5")
                dose_unit=medication_cols[2].selectbox("Unit",["mg","micrograms","g","mL","tablet(s)","capsule(s)","puff(s)","unit(s)","other"])
                route=medication_cols[0].selectbox("How it is taken",["By mouth","Inhaled","Injection","Applied to skin","Eye","Ear","Other"])
                frequency=medication_cols[1].selectbox("How often",["Once daily","Twice daily","Three times daily","Four times daily","Once weekly","As needed","Other"])
                start_date=medication_cols[2].date_input("Start date",date.today())
                status=medication_cols[0].selectbox("Status",["Active","Completed","Stopped","On hold"])
                end_date=None
                if status in {"Completed","Stopped"}:
                    end_date=medication_cols[1].date_input("End date",date.today())
                reason=st.text_input("Reason for taking it")
                prescriber=st.text_input("Prescribed or confirmed by", "Cimas clinic")
                instructions=st.text_area("Directions or special instructions",placeholder="For example: take with food")
                adherence=st.selectbox("Is it being taken as directed?",["Usually takes as directed","Sometimes misses doses","Not currently taking","Not reviewed"])
                information_source=st.selectbox("Information source",["Clinician record","Patient reported","Medicine container","Pharmacy record","Caregiver reported"])
                save_medication=st.form_submit_button("Save medication",type="primary")
            if save_medication:
                if not medication_name.strip() or not dose_value.strip():
                    st.error("Enter both the medicine name and dose.")
                else:
                    add_medication({"member_id":member_id,"medication_name":medication_name.strip(),"dose_value":dose_value.strip(),"dose_unit":dose_unit,"route":route,"frequency":frequency,"start_date":start_date.isoformat(),"end_date":end_date.isoformat() if end_date else None,"status":status,"reason":reason.strip(),"prescriber":prescriber.strip(),"instructions":instructions.strip(),"adherence":adherence,"information_source":information_source,"last_reviewed":date.today().isoformat()})
                    add_event({"member_id":member_id,"event_date":start_date.isoformat(),"event_type":"Medicine","title":f"{medication_name.strip()} {dose_value.strip()} {dose_unit}","details":f"{route}; {frequency}. {instructions.strip()}","provider":prescriber.strip(),"outcome":status})
                    st.success("Medication and dosage saved to the health record.")

        if active_medications:
            with st.expander("Stop or complete a current medication"):
                medication_options={f"{item['medication_name']} · {item['dose_value']} {item['dose_unit']} · {item['frequency']}":item for item in active_medications}
                with st.form("stop_medication_form"):
                    selected_medication=st.selectbox("Medication",list(medication_options))
                    new_status=st.selectbox("New status",["Stopped","Completed","On hold"])
                    medication_end=st.date_input("Date",date.today())
                    stop_reason=st.text_input("Reason or note")
                    save_stop=st.form_submit_button("Update medication status")
                if save_stop:
                    item=medication_options[selected_medication]
                    update_medication_status(item["medication_id"],new_status,medication_end.isoformat() if new_status != "On hold" else None,date.today().isoformat())
                    add_event({"member_id":member_id,"event_date":medication_end.isoformat(),"event_type":"Medicine","title":f"{item['medication_name']} marked {new_status.lower()}","details":stop_reason.strip(),"provider":"Medication review","outcome":new_status})
                    st.success("Medication status updated.")

        if past_medications:
            with st.expander("Past medications"):
                past_df=pd.DataFrame(past_medications).rename(columns={"medication_name":"Medicine","dose_value":"Dose","dose_unit":"Unit","frequency":"How often","start_date":"Started","end_date":"Ended","status":"Status","reason":"Reason","prescriber":"Prescriber"})
                st.dataframe(past_df[["Medicine","Dose","Unit","How often","Started","Ended","Status","Reason","Prescriber"]],width="stretch",hide_index=True)

    with events_tab:
        events_df = pd.DataFrame(event_rows).rename(columns={"event_date":"Date","event_type":"Type","title":"Event","details":"Details","provider":"Provider","outcome":"Outcome"})
        st.dataframe(events_df[["Date","Type","Event","Details","Provider","Outcome"]].sort_values("Date",ascending=False),width="stretch",hide_index=True)
        with st.form("health_event_form",clear_on_submit=True):
            event_cols=st.columns(3)
            event_date=event_cols[0].date_input("Event date",date.today())
            event_type=event_cols[1].selectbox("Type",["Illness","Diagnosis","Clinical finding","Hospital stay","Injury","Medicine","Care plan"])
            provider=event_cols[2].text_input("Doctor or facility","Cimas clinic")
            title=st.text_input("What happened?")
            details=st.text_area("Symptoms, treatment, or useful details")
            outcome=st.text_input("Outcome",placeholder="Recovered, ongoing, under review…")
            save_event=st.form_submit_button("Add event",type="primary")
        if save_event and title.strip():
            add_event({"member_id":member_id,"event_date":event_date.isoformat(),"event_type":event_type,"title":title.strip(),"details":details.strip(),"provider":provider.strip(),"outcome":outcome.strip()})
            st.success("Health event saved to the database.")

    with share_tab:
        st.markdown("#### Create temporary doctor access")
        st.write("The QR opens a read-only summary of check-ups, illnesses, medicines, allergies, and recent care.")
        detected_address=current_app_address()
        base_url=st.text_input("App address used by the QR code",detected_address,help="This is copied automatically from the address of the app currently open in your browser.")
        if st.button("Generate secure QR code",type="primary"):
            token=secrets.token_urlsafe(24)
            clinician_share_store()[token]={"summary":patient_summary(name,current,event_rows,checkup_rows,medication_rows),"expires":datetime.now()+timedelta(minutes=15)}
            st.session_state.share_token=token
        token=st.session_state.get("share_token"); record=clinician_share_store().get(token) if token else None
        if record and datetime.now()<record["expires"]:
            clinician_url=f"{base_url.rstrip('/')}?share={token}"; qr_image=qrcode.make(clinician_url) if qrcode else None
            qr_col,info_col=st.columns([1,2])
            with qr_col:
                if qr_image:
                    buffer=BytesIO(); qr_image.save(buffer,format="PNG"); st.image(buffer.getvalue(),width=220)
            with info_col:
                st.success("Doctor-access link created for 15 minutes.")
                st.write("The QR contains only a temporary link—not the medical history itself.")
                if st.button("Revoke doctor access"):
                    clinician_share_store().pop(token,None); st.session_state.pop("share_token",None); st.rerun()
            st.markdown("**Copy or open the address encoded in the QR code:**")
            st.code(clinician_url,language=None)
            st.caption("Use the copy icon in the top-right corner of the address box.")
            st.link_button("Open doctor view",clinician_url)


def member_view() -> None:
    saved = latest_checkup("HT-001")
    left, right = st.columns([.82, 1.95], gap="medium")
    with left:
        name, profile, entered_state, plan, horizon = profile_and_plan(saved)

    current = entered_state
    if st.session_state.get("observations"):
        latest = st.session_state.observations[-1]
        current = assimilate_observation(entered_state, weight_kg=latest["Weight"], sbp=latest["Systolic BP"], dbp=latest["Diastolic BP"], hba1c=latest["HbA1c"], egfr=latest["eGFR"])
        profile.update(weight_kg=current.weight_kg)

    simulation = pd.DataFrame(simulate_parallel(current, plan, horizon))
    usual_end = simulation[simulation["Path"] == "Usual path"].iloc[-1]
    goal_end = simulation[simulation["Path"] == "Intervention twin"].iloc[-1]
    current_score = twin_index(current)
    goal_score = int(goal_end["Twin index"])

    scenario_profile = dict(profile)
    scenario_profile.update(weight_kg=float(goal_end["Weight"]), waist_cm=float(goal_end["Waist"]), daily_activity=YES if goal_end["Activity days"] >= 5 else NO, daily_fruit_veg=YES if goal_end["Diet score"] >= 5 else NO)
    diabetes_now = findrisc_pct(findrisc_points(profile))
    diabetes_goal = findrisc_pct(findrisc_points(scenario_profile))

    with right:
        st.markdown('<div class="score-panel">', unsafe_allow_html=True)
        st.markdown(f'<div class="score-kicker">Your HealthTwin score — {escape(name)} <span style="color:#059669">● up to date</span></div><div><span class="score">{current_score}</span><span class="score-outof"> / 100</span><span class="score-change">→ {goal_score} if the plan is followed</span></div>', unsafe_allow_html=True)
        saved_checkups = checkups("HT-001")
        if len(saved_checkups) >= 2:
            previous, latest = saved_checkups[-2], saved_checkups[-1]
            st.caption(
                f"Since the previous check-up ({previous['checkup_date']}): "
                f"score {latest['twin_score']-previous['twin_score']:+.0f}, "
                f"weight {latest['weight_kg']-previous['weight_kg']:+.1f} kg, "
                f"upper BP {latest['sbp']-previous['sbp']:+.0f}, "
                f"average blood sugar {latest['hba1c']-previous['hba1c']:+.1f}."
            )
        metric = st.radio("Health measure", ["Overall", "Weight", "Blood pressure", "Average blood sugar", "Kidney function"], horizontal=True, label_visibility="collapsed")
        st.plotly_chart(chart_for(simulation, metric, current.height_cm), width="stretch", config={"displayModeBar":False}, theme=None)
        st.markdown('</div>', unsafe_allow_html=True)

        cards = st.columns(2)
        with cards[0]:
            if diabetes_now is None or diabetes_goal is None:
                risk_card("Type 2 Diabetes", "Not calculated", None, "Not calculated", "", "diabetes", "Complete every required screening answer")
            else:
                risk_card("Type 2 Diabetes", f"{diabetes_now}%", diabetes_now, f"{diabetes_goal}%", f"({diabetes_goal-diabetes_now:+.0f} points)", "diabetes", "Estimated 10-year diabetes screening result")
            st.write("")
            risk_card("Average Blood Sugar", f"{current.hba1c:.1f}%", current.hba1c, f"{goal_end['HbA1c']:.1f}%", f"({goal_end['HbA1c']-current.hba1c:+.1f})", "hba1c", "HbA1c shows average blood sugar over about three months")
        with cards[1]:
            risk_card("Blood Pressure", f"{current.sbp:.0f}/{current.dbp:.0f}", current.sbp, f"{goal_end['Systolic BP']:.0f}/{goal_end['Diastolic BP']:.0f}", f"({goal_end['Systolic BP']-current.sbp:+.0f} upper number)", "bp", "Projected blood-pressure reading", secondary=current.dbp)
            st.write("")
            risk_card("Kidney Function", f"{current.egfr:.0f}", current.egfr, f"{goal_end['eGFR']:.0f}", f"({goal_end['eGFR']-current.egfr:+.1f})", "egfr", "eGFR estimates how well the kidneys filter blood")

        st.markdown("### Health score for each condition")
        st.caption("Each 0–100 score is a simple visual guide to closeness to the displayed screening reference—not a diagnosis. Status and the exact gap are shown below.")
        current_conditions = condition_assessments(height_cm=current.height_cm,weight_kg=current.weight_kg,sbp=current.sbp,dbp=current.dbp,hba1c=current.hba1c,egfr=current.egfr,diabetes_risk=diabetes_now)
        goal_conditions = condition_assessments(height_cm=current.height_cm,weight_kg=float(goal_end["Weight"]),sbp=float(goal_end["Systolic BP"]),dbp=float(goal_end["Diastolic BP"]),hba1c=float(goal_end["HbA1c"]),egfr=float(goal_end["eGFR"]),diabetes_risk=diabetes_goal)
        status_colors={"On track":"#059669","Monitor":"#d97706","Review":"#ea580c","Urgent":"#be123c","Not calculated":"#64748b"}
        cards=[]
        for now,future in zip(current_conditions,goal_conditions):
            accent=status_colors.get(now["Status"],"#64748b")
            change=future["Score"]-now["Score"]
            change_color="#047857" if change>0 else "#be123c" if change<0 else "#64748b"
            change_bg="#ecfdf5" if change>0 else "#fff1f2" if change<0 else "#f1f5f9"
            cards.append(dedent(f"""
              <div class="condition-card" style="--accent:{accent}">
                <div class="condition-card-head">
                  <div class="condition-card-name">{escape(now['Condition'])}</div>
                  <div class="condition-status">{escape(now['Status'])}</div>
                </div>
                <div class="condition-score-row">
                  <div class="condition-score-block">
                    <div class="condition-score-label">Today</div>
                    <div class="condition-score-number">{now['Score']}<span style="font-size:.75rem;color:#64748b"> / 100</span></div>
                  </div>
                  <div class="condition-arrow">→</div>
                  <div class="condition-score-block">
                    <div class="condition-score-label">Modelled plan</div>
                    <div class="condition-score-number future">{future['Score']}<span style="font-size:.75rem;color:#64748b"> / 100</span></div>
                    <div class="condition-change" style="color:{change_color};background:{change_bg}">{change:+d} points</div>
                  </div>
                </div>
                <div class="condition-track">
                  <div class="condition-track-fill" style="width:{now['Score']}%"></div>
                  <span class="condition-marker" style="left:{now['Score']}%"></span>
                  <span class="condition-marker future" style="left:{future['Score']}%"></span>
                </div>
                <div class="condition-reading"><span>Today: <strong>{escape(now['Current'])}</strong></span><span>Reference: <strong>{escape(now['Healthy'])}</strong></span></div>
                <div class="condition-reading"><span>Modelled: <strong>{escape(future['Current'])}</strong></span><span>Status: <strong>{escape(future['Status'])}</strong></span></div>
                <div class="condition-gap"><strong>Current gap:</strong> {escape(now['Difference'])}<br><strong>With plan:</strong> {escape(future['Difference'])}</div>
              </div>
            """).strip())
        st.html('<div class="condition-grid">'+''.join(cards)+'</div>')
        with st.expander("View condition scores as a table"):
            st.dataframe(pd.DataFrame(current_conditions).rename(columns={"Score":"Health score","Current":"Current reading","Healthy":"Displayed reference","Difference":"Distance from reference"}),width="stretch",hide_index=True,column_config={"Health score":st.column_config.ProgressColumn("Health score",min_value=0,max_value=100)})

        st.markdown("### What's driving the improvement")
        levers = []
        if plan.weight_loss_kg: levers.append((f"Weight: {current.weight_kg:.0f} → {goal_end['Weight']:.0f} kg", abs(float(goal_end["Weight"]-current.weight_kg))))
        if plan.activity_target > current.activity_days: levers.append((f"Activity: {current.activity_days:.0f} → {goal_end['Activity days']:.1f} days/week", float(goal_end["Activity days"]-current.activity_days)))
        if plan.quit_smoking_month and current.smoking_exposure: levers.append(("Become smoke-free", 1-float(goal_end["Smoking exposure"])))
        if plan.bp_support_effect: levers.append(("Improve blood-pressure control", abs(float(goal_end["Systolic BP"]-current.sbp))))
        levers.sort(key=lambda x:x[1], reverse=True)
        with st.container(border=True):
            for label, impact in levers[:4]:
                st.markdown(f'<div class="lever"><span>{escape(label)}</span><span class="lever-impact">active lever</span></div>', unsafe_allow_html=True)

        with st.expander("Add results from a new health check-up"):
            if "observations" not in st.session_state: st.session_state.observations = []
            with st.form("observation"):
                obs = st.columns(3)
                weight_obs = obs[0].number_input("Observed weight", 40.0, 180.0, float(current.weight_kg), .1)
                sbp_obs = obs[1].number_input("New upper BP number", 80, 240, int(current.sbp))
                dbp_obs = obs[2].number_input("New lower BP number", 40, 150, int(current.dbp))
                hba1c_obs = obs[0].number_input("New average blood sugar", 4.0, 14.0, float(current.hba1c), .1)
                egfr_obs = obs[1].number_input("New kidney function result", 1.0, 180.0, float(current.egfr), .1)
                if st.form_submit_button("Save new results", type="primary"):
                    st.session_state.observations.append({"Weight":weight_obs,"Systolic BP":sbp_obs,"Diastolic BP":dbp_obs,"HbA1c":hba1c_obs,"eGFR":egfr_obs})
                    st.rerun()
            if st.session_state.observations:
                st.caption(f"Health outlook updated with {len(st.session_state.observations)} follow-up check-up(s).")

    health_record_section(name, current, plan, horizon)


FLEET = [
    ("T. Moyo","Harare",TwinState(age=52,weight_kg=96,waist_cm=108,sbp=158,dbp=98,hba1c=6.4,egfr=78,activity_days=1,diet_score=2,smoking_exposure=1)),
    ("R. Chikwava","Bulawayo",TwinState(age=48,weight_kg=87,waist_cm=98,sbp=142,dbp=88,hba1c=5.9,egfr=91,activity_days=2,diet_score=4,smoking_exposure=0)),
    ("S. Ndoro","Mutare",TwinState(age=61,weight_kg=101,waist_cm=112,sbp=166,dbp=101,hba1c=7.2,egfr=58,activity_days=0,diet_score=2,smoking_exposure=1)),
    ("P. Gumbo","Harare",TwinState(age=39,weight_kg=79,waist_cm=88,sbp=126,dbp=81,hba1c=5.5,egfr=103,activity_days=4,diet_score=5,smoking_exposure=0)),
    ("F. Sibanda","Gweru",TwinState(age=56,weight_kg=91,waist_cm=103,sbp=151,dbp=95,hba1c=6.3,egfr=73,activity_days=2,diet_score=3,smoking_exposure=0)),
    ("N. Mutasa","Harare",TwinState(age=44,weight_kg=84,waist_cm=96,sbp=136,dbp=87,hba1c=5.8,egfr=95,activity_days=2,diet_score=3,smoking_exposure=1)),
    ("C. Dube","Masvingo",TwinState(age=58,weight_kg=99,waist_cm=110,sbp=162,dbp=99,hba1c=6.8,egfr=62,activity_days=1,diet_score=2,smoking_exposure=1)),
    ("L. Mhlanga","Bulawayo",TwinState(age=35,weight_kg=70,waist_cm=82,sbp=118,dbp=76,hba1c=5.2,egfr=110,activity_days=5,diet_score=6,smoking_exposure=0)),
    ("B. Chirwa","Mutare",TwinState(age=63,weight_kg=89,waist_cm=101,sbp=146,dbp=91,hba1c=6.1,egfr=69,activity_days=2,diet_score=4,smoking_exposure=0)),
]


def fleet_data() -> pd.DataFrame:
    rows=[]
    for name,region,state in FLEET:
        sim=pd.DataFrame(simulate_parallel(state,InterventionPlan(),24))
        usual=sim[sim["Path"]=="Usual path"].iloc[-1]; goal=sim[sim["Path"]=="Intervention twin"].iloc[-1]
        levers=[]
        if state.sbp>=140: levers.append("Blood pressure")
        if state.hba1c>=6: levers.append("Blood sugar")
        if state.smoking_exposure: levers.append("Smoking")
        if state.activity_days<3: levers.append("Activity")
        improvement=int(goal["Twin index"]-usual["Twin index"])
        rows.append({"Member":name,"Age":int(state.age),"Region":region,"Current score":twin_index(state),"Score with support":int(goal["Twin index"]),"Possible improvement":improvement,"Main opportunities":", ".join(levers[:2]) or "Routine prevention","Suggested action":"Wellness outreach" if improvement>=10 else "Routine monitoring"})
    return pd.DataFrame(rows).sort_values("Possible improvement",ascending=False)


def care_view() -> None:
    fleet=fleet_data()
    stats=st.columns(4)
    with stats[0]: stat_card("Members analysed","1,240","illustrative member group")
    with stats[1]: stat_card("Priority outreach",f"{(fleet['Possible improvement']>=10).mean():.0%}","members with the most to gain")
    with stats[2]: stat_card("Average HealthTwin score",f"{fleet['Current score'].mean():.0f}","today")
    with stats[3]: stat_card("Possible improvement",f"+{fleet['Possible improvement'].mean():.1f}","average over 24 months")

    left,right=st.columns([2.05,1],gap="medium")
    with left:
        st.markdown("### Members flagged for outreach")
        st.dataframe(
            fleet,
            width="stretch",
            hide_index=True,
            column_config={
                "Current score": st.column_config.ProgressColumn("Current score", min_value=0, max_value=100),
                "Score with support": st.column_config.ProgressColumn("Score with support", min_value=0, max_value=100),
            },
        )
    with right:
        st.markdown("### Where support could help most")
        lever_counts={}
        for text in fleet["Main opportunities"]:
            for lever in text.split(", "): lever_counts[lever]=lever_counts.get(lever,0)+1
        lever_df=pd.DataFrame([{"Lever":k,"Members":v} for k,v in lever_counts.items()]).sort_values("Members",ascending=False)
        fig=go.Figure(go.Bar(x=lever_df["Lever"],y=lever_df["Members"],marker_color="#047857"))
        fig.update_layout(height=270,margin={"l":55,"r":15,"t":20,"b":55},paper_bgcolor="#ffffff",plot_bgcolor="#ffffff",font={"color":"#334155","size":10},xaxis={"title":{"text":"Main opportunity","font":{"color":"#334155"}},"tickfont":{"color":"#334155"},"showline":True,"linecolor":"#94a3b8","ticks":"outside"},yaxis={"title":{"text":"Members","font":{"color":"#334155"}},"tickfont":{"color":"#334155"},"dtick":1,"gridcolor":"#e2e8f0","showline":True,"linecolor":"#94a3b8","ticks":"outside"})
        st.plotly_chart(fig,width="stretch",config={"displayModeBar":False},theme=None)
        st.markdown("### Possible improvement by region")
        regional=fleet.groupby("Region",as_index=False)["Possible improvement"].mean().sort_values("Possible improvement",ascending=False)
        for _, row in regional.iterrows():
            improvement = row["Possible improvement"]
            st.write(f"**{row['Region']}** · +{improvement:.1f} points")
            st.progress(min(1.0,improvement/30))

    with st.expander("Model details and limitations"):
        st.write(f"Model version **{ENGINE_VERSION}** compares how health measures may change with and without the selected support plan. The current calculations are illustrative and must be tested with approved Cimas data before real-world use.")


shared_token = st.query_params.get("share")
if shared_token:
    render_clinician_record(shared_token)


header_left,header_right=st.columns([3,1])
with header_left:
    st.markdown('<div class="brand"><span style="font-size:1.25rem">🫀</span><div class="brand-name">Cimas HealthTwin AI</div></div><div class="tagline">“Predict tomorrow\'s health, today.”</div>',unsafe_allow_html=True)
with header_right:
    view=st.radio("View",["Member view","Care manager view"],horizontal=True,label_visibility="collapsed")

if view=="Member view": member_view()
else: care_view()

st.markdown('<div class="footer">Healthathon 3.0 prototype using synthetic member and scheme data. The digital twin is illustrative and does not replace professional medical judgement.</div>',unsafe_allow_html=True)
