"""Reproduce the base-case ranking, sensitivity analysis, and portfolio figures."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "scenario-scoring.csv"
FIGURE_DIR = ROOT / "figures"

CRITERIA = {
    "demand_score": "Demand",
    "capability_fit_score": "Platform fit",
    "commercialization_score": "Commercialization",
    "regulatory_feasibility_score": "Regulatory feasibility",
    "data_network_effect_score": "Data/network effect",
}

WEIGHT_SETS = {
    "Base case": {
        "demand_score": 0.20,
        "capability_fit_score": 0.25,
        "commercialization_score": 0.20,
        "regulatory_feasibility_score": 0.20,
        "data_network_effect_score": 0.15,
    },
    "Growth platform": {
        "demand_score": 0.25,
        "capability_fit_score": 0.30,
        "commercialization_score": 0.20,
        "regulatory_feasibility_score": 0.10,
        "data_network_effect_score": 0.15,
    },
    "Compliance first": {
        "demand_score": 0.15,
        "capability_fit_score": 0.20,
        "commercialization_score": 0.15,
        "regulatory_feasibility_score": 0.35,
        "data_network_effect_score": 0.15,
    },
    "Asset light": {
        "demand_score": 0.15,
        "capability_fit_score": 0.30,
        "commercialization_score": 0.25,
        "regulatory_feasibility_score": 0.15,
        "data_network_effect_score": 0.15,
    },
}


def validate_weights(weights: dict[str, float]) -> None:
    """Raise when a weight set is incomplete or does not sum to one."""
    if set(weights) != set(CRITERIA):
        raise ValueError("Weight keys must match the five scoring criteria.")
    if abs(sum(weights.values()) - 1.0) > 1e-9:
        raise ValueError("Weights must sum to 1.0.")


def score_scenarios(frame: pd.DataFrame, weights: dict[str, float]) -> pd.DataFrame:
    """Return scenarios ranked by a transparent weighted-average score."""
    validate_weights(weights)
    result = frame.copy()
    for column in CRITERIA:
        if not result[column].between(1, 5).all():
            raise ValueError(f"{column} must contain scores from 1 to 5.")
    result["weighted_score"] = sum(result[column] * weight for column, weight in weights.items())
    result["rank"] = result["weighted_score"].rank(method="min", ascending=False).astype(int)
    return result.sort_values(["weighted_score", "scenario"], ascending=[False, True])


def build_sensitivity(frame: pd.DataFrame) -> pd.DataFrame:
    """Create a long-form table of score and rank under each strategy profile."""
    outputs: list[pd.DataFrame] = []
    for profile, weights in WEIGHT_SETS.items():
        ranked = score_scenarios(frame, weights)[["scenario_id", "scenario", "weighted_score", "rank"]]
        ranked.insert(0, "profile", profile)
        outputs.append(ranked)
    return pd.concat(outputs, ignore_index=True)


def make_priority_chart(ranked: pd.DataFrame) -> None:
    ordered = ranked.sort_values("weighted_score")
    colors = ["#2563EB" if score >= 4 else "#64748B" if score >= 3 else "#B45309" for score in ordered["weighted_score"]]
    fig, ax = plt.subplots(figsize=(10, 5.8))
    ax.barh(ordered["scenario"], ordered["weighted_score"], color=colors)
    ax.axvline(4.0, color="#94A3B8", linestyle="--", linewidth=1)
    ax.set_xlim(0, 5)
    ax.set_xlabel("Weighted score (1–5 analyst judgment)")
    ax.set_title("Low-altitude economy scenario priority")
    for y, value in enumerate(ordered["weighted_score"]):
        ax.text(value + 0.06, y, f"{value:.2f}", va="center", fontsize=9)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.grid(axis="x", color="#E2E8F0", linewidth=0.8)
    ax.set_axisbelow(True)
    fig.tight_layout()
    fig.savefig(FIGURE_DIR / "scenario-priority.png", dpi=180, bbox_inches="tight")
    plt.close(fig)


def make_opportunity_matrix(ranked: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(9, 6.3))
    point_offsets = {
        "Urban instant delivery": (-0.10, 0.08),
        "Low-altitude digital infrastructure and services": (0.10, -0.08),
    }
    plot_x = [
        row["regulatory_feasibility_score"] + point_offsets.get(row["scenario"], (0, 0))[0]
        for _, row in ranked.iterrows()
    ]
    plot_y = [
        row["capability_fit_score"] + point_offsets.get(row["scenario"], (0, 0))[1]
        for _, row in ranked.iterrows()
    ]
    sizes = 130 + ranked["data_network_effect_score"] * 60
    scatter = ax.scatter(
        plot_x,
        plot_y,
        s=sizes,
        c=ranked["demand_score"],
        cmap="Blues",
        vmin=1,
        vmax=5,
        edgecolor="white",
        linewidth=1.2,
    )
    short_labels = {
        "Urban instant delivery": "Instant delivery",
        "Low-altitude digital infrastructure and services": "Digital services",
        "Industrial inspection": "Inspection",
        "Urban governance and emergency response": "Governance",
        "Medical and emergency logistics": "Medical logistics",
        "Tourism and passenger mobility": "Passenger mobility",
    }
    label_offsets = {
        "Urban instant delivery": (-92, 10),
        "Low-altitude digital infrastructure and services": (10, -17),
        "Industrial inspection": (8, 8),
        "Urban governance and emergency response": (8, 8),
        "Medical and emergency logistics": (8, 8),
        "Tourism and passenger mobility": (8, 8),
    }
    for point_index, (_, row) in enumerate(ranked.iterrows()):
        ax.annotate(
            short_labels[row["scenario"]],
            (plot_x[point_index], plot_y[point_index]),
            xytext=label_offsets[row["scenario"]],
            textcoords="offset points",
            fontsize=9,
        )
    ax.axvline(3, color="#CBD5E1", linewidth=1)
    ax.axhline(3, color="#CBD5E1", linewidth=1)
    ax.set_xlim(0.7, 5.3)
    ax.set_ylim(0.7, 5.7)
    ax.set_xlabel("Regulatory feasibility score")
    ax.set_ylabel("Platform capability fit score")
    ax.set_title("Opportunity matrix")
    colorbar = fig.colorbar(scatter, ax=ax, pad=0.02)
    colorbar.set_label("Demand score")
    ax.grid(color="#F1F5F9", linewidth=0.7)
    fig.text(
        0.12,
        0.01,
        "Equal-position points are offset slightly for readability; labels retain the original scores.",
        fontsize=8,
        color="#64748B",
    )
    fig.tight_layout(rect=[0, 0.035, 1, 1])
    fig.savefig(FIGURE_DIR / "opportunity-matrix.png", dpi=180, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    source = pd.read_csv(DATA_PATH)
    ranked = score_scenarios(source, WEIGHT_SETS["Base case"])
    sensitivity = build_sensitivity(source)
    sensitivity.to_csv(ROOT / "data" / "sensitivity-results.csv", index=False)
    ranked[["rank", "scenario", "weighted_score", "suggested_posture"]].to_csv(
        ROOT / "data" / "base-case-ranking.csv", index=False
    )
    make_priority_chart(ranked)
    make_opportunity_matrix(ranked)
    print(ranked[["rank", "scenario", "weighted_score", "suggested_posture"]].to_string(index=False))


if __name__ == "__main__":
    main()
