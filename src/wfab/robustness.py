"""Phase 6 robustness / honesty checks.

Tests whether the headline collapse is an artefact of specific choices:

1. **Window length**: rebuild features at 3 s / 5 s / 10 s and re-evaluate the best
   fusion combo. If the collapse holds across window lengths it is not a windowing
   artefact.
2. **Bootstrap CIs on the collapse**: resample the per-session-pair EERs to put an
   interval on within vs cross so the gap is shown to be real, not noise.
3. **Proxy vs true**: explicitly tag Blasco cross-session as cross-ACTIVITY (proxy) and
   Exam-Stress cross-session as cross-DAY (true), so the paper never conflates them.

This module is intentionally cheap: it reuses the frozen feature matrices where possible
and only rebuilds features for the window-length sweep (Blasco only, which is fast).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from .repro import REPO_ROOT, get_logger, load_config, set_seed
from .evaluation import within_session, cross_session
from . import build_features as bf

log = get_logger(__name__)


def bootstrap_collapse(df: pd.DataFrame, combo, seed: int, n_boot: int = 500) -> dict:
    """Bootstrap CI on within- and cross-session EER for one combination."""
    rng = np.random.default_rng(seed)
    w = within_session(df, combo, seed=seed, model="rf")
    c = cross_session(df, combo, seed=seed, model="rf")
    w_pairs = np.array([v["eer"] for v in w.detail.values()])
    c_pairs = np.array([v["eer"] for v in c.detail.values()])

    def ci(arr):
        if len(arr) < 2:
            return [float(arr.mean()), float(arr.mean())] if len(arr) else [None, None]
        boot = [rng.choice(arr, len(arr), replace=True).mean() for _ in range(n_boot)]
        return [round(float(np.percentile(boot, 2.5)), 4), round(float(np.percentile(boot, 97.5)), 4)]

    return {"combination": "+".join(combo),
            "within_eer": round(w.eer, 4), "within_ci95": ci(w_pairs),
            "cross_eer": round(c.eer, 4), "cross_ci95": ci(c_pairs),
            "n_within_units": len(w_pairs), "n_cross_units": len(c_pairs)}


def window_length_sweep(dataset: str, data_root: str, combo, seed: int,
                        lengths=(3.0, 5.0, 10.0)) -> list[dict]:
    out = []
    for wl in lengths:
        df = bf.build(dataset, data_root, window_seconds=wl,
                      max_windows_per_recording=200, seed=seed)
        w = within_session(df, combo, seed=seed, model="rf")
        c = cross_session(df, combo, seed=seed, model="rf")
        out.append({"window_s": wl, "within_eer": round(w.eer, 4),
                    "cross_eer": round(c.eer, 4),
                    "collapse_x": round(c.eer / w.eer, 2) if w.eer > 0 else None})
        log.info("[%s wl=%.0fs] within=%.3f cross=%.3f", dataset, wl, w.eer, c.eer)
    return out


def label_shuffle_control(df: pd.DataFrame, combo, seed: int) -> dict:
    """Leakage control: permute subject_id WITHIN each session, then re-run the
    within- and cross-session evaluation. A leak-free pipeline must score at
    chance (EER ~0.50) once identity is destroyed. If it does not, the reported
    accuracy is an artefact rather than genuine identity signal.
    """
    rng = np.random.default_rng(seed)
    shuffled = df.copy()
    for sess in shuffled.session_id.unique():
        m = shuffled.session_id == sess
        perm = shuffled.loc[m, "subject_id"].to_numpy().copy()
        rng.shuffle(perm)
        shuffled.loc[m, "subject_id"] = perm
    w_real = within_session(df, combo, seed=seed, model="rf")
    c_real = cross_session(df, combo, seed=seed, model="rf")
    w_shuf = within_session(shuffled, combo, seed=seed, model="rf")
    c_shuf = cross_session(shuffled, combo, seed=seed, model="rf")
    return {"combination": "+".join(combo),
            "within_real_eer": round(w_real.eer, 4), "within_shuffled_eer": round(w_shuf.eer, 4),
            "cross_real_eer": round(c_real.eer, 4), "cross_shuffled_eer": round(c_shuf.eer, 4),
            "passes": bool(w_shuf.eer > 0.42 and c_shuf.eer > 0.42)}


def split_leakage_check(df: pd.DataFrame, combo, seed: int) -> dict:
    """Quantify temporal-adjacency leakage in the within-session split.

    A RANDOM window split lets autocorrelated neighbours straddle the enrol/probe
    boundary and inflates within-session accuracy; a time-BLOCKED split does not.
    We report both so the inflation is explicit and the honest (blocked) number is
    the one used everywhere else.
    """
    w_block = within_session(df, combo, seed=seed, model="rf", split="blocked")
    w_rand = within_session(df, combo, seed=seed, model="rf", split="random")
    return {"combination": "+".join(combo),
            "within_blocked_eer": round(w_block.eer, 4),
            "within_random_eer": round(w_rand.eer, 4),
            "inflation_abs": round(w_block.eer - w_rand.eer, 4)}


def main() -> dict:
    cfg = load_config(); seed = set_seed(cfg["seed"])
    rdir = Path(REPO_ROOT) / "results"
    report = {"proxy_vs_true": {
        "blasco2018": "cross-ACTIVITY (same day, 3 states) — PROXY for cross-session",
        "exam_stress": "cross-DAY (3 exams on different days) — TRUE cross-session"}}

    # bootstrap CIs + leakage controls on each dataset's best fusion combo
    boots, shuffles, splits = {}, {}, {}
    for ds, combo in [("blasco2018", ("ppg", "ecg", "gsr")),
                      ("exam_stress", ("ppg", "gsr", "acc"))]:
        p = rdir / f"{ds}_features.parquet"
        if p.exists():
            d = pd.read_parquet(p)
            boots[ds] = bootstrap_collapse(d, combo, seed)
            shuffles[ds] = label_shuffle_control(d, combo, seed)
            splits[ds] = split_leakage_check(d, combo, seed)
    report["bootstrap"] = boots
    report["label_shuffle_control"] = shuffles
    report["split_leakage_check"] = splits

    # window-length sweep (Blasco, fast)
    report["window_sweep_blasco"] = window_length_sweep(
        "blasco2018", "data/blasco2018", ("ppg", "ecg", "gsr"), seed)

    (rdir / "robustness_phase6.json").write_text(json.dumps(report, indent=2))
    log.info("wrote robustness_phase6.json")
    return report


if __name__ == "__main__":
    rep = main()
    print(json.dumps(rep, indent=2))
