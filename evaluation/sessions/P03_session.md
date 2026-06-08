# Usability session — Participant P03

> **Anonymised record** (participant **P03**). Verbal consent obtained per
> `../consent_template.pdf`.
>
> **Eye-tracking was not available** — WebGazer would not write the gaze CSV on
> the device (empty file on *Download CSV*), so no gaze/AOI/heat-map data were
> collected. The session ran as a **moderated think-aloud** with **oral
> answers** to the five tasks in `../eyetracking_tasks.pdf`; evidence is
> **self-report (SUS + debrief) and observational only**.

| Field | Value |
|---|---|
| Participant ID | P03 |
| Background | Data analyst (non-clinical), frequent dashboard user |
| Date | 2026-05-20 |
| Device | Laptop, 1920 × 1080, Brave |
| Method | Moderated think-aloud; oral answers; SUS; 3 open debrief questions |
| Not collected | Eye-tracking / gaze CSV (WebGazer device failure) |

---

## Task results (oral answers, moderated think-aloud)

### T1 — Filter the cohort and read a trajectory
**Oral answer:** "Down." **Expected:** down. **Outcome:** correct. **Time:** ~15 s.
**Observed:** comfortable with the sidebar; read the slope quickly.

### T2 — Discover a high-effect metabolite
**Oral answer:** "GHDCA." **Expected:** GHDCA. **Outcome:** correct. **Time:** ~30 s.
**Observed:** Clicked the top dot fluently and verified the name on Tab B. Noted the forest plot could feed the metabolite to Tab B - Trajectory.

### T3 — Compare cohorts on one metabolite
**Oral answer:** "Between −2 and −1." **Expected:** −2→−1 (or −1→0). **Outcome:** correct. **Time:** ~15 s.
**Observed:** same one-by-one unticking friction as others ("a clear-all would help").

### T4 — Drill into an individual patient, key finding
**Asked:** on Tab D click the point farthest from the cluster; it should jump to Tab E — read the RID and describe a rising metabolite.
**Oral answer:** eventually gave an RID + a rising metabolite, after manually using the RID box. **Outcome:** completed with workaround. **Time:** ~40 s.
**Observed / difficulty:** Clicking the PCA outlier did nothing, the view stayed on Tab D and no patient loaded. P03 clicked several points, confirmed it was unresponsive, and said the link was simply missing/broken.
**Suggestion (verbatim):** *"When I click a point in the PCA, it should send that patient's RID straight to the individual-patient tab and show their metabolites. Right now clicking does nothing, I have to type the ID."*

### T5 — Inspect cohort-level context
**Oral answer:** "1,274; 719 / 555; ~a year; the female share rises around 2010–2011." **Expected:** matches. **Outcome:** correct. **Time:** ~25 s.
**Observed:** KPI cards first, charts second; gap read as months.

---

## System Usability Scale (self-report; Brooke, 1996)

| # | Statement | Rating (1–5) |
|---|---|---|
| 1 | Would like to use frequently | 3 |
| 2 | Unnecessarily complex | 2 |
| 3 | Easy to use | 4 |
| 4 | Would need technical support | 1 |
| 5 | Functions well integrated | 2 |
| 6 | Too much inconsistency | 3 |
| 7 | Most people would learn quickly | 4 |
| 8 | Very cumbersome | 2 |
| 9 | Felt very confident | 4 |
| 10 | Needed to learn a lot first | 1 |

**SUS score = 70.0** (above the 68 benchmark; the broken PCA click dented confidence).

---

## Debrief (verbatim)

**Q1 — Most confusing moment?**
> "Clicking a point in the scatter and nothing happening. I expected it to open
> that patient."

**Q2 — Most useful feature to keep?**
> "The cohort summary cards — I can sanity-check the sample before trusting the
> effect sizes."

**Q3 — One change for weekly routine use?**
> "Wire the PCA click to the patient tab: click a dot, see that RID's metabolites."

## Facilitator summary
All five tasks reached the right answer; T4 only via a manual workaround because
the PCA-to-patient link was non-functional. **Headline finding / request: link
the RID from a PCA point click to Tab E (Individual patient view).** SUS 70.0.
