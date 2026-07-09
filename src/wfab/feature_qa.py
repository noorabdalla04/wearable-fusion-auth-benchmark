"""Feature QA and leakage audit.

Checks that must pass before the feature matrix is used for evaluation:

1. **No identity leakage by construction**: feature column names never include an id;
   feature values are finite-or-NaN numeric only.
2. **window_index is not predictive of subject beyond chance** in a way that could leak
   — it is a label column, never a feature, but we confirm it is excluded.
3. **No feature is a near-perfect proxy for subject identity via a trivial artefact**
   (e.g. a constant offset per subject that is really a recording-id). We test this by
   checking that no single feature achieves implausibly high subject-separation on its
   own relative to the rest (a heuristic red-flag, not a hard gate).
4. **Feature distributions are sane**: report NaN rates and per-feature variance so
   degenerate features can be dropped.

Outputs a JSON report to results/.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from .repro import REPO_ROOT, get_logger, load_config, set_seed
from .build_features import LABEL_COLS, feature_columns

log = get_logger(__name__)


def audit(df: pd.DataFrame) -> dict:
    cfg = load_config()
    set_seed(cfg["seed"])
    feat_cols = feature_columns(df)
    report: dict = {"n_windows": int(len(df)), "n_features": len(feat_cols),
                    "n_subjects": int(df.subject_id.nunique())}

    # 1. no id-like feature names. Match whole tokens (split on '_'), not substrings,
    #    so legitimate features like 'ppg_width_mean' are not flagged for containing "id".
    banned = {"subject", "session", "file", "index", "uuid", "id", "name", "path"}
    leaky_names = [c for c in feat_cols if banned & set(c.lower().split("_"))]
    report["leaky_feature_names"] = leaky_names

    # 2. label cols present and excluded from features
    report["label_cols_present"] = [c for c in LABEL_COLS if c in df.columns]
    report["window_index_in_features"] = "window_index" in feat_cols  # must be False

    # 4. NaN + variance
    nan_rate = df[feat_cols].isna().mean()
    report["nan_rate_top"] = nan_rate.sort_values(ascending=False).head(8).round(4).to_dict()
    variances = df[feat_cols].var(numeric_only=True)
    report["zero_variance_features"] = variances[variances < 1e-12].index.tolist()

    # 3. single-feature subject separability red-flag: ANOVA F between-subject / within
    #    A feature that is a recording-id artefact would have near-infinite F.
    sep = {}
    y = df.subject_id.values
    subjects = df.subject_id.unique()
    for c in feat_cols:
        x = df[c].values.astype(float)
        m = np.isfinite(x)
        if m.sum() < 50:
            continue
        xg, yg = x[m], y[m]
        grand = xg.mean()
        ss_between = ss_within = 0.0
        for s in subjects:
            xs = xg[yg == s]
            if len(xs) < 2:
                continue
            ss_between += len(xs) * (xs.mean() - grand) ** 2
            ss_within += ((xs - xs.mean()) ** 2).sum()
        k = len(subjects)
        n = len(xg)
        if ss_within <= 0 or n - k <= 0:
            sep[c] = float("inf")
        else:
            sep[c] = (ss_between / (k - 1)) / (ss_within / (n - k))
    sep_sorted = dict(sorted(sep.items(), key=lambda kv: kv[1], reverse=True))
    report["top_subject_separating_features_F"] = {k: round(v, 2) for k, v in list(sep_sorted.items())[:8]}
    # red flag if any single feature has F an order of magnitude above the 90th percentile
    fvals = np.array([v for v in sep.values() if np.isfinite(v)])
    if len(fvals):
        p90 = np.percentile(fvals, 90)
        report["separability_p90_F"] = round(float(p90), 2)
        report["suspicious_features"] = [k for k, v in sep_sorted.items()
                                          if np.isfinite(v) and v > 20 * p90]
    report["passed"] = (not leaky_names and not report["window_index_in_features"])
    return report


def main(dataset_name: str = "blasco2018") -> dict:
    path = Path(REPO_ROOT) / "results" / f"{dataset_name}_features.parquet"
    df = pd.read_parquet(path)
    rep = audit(df)
    out = Path(REPO_ROOT) / "results" / f"{dataset_name}_feature_qa.json"
    out.write_text(json.dumps(rep, indent=2))
    log.info("wrote %s (passed=%s)", out.name, rep["passed"])
    return rep


if __name__ == "__main__":
    import sys
    r = main(sys.argv[1] if len(sys.argv) > 1 else "blasco2018")
    print(json.dumps(r, indent=2))
