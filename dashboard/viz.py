"""Figure builders for the dashboard.

Every function returns a `plotly.graph_objects.Figure`. The data is loaded
once at module import (`DF`) so callbacks just re-aggregate slices.

Visit-ordinal anchoring
=======================
The primary x-axis is `visit_rel` — the offset (in visits, not months) from
each patient's "diagnosis change" visit. For converters that diagnosis change is the first
visit at the new diagnosis (conversion). For stable patients it is the
last observed visit. This lets converters and stable patients share an
x-axis even though ADNI's visit cadence is roughly yearly.
"""
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
from plotly.subplots import make_subplots
from scipy import stats
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

# --------------------------------------------------------------------------- #
# Shared Plotly template — keeps every figure visually consistent with the
# surrounding HTML chrome (assets/styles.css).
# --------------------------------------------------------------------------- #

INK_PRIMARY   = "#0f172a"
INK_SECONDARY = "#475569"
INK_MUTED     = "#94a3b8"
BORDER        = "#e2e8f0"
ACCENT        = "#0ea5e9"
CARD_BG       = "#ffffff"
FONT_FAMILY = '"Inter", system-ui, "Segoe UI", Roboto, sans-serif'

pio.templates["clinical"] = go.layout.Template(
    layout=go.Layout(
        font=dict(family=FONT_FAMILY, color=INK_PRIMARY, size=12),
        title=dict(font=dict(size=14, color=INK_PRIMARY), x=0.0,
                    pad=dict(t=4, b=8, l=4)),
        paper_bgcolor=CARD_BG,
        plot_bgcolor=CARD_BG,
        colorway=["#0ea5e9", "#dc2626", "#7c3aed", "#fbbf24",
                  "#16a34a", "#475569"],
        margin=dict(l=60, r=24, t=68, b=48),
        xaxis=dict(showgrid=True, gridcolor=BORDER, zerolinecolor=BORDER,
                   linecolor=BORDER, tickfont=dict(size=11,
                                                    color=INK_SECONDARY),
                   title=dict(font=dict(size=12, color=INK_SECONDARY))),
        yaxis=dict(showgrid=True, gridcolor=BORDER, zerolinecolor=BORDER,
                   linecolor=BORDER, tickfont=dict(size=11,
                                                    color=INK_SECONDARY),
                   title=dict(font=dict(size=12, color=INK_SECONDARY))),
        legend=dict(font=dict(size=11, color=INK_SECONDARY),
                    bgcolor="rgba(0,0,0,0)"),
        hoverlabel=dict(bgcolor=CARD_BG, bordercolor=BORDER,
                        font=dict(family=FONT_FAMILY, size=12,
                                   color=INK_PRIMARY)),
    )
)
pio.templates.default = "clinical"

# --------------------------------------------------------------------------- #
# Constants
# --------------------------------------------------------------------------- #

ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "interim" / "mtb_sig_with_trajectory.pkl"

# 29 statistically-significant metabolites + 3 ratios
METABOLITES = [
    "C1_0", "TDCA", "CA", "C5_0", "HDCA", "L_TRYPTOPHAN", "MUROCA",
    "HIPPURIC_ACID", "L_LYSINE", "GHDCA", "GLCA", "GLYCOLIC_ACID", "UCA",
    "secondary_primary_ratio", "DCA_CA_ratio", "C20_5_CIS_5_8_11_14_17",
    "BETA_ALANINE", "DCA", "C22_6_CIS_4_7_10_13_16_19", "GLYCERIC_ACID",
    "X__2_METHYLPENTANOIC_ACID", "APOCA", "microbial_bile_acid_index",
    "ISOLCA", "LCA", "NORDCA", "C6_0", "L_TYROSINE", "GDCA",
]

METABOLITE_GROUPS = {
    "Bile acids — primary":   ["CA", "TDCA", "MUROCA", "HDCA", "UCA", "APOCA"],
    "Bile acids — secondary": ["DCA", "GDCA", "GLCA", "GHDCA", "ISOLCA", "LCA", "NORDCA"],
    "Bile-acid ratios":       ["secondary_primary_ratio", "DCA_CA_ratio",
                               "microbial_bile_acid_index"],
    "Amino acids":            ["L_TRYPTOPHAN", "L_LYSINE", "L_TYROSINE", "BETA_ALANINE"],
    "Fatty acids (acyl)":     ["C1_0", "C5_0", "C6_0",
                               "C20_5_CIS_5_8_11_14_17",
                               "C22_6_CIS_4_7_10_13_16_19"],
    "Organic acids / other":  ["HIPPURIC_ACID", "GLYCOLIC_ACID", "GLYCERIC_ACID",
                               "X__2_METHYLPENTANOIC_ACID"],
}

ORDERED_METABOLITES = [
    m for grp in METABOLITE_GROUPS.values() for m in grp if m in METABOLITES
]

METABOLITE_TO_FAMILY = {
    m: grp for grp, members in METABOLITE_GROUPS.items() for m in members
}

