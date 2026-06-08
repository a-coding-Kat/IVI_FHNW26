# Gut-Microbiome Metabolite Dashboard

An interactive multi-view dashboard built for the IVI (Interactive Visualization)
module. It lets clinicians explore how 29 bile-acid and related serum metabolites
change in the visits leading up to a diagnostic transition (NL → MCI, MCI → AD,
or MCI → NL reversion) in the ADNI cohort.

The project follows the full visualization pipeline: dataset exploration,
interactive prototype, usability evaluation, design revision, and reporting.

---

## Repository structure

```
IVI/
├── environment.yml                   conda environment (project setup)
├── README.md
│
├── dashboard/                        the Plotly Dash application
│   ├── app.py                        Dash app: layout + callbacks (run this)
│   ├── viz.py                        figure builders + data load
│   ├── prep.py                       builds data/mtb_sig_with_trajectory.pkl
│   ├── test_dashboard.py             pytest smoke / sanity tests
│   ├── assets/                       styles.css (auto-served by Dash)
│   ├── images/                       static images
│   └── README.md                     dashboard-specific notes
│
├── evaluation/                       usability-study materials
│   ├── tasks.md                      the five participant tasks
│   ├── eyetracking_tasks.pdf         task script (research questions)
│   ├── debrief_questions.md          SUS + open debrief questions
│   ├── consent_template.pdf
│   ├── findings_summary.md           consolidated findings for implementation
│   └── sessions/                     anonymised participant records
│       ├── P01_session.md
│       ├── P02_session.md
│       ├── P03_session.md
│       └── README.md
│
├── data/                             cleaned pickles for the dashboard (tracked)
│   ├── mtb_sig_with_trajectory.pkl       the only file the dashboard loads
│   ├── mtb_significant.pkl               input to prep.py
│   └── *.png                             EDA figures
│
├── raw/                              ADNI-derived source pickles (git-ignored, DUA-governed)
└── documents/                        supplementary material (presentation, etc.)
```

## Environment

The project uses a **conda** environment defined in `environment.yml`

## Data

The raw ADNI data is governed by the ADNI Data Use Agreement and is not
redistributed here, but is available from the repository owner. The dashboard
only needs `data/mtb_sig_with_trajectory.pkl` at runtime.

---

## How to run

```bash
# 1.  Create and activate the conda environment (run from the repo root)
conda env create -f environment.yml
conda activate ivi

# 2.  Launch the dashboard
cd dashboard
python app.py            # opens on http://127.0.0.1:8050
```

## Citation / acknowledgements

Data are derived from the Alzheimer's Disease Neuroimaging Initiative
(ADNI; Mueller et al., 2005)
