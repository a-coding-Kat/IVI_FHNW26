# Gut-Microbiome Metabolite Dashboard — Visit-Ordinal Edition

Interactive Plotly Dash dashboard for clinicians studying how gut-microbiome
metabolites change in participants who progress from **MCI → AD** and from
**NL → MCI**, with stable cohorts (NL, MCI, AD) as references.

## Why visit-ordinal anchoring

Earlier versions anchored on *calendar months before conversion*. ADNI's
metabolite cohort, however, has a roughly **yearly visit cadence** (median
inter-visit gap 12 months, IQR 11.5–12.7). Calendar windows like −6 mo /
−12 mo therefore mix "the visit before conversion" with "the visit two
visits before" depending on each patient's schedule. Coverage at calendar
−6 mo for NL→MCI was just 9 %.

This edition re-anchors on **visit ordinals**:

| Slot | Meaning |
|---:|---|
| `0`  | endpoint visit — conversion for converters, last observed visit for stable |
| `-1` | visit immediately before endpoint |
| `-2` | two visits before |
| `-3` | three visits before |
| `+1` | one visit after endpoint (converters only — stable have none) |

Coverage in the new framing (% of patients with a measurement at that slot):

| Cohort      | -3 | -2 | -1 | 0 | +1 |
|---|---:|---:|---:|---:|---:|
| MCI→AD      | 11 % | 72 % | 98 % | 100 % | 72 % |
| NL→MCI      | 15 % | 43 % | 59 % | 100 % | 79 % |
| stable_NL   | 17 % | 86 % | 98 % | 100 % | — |
| stable_MCI  | 7 %  | 75 % | 94 % | 100 % | — |

## Architecture

```
dashboard/
├── prep.py            # builds interim/mtb_sig_with_trajectory.pkl
├── viz.py             # figure builders (no Dash imports)
├── app.py             # Dash layout + callbacks (no plotly imports)
├── requirements.txt
└── README.md
```

Splitting `viz` from `app` means figure logic is import-time-fast to test
in a notebook or REPL, and the dashboard module stays small.

## Run

```bash
cd dashboard
python -m venv .venv
.\.venv\Scripts\Activate.ps1     # Windows PowerShell
# source .venv/bin/activate      # macOS / Linux
pip install -r requirements.txt
python prep.py                   # regenerates the pickle once
python app.py                    # opens on http://127.0.0.1:8050
```

## Four tabs

### A · Trajectory

A single metabolite across visit slots `{-3, -2, -1, 0, +1}`. Each chosen
trajectory class is drawn as a **stem-and-error** marker per slot
(mean ± 95 % CI), with the number of patients per slot in the hover.
Optional spaghetti per patient. Below the chart sits a per-slot stats
table (n visits, n patients, mean, median, Δ vs baseline, Mann-Whitney p).

**Stem-and-error replaces the smoothed CI band** that earlier versions
used. With at most one measurement per patient per year, a continuous
mean line implies a precision the data doesn't have; discrete markers
at each slot are honest about the sampling.

### B · Forest plot

For every significant metabolite (29 of them, plus 3 ratios), the
**effect size (Hedges' g)** of `converter − baseline` at the selected
visit slot, with 95 % CIs. Grouped by metabolite family (primary bile
acids, secondary bile acids, ratios, amino acids, fatty acids, organic
acids). The instant answer to *"which metabolites differ at slot −1?"*
— and which families those differences cluster in.

Click a dot → that metabolite becomes the active one in Tab A and the
patient drill-down.

### C · PCA biological state space

Each visit is a 29-dimensional metabolite profile. PCA collapses that
into 2-D so all visits can be plotted on one map. Points coloured by
trajectory class, diagnosis, visit slot, or sex. Optional patient
first → last arrows reveal whether converters move in a different
direction in metabolite space than stable patients. The PC-loading bars
below tell you which metabolites drive each component, so the geometry
is interpretable rather than abstract.

### D · Patient drill-down

3 × 3 small-multiples for one selected patient (top 9 metabolites by
family ordering), markers coloured by diagnosis at each visit, vertical
dashed line at slot 0 (the endpoint). Auto-fills when you click any
data point in Tabs A or C.

## Filters (sidebar)

* **Trajectory groups** — any subset of `MCI->AD`, `NL->MCI`, `NL->MCI->AD`,
  `stable_NL`, `stable_MCI`, `stable_AD`. Affects every view.
* **Sex** — All / Male / Female. Affects every view.
* **Metabolite** — drives Tab A and the patient drill-down.
* **Forest plot converter / baseline / slot** — drives Tab B and the
  stats table beneath Tab A.
* **PCA color-by** and **arrows** — drives Tab C.
* **Drill-down patient (RID)** — populates from the trajectory-group
  selection; auto-fills on click.

## Design rationale (short version)

| Decision | Why |
|---|---|
| Visit-ordinal anchor instead of calendar months | Yearly cadence means calendar windows are mostly empty; ordinals are 100 % populated at slot 0 |
| Stable patients anchored at *last visit* | Gives them a slot-0 to compare against converters' slot-0 (conversion visit) |
| Stem-and-error instead of smoothed CI bands | One measurement per patient per year; smoothing implies false precision |
| Hedges' g (small-sample bias-corrected) over Cohen's d | Some slots have n < 50; Hedges' g is the standard correction |
| PCA on z-scored 29-metabolite vectors | One projection serves all cohorts; loadings tell the clinician which metabolites drive each axis |
| Click-to-link across views | Tab A trajectory click, Tab B forest dot click, Tab C PCA point click → drill-down to that patient or metabolite |

## Known data limitations to disclose with any clinical write-up

* "Stable" means *did not convert during follow-up*; median follow-up is
  ~24 months, so some "stable" patients may later convert.
* 37 patients have a single visit (no trajectory possible).
* The 29 "significant" metabolites came from an earlier filtering step
  (`interim/mtb_significant.pkl`); changing that filter changes Tab B's
  set of rows.
* Most metabolite values in the pickle are Box-Cox transformed
  (parameters in `interim/boxcox_transformation_params.pkl`). The
  trajectory plot's y-axis is *transformed-units*, not μM. The PCA and
  forest plot use z-scores, which are unit-free.
