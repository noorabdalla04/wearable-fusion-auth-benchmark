"""Tests for preprocessing, feature extraction, and the leakage audit."""
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from wfab.schema import Recording  # noqa: E402
from wfab import preprocess as pp  # noqa: E402
from wfab import features as ft  # noqa: E402
from wfab.feature_qa import audit  # noqa: E402
import pandas as pd  # noqa: E402


def _synthetic_ppg(fs=100.0, dur=10.0, hr=60.0, seed=0):
    rng = np.random.default_rng(seed)
    t = np.arange(int(fs * dur)) / fs
    x = np.sin(2 * np.pi * (hr / 60.0) * t) + 0.05 * rng.standard_normal(len(t))
    return x


def test_segment_lengths_and_count():
    rec = Recording("s1", "rest", "rest", 100.0, {"PPG": _synthetic_ppg()})
    wins = pp.segment_recording(rec, window_seconds=5.0, drop_first=False)
    assert all(w.n_samples == 500 for w in wins)
    assert len(wins) == 2  # 10 s / 5 s


def test_quality_flags_flat_window():
    rec = Recording("s1", "rest", "rest", 100.0, {"PPG": np.zeros(1000)})
    wins = pp.segment_recording(rec, window_seconds=5.0, drop_first=False)
    assert all(not w.is_good for w in wins)  # flat -> bad


def test_ppg_features_recover_heart_rate():
    x = _synthetic_ppg(hr=72.0)
    feats = ft.features_ppg(x, fs=100.0)
    # recovered HR should be in a plausible range around 72
    assert 55 < feats["ppg_hr_mean"] < 90


def test_features_are_numeric_only():
    x = _synthetic_ppg()
    feats = ft.features_ppg(x, fs=100.0)
    for k, v in feats.items():
        assert isinstance(v, float)
        assert not any(b in k.lower().split("_") for b in ("subject", "id", "index"))


def test_audit_flags_injected_leak():
    # build a tiny fake feature frame and inject a leaky column
    rng = np.random.default_rng(0)
    n = 200
    subj = np.repeat([f"s{i}" for i in range(10)], n // 10)
    df = pd.DataFrame({
        "dataset": "d", "subject_id": subj, "session_id": "rest",
        "condition": "rest", "window_index": np.arange(n),
        "ppg_hr_mean": 60 + rng.standard_normal(n),
    })
    rep = audit(df)
    assert rep["passed"] is True
    # now inject a subject-id-encoding feature name
    df["subject_code"] = df["subject_id"].astype("category").cat.codes.astype(float)
    rep2 = audit(df)
    assert "subject_code" in rep2["leaky_feature_names"]
    assert rep2["passed"] is False
