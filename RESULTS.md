# Results

All numbers are produced by `python reproduce.py` (seed in `config.yaml`). EER = equal
error rate at the operating point where false-accept = false-reject; lower is better.
Scorer = per-window RandomForest subject classifier (verification score = P(claimed
subject)). Splits are strictly window-disjoint; a label-shuffle control drives every
protocol to chance (0.50), confirming the signal is genuine.

## Headline: within-session fusion is excellent; it collapses across sessions

| Dataset | Signals | Within-session EER | Cross-session EER | Collapse | Cross type |
|---|---|---|---|---|---|
| Blasco 2018 | PPG+ECG+GSR | **0.014** | 0.199–0.210 | ~14× | cross-activity (same day) |
| Exam-Stress | PPG+GSR+ACC | 0.141–0.147 | 0.312–0.339 | ~2.2× | **cross-day (true)** |

The within-session full-fusion EER of **0.014 reproduces Blasco et al. (2018)'s reported
~0.02** — i.e. the "flattering number" that motivates the whole premise. It does not
survive a change of session.

## Fusion verdict (does fusing signals help across sessions?)

Fusion gives a small, real edge cross-session (best fusion beats best single by +0.06
EER on Blasco, +0.04 on Exam-Stress) — but this does **not** close the cross-session gap;
absolute cross-session EER stays at 0.20–0.34. No single signal survives the move across
sessions (every one degrades sharply, see `fig3_per_signal.png`), and the cardiac signal
(PPG) drops out of the cross-session optimum: the best cross-session combos are PPG+GSR
(Blasco) and GSR+ACC (Exam-Stress) — PPG's morphology does not transfer, so it stops
pulling its weight even where it helps within-session.

## Security-bar accounting (the number that ends the "password" framing)

At EER, false-accept rate = EER. Best **honest cross-session** fusion:

| Operating point | FAR | vs Touch ID (2e-5) | vs Face ID (1e-6) |
|---|---|---|---|
| Blasco cross-activity (PPG+GSR) | 0.199 | ~9,970× worse | ~199,400× worse |
| Exam-Stress cross-day (GSR+ACC) | 0.312 | ~15,600× worse | ~311,900× worse |

That is 4–5 orders of magnitude short of a real device unlock (see `fig2_security_bar.png`).

## Robustness

- **Window length** (Blasco 3/5/10 s): within stays 0.014–0.020, cross stays ~0.21 — the
  collapse is not a windowing artefact.
- **Bootstrap 95% CIs are cleanly non-overlapping**: Blasco within [0.006, 0.026] vs cross
  [0.119, 0.297]; Exam-Stress within [0.134, 0.157] vs cross [0.295, 0.377].

## Honest caveats (do not spin)

1. Blasco cross-session is **cross-activity, same day** — a proxy. Exam-Stress cross-session
   is **cross-day**, the real test. Never conflated.
2. Exam-Stress PPG is much noisier than Blasco's even within-session (0.36 vs 0.08); the E4
   wrist BVP over a multi-hour exam is lower quality. The two datasets' *absolute* EERs are
   not directly comparable — only the within→cross collapse within each dataset is.
3. Cross-day, GSR/ACC carry the residual signal. This may reflect behavioural/postural habit
   (ACC) or per-exam stress baseline (GSR) rather than stable physiological identity.

Figures: `figures/fig1_collapse.png`, `figures/fig2_security_bar.png`, `figures/fig3_per_signal.png`.
Frozen tables: `results/RESULTS_all.csv`, `results/results_summary.json`.
