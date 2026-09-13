"""Pure helper functions used by the Streamlit strategy simulator."""

from __future__ import annotations

from collections.abc import Mapping

import pandas as pd


def normalize_weights(raw_weights: Mapping[str, float]) -> dict[str, float]:
    """Return non-negative weights normalized to one."""
    if not raw_weights:
        raise ValueError("At least one weight is required.")
    cleaned = {key: float(value) for key, value in raw_weights.items()}
    if any(value < 0 for value in cleaned.values()):
        raise ValueError("Weights cannot be negative.")
    total = sum(cleaned.values())
    if total <= 0:
        raise ValueError("At least one weight must be greater than zero.")
    return {key: value / total for key, value in cleaned.items()}


def ranking_matrix(frame: pd.DataFrame, weight_sets: Mapping[str, Mapping[str, float]], scorer) -> pd.DataFrame:
    """Return one scenario-by-profile table of integer ranks."""
    columns: dict[str, pd.Series] = {}
    for profile, weights in weight_sets.items():
        ranked = scorer(frame, dict(weights)).set_index("scenario")
        columns[profile] = ranked["rank"]
    return pd.DataFrame(columns).sort_values(list(columns), kind="stable")


def build_decision_memo(
    ranked: pd.DataFrame,
    profile_name: str,
    normalized_weights: Mapping[str, float],
    criterion_labels: Mapping[str, str],
) -> str:
    """Create a concise Markdown record of the current decision view."""
    top = ranked.iloc[0]
    second = ranked.iloc[1]
    lines = [
        "# Low-altitude Economy Scenario Decision Memo",
        "",
        f"**Decision lens:** {profile_name}",
        "",
        "## Current recommendation",
        "",
        f"1. **{top['scenario']}** — {top['weighted_score']:.2f}/5; {top['suggested_posture']}.",
        f"2. **{second['scenario']}** — {second['weighted_score']:.2f}/5; {second['suggested_posture']}.",
        "",
        "The ranking is a screening result, not an investment forecast. A decision to proceed still requires a city- and route-level permission path, operating partner diligence, and unit-economics evidence.",
        "",
        "## Weighting used",
        "",
    ]
    for key, label in criterion_labels.items():
        lines.append(f"- {label}: {normalized_weights[key]:.0%}")
    lines.extend(
        [
            "",
            "## Leading scenario",
            "",
            f"**Evidence:** {top['key_evidence']}",
            "",
            f"**Main risk:** {top['main_risk']}",
            "",
            f"**First test:** {top['first_test']}",
            "",
            "## Full ranking",
            "",
            "| Rank | Scenario | Score | Suggested posture |",
            "| ---: | --- | ---: | --- |",
        ]
    )
    for _, row in ranked.iterrows():
        lines.append(
            f"| {int(row['rank'])} | {row['scenario']} | {row['weighted_score']:.2f} | {row['suggested_posture']} |"
        )
    lines.extend(
        [
            "",
            "## Evidence required before commitment",
            "",
            "- City-level permission and insurance pathway",
            "- Route demand and ground-service baseline",
            "- Weather interruption and operating-reliability data",
            "- Partner capability and technical-integration assessment",
            "- Pilot success thresholds and explicit stop conditions",
            "",
            "Generated from the transparent scoring model in this repository. Scores are analyst judgments on a 1-5 ordinal scale.",
        ]
    )
    return "\n".join(lines)

