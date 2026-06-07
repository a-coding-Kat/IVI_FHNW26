"""Basic smoke / sanity tests for the Gut-Microbiome Metabolite Dashboard.

These are fast, import-and-call tests (no browser, no running server). `viz.py`
has no Dash dependency, so tests 1-9 run with just plotly/pandas/scikit-learn
and the data pickle present; test 10 needs Dash installed (otherwise skipped).

Run from the dashboard/ folder:

    pip install pytest          # (or: conda install pytest)
    pytest -q
"""
import os
import sys

import pytest

# Make `import viz` / `import app` work no matter where pytest is launched from.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import dashboard.viz_v1 as viz_v1


# 1. The data pickle loads into a non-empty dataframe.
def test_data_loads():
    assert viz_v1.DF is not None
    assert len(viz_v1.DF) > 0


# 2. Every column the views rely on is present (incl. all 29 metabolites).
def test_required_columns():
    needed = {"RID", "dx", "trajectory", "visit_rel", "sex"}
    assert needed.issubset(set(viz_v1.DF.columns))
    assert len(viz_v1.ORDERED_METABOLITES) > 0
    assert all(m in viz_v1.DF.columns for m in viz_v1.METABOLITES)


# 3. The cohort filter actually filters by trajectory AND sex.
def test_filter_df():
    f = viz_v1.filter_df(["MCI->AD"], "Female")
    assert len(f) > 0
    assert set(f["trajectory"].unique()) == {"MCI->AD"}
    assert set(f["sex"].unique()) == {"Female"}


# 4. all_rids() returns only RIDs that belong to the requested cohort.
def test_all_rids_consistent():
    rids = viz_v1.all_rids(["MCI->AD"], "All")
    assert len(rids) > 0
    sub = viz_v1.DF[viz_v1.DF["RID"].isin(rids)]
    assert set(sub["trajectory"].unique()) == {"MCI->AD"}


# 5. Tab B: the trajectory figure builds and has at least one trace.
def test_trajectory_figure():
    fig = viz_v1.trajectory_figure("GLCA", ["MCI->AD"], "All", False)
    assert fig is not None and len(fig.data) >= 1


# 6. Tab C: the forest figure builds and lists metabolite names on its y-axis.
def test_forest_figure():
    fig = viz_v1.forest_figure("MCI->AD", "stable_NL", "All", 0)
    assert len(fig.data) >= 1
    ynames = [y for tr in fig.data for y in (tr.y if tr.y is not None else [])]
    assert "GHDCA" in ynames


# 7. CONNECTED VIEWS: every PCA point carries its RID in customdata[0],
#    which is what the click-to-drill callback reads. If this breaks,
#    clicking a PCA dot can't select a patient.
def test_pca_points_carry_rid():
    fig = viz_v1.pca_figure(["MCI->AD", "stable_NL"], "All", "trajectory", False)
    assert len(fig.data) >= 1
    cd = fig.data[0].customdata
    assert cd is not None and len(cd) > 0
    rid = int(cd[0][0])                       # must parse to an int RID
    assert rid in set(viz_v1.DF["RID"].tolist())


# 8. Tab E: the patient drill-down builds for a real RID, and returns a
#    placeholder figure (not a crash) when no patient is selected.
def test_drilldown_figure():
    rid = int(viz_v1.DF["RID"].iloc[0])
    fig = viz_v1.drilldown_figure(rid)
    assert len(fig.data) >= 1
    assert viz_v1.drilldown_figure(None) is not None


# 9. Tab A: the age-at-transition chart respects the cohort + sex filter
#    (it should never report more observations than the unfiltered cohort).
def test_age_at_conversion_respects_filter():
    full = viz_v1.age_at_conversion_figure(None, "All")
    one = viz_v1.age_at_conversion_figure(["MCI->AD"], "All")
    n_full = sum(len(tr.y if tr.y is not None else []) for tr in full.data)
    n_one = sum(len(tr.y if tr.y is not None else []) for tr in one.data)
    assert 0 < n_one <= n_full


# 10. The Dash app constructs, and has the flag that lazy-tab callbacks
#     (PCA click-to-drill) depend on. Skipped if Dash isn't installed.
def test_app_builds_with_suppress():
    pytest.importorskip("dash")
    import app as appmod
    assert appmod.app.layout is not None
    assert appmod.app.config.suppress_callback_exceptions is True


# 11. Deselect-all (traj_groups == []) is intentional and VIEW-SPECIFIC:
#       Tab B trajectory -> empty ("No data")
#       Tab D PCA        -> shows all points
#       Tab A age chart  -> shows all observations (same as unfiltered)
#     This locks that behaviour in so it can't change silently.
def test_empty_selection_semantics():
    # Tab B: empty on []
    traj = viz_v1.trajectory_figure("GLCA", [], "All", False)
    assert len(traj.data) == 0

    # Tab D: [] shows the same number of points as selecting every class
    all_groups = list(viz_v1.DF["trajectory"].dropna().unique())
    pts = lambda f: sum(len(t.x) for t in f.data if t.x is not None)
    assert pts(viz_v1.pca_figure([], "All", "trajectory", False)) > 0
    assert pts(viz_v1.pca_figure([], "All", "trajectory", False)) == \
        pts(viz_v1.pca_figure(all_groups, "All", "trajectory", False))

    # Tab A: [] matches the unfiltered observation count
    obs = lambda f: sum(len(t.y) for t in f.data if t.y is not None)
    assert obs(viz_v1.age_at_conversion_figure([], "All")) == \
        obs(viz_v1.age_at_conversion_figure(None, "All"))
