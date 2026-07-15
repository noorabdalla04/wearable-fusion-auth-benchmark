# When does wearable multi-signal fusion stop working?
### A cross-session benchmark for fast biometric authentication

**Noor Abdalla** · Independent researcher
Code: https://github.com/noorabdalla04/wearable-fusion-auth-benchmark

> This is the GitHub-readable version of the paper. The typeset PDF (`main.pdf`) is
> built from `main.tex` + `refs.bib`. All numbers are produced by `reproduce.py`.

## Abstract

Consumer wearables can read several physiological signals at once: photoplethysmography
(PPG), electrocardiography (ECG), electrodermal activity (GSR), and accelerometry (ACC). A
recurring proposal is to fuse them into a fast "your body is your password" unlock: glance
at the watch, get identified in seconds, like a fingerprint. Published fusion systems report
near-perfect accuracy (equal error rates around 2%), which makes the idea look solved. We show
that this number is an artefact of evaluating enrolment and test data from the **same recording
session**. We build an open, data-source-agnostic benchmark that (i) under a leak-free
evaluation reaches a comparably low within-session number on a public multi-signal dataset
(Blasco et al. 2018; full-fusion EER 0.030, in the range of the reported ~0.02), and then
(ii) re-evaluates the identical pipeline across sessions using two protocols: a cross-activity
proxy on the same day, and a genuine cross-day protocol on a second dataset (PhysioNet
Exam-Stress; three exams on different days). The within-session strength does not transfer: on
Blasco the best honest cross-activity EER is 0.199 (about a 7x degradation), and on the true
cross-day wrist dataset the signal is already weak within-session (EER 0.234) and stays weak
across days (best 0.312). Signal fusion gives a small, real edge over the best single signal
(+0.04 to +0.06 EER) but does not close the gap, and on both datasets a cardiac channel is
dropped from the cross-session optimum because its within-session identity content does not
transfer. Translated to a security operating point, the best honest
cross-session fusion is ~10,000 to 16,000× more permissive than Touch ID and ~200,000 to
312,000× more permissive than Face ID. We conclude that fast wearable fusion is not a device-unlock
primitive; its honest role is a low-stakes "probably still the same wearer" continuity check.
All code, loaders, and a one-command reproduction are released.

## 1. Introduction

Every modern smartwatch carries an optical pulse sensor, an accelerometer, and increasingly an
electrodermal or single-lead ECG sensor. A long line of work asks whether these signals can
**identify** the wearer, and the most attractive framing is authentication: use the body's own
signals as a password, so a device unlocks the moment it is worn. The literature appears to
support it, with multi-signal fusion reporting equal error rates (EERs) around 2% or better.

There is a catch that is easy to miss and decisive in practice. Most flattering numbers split
a **single recording session** into enrolment and test partitions. Within one session a
classifier can lock onto session-specific nuisance structure (sensor placement, contact
pressure, skin state) that is perfectly predictive *within that session* but has nothing to
do with stable identity. A real unlock must work tomorrow, on a freshly donned device. The
scientific question is therefore not "can we separate people within a session" (we can, easily)
but "does that separation survive a change of session."

**Contributions:** (1) an open, data-source-agnostic benchmark (common schema + thin per-dataset
loaders + one leakage-audited pipeline); (2) a competitive within-session number under a
leak-free split (EER 0.030 on Blasco, in the range of ~0.02); (3) a cross-session evaluation
under a same-day cross-activity proxy and a true cross-day protocol, showing a ~7x collapse on
Blasco and a wrist signal that is weak within-session and stays weak across days; (4) a fusion verdict and security-bar accounting showing the honest operating point
is 4-5 orders of magnitude short of Touch ID / Face ID. This is a negative result with a
constructive framing: we measure precisely where a widely-assumed idea fails, and release the
tooling so the measurement is cheap to repeat.

## 2. Related work

**Physiological biometrics.** PPG and ECG have both been studied as biometric traits, with
within-session accuracies frequently in the high-90s percent. Fusion of cardiac signals with
other modalities is a recurring theme.

