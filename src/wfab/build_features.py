"""Build a labeled feature matrix from a dataset: load -> clean -> segment -> extract.

Produces a pandas DataFrame where:
  - identity/label columns: subject_id, session_id, condition, dataset, window_index
  - all other columns are numeric signal-shape features (prefix ppg_/ecg_/gsr_/acc_)

This is the frozen input to the evaluation harness. The strict separation between
label columns and feature columns is what makes leakage auditable.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .repro import REPO_ROOT, get_logger, load_config
from .preprocess import clean_recording, segment_recording
from .features import extract_window
from .loaders import blasco2018, exam_stress

_LOADERS = {"blasco2018": blasco2018.load, "exam_stress": exam_stress.load}
LABEL_COLS = ["dataset", "subject_id", "session_id", "condition", "window_index"]
log = get_logger(__name__)


def feature_columns(df: pd.DataFrame) -> list[str]:
    """Numeric feature columns = everything that is not a label or an ok_ flag."""
    return [c for c in df.columns if c not in LABEL_COLS and not c.startswith("ok_")]


def build(dataset_name: str, data_root: str | Path,
          window_seconds: float | None = None,
          max_windows_per_recording: int | None = None,
          seed: int = 0) -> pd.DataFrame:
    """Build the feature matrix.

    Retention rule: a window is kept if AT LEAST ONE cardiac channel (PPG or ECG) is
    good. We do NOT require every channel to be good, because a dead auxiliary sensor
    (e.g. a subject whose GSR electrode was flat all recording) must not throw away
    that subject's usable PPG/ECG. Instead we record per-channel quality as ``ok_<CH>``
    columns; the evaluation harness filters to windows where the channels *in the
    combination being tested* are all good. This keeps single-signal and fusion
    evaluations honest and maximises usable data per combination.
    """
    cfg = load_config()
    window_seconds = window_seconds or cfg["window_seconds"]
    load_fn = _LOADERS[dataset_name]
    ds = load_fn(data_root)

    rng = np.random.default_rng(seed)
    rows = []
    n_win = n_kept = 0
    for rec in ds:
        cleaned = clean_recording(rec)
        wins = segment_recording(cleaned, window_seconds=window_seconds)
        # cap very long recordings by uniform subsampling of windows (keeps whole-session
        # coverage rather than only the first N minutes)
        if max_windows_per_recording and len(wins) > max_windows_per_recording:
            sel = np.sort(rng.choice(len(wins), max_windows_per_recording, replace=False))
            wins = [wins[i] for i in sel]
        for w in wins:
            n_win += 1
            ok = {ch: w.quality.get(ch, {}).get("ok", True) for ch in w.signals}
            # keep if at least one cardiac channel is good (PPG or ECG)
            if not (ok.get("PPG", False) or ok.get("ECG", False)):
                continue
            n_kept += 1
            feats = extract_window(w)
            row = {"dataset": w.dataset, "subject_id": w.subject_id,
                   "session_id": w.session_id, "condition": w.condition,
                   "window_index": w.index,
                   **{f"ok_{ch}": bool(v) for ch, v in ok.items()},
                   **feats}
            rows.append(row)
    df = pd.DataFrame(rows)
    log.info("%s: %d/%d retained windows -> matrix %s", dataset_name, n_kept, n_win, df.shape)
    return df


def save(df: pd.DataFrame, dataset_name: str) -> Path:
    out = Path(REPO_ROOT) / "results" / f"{dataset_name}_features.parquet"
    out.parent.mkdir(exist_ok=True)
    df.to_parquet(out, index=False)
    return out


if __name__ == "__main__":
    import sys
    name = sys.argv[1] if len(sys.argv) > 1 else "blasco2018"
    root = sys.argv[2] if len(sys.argv) > 2 else f"data/{name}"
    cap = int(sys.argv[3]) if len(sys.argv) > 3 else None
    df = build(name, root, max_windows_per_recording=cap, seed=load_config()["seed"])
    p = save(df, name)
    feat_cols = feature_columns(df)
    print(f"saved {p.name}: {df.shape[0]} windows x {len(feat_cols)} features")
    print("subjects:", df.subject_id.nunique(), "| conditions:", sorted(df.condition.unique()))
    print("channel ok-rates:", {c: round(df[c].mean(), 3) for c in df.columns if c.startswith("ok_")})
    print("NaN fraction per feature (top 5):")
    print(df[feat_cols].isna().mean().sort_values(ascending=False).head().to_string())