TRAJ_COLORS = {
    # Transitions keep their distinctive colors — they encode change, not state
    "NL->MCI":        "#2563eb",   # decline:    blue
    "MCI->AD":        "#dc2626",   # decline:    red (matches AD endpoint)
    "NL->MCI->AD":    "#7c3aed",   # decline:    purple
    "MCI->NL":        "#0ea5e9",   # improvement: sky-blue (distinct from green NL)
    # Stable cohorts follow the diagnosis color scheme:
    #   NL = green, MCI = grey, AD = red
    "stable_NL":      "#16a34a",   # green
    "stable_MCI":     "#94a3b8",   # grey
    "stable_AD":      "#dc2626",   # red
    "other_unstable": "#a3a3a3",
}

DX_COLORS = {"NL": "#16a34a", "MCI": "#94a3b8", "AD": "#dc2626"}

# Visit-ordinal slots
SLOTS = [-3, -2, -1, 0, 1]


# --------------------------------------------------------------------------- #
# Data
# --------------------------------------------------------------------------- #

def _load() -> pd.DataFrame:
    df = pd.read_pickle(DATA_PATH)
    # Defensive sex normalization (in case the pickle predates the prep fix)
    raw = df["sex"]
    if str(raw.dtype) == "category":
        cats = set(raw.cat.categories)
        if cats <= {0, 1}:
            raw = raw.astype(int).map({0: "Male", 1: "Female"})
        else:
            raw = raw.astype(str)
    elif raw.dtype.kind in "iu":
        raw = raw.astype(int).map({0: "Male", 1: "Female"})
    df["sex"] = pd.Series(
        [str(x).strip() if pd.notna(x) else "Unknown" for x in raw],
        index=df.index, dtype=object,
    )
    # Global z-score for each metabolite (used by heatmap / forest / PCA)
    z = (df[METABOLITES] - df[METABOLITES].mean()) / df[METABOLITES].std()
    z.columns = [f"{c}__z" for c in z.columns]
    return pd.concat([df, z], axis=1)


DF = _load()


def filter_df(traj_groups, sex):
    f = DF[DF["trajectory"].isin(traj_groups)]
    if sex and sex != "All":
        f = f.loc[f["sex"].to_numpy() == sex]
    return f


def all_rids(traj_groups, sex):
    f = filter_df(traj_groups, sex)
    return sorted(f["RID"].unique().tolist())


# --------------------------------------------------------------------------- #
# Tab A — Visit-ordinal trajectory
# --------------------------------------------------------------------------- #

