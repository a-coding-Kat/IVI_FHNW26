# Evaluation materials

This folder contains everything needed to run one usability session
end-to-end, including post-session analysis. The analysis code itself
lives in `../dashboard/analyze_gaze.py`.

## Files

| File | Purpose |
|------|---------|
| `tasks.md` | Five task scripts read to the participant during the session, with expected answers and what each task is measuring. |
| `consent_template.md` | Short verbal-consent script the facilitator reads before calibration. |
| `debrief_questions.md` | System Usability Scale + three open questions for the post-session debrief. |

## Session checklist

1. **Hardware**
   * Laptop with webcam, Chrome browser, 1920 × 1080 monitor.
   * Even ambient light on the participant's face (no severe
     backlighting).
   * Stopwatch (phone is fine), pen, and a printed copy of `tasks.md`.

2. **Software**
   * `cd C:\Users\katar\Code\IVI\dashboard`
   * `python app.py`
   * Open `http://127.0.0.1:8050` in Chrome.
   * Delete any leftover `usability_gaze_log.csv` from a previous
     session — the next participant must start a fresh file.

3. **Pre-session**
   * Read `consent_template.md` aloud. Confirm verbal consent.
   * Click **Start** in the eye-tracking control card. Accept the
     camera permission prompt.
   * Click **Calibrate**. Walk the participant through the 9 yellow
     dots: look at the dot and click it five times, then move on.
     The overlay closes automatically when all 9 dots are gone.
   * Eyeball-check: ask them to look at each corner. The red
     prediction dot should land within roughly the same quadrant.
     If accuracy is visibly broken, **Stop → Start → Calibrate**
     again.

4. **During tasks** (`tasks.md`)
   * Read the scenario, then the instruction, verbatim.
   * Start the stopwatch when the participant begins.
   * Encourage think-aloud; do not coach.
   * Write down: time to completion, audible confusion phrases,
     errors and recovery, whether the expected answer was reached.

5. **Post-session**
   * Click **Stop** in the eye-tracking card.
   * Click **Download CSV** and save the file with the participant
     identifier, e.g. `usability_gaze_log_P02.csv`. Move it into
     `evaluation/sessions/P02/`.
   * Read out `debrief_questions.md`. Record the SUS ratings and
     verbatim answers to the three open questions.
   * Thank the participant.

6. **Analysis**
   ```bash
   cd ..\dashboard
   python analyze_gaze.py ..\evaluation\sessions\P02\usability_gaze_log_P02.csv --width 1920 --height 1080
   ```
   This writes a per-tab dwell bar chart, AOI hit-rate bar chart,
   gaze-density heat-map, and a one-page text summary next to the
   CSV. Aggregate the per-participant outputs across the cohort for
   the report.

## Data retention

CSV files are pseudonymised (participant ID only, no name) and stored
on the researcher's local machine. They are deleted three months
after the report is submitted unless the participant explicitly
agrees to longer retention.
