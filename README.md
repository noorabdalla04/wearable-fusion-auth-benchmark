# wearable-fusion-auth-benchmark

**An honest, reproducible benchmark that tests whether combining several wearable body signals can identify you well enough to unlock a device, and shows that it cannot once you are tested on a different day.**

`License: MIT` · `Python: 3.10+` · `Status: benchmark complete (2 datasets), paper drafted` · `Reproduce: python reproduce.py` · `Raw data: not committed (bring your own)`

---

## What is this, in plain language

Smartwatches and fitness bands can measure several body signals at the same time: the optical pulse at your wrist (PPG), the heart's electrical trace (ECG), your movement (accelerometer, ACC), and how much your skin sweats (skin conductance, GSR). For years, researchers have proposed **fusing** these signals into a fast "your body is your password" unlock: glance at the watch and be recognised in a few seconds, the way a fingerprint works. Published systems report almost perfect accuracy, often "99%+".

There is a catch that most of those glowing numbers hide. **They test you using data recorded in the same sitting as when you enrolled.** Your body signals drift from one day to the next (different stress, posture, skin moisture, sensor placement), so recognising you from the *same* recording is far easier than recognising you *tomorrow*. This is the difference between a **within-session** test (enrol and test in one recording, the flattering setup) and a **cross-session** test (enrol one day, prove who you are on a different day, the honest and realistic setup). A password that only works if you re-type it in the same minute you set it is not a password.

This project builds a clean, leak-free pipeline, **reaches a comparably strong within-session number** so you can see the optimistic result is real, then re-runs the exact same method across sessions to show how far the accuracy falls. It also converts that accuracy into a plain security comparison against a fingerprint reader and Face ID, so you can see how large the gap really is.

**The honest finding is negative, and that is the point:** fused wrist signals do not come close to fingerprint or Face ID security once tested across days. Reporting that gap carefully, with reproducible numbers and honest caveats, is the contribution.

## Why it matters

- It puts a **number on the "same-session" illusion** that makes wearable fusion look solved.
- It gives a **reusable, dataset-agnostic benchmark** so other datasets can be dropped in and judged the same way.
- It translates accuracy into a **real-world security bar** (fingerprint and Face ID), which ends the "wearable password" framing on evidence rather than opinion.

## Table of contents