def trajectory_figure(metabolite, traj_groups, sex, show_lines):
    f = filter_df(traj_groups, sex)
    if f.empty:
        return go.Figure().update_layout(title="No data for current filters",
                                         template="clinical", height=460)

    f = f.dropna(subset=["visit_rel", metabolite]).copy()

    fig = go.Figure()

    if show_lines:
        for rid, g in f.sort_values("visit_rel").groupby("RID"):
            color = TRAJ_COLORS.get(g["trajectory"].iloc[0], "#999")
            fig.add_trace(go.Scatter(
                x=g["visit_rel"], y=g[metabolite],
                mode="lines", line=dict(width=1, color=color),
                opacity=0.18, hoverinfo="skip", showlegend=False,
                customdata=[[int(rid)]] * len(g),
                name=f"RID {rid}",
            ))

    # ----- Systematic dodging -----
    # When multiple cohorts are overlaid, plot each at a small horizontal
    # offset from the integer slot centre so the means + error bars don't
    # stack on top of each other. Total fan width = 0.30 units, well under
    # the 1-unit gap between adjacent slots so they never bleed together.
    # 1 group -> no offset; 2-4 groups -> symmetric offsets around 0.
    def _will_plot(traj):
        gg = f[f["trajectory"] == traj]
        if gg.empty:
            return False
        return (gg["visit_rel"].value_counts() >= 3).any()

    plottable = [t for t in traj_groups if _will_plot(t)]
    n_active = len(plottable)
    if n_active <= 1:
        offsets = {t: 0.0 for t in plottable}
    else:
        spread = 0.15                         # total fan width (halved)
        step   = spread / (n_active - 1)
        offsets = {t: -spread / 2 + i * step
                   for i, t in enumerate(plottable)}

    # Stem-and-error per ordinal slot per group  ── no smoothed band ──
    for traj in traj_groups:
        g = f[f["trajectory"] == traj]
        if g.empty:
            continue
        color  = TRAJ_COLORS.get(traj, "#444")
        dx_off = offsets.get(traj, 0.0)
        slots_int, xs, ys, errs, ns = [], [], [], [], []
        for slot in sorted(g["visit_rel"].unique()):
            sub = g[g["visit_rel"] == slot]
            if len(sub) < 3:
                continue
            mean = sub[metabolite].mean()
            sem  = sub[metabolite].std() / np.sqrt(len(sub))
            slots_int.append(int(slot))
            xs.append(slot + dx_off)
            ys.append(mean)
            errs.append(1.96 * sem)
            ns.append(sub["RID"].nunique())
        if not xs:
            continue
        # Show the 95% CI whiskers only when a single cohort is plotted.
        # With multiple cohorts the bars stack and become visually noisy;
        # the per-slot stats table below the chart still carries the
        # full statistical detail (n, mean, p) so nothing is hidden.
        show_ci      = (n_active == 1)
        error_kwarg  = (dict(error_y=dict(type="data", array=errs,
                                          color=color,
                                          thickness=1.5, width=8))
                         if show_ci else {})
        # Hover line for CI is only meaningful when CI is visible.
        hover = ("<b>%{customdata[1]}</b><br>"
                 "visit slot: %{customdata[2]:+d}<br>"
                 f"{metabolite} mean: %{{y:.2f}}<br>"
                 + ("± 95% CI: %{customdata[3]:.2f}<br>" if show_ci else "")
                 + "n patients: %{customdata[0]}<extra></extra>")
        # customdata carries the integer slot (so hover reads "+0"/"-1"
        # instead of the dodged float) plus the CI half-width when shown.
        if show_ci:
            cd = np.array([[ns[i], traj, slots_int[i], errs[i]]
                            for i in range(len(xs))], dtype=object)
        else:
            cd = np.array([[ns[i], traj, slots_int[i]]
                            for i in range(len(xs))], dtype=object)
        fig.add_trace(go.Scatter(
            x=xs, y=ys,
            mode="lines+markers",
            line=dict(color=color, width=2.5),
            marker=dict(size=10, color=color,
                        line=dict(color="white", width=1)),
            name=f"{traj}  (n={g['RID'].nunique()})",
            customdata=cd,
            hovertemplate=hover,
            **error_kwarg,
        ))

    # Slot dressing
    fig.add_vline(x=0, line=dict(color="black", width=1.2, dash="dash"),
                  annotation_text="diagnosis change",
                  annotation_position="top right",
                  annotation_font_size=11)
    for s in SLOTS:
        if s != 0:
            fig.add_vline(x=s, line=dict(color="#e2e8f0", width=1, dash="dot"))

    fig.update_layout(
        title=(f"<b>{metabolite}</b>  •  visit-ordinal trajectory<br>"
               f"<span style='font-size:11px;color:#64748b'>"
               f"x = visits before/after diagnosis change  "
               f"(converters/reverters: first visit at new diagnosis; "
               f"stable: last observed visit)"
               f"</span>"),
        xaxis_title="Visit slot relative to diagnosis change",
        yaxis_title=f"{metabolite}  (Box-Cox)"
                    if metabolite not in ("L_TYROSINE",
                                          "secondary_primary_ratio",
                                          "DCA_CA_ratio",
                                          "microbial_bile_acid_index")
                    else (f"{metabolite}  (μM)"
                          if metabolite == "L_TYROSINE"
                          else f"{metabolite}  (ratio)"),
        template="clinical",
        height=460,
        margin=dict(l=60, r=20, t=80, b=50),
        legend=dict(orientation="h", y=-0.18),
        xaxis=dict(tickmode="array", tickvals=SLOTS,
                   ticktext=[f"{s:+d}" for s in SLOTS]),
        hovermode="closest",
    )
    return fig


def per_slot_stats_table(metabolite, traj_focus, baseline_group, sex):
    """Mann-Whitney U comparing each ordinal slot to baseline at slot 0."""
    conv = DF[DF["trajectory"] == traj_focus]
    base = DF[DF["trajectory"] == baseline_group]
    if sex and sex != "All":
        conv = conv.loc[conv["sex"].to_numpy() == sex]
        base = base.loc[base["sex"].to_numpy() == sex]
    rows = []
    base_vals = base[metabolite].dropna()
    for s in SLOTS:
        x = conv[conv["visit_rel"] == s][metabolite].dropna()
        n_pat = conv[conv["visit_rel"] == s]["RID"].nunique()
        if len(x) >= 3 and len(base_vals) >= 3:
            try:
                _, p = stats.mannwhitneyu(x, base_vals, alternative="two-sided")
            except ValueError:
                p = np.nan
            rows.append({
                "Slot": f"{s:+d}", "n visits": len(x), "n patients": n_pat,
                "Mean": f"{x.mean():.2f}", "Median": f"{x.median():.2f}",
                f"Δ vs {baseline_group}": f"{(x.mean()-base_vals.mean()):+.2f}",
                "p (MWU)": (f"{p:.2e}" if pd.notna(p) and p < 1e-3
                            else (f"{p:.3f}" if pd.notna(p) else "—")),
            })
        else:
            rows.append({
                "Slot": f"{s:+d}", "n visits": len(x), "n patients": n_pat,
                "Mean": "—", "Median": "—",
                f"Δ vs {baseline_group}": "—", "p (MWU)": "—",
            })
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- #
# Tab B — Forest plot of metabolite effect sizes (converter vs stable)
# --------------------------------------------------------------------------- #

