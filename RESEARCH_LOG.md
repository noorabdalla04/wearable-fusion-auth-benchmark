# Research log

This is the project's lab notebook. It records decisions, rationale, and dead ends
in the order they happened — including the ones that didn't work out. It is meant to
be read top-to-bottom as the story of how the project reached its conclusions.

---

## 2026 — Project framing

**Goal (as refined with the project owner).** Find whether a *combination* of body
signals, captured together in a few seconds on a wearable, can authenticate a person
"uniquely, credibly, consistently, and fast" — the password-like unlock idea.

**Reality check performed before any code.** A literature + feasibility review
established three hard constraints on the *product* version of this idea:

1. **Accuracy collapses across sessions.** Fused within-session numbers look excellent
   (near-zero EER) but degrade sharply across days; single-signal wrist PPG rises to
   ~23% EER cross-day (Sancho et al. 2018, doi:10.3390/s18051525). The best *honest*
   cross-session fusion number found still includes a fingerprint and lands at ~6.9%
   EER (arXiv:2412.05660) — thousands of times short of Touch ID / Face ID.
2. **Hardware access.** No consumer wrist device exposes the simultaneous *raw* signals
   a hobbyist would need without privileged/partner access.
3. **Platform lock.** iOS/Android do not let a third-party biometric gate device unlock.

**Decision.** Do *not* pursue a shippable unlock. Pursue the **honest scientific
contribution** the field skips: a cross-session-honest benchmark of fast multi-signal
wrist fusion, quantifying how far it falls short of the security bar. Framed as a
benchmark / negative result, this is publishable and beginner-feasible on public data.

**Novelty scan (verified).** The single closest prior work is Blasco & Peris-Lopez 2018
(doi:10.3390/s18092782): PPG+ECG+ACC+GSR on 25 subjects across 3 activity states, fused,
AUC 0.99 / EER 0.02 with 60 s training — dataset released publicly. Crucially, its own
stated limitation is that signals "were acquired only once on a given day" and cross-day
analysis is "recommended in a future study." That future study is our opening. Full scan:
`novelty_scan.md` (kept with the project record).

**Anchor dataset.** Blasco 2018 — we extend the exact paper that did the within-session
version.

---

---

## 2026 — Phase 2: Blasco data acquired, schema + loader built

**Download.** Blasco dataset fetched from the Dropbox link cited in the paper
(`LowCostSensorsBiometrics.zip`, 5.7 MB, sha256 `59537950e36f…`). CC BY 4.0.

**Verified format (from the authors' own MATLAB `generate_dataset_original.m`, not
guessed).** 100 Hz; columns are **PPG, GSR, ECG**, then a near-constant reference
column and two zero columns. Directory `1/2/3` = activity states rest / walking /
rest-after-stroll. Subject = UUID, stable across states.

**Honest finding worth flagging: there is NO usable accelerometer in the released
data.** Columns 4–6 are constant/zero. The paper's abstract lists ACC among the
sensors, but the released fusion signals are PPG/ECG/GSR only (matching the paper's
best config, ECG+PPG+GSR). So for the Blasco anchor, our "multi-signal fusion" is
**PPG+ECG+GSR**, not PPG+ACC. ACC-based fusion will have to come from PPG-DaLiA / PTT-PPG.

**Loader validated against the paper.** Loading into the common schema yields exactly
25 subjects × 3 states = 75 recordings, PPG/ECG/GSR at 100 Hz, ages 18–42 (mean 28.1),
16M/9F — matches the paper's stated "16 males and 9 females, average 28.2, median 27".
This subject-demographics match is our evidence the loader reads the data correctly.
See `results/blasco2018_summary.json`. 6/6 unit tests pass.

**Schema design.** One `Recording` = one subject × one session/condition × time-aligned
signals at a common `fs`. `session_id` is the axis the evaluation harness splits on
(within- vs cross-session); `condition` is kept separate so cross-activity and cross-day
are distinguishable. This is the reusable, data-source-agnostic core.

---

---

## 2026 — Phase 3: signal processing + features (with two honest course-corrections)

**Pipeline.** load → clean (neurokit2 ppg_clean/ecg_clean; GSR low-pass) → segment into
5 s non-overlapping windows (drop first for settling) → per-channel quality flags →
per-signal features. 5 s = the fast-auth "glance" window.

**Features (signal-shape only, no identity).** PPG/ECG: heart rate, IBI std, RMSSD,
average-beat morphology (amplitude, width, up-slope), spectral band energy, skew/kurt.
GSR: tonic mean/std/range/slope. ACC: magnitude stats + band energy (when present).
26 features on Blasco (PPG+ECG+GSR).

**Course-correction #1 — retention rule.** First build required ALL channels good per
window, which silently dropped 3 subjects whose GSR electrode was dead the whole
recording — throwing away their perfectly good PPG/ECG. Fixed: keep a window if at
least one cardiac channel (PPG or ECG) is good, and record per-channel `ok_<CH>` flags
so the evaluation harness filters per signal-combination. Result: all 25 subjects
retained, 3871 windows. Per-channel good-rates: **PPG 100%, ECG 94.8%, GSR 84.1%** —
GSR is the weak sensor, and that is now visible rather than hidden.

**Course-correction #2 — leakage-audit false positive.** The audit's banned-substring
check flagged `ppg_width_mean`/`ecg_width_mean` because "width" contains "id". Fixed to
token-boundary matching. Audit now passes: no leaky names, window_index excluded from
features, no zero-variance or suspicious features.

**Leakage audit result (passes).** Top single-feature subject separability is `gsr_mean`
(ANOVA F≈1057) — physiologically real (baseline skin conductance differs between
people), not an artefact; no feature exceeds 20× the 90th-percentile F, so nothing looks
like a hidden recording-id. 11/11 tests pass.

**Artefacts.** `results/blasco2018_features.parquet` (frozen feature matrix, checkpoint),
`results/blasco2018_feature_qa.json`.

---

### Open questions being carried forward
- Cross-DAY data is the weak link: the multi-signal sets are single-day. Plan uses
  Blasco's 3 activity states as a cross-condition proxy, plus PhysioNet Exam-Stress
  (3 sessions) for a true — if small — cross-day test.
- Expected headline result is a negative one. That is acceptable and is the point.
