"""Gut-Microbiome Metabolite Dashboard - Visit-Ordinal Edition.

This is the main dashboard tested in the usability study. It is identical
to app_clean.py with the WebGazer / usability eye-tracking elements added:

  * `csv`, `os`, `time` imports and the GAZE_LOG_PATH constant for the
    on-disk session log.
  * An "Usability eye-tracking" control card in the top-right of the
    header with Start / Calibrate / Stop / Download CSV buttons and a
    status note.
  * `dcc.Store(id="gaze-batch-store")` + `dcc.Download(id="gaze-download")`
    plumbing at the bottom of the layout.
  * Three clientside callbacks that route Start / Calibrate / Stop button
    clicks to `window.gazeTracker` (defined in assets/tracking.js).
  * Server callbacks `save_gaze_batch` (appends each batched gaze payload
    to usability_gaze_log.csv) and `download_gaze_csv` (lets the
    researcher export the running log via a Dash Download component).

Tab order, terminology, KPI strip placement and the Cohort-information
layout are inherited verbatim from app_clean.py so the dashboard the
participants test is the dashboard the project shipped.
"""
from __future__ import annotations

# Standard library
import csv                # writer used by the eye-tracking save callback
import io                 # in-memory CSV buffer for the stats download
import logging
import os                 # file-existence check for the gaze-log CSV
import time               # session timestamps for gaze-log filenames

# Quiet down the per-request Werkzeug access log (200 / 304 spam).
logging.getLogger("werkzeug").setLevel(logging.WARNING)

# Dash primitives
from dash import Dash, Input, Output, State, dcc, html, no_update

# Figure builders + in-memory dataframe.
import viz


# --------------------------------------------------------------------------- #
# Eye-tracking output path.
# Written to the working directory the dashboard was launched from.
# --------------------------------------------------------------------------- #
GAZE_LOG_PATH = "usability_gaze_log.csv"


# --------------------------------------------------------------------------- #
# Cohort constants
# --------------------------------------------------------------------------- #
TRAJECTORIES = ["MCI->AD", "NL->MCI", "NL->MCI->AD", "MCI->NL",
                "stable_NL", "stable_MCI", "stable_AD"]
CONVERTER_GROUPS = ["MCI->AD", "NL->MCI", "NL->MCI->AD", "MCI->NL"]
BASELINE_GROUPS = ["stable_NL", "stable_MCI", "stable_AD"]

SECTION_VISIBILITY = {
    "traj":    {"sec-traj-plot"},
    "forest":  {"sec-comparison", "sec-forest-slot"},
    "pca":     {"sec-pca"},
    "patient": {"sec-patient"},
    "info":    set(),
}
ALL_SECTIONS = ["sec-traj-plot", "sec-comparison",
                "sec-forest-slot", "sec-pca", "sec-patient"]


# --------------------------------------------------------------------------- #
# KPI strip helpers
# --------------------------------------------------------------------------- #
def cohort_summary():
    df = viz.DF
    return {
        "n_participants": df["RID"].nunique(),
        "n_visits":       len(df),
        "n_mci_ad":       df[df["trajectory"] == "MCI->AD"]["RID"].nunique(),
        "n_nl_mci":       df[df["trajectory"] == "NL->MCI"]["RID"].nunique(),
        "n_mci_nl":       df[df["trajectory"] == "MCI->NL"]["RID"].nunique(),
    }


def kpi_strip():
    s = cohort_summary()
    cards = [
        ("Participants", f"{s['n_participants']:,}",
         f"{s['n_visits']:,} longitudinal visits"),
        ("MCI -> AD", f"{s['n_mci_ad']:,}",
         "converters with full timeline"),
        ("NL -> MCI", f"{s['n_nl_mci']:,}",
         "early-progression cohort"),
        ("MCI -> NL", f"{s['n_mci_nl']:,}",
         "reverters (improvement)"),
    ]
    # marginTop: gap between the tab bar above and this strip.
    # marginBottom: 0 so the dash-tab-content's own padding-top is the only
    #               gap between this strip and the active tab's content.
    return html.Div(
        className="kpi-row",
        style={"marginTop": "var(--sp-5)", "marginBottom": "0"},
        children=[
            html.Div(className="kpi-card", children=[
                html.Div(label, className="label"),
                html.Div(value, className="value"),
                html.Div(delta, className="delta"),
            ]) for label, value, delta in cards
        ])