def _hedges_g(a: np.ndarray, b: np.ndarray):
    """Hedges' g (bias-corrected standardized mean difference) and 95% CI."""
    na, nb = len(a), len(b)
    if na < 3 or nb < 3:
        return np.nan, np.nan, np.nan
    va, vb = a.var(ddof=1), b.var(ddof=1)
    s_pool = np.sqrt(((na - 1) * va + (nb - 1) * vb) / (na + nb - 2))
    if s_pool == 0 or not np.isfinite(s_pool):
        return np.nan, np.nan, np.nan
    d = (a.mean() - b.mean()) / s_pool
    # Hedges' small-sample correction
    j = 1 - 3 / (4 * (na + nb) - 9)
    g = d * j
    se = np.sqrt((na + nb) / (na * nb) + g ** 2 / (2 * (na + nb)))
    return g, g - 1.96 * se, g + 1.96 * se


def forest_figure(traj_focus, baseline_group, sex, slot):
    """One row per metabolite, x = Hedges' g (converter − baseline) at slot."""
    conv = DF[DF["trajectory"] == traj_focus]
    base = DF[DF["trajectory"] == baseline_group]
    if sex and sex != "All":
        conv = conv.loc[conv["sex"].to_numpy() == sex]
        base = base.loc[base["sex"].to_numpy() == sex]
    conv_slot = conv[conv["visit_rel"] == slot]

    rows = []
    for m in ORDERED_METABOLITES:
        a = conv_slot[m].dropna().to_numpy()
        b = base[m].dropna().to_numpy()
        g, lo, hi = _hedges_g(a, b)
        rows.append({
            "metabolite": m, "family": METABOLITE_TO_FAMILY.get(m, "other"),
            "g": g, "lo": lo, "hi": hi,
            "n_conv": len(a), "n_base": len(b),
        })
    res = pd.DataFrame(rows).dropna(subset=["g"]).copy()
    res = res.sort_values(["family", "g"], ascending=[True, True])
    if res.empty:
        return go.Figure().update_layout(title="No data for current filters",
                                         template="clinical", height=720)

    fam_colors = {
        "Bile acids — primary":   "#3b82f6",
        "Bile acids — secondary": "#22c55e",
        "Bile-acid ratios":       "#a855f7",
        "Amino acids":            "#f59e0b",
        "Fatty acids (acyl)":     "#ef4444",
        "Organic acids / other":  "#64748b",
    }

    fig = go.Figure()
    for fam, sub in res.groupby("family", sort=False):
        fig.add_trace(go.Scatter(
            x=sub["g"], y=sub["metabolite"],
            mode="markers",
            marker=dict(size=10, color=fam_colors.get(fam, "#444"),
                        line=dict(color="white", width=1)),
            error_x=dict(type="data",
                         array=sub["hi"] - sub["g"],
                         arrayminus=sub["g"] - sub["lo"],
                         thickness=1.5, width=4,
                         color=fam_colors.get(fam, "#444")),
            name=fam,
            customdata=np.stack([sub["n_conv"], sub["n_base"], sub["lo"],
                                  sub["hi"]], axis=1),
            hovertemplate=(
                "<b>%{y}</b><br>"
                "Hedges' g = %{x:.2f}  "
                "[%{customdata[2]:.2f}, %{customdata[3]:.2f}]<br>"
                f"n converters = %{{customdata[0]}}  "
                f"n {baseline_group} = %{{customdata[1]}}<extra></extra>"
            ),
        ))

    fig.add_vline(x=0, line=dict(color="black", width=1, dash="dash"))
    fig.update_layout(
        title=(f"<b>{traj_focus}</b> vs <b>{baseline_group}</b> at visit slot "
               f"{slot:+d}  •  effect size (Hedges' g) per metabolite"),
        xaxis_title="Hedges' g  (positive = higher in converters)",
        yaxis_title="",
        template="clinical",
        height=max(520, 22 * len(res) + 120),
        margin=dict(l=180, r=20, t=70, b=40),
        legend=dict(orientation="h", y=-0.08),
    )
    return fig


# --------------------------------------------------------------------------- #
# Tab C — PCA biological state space
# --------------------------------------------------------------------------- #

_PCA_CACHE = {}


def _fit_pca():
    """One-time fit on the cohort-wide z-scored 29-metabolite matrix."""
    if "pca" in _PCA_CACHE:
        return _PCA_CACHE["pca"], _PCA_CACHE["scaler"], _PCA_CACHE["idx"]
    X = DF[METABOLITES].copy()
    keep = X.dropna().index
    Xv = X.loc[keep].to_numpy()
    scaler = StandardScaler().fit(Xv)
    pca = PCA(n_components=4).fit(scaler.transform(Xv))
    _PCA_CACHE.update(pca=pca, scaler=scaler, idx=keep)
    return pca, scaler, keep


