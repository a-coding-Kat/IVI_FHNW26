"""Build interim/mtb_sig_with_trajectory.pkl.

Adds to the significant-metabolites table:

Per-row clinical labels
    dx            'NL' / 'MCI' / 'AD'
    sex           'Male' / 'Female' (source pickle stores it as
                  Categorical[int]; 0=Male, 1=Female)

Per-patient trajectory class (order-aware)
    trajectory   compressed dx-sequence, e.g. 'NL->MCI', 'MCI->NL',
                 'MCI->AD', 'NL->MCI->AD'; 'stable_NL/MCI/AD' for
                 patients with a single dx; 'other_unstable' for rare
                 oscillating sequences (≤10 patients each in this cohort).

Calendar conversion months (legacy support)
    months_at_mci_conv, months_at_ad_conv, t_event

Visit-ordinal anchoring (THE PRIMARY anchor)
    visit_idx                     1-based per-RID visit index
    n_visits                      total visits per RID
    first_dx_change_visit_idx     first visit where dx differs from baseline
    conv_ad_visit_idx             first AD visit (NaN if never AD)
    conv_mci_visit_idx            first MCI visit (NaN if never MCI)
    end_visit_idx                 the "diagnosis-change" anchor:
                                    - AD-containing trajectory -> first AD
                                    - any other progression    -> first dx
                                                                   change
                                    - stable                   -> last visit
    visit_rel                     visit_idx - end_visit_idx
                                  (0 = diagnosis-change visit / last visit)
"""
from __future__ import annotations

from pathlib import Path
import pickle

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "interim" / "mtb_significant.pkl"
DST = ROOT / "interim" / "mtb_sig_with_trajectory.pkl"

SEX_MAP = {0: "Male", 1: "Female"}

# Trajectory classes we keep as first-class options in the dashboard.
# Anything else collapses into "other_unstable".
CANONICAL_CLASSES = {
    "stable_NL", "stable_MCI", "stable_AD",
    "NL->MCI", "MCI->AD", "NL->MCI->AD",
    "MCI->NL",
}


def decode_sex(s: pd.Series) -> pd.Series:
    if str(s.dtype) == "category":
        cats = set(s.cat.categories)
        if cats <= {0, 1}:
            return s.astype(int).map(SEX_MAP)
        return s.astype(str)
    if s.dtype.kind in "iu":
        return s.astype(int).map(SEX_MAP)
    return s.astype(str)


def classify(traj):
    """Order-aware. Compresses consecutive duplicates."""
    seq = []
    for d in traj:
        if not seq or seq[-1] != d:
            seq.append(d)
    if len(seq) == 1:
        return "stable_" + seq[0]
    cls = "->".join(seq)
    return cls if cls in CANONICAL_CLASSES else "other_unstable"


def find_conv_months(g):
    g = g.sort_values("months_from_baseline")
    out = {"months_at_mci_conv": np.nan, "months_at_ad_conv": np.nan}
    m_mci = g[g["dx"] == "MCI"]
    m_ad = g[g["dx"] == "AD"]
    if len(m_mci):
        out["months_at_mci_conv"] = m_mci["months_from_baseline"].iloc[0]
    if len(m_ad):
        out["months_at_ad_conv"] = m_ad["months_from_baseline"].iloc[0]
    return pd.Series(out)


def t_event_row(row):
    if row["trajectory"] in ("MCI->AD", "NL->MCI->AD"):
        return row["months_from_baseline"] - row["months_at_ad_conv"]
    if row["trajectory"] == "NL->MCI":
        return row["months_from_baseline"] - row["months_at_mci_conv"]
    return np.nan


def end_visit_idx_row(row):
    """Slot-0 anchor.

    AD-containing trajectories     -> first AD visit
    other progressions / reversion -> first visit where dx differs from
                                      patient's initial dx (the diagnosis-
                                      change event, even if it's a reversion
                                      such as MCI->NL)
    stable                         -> last observed visit
    """
    cls = row["trajectory"]
    if cls.startswith("stable_"):
        return row["n_visits"]
    if cls in ("MCI->AD", "NL->MCI->AD"):
        return row["conv_ad_visit_idx"]
    if pd.notna(row["first_dx_change_visit_idx"]):
        return row["first_dx_change_visit_idx"]
    return np.nan


def main():
    sig = pickle.load(open(SRC, "rb")).copy()
    diag_map = {1: "NL", 2: "MCI", 3: "AD"}
    sig["dx"] = sig["diagnosis"].astype(int).map(diag_map)
    sig["sex"] = decode_sex(sig["sex"])
    sig = sig.sort_values(["RID", "months_from_baseline"]).reset_index(drop=True)
    sig["trajectory"] = sig["RID"].map(
        sig.groupby("RID")["dx"].apply(classify)
    )

    # Visit ordinals
    sig["visit_idx"] = sig.groupby("RID").cumcount() + 1
    sig["n_visits"] = sig.groupby("RID")["visit_idx"].transform("max")

    # Legacy calendar conversion
    conv = (sig.groupby("RID", group_keys=False)
              .apply(find_conv_months).reset_index())
    sig = sig.merge(conv, on="RID", how="left")
    sig["t_event"] = sig.apply(t_event_row, axis=1)

    # Visit indices of first MCI / first AD per patient
    def _conv_visit(g, dx_label):
        gg = g[g["dx"] == dx_label]
        return gg["visit_idx"].iloc[0] if len(gg) else np.nan
    sig["conv_ad_visit_idx"] = sig["RID"].map(
        sig.groupby("RID").apply(lambda g: _conv_visit(g, "AD"))
    )
    sig["conv_mci_visit_idx"] = sig["RID"].map(
        sig.groupby("RID").apply(lambda g: _conv_visit(g, "MCI"))
    )

    # First visit where dx differs from the patient's baseline dx
    def _first_dx_change(g):
        g = g.sort_values("visit_idx")
        first = g["dx"].iloc[0]
        diff = g[g["dx"] != first]
        return diff["visit_idx"].iloc[0] if len(diff) else np.nan
    sig["first_dx_change_visit_idx"] = sig["RID"].map(
        sig.groupby("RID").apply(_first_dx_change)
    )

    sig["end_visit_idx"] = sig.apply(end_visit_idx_row, axis=1)
    sig["visit_rel"] = sig["visit_idx"] - sig["end_visit_idx"]

    sig["sex"] = pd.Series(
        [str(x).strip() if pd.notna(x) else "Unknown" for x in sig["sex"]],
        index=sig.index, dtype=object,
    )

    sig.to_pickle(DST)
    print(f"Wrote {DST}  shape={sig.shape}")
    print("\ntrajectory (unique patients):")
    print(sig.groupby("trajectory")["RID"].nunique().sort_values(ascending=False).to_string())
    print("\nvisit_rel coverage (n patients with a visit at this slot):")
    for traj in ["MCI->AD", "NL->MCI", "MCI->NL", "NL->MCI->AD",
                 "stable_NL", "stable_MCI", "stable_AD"]:
        s = sig[sig["trajectory"] == traj]
        if len(s) == 0:
            continue
        line = [traj.ljust(14)]
        for r in [-3, -2, -1, 0, 1]:
            n = s[s["visit_rel"] == r]["RID"].nunique()
            line.append(f"r={r:+d}: {n:3d}")
        print("  " + "  ".join(line))


if __name__ == "__main__":
    main()