**The permanence problem.** That intuition is rarely tested across time. Permanence, stability
across sessions and days, is a named property in biometrics, and several wrist-PPG studies that
test it report large cross-day degradation. The dataset we anchor on states its own limitation
plainly: its signals "were acquired only once on a given day," and it recommends "cross-day and
long-term analysis" as future work. This study is in part that recommended follow-up, extended
to fusion and to a security-bar comparison.

**Where this sits.** We do not claim that fusing wearable signals to identify a person is new,
nor that the within-session-inflation critique is new: a contemporaneous benchmark,
ECG-biometrics-bench (arXiv:2605.01548), names the same "random-split" fallacy and evaluates
it across seven ECG datasets with closed- and open-set protocols, and is more thorough on the
single-signal cardiac case. Our contribution is the complementary *multi-signal fusion* slice
it does not cover: whether fusing simultaneous signals, the mechanism most often proposed to
reach a fast unlock, survives across sessions. We reach a competitive within-session number
under a leak-free split with the same pipeline we then stress-test, report cross-session
numbers with leakage controls and confidence intervals, and state the
security implication in practitioner units.

## 3. Methods

### 3.1 Datasets

| Dataset | Subjects | Sessions | Signals | Rate | Cross-session axis |
|---|---|---|---|---|---|
| Blasco 2018 | 25 | 3 activities (1 day) | PPG, ECG, GSR | 100 Hz | cross-activity (proxy) |
| Exam-Stress | 10 | 3 exams (different days) | PPG, ACC, GSR | 64 Hz† | cross-day (true) |

**Blasco 2018.** 25 subjects (ages 18-42, mean 28.1; 16 M, 9 F), three activity states on a
single day (seated rest; walking; seated after a stroll). PPG/ECG/GSR at 100 Hz. There is **no
usable accelerometer** in the released files, so Blasco fusion is PPG+ECG+GSR. Because all
recordings are from one day, its cross-"session" axis is really **cross-activity**, a proxy.

**PhysioNet Exam-Stress.** Empatica E4 wrist device, 10 subjects, three exams on **different
days**. BVP (PPG) 64 Hz, 3-axis ACC 32 Hz, EDA (GSR) 4 Hz; **no ECG**. Fusion is PPG+ACC+GSR;
cross-session axis is a genuine **cross-day** test. Recordings span 3 to 7 h.
† Channels have different native rates; the loader resamples all onto a shared 64 Hz grid.

Together the two datasets cover all four signals and provide both a same-day proxy and a true
cross-day protocol.

### 3.2 Common schema
A single `Recording` type holds {subject id, session id, condition, sampling rate, dict of
equal-length time-aligned channels} with canonical channel names. Each dataset has a thin
loader; no downstream code knows which dataset it is processing. This let us add a second
dataset (different device, signals, rates) with **zero** change to the processing, feature,
evaluation, or analysis code. `session_id` is the split axis.

### 3.3 Signal processing & windowing
Standard cleaning (NeuroKit2 for PPG/ECG; 5 Hz low-pass for GSR; ACC as vector magnitude).
Non-overlapping **5-second windows**, the fast "glance-and-go" regime. Per-window quality
flags mark bad channels; a window is kept if ≥1 cardiac channel is good, with per-channel "ok"
flags for per-combination filtering.

### 3.4 Features
Signal-shape features only, never identity/recording tokens: cardiac HR/variability and pulse
morphology, spectral band energy, distributional shape; GSR level/spread/slope; ACC
level/spread/band energy. 26 features per dataset.

### 3.5 Leakage audit
Automated audit rejects identity-like names (token-boundary), confirms window index is never a
feature, flags degenerate features, and red-flags implausible single-feature separability.
Passes on both datasets. End-to-end control: within-session label permutation must score at
chance, and it does (§4.5).

### 3.6 Evaluation
Closed-set verification; report EER and ROC AUC. Scorer = per-window RandomForest subject
classifier (200 trees); verification score = P(claimed subject). We use a supervised classifier
because that is the model class that produces the flattering literature numbers (a distance
template gives within-session EER ≈ 0.17 and does not reproduce them). Standardisation fit on
enrolment only.
- **Within-session:** enrol/test on disjoint window partitions of the same session (runtime
  disjointness assertion), averaged over sessions.
- **Cross-session:** enrol on one session, test on a different one (common subjects), averaged
  over ordered session pairs. Blasco = cross-activity; Exam-Stress = cross-day.