def pca_figure(traj_groups, sex, color_by, show_arrows, pcs=(0, 1)):
    """2-D PCA of each visit's 29-metabolite vector."""
    pca, scaler, keep = _fit_pca()
    base = DF.loc[keep].copy()
    if traj_groups:
        base = base[base["trajectory"].isin(traj_groups)]
    if sex and sex != "All":
        base = base.loc[base["sex"].to_numpy() == sex]
    if base.empty:
        return go.Figure().update_layout(
            title="No data for current filters",
            template="clinical", height=620)

    coords = pca.transform(scaler.transform(base[METABOLITES].to_numpy()))
    base = base.assign(PC1=coords[:, pcs[0]], PC2=coords[:, pcs[1]])
    var = pca.explained_variance_ratio_ * 100

    fig = go.Figure()

    if color_by == "trajectory":
        groups = base["trajectory"].unique()
        for grp in groups:
            sub = base[base["trajectory"] == grp]
            fig.add_trace(go.Scatter(
                x=sub["PC1"], y=sub["PC2"], mode="markers",
                marker=dict(size=7,
                            color=TRAJ_COLORS.get(grp, "#444"),
                            opacity=0.65,
                            line=dict(width=0.4, color="white")),
                name=f"{grp}  (n={sub['RID'].nunique()})",
                customdata=np.stack([
                    sub["RID"], sub["dx"], sub["visit_rel"].fillna(99)
                ], axis=1),
                hovertemplate=("RID %{customdata[0]}<br>"
                                "dx=%{customdata[1]}<br>"
                                "visit slot=%{customdata[2]:+.0f}<br>"
                                "PC1=%{x:.2f}  PC2=%{y:.2f}<extra></extra>"),
            ))
    elif color_by == "dx":
        for dx in ["NL", "MCI", "AD"]:
            sub = base[base["dx"] == dx]
            if sub.empty:
                continue
            fig.add_trace(go.Scatter(
                x=sub["PC1"], y=sub["PC2"], mode="markers",
                marker=dict(size=7, color=DX_COLORS[dx], opacity=0.65,
                            line=dict(width=0.4, color="white")),
                name=f"dx={dx}  (n={len(sub)})",
                customdata=np.stack([sub["RID"], sub["trajectory"]], axis=1),
                hovertemplate=("RID %{customdata[0]}<br>%{customdata[1]}<br>"
                                "PC1=%{x:.2f}  PC2=%{y:.2f}<extra></extra>"),
            ))
    elif color_by == "visit_rel":
        sub = base.dropna(subset=["visit_rel"])
        fig.add_trace(go.Scatter(
            x=sub["PC1"], y=sub["PC2"], mode="markers",
            marker=dict(size=7, color=sub["visit_rel"],
                        colorscale="RdBu_r", cmid=0,
                        showscale=True, opacity=0.7,
                        colorbar=dict(title="visit slot"),
                        line=dict(width=0.4, color="white")),
            customdata=np.stack([sub["RID"], sub["dx"],
                                  sub["trajectory"]], axis=1),
            hovertemplate=("RID %{customdata[0]}<br>%{customdata[2]}<br>"
                            "dx=%{customdata[1]}<extra></extra>"),
            name="visits",
        ))
    elif color_by == "sex":
        for sx, c in [("Male", "#3b82f6"), ("Female", "#ec4899")]:
            sub = base[base["sex"] == sx]
            if sub.empty:
                continue
            fig.add_trace(go.Scatter(
                x=sub["PC1"], y=sub["PC2"], mode="markers",
                marker=dict(size=7, color=c, opacity=0.65,
                            line=dict(width=0.4, color="white")),
                name=f"{sx}  (n={len(sub)})",
                # customdata[0] must be RID for the click_to_drill
                # callback to teleport into the patient view.
                customdata=np.stack([
                    sub["RID"], sub["dx"], sub["trajectory"],
                ], axis=1),
                hovertemplate=("RID %{customdata[0]}<br>"
                               "%{customdata[2]}<br>"
                               "dx=%{customdata[1]}<br>"
                               "PC1=%{x:.2f}  PC2=%{y:.2f}<extra></extra>"),
            ))

    # Per-patient first → last arrows
    if show_arrows:
        for rid, g in base.sort_values("visit_idx").groupby("RID"):
            if len(g) < 2:
                continue
            fig.add_annotation(
                x=g["PC1"].iloc[-1], y=g["PC2"].iloc[-1],
                ax=g["PC1"].iloc[0], ay=g["PC2"].iloc[0],
                xref="x", yref="y", axref="x", ayref="y",
                showarrow=True, arrowhead=2, arrowsize=0.8,
                arrowwidth=1, arrowcolor="rgba(0,0,0,0.35)",
            )

    fig.update_layout(
        title=("<b>PCA biological state space</b>  •  "
               f"each visit projected onto PC{pcs[0]+1}/PC{pcs[1]+1}<br>"
               f"<span style='font-size:11px;color:#64748b'>"
               f"PC{pcs[0]+1} {var[pcs[0]]:.1f}% var  •  "
               f"PC{pcs[1]+1} {var[pcs[1]]:.1f}% var  •  "
               f"{len(base):,} visits  •  "
               f"{base['RID'].nunique():,} participants</span>"),
        xaxis_title=f"PC{pcs[0]+1} ({var[pcs[0]]:.1f}% var)",
        yaxis_title=f"PC{pcs[1]+1} ({var[pcs[1]]:.1f}% var)",
        template="clinical",
        height=620,
        margin=dict(l=60, r=20, t=80, b=50),
        legend=dict(orientation="h", y=-0.12),
    )
    return fig


