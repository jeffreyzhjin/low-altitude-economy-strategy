"""Interactive strategy simulator for the low-altitude economy portfolio project."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "analysis"))

from decision_support import build_decision_memo, normalize_weights, ranking_matrix
from scenario_scoring import CRITERIA, WEIGHT_SETS, score_scenarios


st.set_page_config(
    page_title="Low-altitude Economy Strategy Simulator",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .block-container {padding-top: 2.2rem; padding-bottom: 3rem; max-width: 1480px;}
    [data-testid="stSidebar"] {background: #f4f7fa;}
    [data-testid="stMetric"] {background: white; border: 1px solid #d9e2ec; border-radius: 10px; padding: 14px 16px;}
    [data-testid="stMetricLabel"] {color: #627d98;}
    [data-testid="stMetricValue"] {color: #102a43;}
    .eyebrow {
        display: block;
        min-height: 1.7rem;
        padding: .28rem 0 .22rem;
        margin: 0 0 .25rem;
        overflow: visible;
        font-size: .78rem;
        font-weight: 700;
        line-height: 1.55 !important;
        color: #1f5aa6;
        letter-spacing: .09em;
        text-transform: uppercase;
    }
    .decision-box {background: #eaf2fb; border-left: 5px solid #1f5aa6; padding: 1rem 1.2rem; border-radius: 7px; margin: .6rem 0 1.2rem;}
    .risk-box {background: #fff6e5; border-left: 5px solid #b7791f; padding: .9rem 1.1rem; border-radius: 7px;}
    .small-note {color: #627d98; font-size: .88rem;}
    div[data-baseweb="tab-list"] {gap: 1.25rem;}
    button[data-baseweb="tab"][aria-selected="true"] {color: #1f5aa6 !important;}
    div[data-baseweb="tab-highlight"] {background-color: #1f5aa6 !important;}
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data
def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    scenarios = pd.read_csv(ROOT / "data" / "scenario-scoring.csv")
    sources = pd.read_csv(ROOT / "data" / "source-ledger.csv")
    return scenarios, sources


def weight_summary(weights: dict[str, float]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Criterion": [CRITERIA[key] for key in CRITERIA],
            "Weight": [f"{weights[key]:.0%}" for key in CRITERIA],
        }
    )


SHORT_SCENARIO_NAMES = {
    "Urban instant delivery": "Instant delivery",
    "Low-altitude digital infrastructure and services": "Digital services",
    "Industrial inspection": "Inspection",
    "Urban governance and emergency response": "Urban governance",
    "Medical and emergency logistics": "Medical logistics",
    "Tourism and passenger mobility": "Passenger mobility",
}


def priority_chart(ranked: pd.DataFrame) -> go.Figure:
    plot_frame = ranked.sort_values("weighted_score", ascending=True).copy()
    plot_frame["Scenario"] = plot_frame["scenario"].replace(SHORT_SCENARIO_NAMES)
    plot_frame["Color"] = plot_frame["weighted_score"].map(
        lambda value: "Advance" if value >= 4 else "Assess" if value >= 3 else "Monitor"
    )
    fig = px.bar(
        plot_frame,
        x="weighted_score",
        y="Scenario",
        orientation="h",
        color="Color",
        color_discrete_map={"Advance": "#1f5aa6", "Assess": "#627d98", "Monitor": "#b7791f"},
        text=plot_frame["weighted_score"].map(lambda value: f"{value:.2f}"),
    )
    fig.update_traces(textposition="outside", hovertemplate="%{y}<br>Score: %{x:.2f}<extra></extra>")
    fig.update_layout(
        height=390,
        margin=dict(l=10, r=55, t=20, b=20),
        xaxis=dict(range=[0, 5.25], title="Weighted score (1-5)"),
        yaxis_title=None,
        legend_title=None,
        plot_bgcolor="white",
        paper_bgcolor="white",
    )
    fig.add_vline(x=4, line_dash="dash", line_color="#9fb3c8")
    return fig


def opportunity_chart(ranked: pd.DataFrame) -> go.Figure:
    display = ranked.copy()
    display["Short name"] = display["scenario"].replace(SHORT_SCENARIO_NAMES)
    point_offsets = {
        "Urban instant delivery": (-0.10, 0.08),
        "Low-altitude digital infrastructure and services": (0.10, -0.08),
    }
    display["plot_x"] = display.apply(
        lambda row: row["regulatory_feasibility_score"] + point_offsets.get(row["scenario"], (0, 0))[0],
        axis=1,
    )
    display["plot_y"] = display.apply(
        lambda row: row["capability_fit_score"] + point_offsets.get(row["scenario"], (0, 0))[1],
        axis=1,
    )
    text_positions = {
        "Urban instant delivery": "top left",
        "Low-altitude digital infrastructure and services": "bottom right",
        "Industrial inspection": "top center",
        "Urban governance and emergency response": "top center",
        "Medical and emergency logistics": "top center",
        "Tourism and passenger mobility": "top center",
    }
    display["text_position"] = display["scenario"].map(text_positions)
    custom_data = display[
        [
            "scenario",
            "regulatory_feasibility_score",
            "capability_fit_score",
            "demand_score",
            "weighted_score",
        ]
    ]
    fig = go.Figure(
        go.Scatter(
            x=display["plot_x"],
            y=display["plot_y"],
            mode="markers+text",
            text=display["Short name"],
            textposition=display["text_position"],
            cliponaxis=False,
            customdata=custom_data,
            marker=dict(
                size=display["demand_score"] * 8 + 8,
                color=display["weighted_score"],
                colorscale=[[0, "#d9e2ec"], [1, "#1f5aa6"]],
                cmin=1,
                cmax=5,
                colorbar=dict(title="Weighted<br>score", thickness=16),
                line=dict(color="white", width=1.5),
                opacity=0.88,
            ),
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>"
                "Regulatory feasibility: %{customdata[1]:.0f}<br>"
                "Platform capability fit: %{customdata[2]:.0f}<br>"
                "Demand: %{customdata[3]:.0f}<br>"
                "Weighted score: %{customdata[4]:.2f}<extra></extra>"
            ),
        )
    )
    fig.update_layout(
        height=460,
        margin=dict(l=15, r=35, t=55, b=25),
        xaxis=dict(range=[0.6, 5.4], dtick=1, title="Regulatory feasibility", fixedrange=True),
        yaxis=dict(range=[0.6, 5.75], dtick=1, title="Platform capability fit", fixedrange=True),
        plot_bgcolor="white",
        paper_bgcolor="white",
        showlegend=False,
    )
    fig.add_vline(x=3, line_color="#d9e2ec")
    fig.add_hline(y=3, line_color="#d9e2ec")
    return fig


scenarios, sources = load_data()

with st.sidebar:
    st.header("Decision settings")
    profile_options = list(WEIGHT_SETS) + ["Custom"]
    selected_profile = st.selectbox(
        "Strategy lens",
        profile_options,
        help="Each lens changes how the same six scenarios are evaluated.",
    )

    if selected_profile == "Custom":
        st.caption("Set relative importance. Values are normalized automatically.")
        raw_weights = {}
        defaults = WEIGHT_SETS["Base case"]
        for key, label_text in CRITERIA.items():
            raw_weights[key] = st.slider(
                label_text,
                min_value=0,
                max_value=50,
                value=int(defaults[key] * 100),
                step=5,
                key=f"weight_{key}",
            )
        try:
            weights = normalize_weights(raw_weights)
        except ValueError:
            st.error("Set at least one criterion above zero.")
            st.stop()
        st.caption(f"Raw total: {sum(raw_weights.values())} · Applied total: 100%")
    else:
        weights = dict(WEIGHT_SETS[selected_profile])
        st.dataframe(weight_summary(weights), hide_index=True, use_container_width=True)

    st.divider()
    st.markdown("**Decision owner**")
    st.caption("A platform with users, merchants, maps, payments, cloud, AI, dispatch, and operations teams.")
    st.markdown("**Decision boundary**")
    st.caption("Choose where to test first. This is not a nationwide investment case.")

ranked = score_scenarios(scenarios, weights).reset_index(drop=True)
top = ranked.iloc[0]
runner_up = ranked.iloc[1]
score_gap = float(top["weighted_score"] - runner_up["weighted_score"])
is_tied = score_gap < 0.005
preset_matrix = ranking_matrix(scenarios, WEIGHT_SETS, score_scenarios)
stable_top_two = all(
    set(preset_matrix[profile].nsmallest(2).index)
    == {"Urban instant delivery", "Low-altitude digital infrastructure and services"}
    for profile in preset_matrix.columns
)

st.markdown('<div class="eyebrow">Interactive portfolio case</div>', unsafe_allow_html=True)
st.title("Low-altitude Economy Strategy Simulator")
st.caption("Test how strategic priorities change when demand, platform fit, commercialization, regulation, and data effects are weighted differently.")
st.info("Scores are transparent analyst judgments on a 1-5 scale. They support scenario screening; they do not estimate market size, probability of success, or investment return.")

overview_tab, sensitivity_tab, evidence_tab, pilot_tab, method_tab = st.tabs(
    ["Decision view", "Sensitivity", "Evidence", "90-day pilot", "Method"]
)

with overview_tab:
    st.subheader("Current decision")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric(
        "Recommended first move",
        "Joint shortlist" if is_tied else SHORT_SCENARIO_NAMES[top["scenario"]],
        help=f"{top['scenario']} · {top['suggested_posture']}",
    )
    m2.metric("Leading score", f"{top['weighted_score']:.2f} / 5")
    m3.metric("Runner-up score", f"{runner_up['weighted_score']:.2f} / 5", help=runner_up["scenario"])
    m4.metric("Lead over runner-up", f"{score_gap:.2f} points")

    if is_tied:
        decision_copy = (
            f"<b>No clear lead under the {selected_profile.lower()} lens</b><br>"
            f"<b>{top['scenario']}</b> and <b>{runner_up['scenario']}</b> are tied at "
            f"{top['weighted_score']:.2f}. Treat them as a joint shortlist and use pilot evidence to separate them."
        )
    else:
        decision_copy = (
            f"<b>Recommendation under the {selected_profile.lower()} lens</b><br>"
            f"Start with <b>{top['scenario']}</b>. The suggested posture is "
            f"<b>{top['suggested_posture'].lower()}</b>. Keep <b>{runner_up['scenario']}</b> "
            "as the second workstream rather than treating the sector as one large market bet."
        )
    st.markdown(
        f"""
        <div class="decision-box">
        {decision_copy}
        </div>
        """,
        unsafe_allow_html=True,
    )

    chart_col, detail_col = st.columns([1.45, 1])
    with chart_col:
        st.markdown("#### Scenario ranking")
        st.plotly_chart(priority_chart(ranked), use_container_width=True, config={"displayModeBar": False})
    with detail_col:
        st.markdown("#### Review one scenario")
        selected_scenario = st.selectbox("Scenario", ranked["scenario"].tolist(), label_visibility="collapsed")
        detail = ranked.loc[ranked["scenario"] == selected_scenario].iloc[0]
        st.markdown(f"**Suggested posture:** {detail['suggested_posture']}")
        st.markdown(f"**Why it is credible**  \n{detail['key_evidence']}")
        st.markdown(f"**Main risk**  \n{detail['main_risk']}")
        st.markdown(f"**First test**  \n{detail['first_test']}")
        st.caption(detail["analyst_note"])

    st.divider()
    st.markdown("#### Opportunity map")
    st.plotly_chart(opportunity_chart(ranked), use_container_width=True, config={"displayModeBar": False})
    st.caption("Bubble size represents demand score. The two equal-position points at the top are offset slightly so both scenarios remain visible; hover labels report the original scores.")

with sensitivity_tab:
    st.subheader("Does the recommendation survive a different strategy lens?")
    if stable_top_two:
        st.success("Instant delivery and digital services remain the top two scenarios in all four predefined profiles.")
    else:
        st.warning("The top-two recommendation changes across predefined profiles.")

    display_matrix = preset_matrix.copy()
    display_matrix.index.name = "Scenario"
    st.dataframe(
        display_matrix.style.background_gradient(cmap="Blues_r", vmin=1, vmax=6).format("{:.0f}"),
        use_container_width=True,
    )

    st.markdown("#### Why rankings move")
    st.write(
        "Growth-oriented weighting favors demand and platform fit. Compliance-first weighting rewards scenarios with a clearer permission path. Asset-light weighting favors software, workflow, and partnership models over aircraft ownership."
    )
    st.markdown('<div class="risk-box"><b>Interpretation rule</b><br>A small score gap is not a precise economic difference. Use movement across profiles to identify which assumptions need evidence before a pilot.</div>', unsafe_allow_html=True)

with evidence_tab:
    st.subheader("Evidence ledger")
    st.caption("Verified facts are stored separately from the judgment made from them.")
    evidence_types = sorted(sources["source_type"].dropna().unique())
    selected_types = st.multiselect("Source type", evidence_types, default=evidence_types)
    filtered_sources = sources[sources["source_type"].isin(selected_types)].copy()
    st.dataframe(
        filtered_sources[
            ["organization", "title", "publication_date", "verified_fact", "decision_use", "evidence_strength", "url"]
        ],
        hide_index=True,
        use_container_width=True,
        column_config={
            "organization": "Organization",
            "title": "Source",
            "publication_date": "Published",
            "verified_fact": st.column_config.TextColumn("Verified fact", width="large"),
            "decision_use": st.column_config.TextColumn("Decision use", width="medium"),
            "evidence_strength": "Strength",
            "url": st.column_config.LinkColumn("Link", display_text="Open source"),
        },
    )
    st.caption("Official policy and regulator statistics carry the highest evidence strength. Company figures remain self-reported.")

with pilot_tab:
    st.subheader("A 90-day pilot should answer four questions")
    p1, p2, p3 = st.columns(3)
    with p1:
        st.markdown("**Days 1-30 · Choose the route**")
        st.write("Select one city, one repeatable route, one licensed operator, one demand partner, and a ground-service baseline.")
    with p2:
        st.markdown("**Days 31-60 · Build the workflow**")
        st.write("Connect orders, dispatch, customer notifications, incident reporting, insurance evidence, and fallback operations.")
    with p3:
        st.markdown("**Days 61-90 · Operate and compare**")
        st.write("Run limited operations and compare cost, time, reliability, safety, utilization, and repeat use.")

    questions = pd.DataFrame(
        [
            ["Demand", "Does the route solve a frequent and costly problem?", "Qualified orders; repeat use"],
            ["Operations", "Can the service meet reliability and safety thresholds?", "Completion; on-time; incidents; fallback"],
            ["Economics", "Does density create a credible cost advantage?", "Cost per completed order; utilization"],
            ["Scalability", "Can the model repeat without bespoke work?", "Permission time; manual steps; integration effort"],
        ],
        columns=["Decision question", "What must be learned", "Example measures"],
    )
    st.dataframe(questions, hide_index=True, use_container_width=True)
    st.warning("Stop if there is no executable permission path, safety responsibility is unclear, or the service lacks a credible ground fallback.")

    memo = build_decision_memo(ranked, selected_profile, weights, CRITERIA)
    st.download_button(
        "Download current decision memo",
        data=memo,
        file_name="low-altitude-economy-decision-memo.md",
        mime="text/markdown",
        use_container_width=True,
    )

with method_tab:
    st.subheader("Method and limits")
    method_frame = pd.DataFrame(
        [
            ["Market demand", "Is the customer problem frequent, costly, or urgent?"],
            ["Platform capability fit", "Can users, merchants, maps, cloud, AI, dispatch, and operations create an advantage?"],
            ["Commercialization clarity", "Is the payer, value metric, and revenue path identifiable?"],
            ["Regulatory feasibility", "Can a limited pilot operate with realistic permissions, insurance, and safeguards?"],
            ["Data and network effects", "Does usage improve routing, risk, supply, or matching?"],
        ],
        columns=["Criterion", "Decision question"],
    )
    st.dataframe(method_frame, hide_index=True, use_container_width=True)
    st.markdown("**Scoring rule:** weighted score = sum of criterion score × normalized criterion weight.")
    st.markdown(
        "**Not included:** market-size forecasts, discounted cash flow, aircraft certification, route-level legal review, or safety-case approval. These require primary diligence before capital commitment."
    )
    st.markdown(
        "**Reproducible files:** `data/scenario-scoring.csv`, `data/source-ledger.csv`, `analysis/scenario_scoring.py`, and `model/low-altitude-scenario-model.xlsx`."
    )

st.divider()
st.caption("Portfolio project by ZHANG JIN · Renmin University of China · Evidence and assumptions current to 13 September 2026")