# --------------------------------------------------------------------------- #
# Eye-tracking control card (header right column)
# --------------------------------------------------------------------------- #
def eye_tracking_card():
    """Small card with Start / Calibrate / Stop / Download CSV buttons.

    Hidden state Components (gaze-batch-store, gaze-download) live at the
    bottom of the layout; this card only exposes the user-facing controls.
    """
    return html.Div(
        className="card",
        style={"padding": "10px 12px", "minWidth": "260px"},
        children=[
            html.Div("Usability eye-tracking",
                     className="card-title",
                     style={"marginBottom": "6px"}),
            html.Div(style={"display": "flex", "gap": "6px",
                            "flexWrap": "wrap"}, children=[
                html.Button("Start", id="gaze-start-btn",
                            className="btn btn-accent", n_clicks=0),
                html.Button("Calibrate", id="gaze-calibrate-btn",
                            className="btn", n_clicks=0),
                html.Button("Stop", id="gaze-stop-btn",
                            className="btn", n_clicks=0),
                html.Button("Download CSV", id="gaze-download-btn",
                            className="btn", n_clicks=0),
            ]),
            html.Div(id="gaze-status",
                     className="note",
                     style={"marginTop": "8px"},
                     children="Tracker idle. Click Start, then "
                              "Calibrate before each session."),
        ])


# --------------------------------------------------------------------------- #
# Sidebar
# --------------------------------------------------------------------------- #
def section(title, *children, sec_id=None):
    kwargs = {
        "className": "sidebar-section",
        "children": [html.H3(title), *children],
    }
    if sec_id is not None:
        kwargs["id"] = sec_id
    return html.Div(**kwargs)


SIDEBAR = html.Div(className="sidebar", children=[
    section(
        "Cohort",
        html.Label("Trajectory groups (overlaid)"),
        dcc.Checklist(
            id="traj-groups",
            options=[{"label": t, "value": t} for t in TRAJECTORIES],
            value=["MCI->AD", "stable_NL", "stable_MCI"],
            labelStyle={"display": "block", "fontSize": 13,
                        "marginBottom": "4px"},
        ),
        html.Label("Sex"),
        dcc.RadioItems(
            id="sex",
            options=[{"label": s, "value": s}
                     for s in ["All", "Male", "Female"]],
            value="All", inline=True, style={"fontSize": 13},
        ),
    ),

    section(
        "Trajectory plot",
        html.Label("Active metabolite"),
        dcc.Dropdown(
            id="metabolite",
            options=[{"label": m, "value": m}
                     for m in viz.ORDERED_METABOLITES],
            value="GLCA", clearable=False, style={"fontSize": 13},
        ),
        sec_id="sec-traj-plot",
    ),

    section(
        "Comparison (forest plot & stats)",
        html.Label("Converter / reverter group"),
        dcc.RadioItems(
            id="traj-focus",
            options=[{"label": t, "value": t} for t in CONVERTER_GROUPS],
            value="MCI->AD",
            labelStyle={"display": "block", "fontSize": 13,
                        "marginBottom": "4px"},
        ),
        html.Label("Baseline (reference)"),
        dcc.Dropdown(
            id="baseline-group",
            options=[{"label": t, "value": t} for t in BASELINE_GROUPS],
            value="stable_NL", clearable=False, style={"fontSize": 13},
        ),
        sec_id="sec-comparison",
    ),

    section(
        "Forest plot",
        html.Label("Visit slot"),
        dcc.RadioItems(
            id="forest-slot",
            options=[{"label": f"{s:+d}", "value": s} for s in viz.SLOTS],
            value=0, inline=True, style={"fontSize": 13},
        ),
        sec_id="sec-forest-slot",
    ),

    section(
        "PCA",
        html.Label("Color by"),
        dcc.RadioItems(
            id="pca-color",
            options=[
                {"label": "trajectory", "value": "trajectory"},
                {"label": "diagnosis",  "value": "dx"},
                {"label": "visit slot", "value": "visit_rel"},
                {"label": "sex",        "value": "sex"},
            ],
            value="trajectory",
            labelStyle={"display": "block", "fontSize": 13,
                        "marginBottom": "4px"},
        ),
        dcc.Checklist(
            id="pca-arrows",
            options=[{"label": "Show patient first->last arrows",
                      "value": "yes"}],
            value=[], style={"fontSize": 13, "marginTop": "8px"},
        ),
        sec_id="sec-pca",
    ),

    section(
        "Individual patient view",
        html.Label("RID"),
        dcc.Dropdown(id="rid", options=[], value=None,
                     style={"fontSize": 13},
                     placeholder="click a point/line/dot in any view"),
        sec_id="sec-patient",
    ),

    html.Div(id="meta-summary", className="note",
             style={"marginTop": "12px"}),
])