def pca_loadings_figure(pcs=(0, 1)):
    """Top loading metabolites for the selected PCs."""
    pca, _, _ = _fit_pca()
    loadings = pca.components_  # (n_components, n_features)
    fig = make_subplots(rows=1, cols=2,
                        subplot_titles=[f"PC{pcs[0]+1} loadings",
                                        f"PC{pcs[1]+1} loadings"],
                        horizontal_spacing=0.18)
    for col, pc in enumerate(pcs, start=1):
        lo = pd.Series(loadings[pc], index=METABOLITES).sort_values()
        fig.add_trace(go.Bar(
            x=lo.values, y=lo.index, orientation="h",
            marker=dict(color=np.where(lo.values >= 0, "#0ea5e9", "#f43f5e")),
            hovertemplate="%{y}: %{x:.2f}<extra></extra>",
            showlegend=False,
        ), row=1, col=col)
    fig.update_layout(
        template="clinical",
        height=720, margin=dict(l=120, r=20, t=60, b=40),
        title="<b>PC loadings</b>  •  contribution of each metabolite",
    )
    return fig


# --------------------------------------------------------------------------- #
# Tab D — Patient drill-down
# --------------------------------------------------------------------------- #

def drilldown_figure(rid):
    if rid is None or rid not in DF["RID"].unique():
        return go.Figure().update_layout(
            title=("Click a trajectory line, forest dot, PCA point, or pick a "
                   "patient to see their full metabolite panel"),
            template="clinical", height=640,
        )
    g = DF[DF["RID"] == int(rid)].sort_values("visit_idx")
    traj = g["trajectory"].iloc[0]
    sex = g["sex"].iloc[0]
    n_v = int(g["n_visits"].iloc[0])
    end_idx = g["end_visit_idx"].iloc[0]

    panel = ORDERED_ME
# --------------------------------------------------------------------------- #
# Tab D — Patient drill-down
# --------------------------------------------------------------------------- #

def drilldown_figure(rid):
    if rid is None or rid not in DF["RID"].unique():
        return go.Figure().update_layout(
            title=("Click a trajectory line, forest dot, PCA point, or pick "
                   "a patient to see their full metabolite panel"),
            template="clinical", height=640,
        )
    g = DF[DF["RID"] == int(rid)].sort_values("visit_idx")
    traj = g["trajectory"].iloc[0]
    sex = g["sex"].iloc[0]
    n_v = int(g["n_visits"].iloc[0])

    panel = ORDERED_METABOLITES[:9]
    fig = make_subplots(rows=3, cols=3, subplot_titles=panel,
                        vertical_spacing=0.12, horizontal_spacing=0.07)
    for i, m in enumerate(panel):
        r, c = i // 3 + 1, i % 3 + 1
        fig.add_trace(go.Scatter(
            x=g["visit_rel"], y=g[m],
            mode="lines",
            line=dict(color=TRAJ_COLORS.get(traj, "#333"), width=2),
            showlegend=False, hoverinfo="skip",
        ), row=r, col=c)
        for dx, color in DX_COLORS.items():
            sub = g[g["dx"] == dx]
            if not sub.empty:
                fig.add_trace(go.Scatter(
                    x=sub["visit_rel"], y=sub[m],
                    mode="markers",
                    marker=dict(size=10, color=color,
                                line=dict(width=1, color="black")),
                    showlegend=(i == 0), name=dx,
                    customdata=sub[["months_from_baseline"]].to_numpy(),
                    hovertemplate=("Dx=" + dx + "<br>visit slot "
                                   "%{x:+d}<br>" + m + " = %{y:.2f}<br>"
                                   "month %{customdata[0]:.0f}"
                                   "<XX></XX>").replace("XX", "extra"),
                ), row=r, col=c)
        fig.add_vline(x=0, line=dict(color="black", width=1, dash="dash"),
                      row=r, col=c)

    fig.update_xaxes(tickmode="array", tickvals=SLOTS,
                     ticktext=[("+" if s>=0 else "") + str(s) for s in SLOTS])
    end_word = ("last observed visit" if traj.startswith("stable_")
                else "diagnosis change")
    title_txt = ("<b>RID " + str(rid) + "</b>  ·  " + str(traj) + "  ·  "
                 + str(sex) + "  ·  " + str(n_v)
                 + " visits  ·  slot 0 = " + end_word)
    fig.update_layout(
        title=title_txt, template="clinical", height=640,
        margin=dict(l=50, r=20, t=80, b=40),
        legend=dict(orientation="h", y=1.05),
    )
    return fig


# --------------------------------------------------------------------------- #
# Tab E - Cohort overview (statistical summary of the dataset)
# --------------------------------------------------------------------------- #

# Canonical consecutive yearly transitions, in chronological order.
# We exclude sc -> bl and bl -> m06 / m06 -> m12 per the cohort-info brief:
# the early-screening cadence isn't the "real" follow-up cadence.
_GAP_TRANSITIONS_ORDER = [
    "bl -> m12",
    "m12 -> m24",
    "m24 -> m36",
    "m36 -> m48",
    "m48 -> m60",
    "m60 -> m72",
    "m72 -> m84",
    "m84 -> m96",
]