All randomness seeded; the whole pipeline regenerates via `reproduce.py`.

## 4. Results

### 4.1 A strong within-session number, under a leak-free split
On Blasco, full-fusion within-session verification reaches **EER 0.030** under a leak-free
time-blocked split, in the range of the ~0.02
reported by Blasco et al. This is a comparably low number, not a like-for-like reproduction
(Blasco used a different scorer and 60 s training; we use a per-window RandomForest); it is
enough to show our pipeline is competitive with the result that motivates the
"body-as-password" premise, so the cross-session failure below is not a weak-model artefact.
A prior version used a random-window split and reported EER 0.014; that split leaks temporally
adjacent windows, and 0.030 (leak-free) is the honest number. Every single signal is
individually usable within session (EER 0.113-0.212).

### 4.2 Accuracy collapses across sessions

| Dataset | Signals | Within EER | Cross EER | Collapse |
|---|---|---|---|---|
| Blasco 2018 | PPG+ECG+GSR | **0.030** | 0.199-0.210 | ~6.9x (same-combo) |
| Exam-Stress | PPG+GSR+ACC | 0.234 | 0.312-0.339 | ~1.5x (same-combo) |

![Within vs cross EER]({{artifact:art_fd5c405b-9334-494f-8a32-9013796f9849}})

On Blasco the best cross-activity EER is 0.199 (~7x same-combination degradation from the
within-session 0.030). On Exam-Stress, the true cross-day test on a real wrist device, the
signal is already weak within-session (full-fusion EER 0.234) and only degrades a further
~1.5x to 0.312 across days; there is no strong number to collapse from (a within-session
baseline that is itself weaker because multi-hour wrist BVP is far noisier). At these operating
points the system is close to a coin flip at any usable threshold.

### 4.3 Does fusion survive? A small edge, not a rescue
Fusion's cross-session advantage over the best single signal is real but small: +0.062 EER
(Blasco), +0.041 (Exam-Stress). It does not close the gap; absolute cross-session EER stays
0.20-0.34. The full-fusion triple is never the cross-session optimum: the best combination is
PPG+GSR on Blasco (ECG drops out) and GSR+ACC on Exam-Stress (PPG drops out): in each dataset
a **cardiac channel is discarded** because its within-session identity content does not transfer.

![Per-signal degradation]({{artifact:art_f14625cb-e4af-4872-af62-93f43ed3aa88}})

No single signal survives the move across sessions. On the wrist device (Exam-Stress) the
cardiac PPG, the signal a consumer unlock would most naturally rely on, is the least useful
single signal across days in absolute terms (cross-day EER 0.467, near chance) and is dropped
from the optimum. Note there is no universal "cardiac degrades most" rule: on Blasco the
cardiac ECG degrades most across sessions, while on Exam-Stress PPG degrades least (it barely
worked within-session). The "fusion helps" edge is also a best-of-7-combinations selection on
~6 session-pair units (optimistically biased), and on Exam-Stress the full triple (0.339) is
worse than 2-signal GSR+ACC (0.312), i.e. adding PPG hurts.

### 4.4 Security-bar accounting
At the equal-error operating point, false-accept rate = EER. Against Touch ID
(FAR ≈ 2×10⁻⁵, ~1 in 50,000) and Face ID (FAR ≈ 1×10⁻⁶, ~1 in 1,000,000):

| Operating point | Combination | FAR (=EER) | vs Touch ID | vs Face ID |
|---|---|---|---|---|
| Blasco cross-activity | PPG+GSR | 0.199 | ~10,000x | ~200,000x |
| Exam-Stress cross-day | GSR+ACC | 0.312 | ~15,600x | ~312,000x |

![Security bar]({{artifact:art_e20bdd4d-8584-4c95-8841-3d1d7e54111c}})

The best honest cross-session fusion is 4-5 orders of magnitude short of a real device unlock.
Two caveats keep this an order-of-magnitude, directional statement: the device FARs are
manufacturer specs tuned to a low-FAR (high false-reject) point, whereas ours is the balanced
equal-error point; and our EER is closed-set while Touch ID/Face ID are open-set, which would
if anything widen the gap.

