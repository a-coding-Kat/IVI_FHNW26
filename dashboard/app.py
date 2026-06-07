"""Gut-Microbiome Metabolite Dashboard - Visit-Ordinal Edition
"""
from __future__ import annotations

# Standard library
import io                 # in-memory CSV buffer for the download button
import logging

# Quiet down the per-request Werkzeug access log (200 / 304 spam).
logging.getLogger("werkzeug").setLevel(logging.WARNING)

# Dash primitives
from dash import Dash, Input, Output, State, dcc, html, no_update, ctx

# Figure builders + the in-memory dataframe.
import viz


# --------------------------------------------------------------------------- #
# Colour overrides for THIS app only.
#
# Replace the dashboard-wide NL/AD colours with a colourblind-friendlier,
# higher-contrast pair:
#     NL  green  ->  vibrant blue   (#0072B2)
#     AD  red    ->  bright orange  (#E69F00)
#     MCI grey   ->  unchanged       (#94a3b8)
#
# Figure builders look up viz.DX_COLORS / viz.TRAJ_COLORS on every call,
# so monkey-patching the dicts here propagates to every chart in this
# process. The base palette in viz.py is untouched, so app.py and
# app_clean_umap.py keep the original green / grey / red.
# --------------------------------------------------------------------------- #
viz.DX_COLORS["NL"] = "#0072B2"     # vibrant blue
viz.DX_COLORS["AD"] = "#E69F00"     # bright orange

