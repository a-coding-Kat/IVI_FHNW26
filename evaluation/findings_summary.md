# Usability evaluation — summary of findings for dashboard implementation

Formative usability evaluation of the Gut-Microbiome Metabolite Dashboard with
**three participants (P01-P03)**. Per-participant records are in `sessions/`.

---

## 1. Method and rationale

A **formative, moderated think-aloud** test was used: each participant worked
through the five tasks in `eyetracking_tasks.pdf` while verbalising their
reasoning and answering each task question **orally**; the facilitator recorded
the answer, task success, time, and observed difficulty. This was complemented by
two **self-report** instruments - the System Usability Scale and three open
debrief questions (`debrief_questions.md`). Sessions ran on a 1920x1080 laptop in
Brave on 2026-05-20 (P01) and 2026-06-03 (P02, P03).

Why this design, with sources:

- **Small-n formative testing.** Nielsen & Landauer (1993) and Virzi (1992) show
  that a handful of users surfaces the majority of usability problems; Nielsen's
  practitioner guidance ("Why You Only Need to Test with 5 Users", 2000) makes
  the case for iterative small rounds over one large study. With **n = 3** we
  expect to catch the most severe, high-frequency issues (the goal here), while
  accepting lower coverage of rarer problems.
- **Think-aloud / verbal protocol.** Concurrent verbalisation follows Ericsson &
  Simon's protocol-analysis method (*Protocol Analysis: Verbal Reports as Data*,
  1984/1993); Dumas & Redish (*A Practical Guide to Usability Testing*, 1999) and
  Tullis & Albert (*Measuring the User Experience*, 2013) for the observational
  measures (task success, time, errors).
- **Self-report metric.** The **SUS** (Brooke, 1996) is a validated 10-item
  global usability scale; the conventional pass mark is **68**, and Sauro & Lewis
  (*Quantifying the User Experience*, 2016) and Bangor, Kortum & Miller (2008)
  provide the benchmarking / adjective grading used below.
- **Heuristic lens.** Findings are triaged against Nielsen's (1994) ten usability
  heuristics (e.g. *visibility of system status*, *recognition over recall*,
  *consistency*).

### Is the debrief "enough"?

For a formative round with n = 3, **SUS + three open questions is an adequate
minimum**, but it is light on per-task diagnostics. Following Sauro & Lewis (2016)
and Tullis & Albert (2013), the next round should add:

1. a **Single Ease Question** (SEQ, 1-7; Sauro, 2009) immediately after each task,
   to localise difficulty quantitatively rather than only in the global SUS;
2. **task-level success and time** captured to a fixed protocol (gathered here,
   but informally);
3. one or two more open prompts (e.g. *"what did you expect to happen?"* to
   capture expectation mismatches).

SUS itself does **not** need more items - adding questions to a validated scale
breaks its norms (Brooke, 1996; Sauro & Lewis, 2016). The gap is per-task
granularity, not global-scale length.

### Limitations (important)

- **No physiological / attention channel.** Eye-tracking was planned but failed:
  WebGazer would not write the gaze CSV on the test device (the *Download CSV*
  action produced an empty file). The study is therefore limited to **self-report
  (SUS, debrief) and observation (think-aloud, facilitator notes)**.
  Attention-level hypotheses - e.g. whether users fixate the KPI cards before the
  charts on Tab A, or experience change-blindness on a tab switch - could **not**
  be measured objectively and rest only on think-aloud, which is subject to
  recall and verbalisation bias (Ericsson & Simon, 1984).
- **Small, single-session, convenience sample** (one clinician, one clinical
  researcher, one analyst); formative, not summative - results indicate
  direction, not generalisable rates.

---

## 2. Results

### Per participant

