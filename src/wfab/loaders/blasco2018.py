"""Loader for the Blasco & Peris-Lopez 2018 multi-modal wearable biometrics dataset.

Paper : "On the Feasibility of Low-Cost Wearable Sensors for Multi-Modal Biometric
         Verification", Sensors 2018, doi:10.3390/s18092782 (CC BY 4.0).
Data  : released with the paper (LowCostSensorsBiometrics.zip).

Verified file format (confirmed against the authors' MATLAB code
``generate_dataset_original.m`` and by inspecting the raw files):

- Directory layout: ``<root>/{1,2,3}/<uuid>_<k>_<Sex>_<Age>.txt``
  where the top-level dir is the activity state:
    dir "1"  (filename tag _1_) -> seated at rest
    dir "2"  (filename tag _3_) -> walking
    dir "3"  (filename tag _4_) -> seated after a gentle stroll
- Each .txt is comma-separated, sampling rate Fs = 100 Hz, columns:
    col 1 = PPG, col 2 = GSR, col 3 = ECG, col 4 = ~constant reference,
    cols 5-6 = zeros (unused).
  => Only PPG, GSR, ECG are usable signals. There is NO usable accelerometer in
     the released data (cols 4-6 are constant/zero), consistent with the paper's
     fusion using PPG/ECG/GSR.
- ``subject_id`` = the UUID (stable across the 3 states).
- ``session_id`` = the activity state (we treat the 3 states as the cross-CONDITION
  axis; this dataset is single-day, so it has no true cross-DAY axis).
"""
from __future__ import annotations

import re
from pathlib import Path

import numpy as np

from ..schema import Dataset, Recording

FS = 100.0
# top-level dir name -> (filename state tag, human-readable condition)
_STATE_MAP = {
    "1": ("1", "rest_seated"),
    "2": ("3", "walking"),
    "3": ("4", "rest_after_stroll"),
}
# verified column order (0-indexed): PPG, GSR, ECG, then unused
_COL = {"PPG": 0, "GSR": 1, "ECG": 2}

_FNAME_RE = re.compile(r"^(?P<uuid>[0-9a-fA-F-]+)_(?P<tag>\d+)_(?P<sex>Male|Female)_(?P<age>\d+)\.txt$")


def _find_root(data_root: str | Path) -> Path:
    """Locate the directory that contains the 1/2/3 state folders."""
    root = Path(data_root)
    candidates = [root, root / "LowCostSensorsBiometrics",
                  root / "blasco2018" / "LowCostSensorsBiometrics"]
    for c in candidates:
        if all((c / d).is_dir() for d in ("1", "2", "3")):
            return c
    # deep search as a fallback
    for p in root.rglob("LowCostSensorsBiometrics"):
        if all((p / d).is_dir() for d in ("1", "2", "3")):
            return p
    raise FileNotFoundError(f"Could not find Blasco state dirs 1/2/3 under {root}")


def load(data_root: str | Path) -> Dataset:
    """Load the Blasco 2018 dataset into the common schema."""
    root = _find_root(data_root)
    recordings: list[Recording] = []
    for dirname, (tag, condition) in _STATE_MAP.items():
        state_dir = root / dirname
        for fp in sorted(state_dir.glob("*.txt")):
            m = _FNAME_RE.match(fp.name)
            if not m:
                continue
            arr = np.loadtxt(fp, delimiter=",")
            if arr.ndim != 2 or arr.shape[1] < 3:
                raise ValueError(f"unexpected shape {arr.shape} in {fp}")
            signals = {ch: arr[:, idx].astype(float) for ch, idx in _COL.items()}
            recordings.append(Recording(
                subject_id=m.group("uuid"),
                session_id=condition,          # single-day: session == condition
                condition=condition,
                fs=FS,
                signals=signals,
                dataset="blasco2018",
                meta={"sex": m.group("sex"), "age": int(m.group("age")),
                      "source_file": str(fp.relative_to(root)), "state_tag": tag},
            ))
    if not recordings:
        raise RuntimeError(f"No recordings loaded from {root}")
    return Dataset("blasco2018", recordings)