def visit_gap_figure():
    """Bar chart: mean +/- std months between consecutive yearly visits."""
    d = DF.sort_values(["RID", "months_from_baseline"]).copy()
    d["prev_viscode2"] = d.groupby("RID")["VISCODE2"].shift(1)
    d["prev_months"] = d.groupby("RID")["months_from_baseline"].shift(1)
    d["gap_months"] = d["months_from_baseline"] - d["prev_months"]
    d["transition"] = (d["prev_viscode2"].astype(str)
                        + " -> " + d["VISCODE2"].astype(str))
    d = d.dropna(subset=["gap_months"])
    agg = (d[d["transition"].isin(_GAP_TRANSITIONS_ORDER)]
             .groupby("transition")["gap_months"]
             .agg(["count", "mean", "std", "median"]).round(2)
             .reindex(_GAP_TRANSITIONS_ORDER).dropna(how="all").reset_index())

    fig = go.Figure(go.Bar(
        x=agg["transition"], y=agg["mean"],
        error_y=dict(type="data", array=agg["std"], thickness=1.5, width=8,
                     color=INK_SECONDARY),
        marker=dict(color=ACCENT, line=dict(color="white", width=1)),
        customdata=np.stack([agg["count"], agg["std"], agg["median"]], axis=1),
        hovertemplate=("<b>%{x}</b><br>"
                       "mean = %{y:.1f} mo<br>"
                       "std  = %{customdata[1]:.1f}<br>"
                       "median = %{customdata[2]:.1f}<br>"
                       "n transitions = %{customdata[0]}<extra></extra>"),
    ))
    fig.add_hline(y=12, line=dict(color=INK_MUTED, dash="dot", width=1),
                  annotation_text="12 months", annotation_position="right")
    fig.update_layout(
        title=("<b>Inter-visit gap by transition</b>  -  "
               "screening (sc -> bl, bl -> m06, m06 -> m12) excluded"),
        xaxis_title="Visit transition",
        yaxis_title="Months elapsed (mean +/- std)",
        template="clinical",
        height=420,
    )
    return fig


def age_at_conversion_figure():
    """Boxplot of age at conversion for each diagnosis transition.

    For each patient we walk their visits in chronological order and
    record the age recorded at the visit where the dx changed:
        NL -> MCI :  first MCI visit that follows an NL visit
        MCI -> NL :  first NL visit that follows an MCI visit (reverter)
        MCI -> AD :  first AD visit that follows an MCI visit

    A patient may contribute to more than one transition (e.g. NL->MCI
    then MCI->AD). Only the first occurrence of each transition per
    patient is counted. Patients with no observed transition contribute
    nothing.
    """
    rows = []
    d = DF.dropna(subset=["dx", "age_at_visit"]) \
          .sort_values(["RID", "visit_idx"])
    for rid, g in d.groupby("RID"):
        dxs  = g["dx"].tolist()
        ages = g["age_at_visit"].tolist()
        seen = set()
        for i in range(len(dxs) - 1):
            a, b = dxs[i], dxs[i + 1]
            key = (a, b)
            if a == b or key in seen:
                continue
            seen.add(key)
            if key in {("NL", "MCI"), ("MCI", "NL"), ("MCI", "AD")}:
                rows.append((f"{a} -> {b}", ages[i + 1]))

    df = pd.DataFrame(rows, columns=["transition", "age"])

    # Standardised colours: end-state diagnosis colour for each box.
    palette = {
        "NL -> MCI": DX_COLORS["MCI"],   # grey
        "MCI -> NL": DX_COLORS["NL"],    # green (reverters)
        "MCI -> AD": DX_COLORS["AD"],    # red
    }
    order = ["NL -> MCI", "MCI -> NL", "MCI -> AD"]

    fig = go.Figure()
    for tr in order:
        sub = df[df["transition"] == tr]
        n   = len(sub)
        med = sub["age"].median() if n else float("nan")
        fig.add_trace(go.Box(
            y=sub["age"],
            name=f"{tr}<br><span style='font-size:10px;"
                 f"color:{INK_MUTED}'>n = {n}, median = {med:.1f}</span>",
            marker=dict(color=palette[tr]),
            boxmean=True,         # show mean dashed line + sd diamond
            boxpoints="outliers",
            line=dict(width=1.5),
            fillcolor=palette[tr],
            opacity=0.55,
            hovertemplate="%{y:.1f} yr<extra></extra>",
        ))

    fig.update_layout(
        title=("<b>Age at first diagnosis transition</b>  -  "
               "one observation per patient per transition"),
        xaxis_title="Diagnosis transition",
        yaxis_title="Age at the new-diagnosis visit (years)",
        template="clinical",
        height=420,
        showlegend=False,
    )
    return fig