| ID | Background | Date | SUS | Tasks correct | Headline finding |
|----|------------|------|----:|---------------|------------------|
| P01 | Clinician (neurology) | 2026-05-20 | 82.5 | 5/5 (T4 with help) | CI whiskers vanish when cohorts are overlaid -> confusing |
| P02 | Clinical researcher | 2026-06-03 | 70.0 | 5/5 (T4 with help) | Clearing the cohort list one box at a time -> wants "Deselect all" |
| P03 | Data analyst (non-clinical) | 2026-06-03 | 70.0 | 5/5 (T4 via workaround) | PCA click does nothing -> wants the RID linked from PCA to Tab E |

**Mean SUS = 74.2** - above the 68 average and roughly *"Good"* on the Bangor et
al. (2008) adjective scale. (Each score is computed from the participant's own
10-item ratings: odd items score-1, even items 5-score, summed and x2.5.)

### Per task (all three participants)

| Task | Probe | Outcome | Notes |
|------|-------|---------|-------|
| T1 | Filter to female NL->MCI, read GLCA slope | 3/3 correct, unaided (~15 s) | Filters found and used easily |
| T2 | Forest: largest +Hedges' g (GHDCA) | 3/3 correct | P02 hovered for a value before reading the click tip; P01 briefly surprised by the colours; P03 noted the forest already feeds the metabolite to Tab B |
| T3 | Compare 3 cohorts, steepest rise | 3/3 correct | CI suppression confused P01; the manual deselection frustrated P02 and P03 |
| T4 | PCA outlier -> patient view | 3/3 only with help / workaround | **PCA-to-patient click was non-functional** - the clearest defect |
| T5 | Tab A cohort context (counts, ratio, gap, year) | 3/3 correct, unaided | KPI cards read first; inter-visit gap read as months |

All participants reached every expected answer, but **T4 required assistance or a
manual workaround for all three** because the PCA->patient click did not function.

---

## 3. Findings -> implementation (prioritised)

| # | Finding (source) | Heuristic | Recommended change | Status |
|---|------------------|-----------|--------------------|--------|
| F1 | **Critical:** clicking a PCA point did not open the patient view; all three needed help/workaround on T4 (P01, P02, P03). P03: *"clicking does nothing, I have to type the ID."* | H1 visibility / functionality | Link the RID from a PCA point click straight to **Tab E** and render that patient. | **Implemented** (a `dcc.Store(id="selected-rid")` source of truth + `suppress_callback_exceptions=True` for the lazy-tab callbacks + the `ctx.triggered_id` click handler). |
| F2 | **Major:** clearing the cohort list took seven one-by-one unticks; frustrating in T3 (P02 request, P03 echoed). P02: *"is there no clear-all?"* | Reduce memory load / efficiency | Add a **"Deselect all"** button to the cohort checklist. | **Implemented.** |
| F3 | **Major:** the **CI bands are confusing** - the trajectory shows mean +/- 95% CI with one cohort but means-only with several, and the change is unlabelled (P01: *"where did the error bars go?"*). | H1 visibility / consistency | Signpost it: a caption/legend note ("CI shown for a single cohort; see the stats table for multi-cohort intervals"), or always show CIs with an explanation. | **Open - recommended.** |
| F4 | **Minor:** typing a RID outside the selected cohort returned *"No options found"* in the patient box. | Flexibility / error prevention | Let the patient box list **all** patients, independent of the cohort checklist. | **Implemented.** |
| F5 | **Minor:** cohort controls were not found immediately (P02 scanned the header before noticing the left sidebar). | H6 recognition over recall | A clearer section label or a brief first-run hint. | Optional. |
| F6 | **Minor:** the diagnosis/cohort colours briefly surprised a participant (P01, T2). | Encode / aesthetic | Confirm the colour legend is visible and the palette is colourblind-safe. | Optional (Wong palette already applied). |

The three highest-impact items (F1-F3) map directly to the *Design improvements*
section of the project report.

---

## 4. Next steps

1. **Re-test T3 and T4** on the revised build to confirm F1 (PCA click-to-drill)
   and F2 (deselect-all) are resolved.
2. **Restore an attention channel** - fix the WebGazer CSV write, or fall back to
   screen + face recording or a hardware eye-tracker - to validate the
   attention-level hypotheses self-report could not.
