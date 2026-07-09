"""Signal cleaning and windowing for the fast-auth use case.

Two stages:

1. ``clean_recording`` : per-channel filtering/denoising.
   - PPG, ECG : neurokit2 cleaners (bandpass + method-specific denoising).
   - GSR/EDA  : low-pass (tonic+phasic retained; high-freq noise removed).
   - ACC      : passed through (used for motion features / artefact flags).

2. ``segment_recording`` : cut a cleaned Recording into fixed-length, non-overlapping
   windows (``window_seconds`` from config; default 5 s) to mimic a few-seconds glance.
   Each window is quality-checked; flat / saturated / NaN windows are flagged.

The output ``Window`` objects carry the same identity fields as their parent Recording
so that the evaluation harness can enforce subject-wise, session-aware splits.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import neurokit2 as nk

from .schema import Recording

# channels that get a physiological cleaner vs a plain filter
_NK_PPG = "PPG"
_NK_ECG = "ECG"


@dataclass
class Window:
    """A fixed-length multi-signal segment cut from one Recording."""
    subject_id: str
    session_id: str
    condition: str
    fs: float
    signals: dict[str, np.ndarray]
    dataset: str = ""
    index: int = 0          # window position within the recording
    quality: dict = field(default_factory=dict)  # per-channel quality flags
    meta: dict = field(default_factory=dict)

    @property
    def is_good(self) -> bool:
        """A window is usable if no channel is flagged bad."""
        return all(v.get("ok", True) for v in self.quality.values())

    @property
    def n_samples(self) -> int:
        return len(next(iter(self.signals.values())))


def _lowpass(x: np.ndarray, fs: float, cutoff: float = 5.0) -> np.ndarray:
    return nk.signal_filter(x, sampling_rate=fs, highcut=cutoff, method="butterworth", order=4)


def clean_recording(rec: Recording) -> Recording:
    """Return a new Recording with each channel cleaned in-place-style (new arrays)."""
    cleaned: dict[str, np.ndarray] = {}
    for ch, x in rec.signals.items():
        try:
            if ch == _NK_PPG:
                cleaned[ch] = nk.ppg_clean(x, sampling_rate=rec.fs)
            elif ch == _NK_ECG:
                cleaned[ch] = nk.ecg_clean(x, sampling_rate=rec.fs)
            elif ch in ("GSR", "EDA"):
                cleaned[ch] = _lowpass(x, rec.fs, cutoff=5.0)
            else:  # ACC*, TEMP: leave raw
                cleaned[ch] = np.asarray(x, dtype=float)
        except Exception:
            # if a cleaner fails on a pathological segment, keep raw and let QA flag it
            cleaned[ch] = np.asarray(x, dtype=float)
    return Recording(rec.subject_id, rec.session_id, rec.condition, rec.fs,
                     cleaned, dataset=rec.dataset, meta=dict(rec.meta))


def _window_quality(x: np.ndarray) -> dict:
    """Flag a window channel as bad if flat, NaN/inf, or saturated."""
    ok = True
    reasons = []
    if not np.all(np.isfinite(x)):
        ok = False; reasons.append("nonfinite")
    std = float(np.std(x))
    if std < 1e-6:
        ok = False; reasons.append("flat")
    # saturation: a large fraction pinned at the min or max
    if len(x):
        vmax, vmin = np.max(x), np.min(x)
        frac_pinned = max(np.mean(x == vmax), np.mean(x == vmin))
        if frac_pinned > 0.5:
            ok = False; reasons.append("saturated")
    return {"ok": ok, "std": std, "reasons": reasons}


def segment_recording(rec: Recording, window_seconds: float = 5.0,
                      drop_first: bool = True) -> list[Window]:
    """Cut into non-overlapping windows of ``window_seconds``.

    ``drop_first`` skips the first window (filter/settling transients), matching the
    authors' practice of discarding initial samples.
    """
    wlen = int(round(window_seconds * rec.fs))
    if wlen <= 0:
        raise ValueError("window too short for sampling rate")
    n_windows = rec.n_samples // wlen
    windows: list[Window] = []
    start_idx = 1 if drop_first else 0
    for w in range(start_idx, n_windows):
        s, e = w * wlen, (w + 1) * wlen
        seg = {ch: x[s:e] for ch, x in rec.signals.items()}
        quality = {ch: _window_quality(v) for ch, v in seg.items()}
        windows.append(Window(
            subject_id=rec.subject_id, session_id=rec.session_id, condition=rec.condition,
            fs=rec.fs, signals=seg, dataset=rec.dataset, index=w,
            quality=quality, meta=dict(rec.meta)))
    return windows
