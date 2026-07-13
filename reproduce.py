#!/usr/bin/env python
"""One-command reproduction of the whole benchmark, from raw data to figures.

Prerequisites: download the datasets into data/ per data/README.md
  data/blasco2018/LowCostSensorsBiometrics/{1,2,3}/...
  data/exam_stress/.../Data/S1..S10/...

Then: python reproduce.py   (with the wfab environment active)

Every step is deterministic given config.yaml:seed. Steps that need raw data are
skipped with a clear message if the data is absent, so the script also serves as a
self-check on which datasets are present.
"""
from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from wfab.repro import get_logger, load_config, set_seed
from wfab import build_features as bf
from wfab import feature_qa, run_benchmark, analysis, robustness, make_figures

log = get_logger("reproduce")
DATASETS = {"blasco2018": "data/blasco2018", "exam_stress": "data/exam_stress"}
CAPS = {"blasco2018": None, "exam_stress": 200}


def have(ds, root):
    p = Path(root)
    if ds == "blasco2018":
        return any(p.rglob("LowCostSensorsBiometrics/1"))
    if ds == "exam_stress":
        return any(p.rglob("Data/S1"))
    return False


def main():
    cfg = load_config(); seed = set_seed(cfg["seed"])
    present = [ds for ds, root in DATASETS.items() if have(ds, root)]
    if not present:
        log.error("No datasets found under data/. See data/README.md."); return 1
    log.info("datasets present: %s", present)

    for ds in present:
        log.info("=== %s: build features ===", ds)
        df = bf.build(ds, DATASETS[ds], window_seconds=cfg["window_seconds"],
                      max_windows_per_recording=CAPS[ds], seed=seed)
        bf.save(df, ds)
        feature_qa.main(ds)
        run_benchmark.run(ds)

    log.info("=== analysis + robustness + figures ===")
    analysis.main()
    if "blasco2018" in present:
        robustness.main()
    make_figures.main()
    log.info("DONE. See results/ and figures/.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
