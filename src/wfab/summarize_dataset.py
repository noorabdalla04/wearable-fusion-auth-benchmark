"""Produce a summary of a loaded dataset (subjects, signals, durations, rates).

Usage:
    python -m wfab.summarize_dataset blasco2018 data/blasco2018

Writes a JSON + CSV summary into results/ so the dataset composition is a tracked,
reproducible artifact.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from .repro import REPO_ROOT, get_logger
from .loaders import blasco2018

_LOADERS = {"blasco2018": blasco2018.load}
log = get_logger(__name__)


def summarize(dataset_name: str, data_root: str | Path) -> dict:
    if dataset_name not in _LOADERS:
        raise ValueError(f"unknown dataset {dataset_name!r}; have {list(_LOADERS)}")
    ds = _LOADERS[dataset_name](data_root)
    summary = ds.summary()

    # per-recording table
    rows = []
    for r in ds:
        row = {"subject_id": r.subject_id, "session_id": r.session_id,
               "condition": r.condition, "fs": r.fs, "duration_s": round(r.duration_s, 1),
               "n_samples": r.n_samples, **{f"has_{c}": (c in r.signals) for c in ("PPG", "ECG", "GSR", "ACC")}}
        row.update({k: r.meta.get(k) for k in ("sex", "age")})
        rows.append(row)
    df = pd.DataFrame(rows)

    summary["duration_s_stats"] = {
        "min": float(df.duration_s.min()), "max": float(df.duration_s.max()),
        "mean": float(df.duration_s.mean()), "median": float(df.duration_s.median())}
    if "age" in df and df["age"].notna().any():
        summary["age_stats"] = {"min": int(df.age.min()), "max": int(df.age.max()),
                                "mean": round(float(df.age.mean()), 1)}
        summary["sex_counts"] = df.drop_duplicates("subject_id")["sex"].value_counts().to_dict()

    out_dir = Path(REPO_ROOT) / "results"
    out_dir.mkdir(exist_ok=True)
    (out_dir / f"{dataset_name}_summary.json").write_text(json.dumps(summary, indent=2))
    df.to_csv(out_dir / f"{dataset_name}_recordings.csv", index=False)
    log.info("wrote results/%s_summary.json and _recordings.csv", dataset_name)
    return summary


if __name__ == "__main__":
    name = sys.argv[1] if len(sys.argv) > 1 else "blasco2018"
    root = sys.argv[2] if len(sys.argv) > 2 else f"data/{name}"
    s = summarize(name, root)
    print(json.dumps(s, indent=2))