# Keep the trajectory palette consistent with the new endpoint colours.
viz.TRAJ_COLORS["stable_NL"] = "#0072B2"   # matches new NL
viz.TRAJ_COLORS["stable_AD"] = "#E69F00"   # matches new AD
viz.TRAJ_COLORS["MCI->AD"]   = "#E69F00"   # decline ending at AD


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

    # NL -> AD "direct" converters: patients whose dx history is exactly
    # {NL, AD}, never visiting MCI. The trajectory classifier folds these
    # into `other_unstable`, so count them on the fly from each patient's
    # observed dx values.
    dx_sets = df.groupby("RID")["dx"].apply(
        lambda s: set(s.dropna().tolist())
    )
    n_nl_ad = int((dx_sets == {"NL", "AD"}).sum())

    return {
        "n_participants": df["RID"].nunique(),
        "n_visits":       len(df),
        "n_mci_ad":       df[df["trajectory"] == "MCI->AD"]["RID"].nunique(),
        "n_nl_mci":       df[df["trajectory"] == "NL->MCI"]["RID"].nunique(),
        "n_mci_nl":       df[df["trajectory"] == "MCI->NL"]["RID"].nunique(),
        "n_nl_ad":        n_nl_ad,
    }


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
        ),
        html.Div(style={"display": "flex", "gap": "4px",
                        "marginTop": "4px", "marginBottom": "8px"},
                 children=[
            html.Button("Deselect all", id="traj-deselect-btn",
                        className="btn", n_clicks=0,
                        style={"fontSize": "11px", "padding": "3px 8px"}),
        ]),
        html.Label("Sex"),
        dcc.RadioItems(
            id="sex",
            options=[{"label": s, "value": s}
                     for s in ["All", "Male", "Female"]],
            value="All", inline=True,
            labelStyle={"marginRight": "16px"},   # space between All / Male / Female
            inputStyle={"marginRight": "4px"},
        ),
    ),

    section(
        "Trajectory plot",
        html.Label("Active metabolite"),
        dcc.Dropdown(
            id="metabolite",
            options=[{"label": m, "value": m}
                     for m in viz.ORDERED_METABOLITES],
            value="GLCA",
            clearable=False,
            searchable=True,                       # type to filter
            placeholder="Type to filter metabolites...",
            optionHeight=32,
            className="metabolite-dropdown",
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
        ),
        html.Label("Baseline (reference)"),
        dcc.Dropdown(
            id="baseline-group",
            options=[{"label": t, "value": t} for t in BASELINE_GROUPS],
            value="stable_NL", clearable=False,
        ),
        sec_id="sec-comparison",
    ),

    section(
        "Forest plot",
        html.Label("Visit slot"),
        dcc.RadioItems(
            id="forest-slot",
            options=[{"label": f"{s:+d}", "value": s} for s in viz.SLOTS],
            value=0, inline=True,
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
        ),
        dcc.Checklist(
            id="pca-arrows",
            options=[{"label": "Show patient first->last arrows",
                      "value": "yes"}],
            value=[], style={"marginTop": "8px"},
        ),
        sec_id="sec-pca",
    ),

    section(
        "Individual patient view",
        html.Label("RID"),
        dcc.Dropdown(id="rid", options=[], value=None, searchable=True,
                     placeholder="Type a RID"),
        sec_id="sec-patient",
    ),

    html.Div(id="meta-summary", className="note"),
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
    # Dash 3.x ships React 18 by default. This app works on React 18,
    # but if graph click events (PCA dot -> patient drill-down) ever
    # misbehave under React 18, uncomment the next two lines to pin the
    # Dash 2.x React (must run BEFORE Dash() is constructed):
    # import dash
    # dash._dash_renderer._set_react_version("16.14.0")
    app = Dash(__name__,
               title="Metabolite Trajectories - Visit-Ordinal",
               update_title=None,
               # REQUIRED: tab content (pca-fig, drilldown-fig, trajectory-fig,
               # forest-fig) is rendered lazily by render_tab(), so these IDs
               # are absent from the initial layout. Without this flag Dash
               # refuses to wire callbacks that reference them and the
               # click-to-drill (PCA dot -> patient view) silently never fires.
               suppress_callback_exceptions=True)

    app.layout = html.Div(
        className="app-shell",
        children=[
            SIDEBAR,
            html.Div(
                className="main",
                children=[
                    html.Div(
                        className="header",
                        children=[
                            html.H1("Gut-Microbiome Metabolite Trajectories"),
                            html.Div(
                                className="subtitle",
                                children=[
                                    "Visit-ordinal anchoring. ",
                                    html.B("Timepoint 0"),
                                    " represents the visit where a diagnosis change occurred, serving as the alignment anchor for ",
                                    "all patients' clinical histories. Prior to this point, patients held a different diagnosis than ",
                                    html.Br(),
                                    "they did afterward. The x-axis is visit count from diagnosis change, not calendar months.",
                                ],
                            ),
                        ],
                    ),
                    dcc.Tabs(
                        id="tabs",
                        value="info",
                        className="dash-tabs",
                        children=[
                            dcc.Tab(label="A - Cohort information", value="info"),
                            dcc.Tab(label="B - Trajectory", value="traj"),
                            dcc.Tab(label="C - Forest plot", value="forest"),
                            dcc.Tab(label="D - PCA state", value="pca"),
                            dcc.Tab(label="E - Individual patient view", value="patient"),
                        ],
                    ),
                    html.Div(id="tab-content", className="dash-tab-content"),
                ],
            ),
            dcc.Download(id="stats-download"),
        ],
    )
    

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
            s = cohort_summary()
            top_row = html.Div(className="kpi-row", children=[
                html.Div(className="kpi-card", children=[
                    html.Div("Participants", className="label"),
                    html.Div(f"{s['n_participants']:,}", className="value"),
                    html.Div(f"{s['n_visits']:,} longitudinal visits",
                             className="delta"),
                ]),
                html.Div(className="kpi-card", children=[
                    html.Div("Sex split", className="label"),
                    html.Div(f"{k['n_male']:,} M / {k['n_female']:,} F",
                             className="value"),
                    html.Div("unique participants", className="delta"),
                ]),
                html.Div(className="kpi-card", children=[
                    html.Div("Inter-visit gap", className="label"),
                    html.Div(f"{k['follow_up_gap_mean']:.1f} +/- "
                             f"{k['follow_up_gap_std']:.1f} months",
                             className="value"),
                    html.Div("yearly transitions only "
                             "(screening, baseline, month 06 excluded)",
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
            bottom_row = html.Div(className="kpi-row", children=[
                html.Div(className="kpi-card", children=[
                    html.Div("NL -> MCI", className="label"),
                    html.Div(f"{s['n_nl_mci']:,}", className="value"),
                    html.Div("early-progression cohort",
                             className="delta"),
                ]),
                html.Div(className="kpi-card", children=[
                    html.Div("MCI -> NL", className="label"),
                    html.Div(f"{s['n_mci_nl']:,}", className="value"),
                    html.Div("reverters (improvement)", className="delta"),
                ]),
                html.Div(className="kpi-card", children=[
                    html.Div("NL -> AD", className="label"),
                    html.Div(f"{s['n_nl_ad']:,}", className="value"),
                    html.Div("direct converters (never MCI)",
                             className="delta"),
                ]),
                html.Div(className="kpi-card", children=[
                    html.Div("MCI -> AD", className="label"),
                    html.Div(f"{s['n_mci_ad']:,}", className="value"),
                    html.Div("late-progression cohort",
                             className="delta"),
                ]),
            ])
            return [
                top_row,
                bottom_row,
                html.Div(className="card-row", children=[
                    graph_card("Sex composition over calendar years",
                               "info-sex-fig", height=420),
                    graph_card("Mean age per diagnosis over years",
                               "info-age-fig", height=420),
                ]),
                # Age-at-conversion boxplot to the LEFT of the
                # inter-visit-gap chart (per request).
                html.Div(className="card-row", children=[
                    graph_card("Age at first diagnosis transition",
                               "info-conv-age-fig", height=420),
                    graph_card("Inter-visit gap by transition",
                               "info-gap-fig", height=420),
                ]),
            ]
        return html.Div()

    # ----- Tab A: trajectory + stats -----
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

    # ----- Tab A: stats CSV download -----
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

    # ----- Tab B: forest -----
    @app.callback(
        Output("forest-fig", "figure"),
        Input("traj-focus", "value"),
        Input("baseline-group", "value"),
        Input("sex", "value"),
        Input("forest-slot", "value"),
    )
    def update_forest(traj_focus, baseline_group, sex, slot):
        return viz.forest_figure(traj_focus, baseline_group, sex, slot)

    # ----- Tab C: PCA scatter + loadings -----
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

    # ----- Tab D: drilldown -----
    @app.callback(Output("drilldown-fig", "figure"), Input("rid", "value"))
    def update_drilldown(rid):
        return viz.drilldown_figure(rid)

    # ----- Tab A: cohort overview figures -----
    @app.callback(
        Output("info-gap-fig", "figure"),
        Output("info-sex-fig", "figure"),
        Output("info-age-fig", "figure"),
        Output("info-conv-age-fig", "figure"),
        Input("tabs", "value"),
        Input("traj-groups", "value"),
        Input("sex", "value"),
    )
    def update_cohort_info(tab, groups, sex):
        if tab != "info":
            return no_update, no_update, no_update, no_update
        return (viz.visit_gap_figure(),
                viz.sex_over_years_figure(),
                viz.age_over_years_figure(),
                viz.age_at_conversion_figure(groups, sex))

    # ----- RID dropdown rebuild -----
    @app.callback(
        Output("rid", "options"),
        Output("rid", "value"),
        Input("traj-groups", "value"),
        Input("sex", "value"),
        State("rid", "value"),
    )
    def update_rid_options(groups, sex, current):
        # List ALL patients here, independent of the cohort checklist used by
        # the other tabs, so any RID can be typed into the box or arrive from a
        # click on the PCA / trajectory views. Keep the current selection.
        df = viz.DF
        traj_by_rid = df.drop_duplicates("RID").set_index("RID")["trajectory"]
        rids = sorted(int(r) for r in df["RID"].unique())
        options = [{"label": f"{r}  ({traj_by_rid[r]})", "value": r}
                   for r in rids]
        return options, current

    # ----- Click-to-drill: trajectory / PCA -> Tab E -----
    # Read ONLY the figure the user just clicked via ctx.triggered_id.
    # Dash keeps each graph's clickData populated permanently, so a naive
    # `for click in (traj_click, pca_click)` returns the FIRST non-empty
    # clickData — which means a stale trajectory click (from Tab B) keeps
    # winning and a later PCA click never selects its own point.
    @app.callback(
        Output("rid", "value", allow_duplicate=True),
        Output("tabs", "value"),
        Input("trajectory-fig", "clickData"),
        Input("pca-fig", "clickData"),
        prevent_initial_call=True,
    )
    def click_to_drill(traj_click, pca_click):
        trig = ctx.triggered_id
        if trig == "trajectory-fig":
            click = traj_click
        elif trig == "pca-fig":
            click = pca_click
        else:
            return no_update, no_update
        if not click or not click.get("points"):
            return no_update, no_update
        cd = click["points"][0].get("customdata")
        if not cd:
            return no_update, no_update
        try:
            rid = int(cd[0])
        except (ValueError, TypeError):
            return no_update, no_update
        return rid, "patient"

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

    # ----- Quick clear / fill for the trajectory-group checklist -----
    app.clientside_callback(
        "function(n){ return n ? [] "
        ": window.dash_clientside.no_update; }",
        Output("traj-groups", "value", allow_duplicate=True),
        Input("traj-deselect-btn", "n_clicks"),
        prevent_initial_call=True,
    )
    return app


app = _make_app()
server = app.server


if __name__ == "__main__":
    print(f"[app_clean] loaded {len(viz.DF):,} rows", flush=True)
    print("[app_clean] open  http://127.0.0.1:8050", flush=True)
    app.run(debug=False, host="127.0.0.1", port=8050)
