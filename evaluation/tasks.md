# Usability evaluation — participant task script

Read the **Scenario** out loud, then the **Instruction** verbatim. Start
a stopwatch when the participant begins. Stop the stopwatch when they
deliver the answer in the **Answer expected** box. Do not coach unless
they spend more than two minutes stuck on the same step. Encourage
think-aloud throughout ("What are you looking at? What are you trying
to do?").

There are 5 tasks. Each probes a different interaction vector and a dashboard
tab. The order is fixed because earlier tasks introduce concepts later 
tasks rely on.

---

## T1 — Filter the cohort and read a trajectory 
*(probes: sidebar filtering; Tab B trajectory plot)*

**Scenario.** We want to know whether a particular gut-microbiome
metabolite trends downward in female patients who later develop mild
cognitive impairment, ignoring the male participants who introduce a
sex confound.

**Instruction.** "Using only the sidebar, filter the cohort so it
shows female participants who progress from NL to MCI. Switch to
*Tab B — Trajectory*. The active metabolite at the top of the
dropdown is GLCA. Tell me whether GLCA's mean concentration goes up
or down from Timepoint –3 to Timepoint 0."

**Answer expected.** "Down" (the slope is negative across –3 → 0).

**What we measure.**

* Time-to-first-fixation on the sidebar Cohort section.
* Whether the participant locates the trajectory-groups checklist
  without prompting.
* Whether the participant correctly reads the slope direction
  (validates the chart's clarity at one active cohort, full CI
  whiskers visible).

---

## T2 — Discover a high-effect metabolite  
*(probes: cross-view linking; Tab C forest plot → Tab B trajectory plot)*

**Scenario.** Before forming a hypothesis we want to know which of
the 29 metabolites carries the strongest signal at the conversion
visit (slot 0) when comparing MCI → AD converters against stable
cognitively normal controls.

**Instruction.** "Move to *Tab C — Forest plot*. Make sure the
Converter group is set to MCI→AD and the Baseline is stable_NL. Find
the metabolite with the largest *positive* effect size (Hedges' g),
click directly on its dot, switch back to *Tab B — Trajectory*, and
tell me which metabolite the chart is now showing."

**Answer expected.** Whichever metabolite tops the forest plot at
slot 0 — typically GHDCA or one of the secondary-bile-acid
conjugates.

**What we measure.**

* Whether the click-to-drill affordance is discovered without
  prompting (the "Tip: click a metabolite dot…" caption).
* Time spent on Tab C before the click is made.
* Whether the participant verifies the metabolite name on Tab B
  rather than recalling it from memory.

---

## T3 — Compare two cohorts on the same metabolite 
*(probes: multi-group overlay; dodging + CI suppression)*

**Scenario.** You want to compare the GLCA trajectories of
MCI → AD progressors, stable_NL controls, and stable_MCI controls
side by side to see whether the progressors' rise begins before the
diagnosis-change visit.

**Instruction.** "Back on *Tab B*, untick everything in the
Trajectory groups checklist, then tick MCI→AD, stable_NL, and
stable_MCI. Tell me, looking only at the chart, between which two
slots does the orange MCI→AD line rise most steeply?"

**Answer expected.** Between slot –2 and slot –1 (or slot –1 and
slot 0, depending on the active metabolite).

**What we measure.**

* Whether the participant notices the loss of CI whiskers and
  comments on it (think-aloud).
* Whether the per-slot stats table below the chart is consulted to
  verify the visual reading.
* Reading time per cohort (eye-tracking: dwell on the chart vs the
  table).

---

## T4 — Drill into an individual patient
*(probes: click-to-drill from PCA; Tab D → Tab E)*

**Scenario.** A clinician notices an outlier patient sitting far from
the central cluster in PCA space and wants to know that individual's
metabolite profile across visits.

**Instruction.** "Switch to *Tab D — PCA state*. Find the data point
that sits farthest from the central cluster (any of the four colour
encodings is fine — use whichever feels easiest). Click that point.
The dashboard should jump you to *Tab E — Individual patient view*.
Read me the patient's RID from the sidebar and describe whether at
least one of their nine metabolites shows a clear rising trend."

**Answer expected.** An RID (4-digit integer) and description of a 
metabolite's trend.

**What we measure.**

* Whether the participant experiences change blindness after the
  automatic tab switch (eye-tracking: do their eyes track to the
  patient panel or remain at the PCA position?).
* Discovery of the per-patient RID dropdown.

---

## T5 — Inspect cohort-level context
*(probes: Cohort tab readability, KPI cards, multi-chart parsing)*

**Scenario.** A reviewer asks how representative the study cohort is
in terms of sex balance and follow-up regularity before they will
accept any effect-size claims you make.

**Instruction.** "Go to *Tab A — Cohort information*. Without reading
any chart in detail, tell me: (a) the total number of participants,
(b) the male-to-female ratio, (c) roughly how many months separate
two consecutive visits on average, and (d) at what calendar year the
sex composition of the cohort begins to shift toward more females."

**Answer expected.**

* (a) 1,274
* (b) 719 M / 555 F
* (c) ≈12 months
* (d) Around 2010–2011 (the visual inflection in the stacked area).

**What we measure.**

* Whether the participant locates the KPI cards quickly versus the
  charts (eye-tracking: AOI hit-rate on the top half of Tab A).
* Whether the inter-visit-gap chart is correctly interpreted as
  months, not weeks.

---

## After all five tasks

1. Click **Stop** and **Download CSV** in the eye-tracking control card.
2. Rename the CSV with the participant ID (e.g.
   `usability_gaze_log_P02.csv`) and move it into a per-participant
   folder.
3. Administer the System Usability Scale questionnaire (10 items,
   5-point Likert; see `debrief_questions.md`).
4. Open the three debrief questions in `debrief_questions.md` and
   record the answers verbatim.

## Pilot pass

* the CSV writes correctly under `dashboard/usability_gaze_log.csv`;
* the calibration overlay closes cleanly after the last dot;
* the click-to-drill from Tab D to Tab E fires (it depends on the
  PCA point's `customdata`);
* `analyze_gaze.py` runs without errors on the resulting CSV.
