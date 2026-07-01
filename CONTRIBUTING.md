# Contributing & development notes

This project is developed in the open (agentically), with a running lab notebook in
`RESEARCH_LOG.md`. A few conventions keep it reproducible:

## Principles
- **Honesty over flattery.** Report cross-session numbers, not just within-session ones.
  Negative results are results. Never hide a disappointing operating point.
- **No data leakage.** Splits are always subject-wise. A subject never appears in both
  train and test. Record-wise splits are a bug, not a shortcut.
- **No raw data in git.** Only loaders; users bring their own data under each license.
- **Every result regenerates** from raw data via a single script with a pinned seed
  (`config.yaml: seed`) and the pinned environment (`environment.yml`).

## Workflow
- Small, frequent commits with descriptive messages; the history is the narrative.
- Add a `RESEARCH_LOG.md` entry when a decision or dead end happens, not after.
- Tests in `tests/`; run `pytest` before committing analysis code.

## Environment
```
conda env create -f environment.yml && conda activate wfab
pip install -e .
```