# --------------------------------------------------------------------------- #
# Graph card wrapper
# --------------------------------------------------------------------------- #
def graph_card(title, graph_id, height=None):
    children = [html.Div(title, className="card-title")] if title else []
    children.append(
        dcc.Loading(
            type="dot", color=viz.ACCENT,
            children=dcc.Graph(id=graph_id, config={
                "displaylogo": False,
                "modeBarButtonsToRemove": ["lasso2d", "select2d"],
                "toImageButtonOptions": {"format": "png", "scale": 2},
            }, style={"height": f"{height}px"} if height else {}),
        )
    )
    return html.Div(className="card", children=children)


# --------------------------------------------------------------------------- #
# App factory
# --------------------------------------------------------------------------- #
def _make_app() -> Dash:
    app = Dash(__name__,
               title="Metabolite Trajectories - Visit-Ordinal",
               update_title=None)

    app.layout = html.Div(className="app-shell", children=[
        SIDEBAR,
        html.Div(className="main", children=[
            # Header: title + subtitle on the left, eye-tracking card on
            # the right.  Flex layout keeps them on one line on desktop.
            html.Div(className="header",
                     style={"display": "flex",
                            "justifyContent": "space-between",
                            "alignItems": "flex-start", "gap": "24px"},
                     children=[
                html.Div(style={"flex": "1"}, children=[
                    html.H1("Gut-Microbiome Metabolite Trajectories"),
                    html.Div(className="subtitle", children=[
                        "Visit-ordinal anchoring. ",
                        html.B("Timepoint 0"),
                        " represents the visit where a diagnosis change "
                        "occurred, serving as the alignment anchor for "
                        "all patients' clinical histories. Prior to "
                        "this point, patients held a different "
                        "diagnosis than they did afterward.",
                        html.Br(),
                        "The x-axis is ",
                        html.B("visit count from diagnosis change"),
                        ", not calendar months - ADNI's roughly-yearly "
                        "visit cadence makes calendar windows mostly "
                        "empty.",
                    ]),
                ]),
                eye_tracking_card(),
            ]),
            # tab bar -> KPI strip -> active tab content
            dcc.Tabs(id="tabs", value="info", className="dash-tabs",
                     children=[
                dcc.Tab(label="A - Cohort information", value="info"),
                dcc.Tab(label="B - Trajectory",         value="traj"),
                dcc.Tab(label="C - Forest plot",        value="forest"),
                dcc.Tab(label="D - PCA state",          value="pca"),
                dcc.Tab(label="E - Individual patient view",
                        value="patient"),
            ]),
            kpi_strip(),
            html.Div(id="tab-content", className="dash-tab-content"),
        ]),

        # Hidden plumbing.
        dcc.Download(id="stats-download"),

        # --- Eye-tracking plumbing ---
        # gaze-batch-store receives the periodic batched payload from
        # tracking.js (via window.dash_clientside.set_props). The Python
        # callback save_gaze_batch then appends each batch to
        # GAZE_LOG_PATH. gaze-download holds the dcc.Download trigger
        # for the running CSV.
        dcc.Store(id="gaze-batch-store"),
        dcc.Download(id="gaze-download"),
    ])

    # ----- Tab-aware sidebar visibility -----
    @app.callback(
        [Output(sid, "style") for sid in ALL_SECTIONS],
        Input("tabs", "value"),
    )
    def toggle_sidebar(tab):
        visible = SECTION_VISIBILITY.get(tab, set())
        return [{} if sid in visible else {"display": "none"}
                for sid in ALL_SECTIONS]

    # ----- Tab content -----
    @app.callback(Output("tab-content", "children"), Input("tabs", "value"))
    def render_tab(tab):
        if tab == "traj":
            return [
                graph_card("Metabolite trajectory - mean +/- 95% CI per slot",
                           "trajectory-fig"),
                html.Div(className="card", children=[
                    html.Div(className="card-title",
                             style={"display": "flex",
                                    "justifyContent": "space-between",
                                    "alignItems": "center"},
                             children=[
                        html.Span("Per-slot statistics (vs baseline group)"),
                        html.Button("Download CSV", id="stats-download-btn",
                                    className="btn"),
                    ]),
                    html.Div(id="stats-table"),
                    html.Div(
                        "Two-sided Mann-Whitney U. n = patients with a "
                        "non-missing measurement at that slot.",
                        className="note"),
                ]),
            ]
        if tab == "forest":
            return [
                graph_card("Effect size (Hedges' g) - converter - baseline",
                           "forest-fig"),
                html.Div(
                    "Tip: click a metabolite dot to load it in Tab B and "
                    "the patient drill-down.",
                    className="note card",
                    style={"padding": "12px 16px"},
                ),
            ]
        if tab == "pca":
            return [
                html.Div(className="card-row", children=[
                    graph_card("Biological state space  (PC1 vs PC2)",
                               "pca-fig", height=620),
                    graph_card("PC loadings",
                               "pca-loadings-fig", height=620),
                ]),
            ]
        if tab == "patient":
            return [graph_card(None, "drilldown-fig")]
        if tab == "info":
            k = viz.cohort_kpi_summary()
            kpi_cards = html.Div(
                className="kpi-row",
                # 3 cards instead of 4 since Participants moved to the top
                # strip; override the default 4-column grid.
                style={"gridTemplateColumns": "repeat(3, 1fr)"},
                children=[
                html.Div(className="kpi-card", children=[
                    html.Div("Sex split", className="label"),
                    html.Div(f"{k['n_male']:,} M / {k['n_female']:,} F",
                             className="value"),
                    html.Div("unique participants", className="delta"),
                ]),
                html.Div(className="kpi-card", children=[
                    html.Div("Inter-visit gap", className="label"),
                    html.Div(f"{k['follow_up_gap_mean']:.1f} +/- "
                             f"{k['follow_up_gap_std']:.1f} mo",
                             className="value"),
                    html.Div("yearly transitions only "
                             "(sc->bl, bl->m06, m06->m12 excluded)",
                             className="delta"),
                ]),
                html.Div(className="kpi-card", children=[
                    html.Div("Calendar span", className="label"),
                    html.Div(f"{k['year_max'] - k['year_min']} years",
                             className="value"),
                    html.Div(f"{k['year_min']} to {k['year_max']}",
                             className="delta"),
                ]),
            ])
            return [
                kpi_cards,
                html.Div(className="card-row", children=[
                    graph_card("Sex composition over calendar years",
                               "info-sex-fig", height=420),
                    graph_card("Mean age per diagnosis over years",
                               "info-age-fig", height=420),
                ]),
                graph_card("Inter-visit gap by transition", "info-gap-fig"),
            ]
        return html.Div()

    # ----- Tab B: trajectory + stats -----
    @app.callback(
        Output("trajectory-fig", "figure"),
        Output("stats-table", "children"),
        Input("metabolite", "value"),
        Input("traj-groups", "value"),
        Input("sex", "value"),
        Input("traj-focus", "value"),
        Input("baseline-group", "value"),
    )
    def update_trajectory(metab, groups, sex, traj_focus, baseline_group):
        fig = viz.trajectory_figure(metab, groups, sex, show_lines=False)
        stats_df = viz.per_slot_stats_table(metab, traj_focus,
                                            baseline_group, sex)
        table = html.Table(
            [html.Thead(html.Tr([html.Th(c) for c in stats_df.columns]))] +
            [html.Tbody([html.Tr([html.Td(stats_df.iloc[r][c])
                                  for c in stats_df.columns])
                         for r in range(len(stats_df))])],
            className="stats-table",
        )
        return fig, table

    # ----- Tab B: stats CSV download -----
    @app.callback(
        Output("stats-download", "data"),
        Input("stats-download-btn", "n_clicks"),
        State("metabolite", "value"),
        State("traj-focus", "value"),
        State("baseline-group", "value"),
        State("sex", "value"),
        prevent_initial_call=True,
    )
    def download_stats(n_clicks, metab, focus, baseline, sex):
        if not n_clicks:
            return no_update
        df = viz.per_slot_stats_table(metab, focus, baseline, sex)
        buf = io.StringIO()
        df.to_csv(buf, index=False)
        return dict(content=buf.getvalue(),
                    filename=f"stats_{metab}_{focus}_vs_{baseline}_{sex}.csv")

    # ----- Tab C: forest -----
    @app.callback(
        Output("forest-fig", "figure"),
        Input("traj-focus", "value"),
        Input("baseline-group", "value"),
        Input("sex", "value"),
        Input("forest-slot", "value"),
    )
    def update_forest(traj_focus, baseline_group, sex, slot):
        return viz.forest_figure(traj_focus, baseline_group, sex, slot)

    # ----- Tab D: PCA scatter + loadings -----
    @app.callback(
        Output("pca-fig", "figure"),
        Output("pca-loadings-fig", "figure"),
        Input("traj-groups", "value"),
        Input("sex", "value"),
        Input("pca-color", "value"),
        Input("pca-arrows", "value"),
    )
    def update_pca(groups, sex, color_by, arrows):
        return (viz.pca_figure(groups, sex, color_by,
                               show_arrows=("yes" in arrows)),
                viz.pca_loadings_figure())

    # ----- Tab E: drilldown -----
    @app.callback(Output("drilldown-fig", "figure"), Input("rid", "value"))
    def update_drilldown(rid):
        return viz.drilldown_figure(rid)

    # ----- Tab A: cohort overview figures -----
    @app.callback(
        Output("info-gap-fig", "figure"),
        Output("info-sex-fig", "figure"),
        Output("info-age-fig", "figure"),
        Input("tabs", "value"),
    )
    def update_cohort_info(tab):
        if tab != "info":
            return no_update, no_update, no_update
        return (viz.visit_gap_figure(),
                viz.sex_over_years_figure(),
                viz.age_over_years_figure())

    # ----- RID dropdown rebuild -----
    @app.callback(
        Output("rid", "options"),
        Output("rid", "value"),
        Input("traj-groups", "value"),
        Input("sex", "value"),
        State("rid", "value"),
    )
    def update_rid_options(groups, sex, current):
        rids = viz.all_rids(groups, sex)
        sub = viz.filter_df(groups, sex)
        options = [{"label": f"{r}  ({sub[sub.RID==r]['trajectory'].iloc[0]})",
                    "value": int(r)} for r in rids]
        return options, (current if current in rids
                         else (int(rids[0]) if rids else None))

    # ----- Click-to-drill: trajectory / PCA -> Tab E -----
    @app.callback(
        Output("rid", "value", allow_duplicate=True),
        Output("tabs", "value"),
        Input("trajectory-fig", "clickData"),
        Input("pca-fig", "clickData"),
        prevent_initial_call=True,
    )
    def click_to_drill(traj_click, pca_click):
        for click in (traj_click, pca_click):
            if click and click.get("points"):
                pt = click["points"][0]
                if "customdata" in pt and pt["customdata"]:
                    try:
                        return int(pt["customdata"][0]), "patient"
                    except (ValueError, TypeError):
                        continue
        return no_update, no_update

    # ----- Forest dot click -> active metabolite -----
    @app.callback(
        Output("metabolite", "value"),
        Input("forest-fig", "clickData"),
        prevent_initial_call=True,
    )
    def click_forest(click):
        if click and click.get("points"):
            y = click["points"][0].get("y")
            if y in viz.METABOLITES:
                return y
        return no_update

    # ===================================================================== #
    # EYE-TRACKING CALLBACKS (usability study)
    #
    # Three clientside callbacks route Start / Calibrate / Stop button
    # clicks to window.gazeTracker (defined in assets/tracking.js).
    # The server callback save_gaze_batch appends each periodic batch
    # of gaze samples to the CSV log on disk. download_gaze_csv lets
    # the researcher export the running log via a Dash Download.
    # ===================================================================== #

    # --- clientside: Start tracking
    app.clientside_callback(
        """async function(n) {
            if (!n) { return window.dash_clientside.no_update; }
            const r = await window.gazeTracker.start();
            return r === "active"
                ? "Tracker active. Run calibration before recording."
                : "Tracker failed to start - see browser console.";
        }""",
        Output("gaze-status", "children", allow_duplicate=True),
        Input("gaze-start-btn", "n_clicks"),
        prevent_initial_call=True,
    )

    # --- clientside: Calibrate (launches 9-point grid overlay)
    app.clientside_callback(
        """function(n) {
            if (!n) { return window.dash_clientside.no_update; }
            window.gazeTracker.calibrate();
            return "Calibrating - click each yellow dot 5x.";
        }""",
        Output("gaze-status", "children", allow_duplicate=True),
        Input("gaze-calibrate-btn", "n_clicks"),
        prevent_initial_call=True,
    )

    # --- clientside: Stop tracking, flush remaining buffer
    app.clientside_callback(
        """function(n) {
            if (!n) { return window.dash_clientside.no_update; }
            window.gazeTracker.stop();
            return "Tracker stopped. Click Download CSV to save the log.";
        }""",
        Output("gaze-status", "children", allow_duplicate=True),
        Input("gaze-stop-btn", "n_clicks"),
        prevent_initial_call=True,
    )

    # --- server: persist each batched gaze payload to CSV
    @app.callback(
        Output("gaze-status", "children", allow_duplicate=True),
        Input("gaze-batch-store", "data"),
        prevent_initial_call=True,
    )
    def save_gaze_batch(payload):
        # payload is None on first render; tracking.js sends
        # {samples: [...], flushed_at: ms, session_started_at: ms}.
        if not payload or not payload.get("samples"):
            return no_update
        samples = payload["samples"]
        new_file = not os.path.isfile(GAZE_LOG_PATH)
        with open(GAZE_LOG_PATH, "a", newline="") as f:
            w = csv.writer(f)
            if new_file:
                w.writerow(["timestamp_ms", "x_px", "y_px", "active_tab",
                            "flushed_at_ms", "session_started_at_ms"])
            flushed = payload.get("flushed_at", "")
            started = payload.get("session_started_at", "")
            for s in samples:
                w.writerow([s.get("t", ""),
                            s.get("x", ""),
                            s.get("y", ""),
                            s.get("tab", ""),
                            flushed, started])
        return (f"Wrote {len(samples)} samples at "
                f"{time.strftime('%H:%M:%S')}.")

    # --- server: download the running CSV via dcc.Download
    @app.callback(
        Output("gaze-download", "data"),
        Input("gaze-download-btn", "n_clicks"),
        prevent_initial_call=True,
    )
    def download_gaze_csv(n):
        if not n or not os.path.isfile(GAZE_LOG_PATH):
            return no_update
        with open(GAZE_LOG_PATH, "r") as f:
            content = f.read()
        return dict(content=content,
                    filename=f"usability_gaze_log_{int(time.time())}.csv")

    # ----- Sidebar footer counter -----
    @app.callback(
        Output("meta-summary", "children"),
        Input("traj-groups", "value"),
        Input("sex", "value"),
    )
    def update_meta(groups, sex):
        f = viz.filter_df(groups, sex)
        return (f"Selected: {f['RID'].nunique()} participants - "
                f"{len(f)} visits")

    return app


# --------------------------------------------------------------------------- #
# Module-level Dash instance and WSGI handle.
# `server` is exported so production deployments can: gunicorn app:server
# --------------------------------------------------------------------------- #

app = _make_app()
server = app.server


if __name__ == "__main__":
    counts = dict(viz.DF["sex"].value_counts(dropna=False))
    print(f"[app] loaded {len(viz.DF):,} rows  "
          f"sex dtype={viz.DF['sex'].dtype}  values={counts}",
          flush=True)
    app.run(debug=False, host="127.0.0.1", port=8050)