### 4.5 Robustness and honesty checks
- **Split-leakage check:** a random-window within-session split gives EER 0.014 (Blasco) /
  0.147 (Exam-Stress); the leak-free time-blocked split gives 0.030 / 0.234. The difference is
  temporal-adjacency leakage; all within-session numbers here use the leak-free split.
- **Label-shuffle:** permuting subject labels within session drives both within and cross EER
  to chance (Blasco within 0.030->0.502, cross 0.210->0.497; Exam within 0.234->0.497, cross
  0.339->0.497); real performance is genuine signal, not leakage.
- **Window length:** Blasco features at 3/5/10 s keep within EER 0.022-0.038 and cross ~0.21, so
  the cross-session failure is not a windowing artefact.
- **Bootstrap CIs:** within vs cross 95% CIs do not overlap (Blasco within [0.014, 0.047] vs
  cross [0.119, 0.297]; Exam-Stress within [0.226, 0.249] vs cross [0.295, 0.377]), but are
  resampled over few units (3 within-session sessions, 6 cross-session pairs), so they describe
  session-level not subject-level variation.

## 5. Discussion

**What the number means.** The within-session ~2% EER is real but answers the wrong question.
A password lives in the cross-session regime, where the honest number is 0.20-0.34 EER:
unusable as an unlock.

**Why fusion does not save it.** Fusion gives a small real gain, dwarfed by the cross-session
failure; in each dataset a cardiac channel drops out of the cross-session optimum (ECG on
Blasco, PPG on the wrist device). There is no universal "cardiac degrades most" rule; the
consistent finding is that no channel reaches a usable cross-session operating point. Fusion
cannot rescue signals that individually fail to transfer.

**The honest use case.** A fast fused read cannot be a device unlock, but it can be a low-stakes
**continuity** check ("is this probably still the same wearer") where a 20% error rate is
tolerable because the fallback is benign. Presenting the same technology as a fingerprint
replacement is the error we forestall.

**Limitations.** (1) Blasco's cross axis is cross-activity on one day, a proxy; the true
cross-day result (Exam-Stress) is worse. (2) The two datasets' absolute EERs are not directly
comparable; we compare the within→cross collapse within each. (3) Cross-day, the residual is
carried by GSR/ACC, which may encode behavioural/postural habit or per-session stress baseline
rather than stable identity; we do not claim the residual is "identity." (4) Both datasets are
small (n=25, n=10); direction is robust to our controls, but magnitudes on larger populations
remain to be measured, which the released benchmark enables.

## 6. Conclusion
Fast multi-signal wearable fusion is strong within a single session (Blasco full-fusion EER
0.030 under a leak-free split) and does not transfer: it degrades about 7x across activity
states on the same day, and on a real wrist device across days it never authenticated well even
within a session (EER 0.234) and stays weak (0.312). Either way the honest cross-session
operating point is 4-5 orders of magnitude short of a real device unlock. Fusion helps a little
and does not close the gap; a cardiac channel drops out of the cross-session optimum in each
dataset. We
release a reproducible, leakage-audited, cross-session-honest benchmark and a one-command
reproduction.

## Reproducibility & data availability
All code, loaders, leakage audit, evaluation harness, and `reproduce.py` are at
https://github.com/noorabdalla04/wearable-fusion-auth-benchmark. Raw datasets come from their
original sources under their own licenses (Blasco 2018, DOI 10.3390/s18092782; PhysioNet
Exam-Stress, ODC-By); the repo never redistributes raw data and documents provenance and
checksums. Results were produced with a fixed random seed.

## References
- Blasco, J. & Peris-Lopez, P. (2018). *On the Feasibility of Low-Cost Wearable Sensors for
  Multi-Modal Biometric Verification.* Sensors 18(9), 2782. doi:10.3390/s18092782
- *A Wearable Exam Stress Dataset for Predicting Cognitive Performance in Real-World Settings.*
  PhysioNet v1.0.0 (ODC-By). https://physionet.org/content/wearable-exam-stress/1.0.0/
- *ECG-biometrics-bench: A Unified Framework for Reproducible Benchmarking of ECG Biometrics.*
  arXiv:2605.01548 (2026). https://arxiv.org/abs/2605.01548
