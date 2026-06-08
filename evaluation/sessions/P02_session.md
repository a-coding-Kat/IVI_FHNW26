# Usability session — Participant P02

> **Anonymised record** (participant **P02**). Verbal consent obtained per
> `../consent_template.pdf`.
>
> **Eye-tracking was not available** — WebGazer would not write the gaze CSV on
> the device (empty file on *Download CSV*), so no gaze/AOI/heat-map data were
> collected. The session ran as a **moderated think-aloud** with **oral
> answers** to the five tasks in `../eyetracking_tasks.pdf`; evidence is
> **self-report (SUS + debrief) and observational only**.

| Field | Value |
|---|---|
| Participant ID | P02 |
| Background | Clinical researcher (biomarker studies), light dashboard use |
| Date | 2026-05-20 |
| Device | Laptop, 1920 × 1080, Brave |
| Method | Moderated think-aloud; oral answers; SUS; 3 open debrief questions |
| Not collected | Eye-tracking / gaze CSV (WebGazer device failure) |

---

## Task results (oral answers, moderated think-aloud)

### T1 — Filter the cohort and read a trajectory
**Oral answer:** "Down." **Expected:** down. **Outcome:** correct. **Time:** ~15 s.
**Observed:** took a few seconds scanning the header before noticing the cohort controls are in the left sidebar; once found, filtered correctly.

### T2 — Discover a high-effect metabolite
**Oral answer:** "GHDCA." **Expected:** GHDCA. **Outcome:** correct. **Time:** ~40 s.
**Observed:** initially tried to *hover* the dots for a value before reading the "click a dot" tip; then briefly unsure which tab to return to.

### T3 — Compare cohorts on one metabolite  ⚠ key finding
**Asked:** Untick all, tick MCI→AD + stable_NL + stable_MCI, between which two slots does MCI→AD rise most steeply?
**Oral answer:** "Between −2 and −1." **Expected:** −2→−1 (or −1→0). **Outcome:** correct, but frustrated with the unticking. **Time:** ~45 s.
**Observed / difficulty:** the task needs the checklist emptied first, and P02 had to **untick seven boxes one at a time**, then tick three. Audible: *"do I really have to uncheck all of these one by one — is there no clear-all?"* 
**Suggestion (verbatim):** *"Put a 'deselect all' button on the cohort list so I can clear it in one click."*

### T4 — Drill into an individual patient
**Oral answer:** gave an RID + "GDCA is rising," after switching to the RID box. 
**Outcome:** completed with assistance. Time: ~35 s.
**Observed:** clicking the PCA point did not open the patient view; P02 fell back to the RID dropdown after the facilitator hinted. (Matches the click-to-drill defect later fixed.)

### T5 — Inspect cohort-level context
**Oral answer:** "1,274; 719 / 555; ~12 months; around 2010." **Expected:** matches. **Outcome:** correct. **Time:** ~15 s.
**Observed:** KPI cards read quickly; interpreted the gap as months.

---

## System Usability Scale (self-report; Brooke, 1996)

| # | Statement | Rating (1–5) |
|---|---|---|
| 1 | Would like to use frequently | 4 |
| 2 | Unnecessarily complex | 3 |
| 3 | Easy to use | 4 |
| 4 | Would need technical support | 2 |
| 5 | Functions well integrated | 4 |
| 6 | Too much inconsistency | 2 |
| 7 | Most people would learn quickly | 4 |
| 8 | Very cumbersome | 3 |
| 9 | Felt very confident | 4 |
| 10 | Needed to learn a lot first | 2 |

**SUS score = 70.0** (above the 68 benchmark; pulled down by the T3 friction).

---

## Debrief (verbatim)

**Q1 — Most confusing moment?**
> "Clearing the cohort list. Unchecking each box one by one felt tedious."

**Q2 — Most useful feature to keep?**
> "The forest plot. Individual drill."

**Q3 — One change for weekly routine use?**
> "A 'deselect all' button on the cohort list. That one thing fixes most of my
> frustration."

## Facilitator summary
All five tasks correct; T4 needed help (PCA click didn't open the patient).
**Headline finding / direct request: add a 'deselect all' control to the cohort
checklist.** SUS 70.0.