- [Headline results](#headline-results)
- [The core idea in one picture](#the-core-idea-in-one-picture)
- [Fusion verdict: does combining signals help?](#fusion-verdict-does-combining-signals-help)
- [Security-bar accounting](#security-bar-accounting)
- [Robustness and honesty checks](#robustness-and-honesty-checks)
- [Honest caveats](#honest-caveats)
- [What this repo is (and is not)](#what-this-repo-is)
- [Quickstart / reproduce](#quickstart--reproduce)
- [Repository structure](#repository-structure)
- [Datasets and licenses](#datasets-and-licenses)
- [Status](#status)
- [Citation](#citation)
- [License](#license)

## Headline results

Measured on two public datasets. EER (equal error rate) is the error at the point where wrongly letting someone in and wrongly rejecting the real user happen at the same rate. **Lower is better.**

| Dataset | Signals | Within-session EER | Cross-session EER | Collapse | Cross-session type |
|---|---|---|---|---|---|
| Blasco 2018 | PPG+ECG+GSR | **0.030** (leak-free; in the range of the published ~0.02) | 0.199 to 0.210 | ~6.9x (same-combo) | cross-activity, same day |
| Exam-Stress | PPG+GSR+ACC | 0.234 | 0.312 to 0.339 | ~1.5x (same-combo) | **cross-day (true test)** |

- Under a leak-free split the within-session number is strong on Blasco (0.030) and **does not survive** the move across sessions. On the true cross-day wrist dataset the signal is already weak within-session (0.234) and stays weak, so it never worked well to begin with.
- Fusion gives a small but real edge (about +0.04 to +0.06 EER over the best single signal) that does **not** close the gap.
- The best honest cross-session operating point is roughly **10,000 to 16,000 times more permissive than Touch ID** (fingerprint, about 1 in 50,000) and roughly **200,000 to 312,000 times more permissive than Face ID** (about 1 in 1,000,000). That is 4 to 5 orders of magnitude short of a real device unlock.
- Confirmed by a label-shuffle leakage control (drives every result to chance, 0.50), a window-length sweep, and non-overlapping bootstrap confidence intervals.

Full numbers live in [`RESULTS.md`](RESULTS.md). Figures live in [`figures/`](figures/). Everything regenerates with one command: `python reproduce.py`.

## The core idea in one picture

![Within-session accuracy is excellent and then collapses across sessions]({{artifact:art_fd5c405b-9334-494f-8a32-9013796f9849}})

Within-session, the fused signals identify the wearer almost perfectly. Move the test to a different activity state or a different day, and accuracy falls sharply. The gap between the two bars is the illusion that this project measures.

## Fusion verdict: does combining signals help?

Yes, a little, but not enough. Fusing signals beats the best single signal cross-session by **+0.06 EER on Blasco** and **+0.04 EER on Exam-Stress**. That edge does not close the cross-session gap: absolute cross-session EER stays at **0.20 to 0.34**.

No single signal survives the move across sessions (every one degrades sharply, see `figures/fig3_per_signal.png`). Notably, the cardiac signal (PPG), the component a heartbeat-based "password" would most rely on, **drops out of the cross-session optimum entirely**. The best cross-session combinations are **PPG+GSR** (Blasco) and **GSR+ACC** (Exam-Stress). PPG's waveform shape does not transfer between sessions, so it stops pulling its weight cross-session even where it helped within-session.

![Per-signal cross-session performance]({{artifact:art_f14625cb-e4af-4872-af62-93f43ed3aa88}})

## Security-bar accounting

At the equal-error operating point, the false-accept rate equals the EER. In plain terms, the false-accept rate is how often an impostor gets in. Here is the best **honest cross-session** fusion for each dataset, compared to the two consumer benchmarks (Touch ID at about 1 in 50,000, or 2e-5; Face ID at about 1 in 1,000,000, or 1e-6):

| Operating point | False-accept rate | vs Touch ID (2e-5) | vs Face ID (1e-6) |
|---|---|---|---|
| Blasco cross-activity (PPG+GSR) | 0.199 | ~10,000x worse | ~200,000x worse |
| Exam-Stress cross-day (GSR+ACC) | 0.312 | ~15,600x worse | ~312,000x worse |

That is 4 to 5 orders of magnitude short of a real device unlock (see `figures/fig2_security_bar.png`).

![Cross-session performance against the fingerprint and Face ID security bars]({{artifact:art_e20bdd4d-8584-4c95-8841-3d1d7e54111c}})

## Robustness and honesty checks

- **Window length (Blasco, 3 / 5 / 10 seconds):** within-session stays at 0.022 to 0.038, cross-session stays around 0.21. The collapse is not an artefact of how long a window we chose.
- **Bootstrap 95% confidence intervals are cleanly non-overlapping:** Blasco within [0.006, 0.026] vs cross [0.119, 0.297]; Exam-Stress within [0.134, 0.157] vs cross [0.295, 0.377]. The within-to-cross difference is not statistical noise.
- **Leakage control:** shuffling the identity labels drives every protocol to chance (0.50), confirming the pipeline is learning real identity signal and not leaking the answer through the data split.

## Honest caveats

These are load-bearing. Do not spin them.

1. **Blasco cross-session is cross-activity on the same day, a proxy, not a true cross-day test.** Exam-Stress cross-session is genuinely **cross-day**, the real test. The two are never conflated in the results.
2. **Exam-Stress PPG is much noisier than Blasco's even within-session** (feature-QA noise 0.36 vs 0.08); the wrist BVP sensor recorded over a multi-hour exam is lower quality. The two datasets' *absolute* EERs are therefore not directly comparable. Only the within-to-cross collapse *within each dataset* is a fair comparison.
3. **Cross-day, it is GSR and ACC that carry the residual signal, not the heart.** This may reflect behavioural or postural habit (ACC) or a per-exam stress baseline (GSR) rather than a stable physiological identity. In other words, the little that survives may not be "you" in a way you would want to trust with a lock.

## What this repo is

1. A **data-source-agnostic loader and common schema** so multiple public wearable datasets (Blasco 2018, PPG-DaLiA, PTT-PPG, PhysioNet Exam-Stress, BioSec2) run through one pipeline.
2. A **signal-processing and feature-extraction pipeline** for PPG / ECG / ACC / GSR.
3. A **leakage-free evaluation harness** (subject-wise splits, within-session vs cross-session protocols) reporting EER / AUC / ROC.
4. A **fusion analysis** that measures whether fusion's within-session advantage survives cross-session, with explicit accounting against the fingerprint and Face ID bar.

### What this repo is *not*

It is **not** a shippable unlock. Consumer wrist devices do not expose the raw simultaneous signals a hobbyist would need, and mobile platforms do not let a third-party biometric gate the device lock screen. The honest expected finding, which the results confirm, is that fused wrist signals **do not** reach fingerprint or Face ID security across days. That negative benchmark result is the contribution, not a bug to be fixed.

## Quickstart / reproduce

**1. Create the environment** (conda spec pinned in `environment.yml`, or use `requirements.txt`):

```bash
conda env create -f environment.yml
conda activate wfab
```

Or with pip:

```bash
pip install -r requirements.txt
pip install -e .        # installs the wfab package from src/
```

**2. Bring your own data.** Raw datasets are **never committed** to this repo. Download them yourself under each dataset's own license and place them under `data/` as described in [`data/README.md`](data/README.md). The pipeline expects, for example:

```
data/blasco2018/LowCostSensorsBiometrics/{1,2,3}/...
data/exam_stress/.../Data/S1..S10/...
```

**3. Reproduce the whole benchmark with one command:**

```bash
python reproduce.py
```

This runs every step deterministically from the seed in `config.yaml`: build features, run feature QA, run the within vs cross-session benchmark for each dataset present, then analysis, robustness, and figures. Steps that need a dataset you have not downloaded are **skipped with a clear message**, so the script doubles as a self-check on which datasets are present. Outputs land in `results/` and `figures/`.

**4. Run the tests:**

```bash
pytest
```

## Repository structure

```
wearable-fusion-auth-benchmark/
├── README.md                 # this file
├── RESULTS.md                # full frozen numbers and caveats
├── RESEARCH_LOG.md           # lab notebook, including dead ends
├── CONTRIBUTING.md
├── LICENSE                   # MIT
├── reproduce.py              # one-command, raw-data-to-figures reproduction
├── config.yaml               # single source of truth: seed, window length, splits
├── environment.yml           # pinned conda environment
├── requirements.txt          # pinned pip requirements
├── pyproject.toml            # packaging (wfab, src layout)
├── data/
│   ├── README.md             # dataset provenance, access routes, licenses
│   └── blasco2018/           # (you download raw data here; not committed)
├── src/wfab/
│   ├── schema.py             # common, data-source-agnostic recording schema
│   ├── loaders/              # one loader per dataset -> common schema
│   │   ├── blasco2018.py
│   │   └── exam_stress.py
│   ├── preprocess.py         # signal cleaning and windowing
│   ├── features.py           # per-signal biometric feature extraction
│   ├── build_features.py     # load -> clean -> segment -> extract feature matrix
│   ├── feature_qa.py         # feature QA and leakage audit
│   ├── evaluation.py         # within vs cross-session verification harness
│   ├── run_benchmark.py      # run the benchmark across signal combinations
│   ├── analysis.py           # fusion verdict + security-bar accounting
│   ├── robustness.py         # window sweep, bootstrap CIs, shuffle control
│   ├── make_figures.py       # regenerate the three figures from frozen CSVs
│   ├── summarize_dataset.py  # dataset summary (subjects, signals, durations)
│   └── repro.py              # seeding, config loading, run logging
├── results/                  # frozen tables and JSON summaries
│   ├── RESULTS_all.csv        # every (dataset, combination, protocol) row
│   └── results_summary.json
├── figures/                  # fig1_collapse, fig2_security_bar, fig3_per_signal
├── paper/                    # PAPER.md, main.tex, refs.bib, built PDF
└── tests/                    # loader and feature unit tests
```

## Datasets and licenses

**Raw data is never committed** (see `.gitignore`). Each dataset retains its own license: download it yourself into `data/<dataset>/` and point the loader at it. The full provenance, access route, and license table for every supported dataset is in **[`data/README.md`](data/README.md)**. In short, the pipeline supports Blasco 2018 (anchor, cross-activity proxy), PPG-DaLiA, PTT-PPG, PhysioNet Exam-Stress (true cross-day), and BioSec2 (restricted access, true cross-day). Always confirm a dataset's license against its source before use; entries marked "verify" in `data/README.md` have not been re-checked against the source.

## Status

Benchmark complete on 2 datasets, paper drafted (`paper/PAPER.md`, `paper/main.tex`). This is an open, agentically developed research project; the commit history and [`RESEARCH_LOG.md`](RESEARCH_LOG.md) are the lab notebook, dead ends included. The repo is private during development and flips public alongside the preprint.

Every result regenerates from raw data via `reproduce.py` with pinned seeds and a pinned environment. Only loaders are shipped; you bring your own copy of each dataset under its own license.

## Citation

If you use this benchmark, please cite:

> Noor Abdalla. *When does wearable multi-signal fusion stop working? A cross-session benchmark for fast biometric authentication.* 2026. https://github.com/noorabdalla04/wearable-fusion-auth-benchmark

```bibtex
@misc{abdalla2026wfab,
  author = {Abdalla, Noor},
  title  = {When does wearable multi-signal fusion stop working?
            A cross-session benchmark for fast biometric authentication},
  year   = {2026},
  howpublished = {\url{https://github.com/noorabdalla04/wearable-fusion-auth-benchmark}}
}
```

The Blasco 2018 dataset is described in doi:10.3390/s18092782; cite the original dataset and paper as well when you use it.

## License

Code is released under the **MIT License** (see [`LICENSE`](LICENSE)). Datasets are **not** covered by this license and retain their original licenses; see [`data/README.md`](data/README.md) before downloading or redistributing any data.
