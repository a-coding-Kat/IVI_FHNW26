# Gut-Microbiome Metabolite Dashboard — Visit-Ordinal Edition

Interactive Plotly Dash dashboard for clinicians studying how gut-microbiome metabolites change in participants who progress from **NL → MCI** and from **MCI → AD**, with stable cohorts (NL, MCI, AD) as references.

## Visit-ordinal anchoring

Earlier versions anchored on *calendar months before conversion* were very difficult to overlap, as each patient progresses indicvitually. ADNI's metabolite cohort has a roughly **yearly visit cadence** (median inter-visit gap 12 months, IQR 11.5–12.7). So it is more practical to align all visits per sequence rather than date.

Re-anchoring on **visit ordinals**:

| Slot | Meaning |
|---:|---|
| `0`  | endpoint visit: conversion for converters, last observed visit for stable |
| `-1` | visit immediately before endpoint |
| `-2` | 2 visits before |
| `-3` | 3 visits before |
| `+1` | 1 visit after endpoint (converters only, stable have none) |

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
├── viz.py             # figure builders
├── app.py             # Dash layout + callbacks (no plotly imports)
├── test_dashboard.py
└── README.md
```

Splitting `viz` from `app` means figure logic is import-time-fast to test in a notebook and the dashboard module stays small.

## Run

```bash
# create + activate the conda environment (from the repo root)
conda env create -f ../environment.yml
conda activate ivi

cd dashboard
python prep.py    # regenerates interim/mtb_sig_with_trajectory.pkl (skip if it exists)
python app.py     # opens on http://127.0.0.1:8050
```

## Four tabs

### A · Trajectory

A single metabolite across visit slots `{-3, -2, -1, 0, +1}`. Each chosen trajectory class is drawn as a **stem-and-error** marker per slot
(mean ± 95 % CI), with the number of patients per slot in the hover. Below the chart sits a per-slot stats table (n visits, n patients, mean,
median, Δ vs baseline).

**Stem-and-error replaces the smoothed CI band** that earlier versions used, as per usability test feedback. However, presentation of the dashboard
at FHNW provided feedback, that the whiskers confuse the viewer, so a different solution altogether should be considered.

### B · Forest plot

For every significant metabolite (29 of them, plus 3 ratios), the **effect size (Hedges' g)** of `converter − baseline` at the selected visit slot, 
with 95 % CIs. Grouped by metabolite family (primary bile acids, secondary bile acids, ratios, amino acids, fatty acids, organic acids). 
The instant answer to *"which metabolites differ at slot −1?"*, and which families those differences cluster in.

### C · PCA biological state space

Each visit is a 29-dimensional metabolite profile. PCA collapses that into 2-D so all visits can be plotted on one map. Points coloured by
trajectory class, diagnosis, visit slot, or sex. Optional patient first → last arrows reveal whether converters move in a direction in metabolite 
space than stable patients. The PC-loading bars below tell you which metabolites drive each component, so the geometry is interpretable rather 
than abstract.

### D · Patient drill-down

3 × 3 small-multiples for one selected patient (top 9 metabolites by family ordering), markers coloured by diagnosis at each visit, vertical
dashed line at slot 0 (the endpoint). Auto-fills when you click any data point in Tabs A or C.

## Filters (sidebar)

* **Trajectory groups** — any subset of `MCI->AD`, `NL->MCI`, `NL->MCI->AD`,
  `stable_NL`, `stable_MCI`, `stable_AD`. Affects every view.
* **Sex** — All / Male / Female. Affects every view.
* **Metabolite** — drives Tab B - Trajectory and the patient drill-down.
* **Forest plot converter / baseline / slot** — drives Tab C
* **PCA color-by** and **arrows** — drives Tab D.
* **Drill-down patient (RID)** — auto-fills on selection or typing in, Tab E.

## Design rationale (short version)

| Decision | Why |
|---|---|
| Visit-ordinal anchor instead of calendar months | Not many participants share visit dates, but ordinals are 100 % populated at slot 0 |
| Stable patients anchored at *last visit* | Gives them a slot-0 to compare against converters' slot-0 (conversion visit) |
| Stem-and-error instead of smoothed CI bands | One measurement per patient per year; smoothing implies false precision |
| Hedges' g (small-sample bias-corrected) over Cohen's d | Some slots have n < 50; Hedges' g is the standard correction |
| PCA on z-scored 29-metabolite vectors | One projection serves all cohorts; loadings tell the clinician which metabolites drive each axis |
| Click-to-link across views | Tab A trajectory click, Tab B forest dot click, Tab C PCA point click → drill-down to that patient or metabolite |

## Known data limitations to disclose with any clinical write-up

* 37 patients have a single visit (no trajectory possible).

* Most metabolite values in the pickle are Box-Cox transformed (parameters in `interim/boxcox_transformation_params.pkl`). The
  trajectory plot's y-axis is *transformed-units*, not μM. The PCA and forest plot use z-scores, which are unit-free.
