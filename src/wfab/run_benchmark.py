"""Run the full within- vs cross-session benchmark across signal combinations.

Produces results/<dataset>_benchmark.csv with one row per (protocol, combination).
"""
from __future__ import annotations

import itertools
import json
from pathlib import Path

import pandas as pd

from .repro import REPO_ROOT, get_logger, load_config, set_seed
from .evaluation import within_session, cross_session

log = get_logger(__name__)


def all_combinations(tokens: list[str]) -> list[tuple[str, ...]]:
    combos = []
    for r in range(1, len(tokens) + 1):
        combos += [tuple(c) for c in itertools.combinations(tokens, r)]
    return combos


def run(dataset_name: str = "blasco2018", tokens: list[str] | None = None) -> pd.DataFrame:
    cfg = load_config()
    seed = set_seed(cfg["seed"])
    df = pd.read_parquet(Path(REPO_ROOT) / "results" / f"{dataset_name}_features.parquet")
    # infer available signal tokens from ok_ flags
    if tokens is None:
        tokens = [t for t in ("ppg", "ecg", "gsr", "acc")
                  if f"ok_{t.upper()}" in df.columns]
    rows = []
    for model in ("template", "rf"):
        for combo in all_combinations(tokens):
            wr = within_session(df, combo, seed=seed, model=model)
            cr = cross_session(df, combo, seed=seed, model=model)
            for res in (wr, cr):
                rows.append({"dataset": dataset_name, "model": model,
                             "protocol": res.protocol,
                             "combination": "+".join(res.combination),
                             "n_signals": len(res.combination),
                             "eer": round(res.eer, 4), "auc": round(res.auc, 4),
                             "n_genuine": res.n_genuine, "n_impostor": res.n_impostor,
                             "n_subjects": res.n_subjects})
            log.info("[%s] %s: within EER=%.3f | cross EER=%.3f",
                     model, "+".join(combo), wr.eer, cr.eer)
    out = pd.DataFrame(rows).sort_values(["model", "protocol", "n_signals", "combination"])
    out.to_csv(Path(REPO_ROOT) / "results" / f"{dataset_name}_benchmark.csv", index=False)
    return out


if __name__ == "__main__":
    import sys
    name = sys.argv[1] if len(sys.argv) > 1 else "blasco2018"
    res = run(name)
    print(res.to_string(index=False))
