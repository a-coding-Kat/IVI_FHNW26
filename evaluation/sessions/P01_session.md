# Usability session — Participant P01

> **Anonymised record.** No name or identifying detail is stored; the participant
> is referred to only as **P01**. Verbal consent obtained per
> `../consent_template.pdf`.
>
> **Eye-tracking was not available.** WebGazer would not write the gaze CSV on
> the test device — clicking *Download CSV* produced an empty file (the same
> recorder issue seen during the pilot pass), so no gaze, AOI, or heat-map data
> were collected. The session therefore ran as a **moderated think-aloud**: the
> participant performed the five tasks in `../eyetracking_tasks.pdf` and answered
> each question **orally**, while the facilitator recorded the answer, task
> success, completion time, and observed difficulty. Evidence here is
> **self-report (SUS + debrief) and observational only** — there is no
> physiological/attention channel.

| Field | Value |
|---|---|
| Participant ID | P01 |
| Background | Clinician (neurology), occasional dashboard user |
| Date | 2026-05-20 |
| Device | Laptop, 1920 × 1080, Brave |
| Method | Moderated think-aloud; oral answers; SUS; 3 open debrief questions |
| Not collected | Eye-tracking / gaze CSV (WebGazer device failure) |

---

## Task results (oral answers, moderated think-aloud)

### T1 — Filter the cohort and read a trajectory
**Asked:** filter to female NL→MCI, switch to Tab B, is GLCA's mean going up or down from slot −3 to slot 0?
**Oral answer:** "Down." **Expected:** down. **Outcome:** correct, unaided. **Time:** ~15 s.
**Observed:** found the cohort checklist and Sex radio quickly; set the filter without prompting and read the slope confidently.

### T2 — Discover a high-effect metabolite
**Asked:** on Tab C (MCI→AD vs stable_NL, slot 0) find the largest positive Hedges' g.
**Oral answer:** "GHDCA." **Expected:** GHDCA. **Outcome:** correct, unaided. **Time:** ~20 s.
**Observed:** Slight usprise about colors.

### T3 — Compare cohorts on one metabolite, key finding
**Asked:** Untick all, tick MCI→AD + stable_NL + stable_MCI, between which two slots does MCI→AD rise most steeply?
**Oral answer:** "Between −2 and −1." **Expected:** −2→−1 (or −1→0). **Outcome:** correct. **Time:** ~20 s.
**Observed / difficulty:** **the confidence-interval bands were confusing.** With one cohort the plot showed the mean ± 95% CI whiskers; when the second and third cohorts were added the whiskers disappeared. P01 paused: *"Wait — where did the error bars go? Are these still confidence intervals or just the means now?"* They were unsure whether the change in the plot meant the statistics had changed or only the display. They reached the right answer but explicitly flagged the CI behaviour as unclear.

### T4 — Drill into an individual patient
**Asked:** on Tab D click the point farthest from the cluster; it should jump to Tab E — read the RID and describe a rising metabolite.
**Oral answer:** gave an RID and "HDCA rises toward the last visit," after the facilitator helped. **Outcome:** completed **with assistance**. **Time:** ~55 s.
**Observed:** clicking the PCA point **did not take them to the patient view** — nothing visibly happened. P01 assumed they had mis-clicked, tried twice more, then the facilitator suggested using the RID box. (This matches the click-to-drill defect later found and fixed in `app.py`.)

### T5 — Inspect cohort-level context
**Asked:** from Tab A report participants, M/F ratio, inter-visit gap, and the year the sex balance shifts toward females.
**Oral answer:** "1,274; 719 men / 555 women; about 12 months; around 2010–2011." **Expected:** matches. **Outcome:** correct, unaided. **Time:** ~20 s.
**Observed:** read the KPI cards first, then confirmed the inflection on the stacked-area chart; interpreted the gap as months.

---

## System Usability Scale (self-report; Brooke, 1996)

| # | Statement | Rating (1–5) |
|---|---|---|
| 1 | Would like to use frequently | 5 |
| 2 | Unnecessarily complex | 2 |
| 3 | Easy to use | 5 |
| 4 | Would need technical support | 1 |
| 5 | Functions well integrated | 4 |
| 6 | Too much inconsistency | 2 |
| 7 | Most people would learn quickly | 4 |
| 8 | Very cumbersome | 2 |
| 9 | Felt very confident | 4 |
| 10 | Needed to learn a lot first | 2 |

**SUS score = 82.5** (above the 68 benchmark).***

---

## Debrief (verbatim)

**Q1 — Most confusing moment?**
> "When I added cohorts to the trajectory the error bars vanished. I couldn't
> tell if the confidence intervals were gone or just hidden — label that."

**Q2 — Most useful feature to keep?**
> "Clicking a metabolite in the forest and landing on its trajectory."

**Q3 — One change for weekly routine use?**
> "Make the confidence intervals consistent, or always show them with a note."

## Facilitator summary
All five tasks reached the correct answer; T4 needed help because the PCA click
did not open the patient view. **Headline finding: the CI bands are confusing —
the switch from mean ± 95% CI (one cohort) to means-only (multiple cohorts) is
not signposted.** Self-report SUS high (82.5).

***
SUS Calculation

Step 1: Convert responses
- Odd items (positive statements): score − 1
- Even items (negative statements): 5 − score

Step 2: Sum adjusted scores

Step 3: Multiply by 2.5

68 benchmark indicates above-average usability.