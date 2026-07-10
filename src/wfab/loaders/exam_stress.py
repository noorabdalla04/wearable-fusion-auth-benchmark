"""Loader for the PhysioNet 'Wearable Exam Stress' dataset (Empatica E4).

Paper : Amin et al., "A Wearable Exam Stress Dataset for Predicting Cognitive
        Performance in Real-World Settings", PhysioNet v1.0.0.
License: ODC-By (Open Data Commons Attribution) — confirmed from the bundled LICENSE.txt.
Source : PhysioNet, physionet.org/content/wearable-exam-stress/1.0.0/ (retrieved 2026-07-15).
         DOI intentionally omitted — record it from the landing page before publishing.

Why this dataset matters here
-----------------------------
10 subjects (S1..S10), each recorded during THREE exams on DIFFERENT days
(Midterm 1, Midterm 2, Final). That gives a genuine cross-DAY axis, which Blasco
(single day, 3 activity states) lacks. This is the dataset that turns our
"cross-activity" proxy into a real cross-session/cross-day test.

Signals (Empatica E4 wrist device)
----------------------------------
- BVP  -> PPG   (64 Hz)
- ACC  -> 3-axis accelerometer (32 Hz), unit 1/64 g; we use the magnitude -> ACC
- EDA  -> GSR   (4 Hz)
- (HR, TEMP, IBI also present; not loaded as primary channels)
- NO ECG (wrist device). So Exam-Stress fusion = PPG + ACC + GSR.

Format: each csv's row 0 = start unix timestamp, row 1 = sample rate, then samples.

Harmonisation: channels have different native rates. We resample every channel to a
common ``TARGET_FS`` (64 Hz, the PPG rate) by linear interpolation onto a shared time
grid, then trim to the overlapping span so all channels are time-aligned and equal
length (schema requirement).

``session_id`` = exam name (Midterm 1 / Midterm 2 / Final) = the cross-DAY axis.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

from ..schema import Dataset, Recording

TARGET_FS = 64.0
_EXAMS = ["Midterm 1", "Midterm 2", "Final"]


def _read_e4(path: Path) -> tuple[float, float, np.ndarray]:
    """Return (start_ts, fs, data[n] or data[n,3]) for an E4 csv."""
    raw = np.genfromtxt(path, delimiter=",")
    if raw.ndim == 1:
        start, fs = float(raw[0]), float(raw[1])
        data = raw[2:]
    else:  # ACC: 3 columns
        start, fs = float(raw[0, 0]), float(raw[1, 0])
        data = raw[2:, :]
    return start, fs, data


def _resample_to_grid(start: float, fs: float, data: np.ndarray, grid: np.ndarray) -> np.ndarray:
    """Linear-interpolate a channel onto a shared absolute-time grid (seconds)."""
    n = len(data)
    t = start + np.arange(n) / fs
    return np.interp(grid, t, data, left=np.nan, right=np.nan)


def _load_session(sess_dir: Path) -> dict | None:
    """Load one exam session into aligned {channel: array} at TARGET_FS."""
    need = {"BVP.csv", "EDA.csv", "ACC.csv"}
    if not all((sess_dir / f).exists() for f in need):
        return None
    bvp_s, bvp_fs, bvp = _read_e4(sess_dir / "BVP.csv")
    eda_s, eda_fs, eda = _read_e4(sess_dir / "EDA.csv")
    acc_s, acc_fs, acc = _read_e4(sess_dir / "ACC.csv")
    if len(bvp) == 0 or len(eda) == 0 or len(acc) == 0:
        return None
    acc_mag = np.sqrt((acc.astype(float) ** 2).sum(axis=1))  # 3-axis -> magnitude

    # shared grid over the overlapping time span
    starts = [bvp_s, eda_s, acc_s]
    ends = [bvp_s + len(bvp) / bvp_fs, eda_s + len(eda) / eda_fs, acc_s + len(acc) / acc_fs]
    t0, t1 = max(starts), min(ends)
    if t1 - t0 < 10:  # need at least 10 s of overlap
        return None
    grid = np.arange(t0, t1, 1.0 / TARGET_FS)
    sig = {
        "PPG": _resample_to_grid(bvp_s, bvp_fs, bvp, grid),
        "GSR": _resample_to_grid(eda_s, eda_fs, eda, grid),
        "ACC": _resample_to_grid(acc_s, acc_fs, acc_mag, grid),
    }
    # drop any leading/trailing NaN rows from interpolation edges
    good = np.all([np.isfinite(v) for v in sig.values()], axis=0)
    if good.sum() < TARGET_FS * 10:
        return None
    return {k: v[good] for k, v in sig.items()}


def _find_root(data_root: str | Path) -> Path:
    root = Path(data_root)
    for c in [root, root / "Data", root.parent / "Data"]:
        if (c / "S1").is_dir():
            return c
    for p in root.rglob("Data"):
        if (p / "S1").is_dir():
            return p
    raise FileNotFoundError(f"Could not find exam-stress Data/S1 under {root}")


def load(data_root: str | Path) -> Dataset:
    root = _find_root(data_root)
    recordings: list[Recording] = []
    for sdir in sorted(root.glob("S*"), key=lambda p: int(p.name[1:])):
        for exam in _EXAMS:
            sess = sdir / exam
            if not sess.is_dir():
                continue
            sig = _load_session(sess)
            if sig is None:
                continue
            cond = exam.lower().replace(" ", "")
            recordings.append(Recording(
                subject_id=sdir.name, session_id=cond, condition=cond,
                fs=TARGET_FS, signals=sig, dataset="exam_stress",
                meta={"exam": exam, "device": "Empatica E4"}))
    if not recordings:
        raise RuntimeError(f"No exam-stress recordings loaded from {root}")
    return Dataset("exam_stress", recordings)
