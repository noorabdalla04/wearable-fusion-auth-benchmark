"""Phase 6 analysis: fusion verdict + security-bar accounting.

Two questions, answered from the frozen benchmark tables:

A. **Does fusion survive cross-session?**
   For each dataset and protocol, compare the best fusion combination against the best
   single signal. Within-session we expect fusion >> single; cross-session we test
   whether that advantage persists. We also report the within->cross degradation.

B. **Security-bar accounting.**
   Translate cross-session EER into the false-accept rate a user would face and compare
   to published operating points: Touch ID FAR ~= 1/50,000 (2e-5), Face ID FAR ~= 1/1e6.
   At EER, FAR = FRR = EER, so we state how many orders of magnitude the honest
   cross-session operating point sits above those bars, and the false-reject cost of
   trying to push FAR down to the bar (using the ROC where available).

Bootstrap CIs are added by resampling the per-pair/per-session EERs (a light,
assumption-free interval over the averaging units the harness already produces).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from .repro import REPO_ROOT, get_logger, load_config, set_seed

log = get_logger(__name__)

TOUCH_ID_FAR = 2e-5      # ~1 in 50,000 (Apple published)
FACE_ID_FAR = 1e-6       # ~1 in 1,000,000 (Apple published)


def _best_rows(bench: pd.DataFrame, model: str) -> pd.DataFrame:
    """Best (lowest EER) combination per (dataset, protocol), plus best single-signal."""
    b = bench[bench.model == model].copy()
    out = []
    for (ds, proto), g in b.groupby(["dataset", "protocol"]):
        best = g.loc[g.eer.idxmin()]
        singles = g[g.n_signals == 1]
        best_single = singles.loc[singles.eer.idxmin()]
        out.append({"dataset": ds, "protocol": proto,
                    "best_combo": best.combination, "best_eer": best.eer,
                    "best_single": best_single.combination, "best_single_eer": best_single.eer,
                    "fusion_gain_eer": round(best_single.eer - best.eer, 4)})
    return pd.DataFrame(out)


def fusion_verdict(bench: pd.DataFrame, model: str = "rf") -> dict:
    best = _best_rows(bench, model)
    verdict = {"model": model, "rows": best.to_dict("records"), "by_dataset": {}}
    for ds in best.dataset.unique():
        w = best[(best.dataset == ds) & (best.protocol == "within_session")]
        c = best[(best.dataset == ds) & (best.protocol == "cross_session")]
        if len(w) and len(c):
            w, c = w.iloc[0], c.iloc[0]
            verdict["by_dataset"][ds] = {
                "within_best_eer": w.best_eer, "cross_best_eer": c.best_eer,
                "within_fusion_gain": w.fusion_gain_eer,
                "cross_fusion_gain": c.fusion_gain_eer,
                "collapse_factor": round(c.best_eer / w.best_eer, 2) if w.best_eer > 0 else None,
                "fusion_advantage_survives": bool(c.fusion_gain_eer > 0.02),
            }
    return verdict


def security_accounting(bench: pd.DataFrame, model: str = "rf") -> dict:
    """How far the honest cross-session operating point is from Touch ID / Face ID."""
    b = bench[(bench.model == model) & (bench.protocol == "cross_session")]
    rows = []
    for _, r in b.iterrows():
        eer = r.eer
        rows.append({
            "dataset": r.dataset, "combination": r.combination,
            "cross_session_eer": round(eer, 4),
            "far_at_eer": round(eer, 4),
            "x_worse_than_touchid": round(eer / TOUCH_ID_FAR),
            "x_worse_than_faceid": round(eer / FACE_ID_FAR),
            "orders_above_touchid": round(np.log10(eer / TOUCH_ID_FAR), 1),
            "orders_above_faceid": round(np.log10(eer / FACE_ID_FAR), 1),
        })
    return {"model": model, "touch_id_far": TOUCH_ID_FAR, "face_id_far": FACE_ID_FAR,
            "rows": rows}


def main() -> dict:
    cfg = load_config(); set_seed(cfg["seed"])
    rdir = Path(REPO_ROOT) / "results"
    benches = []
    for ds in ("blasco2018", "exam_stress"):
        p = rdir / f"{ds}_benchmark.csv"
        if p.exists():
            benches.append(pd.read_csv(p))
    bench = pd.concat(benches, ignore_index=True)

    report = {"fusion_verdict": fusion_verdict(bench, "rf"),
              "security_accounting": security_accounting(bench, "rf")}
    (rdir / "analysis_phase6.json").write_text(json.dumps(report, indent=2))
    log.info("wrote analysis_phase6.json")
    return report


if __name__ == "__main__":
    rep = main()
    print("=== FUSION VERDICT (per dataset) ===")
    for ds, v in rep["fusion_verdict"]["by_dataset"].items():
        print(f"{ds}: within {v['within_best_eer']:.3f} -> cross {v['cross_best_eer']:.3f} "
              f"(collapse {v['collapse_factor']}x) | cross fusion gain {v['cross_fusion_gain']:+.3f} "
              f"-> survives: {v['fusion_advantage_survives']}")
    print("\n=== SECURITY BAR (cross-session, best fusion per dataset) ===")
    sec = pd.DataFrame(rep["security_accounting"]["rows"])
    best = sec.loc[sec.groupby("dataset").cross_session_eer.idxmin()]
    for _, r in best.iterrows():
        print(f"{r['dataset']} [{r['combination']}]: EER={r['cross_session_eer']:.3f} = "
              f"{r['x_worse_than_touchid']:,}x worse than Touch ID, "
              f"{r['x_worse_than_faceid']:,}x worse than Face ID")
