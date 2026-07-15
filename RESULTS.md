# Results

All numbers are produced by `python reproduce.py` (seed in `config.yaml`). EER = equal
error rate at the operating point where false-accept = false-reject; lower is better.
Scorer = per-window RandomForest subject classifier (verification score = P(claimed
subject)).

**Within-session evaluation uses a leak-free time-blocked split** (enrol on each subject's
earlier windows, probe on the later ones). An earlier random-window split leaked
autocorrelated neighbours across the enrol/probe boundary and inflated the within-session
numbers; the inflation it caused is quantified explicitly in `split_leakage_check` (Blasco
+0.016 EER, Exam-Stress +0.087 EER) and is not used anywhere else. A label-shuffle control
(permute subject IDs within session) drives every protocol to chance (~0.50), confirming the
reported accuracy is genuine identity signal and not leakage.

## Headline: within-session fusion is strong; it does not survive across sessions

| Dataset | Signals | Within-session EER | Cross-session EER | Same-combo collapse | Cross type |
|---|---|---|---|---|---|
| Blasco 2018 | PPG+ECG+GSR | **0.030** | 0.199-0.210 | ~6.9× | cross-activity (same day) |
| Exam-Stress | PPG+GSR+ACC | 0.234 | 0.312-0.339 | ~1.45× | **cross-day (true)** |

Two honest readings of these two datasets:

- On **Blasco** (a short, clean, seated recording) fusion is strong within-session
  (EER 0.030) and then degrades ~7× across activity states. This reaches a comparably low
  within-session EER to Blasco et al. (2018)'s reported ~0.02, but note it is a different
  scorer and protocol (per-window RandomForest, leak-free split), so it is a *comparable low
  number*, not a like-for-like reproduction.
- On **Exam-Stress** (a real wrist device over multi-hour exams) the honest cross-DAY test,
  fusion is already weak within-session (EER 0.234) and only degrades a further ~1.45× across
  days. The signal never worked well on the wrist even within a session; there is no strong
  number to collapse from. This is the more consequential result for the "watch as a
  password" premise.

## Fusion verdict (does fusing signals help across sessions?)

Fusion gives a small, real cross-session edge over the best single signal (+0.062 EER on
Blasco, +0.041 on Exam-Stress), but this does not close the cross-session gap: absolute
cross-session EER stays at 0.20-0.34. The full three-signal fusion is not the cross-session
optimum on either dataset: the best cross-session combinations are **PPG+GSR on Blasco** (ECG
drops out) and **GSR+ACC on Exam-Stress** (PPG drops out). In each dataset a cardiac channel
is discarded because its within-session identity content does not transfer. On the wrist
device, the cardiac PPG (the signal a consumer unlock would most rely on) is the least useful
single signal across days in absolute terms (cross-day EER 0.467, near chance) and is dropped
from the optimum.

Note the "fusion helps" verdict is a best-of-7-combinations selection made on the same
cross-session data (~6 ordered session-pairs as units), so it is optimistically biased; and
on Exam-Stress the full triple (0.339) is actually worse than the 2-signal GSR+ACC (0.312),
i.e. adding PPG hurts. The edge is real but small and combination-specific, not a "fuse
everything and it gets better" story.

## Per-signal degradation (which signal fails, and how)

Single-signal within-session → cross-session EER:

| Dataset | Signal | Within | Cross | Δ (degradation) |
|---|---|---|---|---|
| Blasco | ECG | 0.115 | 0.374 | +0.259 (most) |
| Blasco | PPG | 0.113 | 0.262 | +0.149 |
| Blasco | GSR | 0.212 | 0.295 | +0.083 (least) |
| Exam-Stress | GSR | 0.275 | 0.353 | +0.078 (most) |
| Exam-Stress | ACC | 0.344 | 0.363 | +0.020 |
| Exam-Stress | PPG | 0.446 | 0.467 | +0.021 (least; already near chance within-session) |

There is **no universal "cardiac degrades most" rule**: on Blasco the cardiac ECG degrades
most, but on Exam-Stress the cardiac PPG degrades least (it simply never worked within-session,
so it had nothing to lose). The consistent finding is that no single signal survives to a
usable cross-session operating point.

## Security-bar accounting (the number that ends the "password" framing)

At the equal-error operating point, false-accept rate = EER. Best **honest cross-session**
fusion, against published device operating points:

| Operating point | FAR (=EER) | vs Touch ID (2e-5) | vs Face ID (1e-6) |
|---|---|---|---|
| Blasco cross-activity (PPG+GSR) | 0.199 | ~10,000× worse | ~200,000× worse |
| Exam-Stress cross-day (GSR+ACC) | 0.312 | ~15,600× worse | ~312,000× worse |

That is 4-5 orders of magnitude short of a real device unlock (`fig2_security_bar.png`). Two
honesty caveats on this comparison: (a) the device FARs are manufacturer specs tuned to a
low-FAR (high false-reject) point, whereas our number is the balanced equal-error point, so
this is an order-of-magnitude, directional comparison, not a same-threshold one; (b) our EER
is closed-set (impostors are the other enrolled subjects) while Touch ID/Face ID are open-set,
which if anything makes the real-world gap larger.

## Robustness

- **Label-shuffle leakage control**: permuting subject IDs within session drives EER to chance
  on both datasets (Blasco within 0.030→0.502, cross 0.210→0.497; Exam-Stress within
  0.234→0.497, cross 0.339→0.497). The reported accuracy is genuine signal.
- **Split-leakage check**: the discarded random-window split gave within 0.014 (Blasco) /
  0.147 (Exam-Stress); the leak-free time-blocked split gives 0.030 / 0.234. The difference is
  the temporal-adjacency leakage we removed.
- **Window length** (Blasco 3/5/10 s): within 0.022-0.038, cross ~0.21 throughout; the
  cross-session failure is not a windowing artefact.
- **Bootstrap 95% CIs** (small resampling universe: n=3 within-session units, n=6 cross-session
  pairs per dataset ,  reported alongside): Blasco within [0.014, 0.047] vs cross [0.119, 0.297];
  Exam-Stress within [0.226, 0.249] vs cross [0.295, 0.377]. The within/cross gap is real, but
  the CIs describe variation across a handful of sessions, not subject-level sampling.

## Honest caveats (do not spin)

1. Blasco cross-session is **cross-activity, same day**, a proxy. Exam-Stress cross-session is
   **cross-day**, the real test. Never conflated.
2. The two datasets' *absolute* EERs are not directly comparable (Exam-Stress E4 wrist BVP over
   multi-hour exams is far noisier than Blasco's short seated recording). Only the within→cross
   change within each dataset is compared.
3. Cross-day, GSR/ACC carry the residual signal. This may reflect behavioural/postural habit
   (ACC) or per-exam stress baseline (GSR) rather than stable physiological identity, so we do
   not claim the residual is "identity."
4. Both datasets are small (n=25, n=10). The direction of the effect is robust to our controls,
   but absolute magnitudes on larger, more diverse populations remain to be measured.
5. The "four signals covered" claim holds only across the two datasets combined; no single
   dataset has both ECG and ACC.

Figures: `figures/fig1_collapse.png`, `figures/fig2_security_bar.png`, `figures/fig3_per_signal.png`.
Frozen tables: `results/RESULTS_all.csv`, `results/results_summary.json`.