def sex_over_years_figure():
    """Stacked area: count of Male / Female participants per calendar year."""
    d = DF.copy()
    d["year"] = pd.to_datetime(d["EXAMDATE"]).dt.year
    # One row per (year, RID, sex) so we count unique participants
    uniq = d.drop_duplicates(subset=["year", "RID"])
    counts = (uniq.groupby(["year", "sex"]).size()
              .unstack("sex", fill_value=0)
              .reset_index().sort_values("year"))
    # Ensure both columns exist
    for col in ("Male", "Female"):
        if col not in counts.columns:
            counts[col] = 0
    counts["total"] = counts["Male"] + counts["Female"]
    counts["pct_male"] = (counts["Male"] / counts["total"] * 100).round(1)
    counts["pct_female"] = (counts["Female"] / counts["total"] * 100).round(1)

    fig = go.Figure()
    # Female -> blue, Male -> magenta (swapped from the original mapping).
    fig.add_trace(go.Scatter(
        x=counts["year"], y=counts["Female"],
        name="Female", mode="lines",
        stackgroup="one",
        line=dict(width=0.5, color="#3b82f6"),
        fillcolor="rgba(59, 130, 246, 0.55)",
        customdata=np.stack([counts["pct_female"], counts["total"]], axis=1),
        hovertemplate=("Year %{x}<br>Female: %{y}  "
                       "(%{customdata[0]:.1f}% of %{customdata[1]})"
                       "<extra></extra>"),
    ))
    fig.add_trace(go.Scatter(
        x=counts["year"], y=counts["Male"],
        name="Male", mode="lines",
        stackgroup="one",
        line=dict(width=0.5, color="#ec4899"),
        fillcolor="rgba(236, 72, 153, 0.55)",
        customdata=np.stack([counts["pct_male"], counts["total"]], axis=1),
        hovertemplate=("Year %{x}<br>Male: %{y}  "
                       "(%{customdata[0]:.1f}% of %{customdata[1]})"
                       "<extra></extra>"),
    ))
    fig.update_layout(
        title="<b>Cohort sex composition over calendar years</b>",
        xaxis_title="Calendar year",
        yaxis_title="Unique participants",
        template="clinical",
        height=400,
        legend=dict(orientation="h", y=-0.18),
        hovermode="x unified",
    )
    return fig


def age_over_years_figure():
    """Line plot: mean age per diagnosis per calendar year."""
    d = DF.copy()
    d["year"] = pd.to_datetime(d["EXAMDATE"]).dt.year
    if "age_at_visit" not in d.columns:
        d["age_at_visit"] = d["year"] - d["birth_year"].astype(float)

    agg = (d.groupby(["year", "dx"])["age_at_visit"]
             .agg(["mean", "std", "count"]).reset_index())
    agg = agg[agg["count"] >= 3]

    fig = go.Figure()
    for dx, color in [("NL", DX_COLORS["NL"]),
                      ("MCI", DX_COLORS["MCI"]),
                      ("AD", DX_COLORS["AD"])]:
        sub = agg[agg["dx"] == dx].sort_values("year")
        if sub.empty:
            continue
        fig.add_trace(go.Scatter(
            x=sub["year"], y=sub["mean"],
            mode="lines+markers", name=dx,
            line=dict(color=color, width=2.5),
            marker=dict(size=7, color=color,
                        line=dict(color="white", width=1)),
            customdata=np.stack([sub["count"]], axis=1),
            hovertemplate=(f"<b>{dx}</b>  year %{{x}}<br>"
                            "mean age %{y:.1f} yr<br>"
                            "n visits = %{customdata[0]}<extra></extra>"),
        ))
    fig.update_layout(
        title="<b>Mean age per diagnosis over calendar years</b>",
        xaxis_title="Calendar year",
        yaxis_title="Mean age (years)",
        template="clinical",
        height=400,
        legend=dict(orientation="h", y=-0.18),
    )
    return fig


def cohort_kpi_summary():
    """Returns plain-text KPI strings for the cohort overview tab."""
    d = DF
    # Inter-visit gap, restricted to canonical transitions
    s = d.sort_values(["RID", "months_from_baseline"]).copy()
    s["prev_v"] = s.groupby("RID")["VISCODE2"].shift(1)
    s["gap"] = (s["months_from_baseline"] -
                s.groupby("RID")["months_from_baseline"].shift(1))
    s["transition"] = s["prev_v"].astype(str) + " -> " + s["VISCODE2"].astype(str)
    gaps = s[s["transition"].isin(_GAP_TRANSITIONS_ORDER)]["gap"].dropna()
    return {
        "n_participants": int(d["RID"].nunique()),
        "n_visits":       int(len(d)),
        "n_male":         int(d.drop_duplicates("RID")["sex"].eq("Male").sum()),
        "n_male":      int(d.drop_duplicates("RID")["sex"].eq("Male").sum()),
        "n_female":    int(d.drop_duplicates("RID")["sex"].eq("Female").sum()),
        "follow_up_gap_mean": float(gaps.mean()),
        "follow_up_gap_std":  float(gaps.std()),
        "year_min": int(pd.to_datetime(d["EXAMDATE"]).dt.year.min()),
        "year_max": int(pd.to_datetime(d["EXAMDATE"]).dt.year.max()),
    }
