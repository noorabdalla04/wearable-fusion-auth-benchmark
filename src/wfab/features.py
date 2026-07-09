"""Per-signal biometric feature extraction from cleaned windows.

For each modality we extract features that established PPG/ECG biometric work relies
on. Everything here is per-window (a few seconds), matching the fast-auth setting.

- PPG : heart-rate + rate variability from systolic peaks; morphology of the average
        pulse (amplitude, width, up/down-slope ratios); spectral band energy.
- ECG : heart-rate + variability from R-peaks; QRS-region morphology of the average
        beat; spectral band energy.
- GSR : tonic level and simple phasic statistics (mean/std/slope/range).
- ACC : magnitude statistics + spectral energy (motion signature), when present.

Features are returned as a flat ``{name: value}`` dict per window. Missing/failed
extractions return NaN for that feature (imputed downstream), never a crash.

IMPORTANT (leakage): features are computed from signal *shape only*. No subject id,
file name, recording index, or absolute timestamp ever enters a feature. This is
enforced by construction here and audited in ``feature_qa``.
"""
from __future__ import annotations

import numpy as np
import neurokit2 as nk
from scipy import signal as sps
from scipy import stats

from .preprocess import Window

_NAN = float("nan")


def _safe(fn, default=_NAN):
    try:
        v = fn()
        return float(v) if np.isfinite(v) else default
    except Exception:
        return default


def _band_energy(x: np.ndarray, fs: float, lo: float, hi: float) -> float:
    f, pxx = sps.welch(x, fs=fs, nperseg=min(len(x), 256))
    mask = (f >= lo) & (f < hi)
    return float(np.trapz(pxx[mask], f[mask])) if mask.any() else _NAN


def _pulse_morphology(x: np.ndarray, peaks: np.ndarray, fs: float, prefix: str) -> dict:
    """Average-beat morphology around detected peaks."""
    out = {}
    if len(peaks) < 3:
        return {f"{prefix}_amp_mean": _NAN, f"{prefix}_amp_std": _NAN,
                f"{prefix}_width_mean": _NAN, f"{prefix}_upslope_mean": _NAN}
    amps = x[peaks]
    out[f"{prefix}_amp_mean"] = float(np.mean(amps))
    out[f"{prefix}_amp_std"] = float(np.std(amps))
    # beat width proxy = median inter-peak interval (samples) -> seconds
    ibi = np.diff(peaks) / fs
    out[f"{prefix}_width_mean"] = float(np.median(ibi)) if len(ibi) else _NAN
    # up-slope: mean derivative in the 100 ms before each peak
    win = max(1, int(0.1 * fs))
    slopes = []
    for p in peaks:
        if p - win >= 0:
            slopes.append((x[p] - x[p - win]) / (win / fs))
    out[f"{prefix}_upslope_mean"] = float(np.mean(slopes)) if slopes else _NAN
    return out


def _hrv(peaks: np.ndarray, fs: float, prefix: str) -> dict:
    """Basic rate + rate-variability features from peak indices."""
    if len(peaks) < 3:
        return {f"{prefix}_hr_mean": _NAN, f"{prefix}_ibi_std": _NAN,
                f"{prefix}_rmssd": _NAN}
    ibi = np.diff(peaks) / fs  # seconds
    hr = 60.0 / ibi
    rmssd = np.sqrt(np.mean(np.diff(ibi) ** 2)) if len(ibi) > 1 else _NAN
    return {f"{prefix}_hr_mean": float(np.mean(hr)),
            f"{prefix}_ibi_std": float(np.std(ibi)),
            f"{prefix}_rmssd": float(rmssd)}


def features_ppg(x: np.ndarray, fs: float) -> dict:
    out = {}
    try:
        _, info = nk.ppg_peaks(x, sampling_rate=fs)
        peaks = np.asarray(info.get("PPG_Peaks", []), dtype=int)
    except Exception:
        peaks = np.array([], dtype=int)
    out.update(_hrv(peaks, fs, "ppg"))
    out.update(_pulse_morphology(x, peaks, fs, "ppg"))
    out["ppg_band_lf"] = _band_energy(x, fs, 0.5, 2.5)
    out["ppg_band_hf"] = _band_energy(x, fs, 2.5, 8.0)
    out["ppg_skew"] = _safe(lambda: stats.skew(x))
    out["ppg_kurt"] = _safe(lambda: stats.kurtosis(x))
    return out


def features_ecg(x: np.ndarray, fs: float) -> dict:
    out = {}
    try:
        _, info = nk.ecg_peaks(x, sampling_rate=fs)
        peaks = np.asarray(info.get("ECG_R_Peaks", []), dtype=int)
    except Exception:
        peaks = np.array([], dtype=int)
    out.update(_hrv(peaks, fs, "ecg"))
    out.update(_pulse_morphology(x, peaks, fs, "ecg"))
    out["ecg_band_lf"] = _band_energy(x, fs, 0.5, 15.0)
    out["ecg_band_hf"] = _band_energy(x, fs, 15.0, 40.0)
    out["ecg_skew"] = _safe(lambda: stats.skew(x))
    out["ecg_kurt"] = _safe(lambda: stats.kurtosis(x))
    return out


def features_gsr(x: np.ndarray, fs: float) -> dict:
    t = np.arange(len(x)) / fs
    slope = _safe(lambda: np.polyfit(t, x, 1)[0]) if len(x) > 1 else _NAN
    return {"gsr_mean": float(np.mean(x)), "gsr_std": float(np.std(x)),
            "gsr_range": float(np.ptp(x)), "gsr_slope": slope}


def features_acc(x: np.ndarray, fs: float) -> dict:
    return {"acc_mean": float(np.mean(x)), "acc_std": float(np.std(x)),
            "acc_range": float(np.ptp(x)),
            "acc_band_lo": _band_energy(x, fs, 0.5, 3.0),
            "acc_band_hi": _band_energy(x, fs, 3.0, 15.0)}


_EXTRACTORS = {"PPG": features_ppg, "ECG": features_ecg, "GSR": features_gsr,
               "ACC": features_acc}


def extract_window(win: Window) -> dict:
    """Extract all features from a window's channels. Returns a flat feature dict.

    Only signal-shape features are produced. Identity fields are attached separately
    by the caller (feature matrix builder), never mixed into the feature values.
    """
    feats: dict = {}
    for ch, x in win.signals.items():
        base = ch.split("_")[0]  # ACC_X -> ACC
        fn = _EXTRACTORS.get(base)
        if fn is not None:
            feats.update(fn(np.asarray(x, dtype=float), win.fs))
    return feats
