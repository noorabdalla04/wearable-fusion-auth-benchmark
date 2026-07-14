# wearable-fusion-auth-benchmark

**An honest cross-session benchmark of fast, multi-signal wearable biometric authentication.**

Consumer wearables can read several body signals at once — the optical pulse (PPG),
the heart's electrical trace (ECG), motion (accelerometer), and skin conductance (GSR).
A recurring claim in the literature is that *fusing* these signals lets a device
recognise its wearer quickly and reliably — potentially as a password-like unlock.
Reported accuracies are often spectacular: equal-error rates near zero, "99%+".

Almost all of those numbers are measured **within a single recording session**. This
project asks the question the flattering numbers skip:

> **Does fast multi-signal fusion still work when you are tested on a *different day*
> or in a *different activity state* — and how far short of a real security bar
> (fingerprint ≈ 1 in 50,000; Face ID ≈ 1 in 1,000,000) does it actually land?**

## What this repo is

1. A **data-source-agnostic loader + common schema** so multiple public wearable
   datasets (Blasco 2018, PPG-DaLiA, PTT-PPG, PhysioNet Exam-Stress, BioSec2) can be
   analysed with one pipeline.
2. A **signal-processing + feature-extraction pipeline** for PPG / ECG / ACC / GSR.
3. A **leakage-free evaluation harness** (subject-wise splits; within-session vs
   cross-session protocols) that reports EER / AUC / ROC.
4. A **fusion analysis** measuring whether fusion's within-session advantage survives
   cross-session, with explicit accounting against the fingerprint / Face-ID bar.

## What this repo is *not*

It is **not** a shippable unlock. Consumer wrist devices do not expose the raw
simultaneous signals a hobbyist would need, and mobile platforms do not let a
third-party biometric gate the device lock screen. The honest expected finding is
that fused wrist signals **do not** reach fingerprint/Face-ID security across days.
That negative/benchmark result is the contribution.

## Headline finding

The paper is drafted (`paper/PAPER.md`, `paper/main.tex`). Result, on two public datasets:

| Dataset | Signals | Within-session EER | Cross-session EER | Collapse |
|---|---|---|---|---|
| Blasco 2018 | PPG+ECG+GSR | **0.014** (reproduces the published ~0.02) | 0.199–0.210 | ~14× (cross-activity) |
| Exam-Stress | PPG+GSR+ACC | 0.141–0.147 | 0.312–0.339 | ~2.2× (**cross-day**) |

- The flattering within-session number **reproduces** — then collapses across sessions.
- Fusion gives a small real edge (+0.04–0.06 EER) that does **not** close the gap.
- The best honest cross-session operating point is **~10,000–16,000× more permissive than
  Touch ID** and **~200,000–312,000× more permissive than Face ID** — 4–5 orders of magnitude
  short of a real unlock.
- Verified by a label-shuffle leakage control (→ chance), a window-length sweep, and
  non-overlapping bootstrap CIs.

Full numbers: `RESULTS.md`. Figures: `figures/`. One-command reproduction: `python reproduce.py`.

## Status

Benchmark complete (2 datasets), paper drafted. This is an open, agentically-developed
research project; the commit history and `RESEARCH_LOG.md` are the lab notebook, including
dead ends. The repo is private during development and flips public alongside the preprint.

## Reproducibility

Every result regenerates from raw data via a single script (see `src/wfab/`) with pinned
seeds and a pinned environment. See `data/README.md` for dataset licenses and access
routes — **raw data is never committed**, only loaders that expect you to bring your own
copy under each dataset's own license.

## License

Code: MIT (see `LICENSE`). Datasets retain their original licenses.
