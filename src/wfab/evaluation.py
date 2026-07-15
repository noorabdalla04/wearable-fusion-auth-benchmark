"""Verification-style evaluation harness with within- vs cross-session protocols.

Task
----
Biometric *verification*: given a probe window and a claimed identity, decide
genuine (same person) vs impostor (different person). We report EER and AUC.

We use a similarity-score formulation that is model-light and interpretable:

1. Select a **signal combination** (subset of feature-prefixes, e.g. {"ppg"} or
   {"ppg","ecg"}). Only windows whose required channels are all good are used
   (via the ``ok_<CH>`` flags), and only that combination's feature columns.
2. Build **enrolment templates** per subject from *train* windows (mean feature
   vector after standardisation).
3. For each *test* (probe) window, compute a similarity score to every subject's
   template. A genuine trial = probe vs its own subject's template; impostor
   trials = probe vs every other subject's template.
4. Pool all genuine and impostor scores, sweep the threshold, report EER + AUC.

Protocols
---------
- ``within_session``: train and test windows are BOTH from the same session, but
  disjoint (a per-session split of windows). Reported per session, then averaged.
  This is the "flattering" number the literature usually reports.
- ``cross_session``: enrol on one session, test on a DIFFERENT session. This is the
  honest number. With Blasco's 3 activity states this is cross-ACTIVITY; with a
  multi-day dataset it is cross-DAY.

Leakage guards (asserted at runtime)
------------------------------------
- A subject's template is never built from windows that also appear as its probes
  (within-session uses a disjoint window split).
- Standardisation statistics are fit on TRAIN windows only, applied to test.
- Splits are subject-aware: all subjects appear in both enrol and test (closed-set
  verification), but never the same *windows*.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.metrics import roc_curve, auc as sk_auc
from sklearn.ensemble import RandomForestClassifier

from .build_features import LABEL_COLS

# map a combination token to the feature-column prefix and the required channel flag
_PREFIX = {"ppg": ("ppg_", "ok_PPG"), "ecg": ("ecg_", "ok_ECG"),
           "gsr": ("gsr_", "ok_GSR"), "acc": ("acc_", "ok_ACC")}


@dataclass
class EvalResult:
    protocol: str
    combination: tuple[str, ...]
    eer: float
    auc: float
    n_genuine: int
    n_impostor: int
    n_subjects: int
    detail: dict


def _combo_columns(df: pd.DataFrame, combo: tuple[str, ...]) -> list[str]:
    cols = []
    for tok in combo:
        prefix = _PREFIX[tok][0]
        cols += [c for c in df.columns if c.startswith(prefix) and c not in LABEL_COLS]
    return cols


def _combo_mask(df: pd.DataFrame, combo: tuple[str, ...]) -> np.ndarray:
    """Rows where every required channel for the combination is good."""
    mask = np.ones(len(df), dtype=bool)
    for tok in combo:
        flag = _PREFIX[tok][1]
        if flag in df.columns:
            mask &= df[flag].astype(bool).values
    return mask


def _standardize(train: np.ndarray, test: np.ndarray):
    mu = np.nanmean(train, axis=0)
    sd = np.nanstd(train, axis=0)
    sd[sd < 1e-9] = 1.0
    ztr = (train - mu) / sd
    zte = (test - mu) / sd
    # impute residual NaNs with the train mean (0 after standardisation)
    ztr = np.nan_to_num(ztr, nan=0.0)
    zte = np.nan_to_num(zte, nan=0.0)
    return ztr, zte


def _eer_auc(genuine: np.ndarray, impostor: np.ndarray) -> tuple[float, float]:
    """EER and AUC from genuine/impostor similarity scores (higher = more genuine)."""
    y = np.concatenate([np.ones_like(genuine), np.zeros_like(impostor)])
    s = np.concatenate([genuine, impostor])
    fpr, tpr, _ = roc_curve(y, s)
    fnr = 1 - tpr
    # EER = point where fpr ~= fnr
    idx = np.nanargmin(np.abs(fpr - fnr))
    eer = float((fpr[idx] + fnr[idx]) / 2)
    return eer, float(sk_auc(fpr, tpr))


def _similarity(probe: np.ndarray, template: np.ndarray) -> float:
    """Negative Euclidean distance in standardised feature space (higher = closer)."""
    return -float(np.linalg.norm(probe - template))


def _score_split(enrol: pd.DataFrame, probe: pd.DataFrame, feat_cols: list[str],
                 model: str = "template", seed: int = 0):
    """Score probe windows against enrolled identities. Returns (genuine, impostor).

    model="template": negative-Euclidean distance to each subject's mean feature
        vector in standardised space. Conservative, interpretable, no supervised fit.
    model="rf": supervised RandomForest(features -> subject) fit on enrol windows;
        verification score = predicted probability of the claimed subject. This is the
        family of method that produces the "flattering" within-session numbers.

    Both are closed-set: every enrolled subject is a candidate identity for every probe.
    """
    Xtr = enrol[feat_cols].values.astype(float)
    Xte = probe[feat_cols].values.astype(float)
    Xtr, Xte = _standardize(Xtr, Xte)
    subjects = sorted(enrol.subject_id.unique())
    probe_subj = probe.subject_id.values
    genuine, impostor = [], []

    if model == "template":
        templates = {s: Xtr[enrol.subject_id.values == s].mean(axis=0) for s in subjects}
        for i in range(len(Xte)):
            ps = probe_subj[i]
            for s, tmpl in templates.items():
                sc = _similarity(Xte[i], tmpl)
                (genuine if s == ps else impostor).append(sc)
    elif model == "rf":
        clf = RandomForestClassifier(n_estimators=200, random_state=seed, n_jobs=-1)
        clf.fit(Xtr, enrol.subject_id.values)
        classes = list(clf.classes_)
        proba = clf.predict_proba(Xte)
        cls_idx = {s: j for j, s in enumerate(classes)}
        for i in range(len(Xte)):
            ps = probe_subj[i]
            for s in subjects:
                if s not in cls_idx:
                    continue
                sc = float(proba[i, cls_idx[s]])
                (genuine if s == ps else impostor).append(sc)
    else:
        raise ValueError(f"unknown model {model!r}")
    return np.array(genuine), np.array(impostor)


def within_session(df: pd.DataFrame, combo: tuple[str, ...], seed: int,
                   test_frac: float = 0.5, model: str = "template",
                   split: str = "blocked") -> EvalResult:
    """Enrol/probe split WITHIN each session; average EER/AUC across sessions.

    split="blocked" (default, LEAK-FREE): order each subject's windows by
        window_index (time) and enrol on the earlier fraction, probe on the
        later fraction. Adjacent windows from one continuous recording are
        autocorrelated; a time-blocked split keeps near-duplicate neighbours
        on the SAME side of the enrol/probe boundary.
    split="random": shuffle windows before the 50/50 cut. This LEAKS temporal
        neighbours across the split and inflates within-session accuracy; kept
        only to quantify that inflation (see robustness.split_leakage_check).
    """
    rng = np.random.default_rng(seed)
    feat_cols = _combo_columns(df, combo)
    d = df[_combo_mask(df, combo)]
    eers, aucs, ng, ni, details = [], [], 0, 0, {}
    for sess in sorted(d.session_id.unique()):
        ds = d[d.session_id == sess]
        # disjoint per-subject window split
        enrol_idx, probe_idx = [], []
        for s in ds.subject_id.unique():
            sub = ds[ds.subject_id == s]
            if len(sub) < 2:
                continue
            if split == "random":
                idx = sub.index.to_numpy()
                rng.shuffle(idx)
            else:  # blocked (time-ordered, leak-free)
                idx = sub.sort_values("window_index").index.to_numpy()
            cut = max(1, int(len(idx) * (1 - test_frac)))
            enrol_idx += list(idx[:cut]); probe_idx += list(idx[cut:])
        enrol, probe = ds.loc[enrol_idx], ds.loc[probe_idx]
        # leakage guard: no window in both
        assert set(enrol.index).isdisjoint(set(probe.index)), "window leak within session"
        if enrol.subject_id.nunique() < 2 or len(probe) == 0:
            continue
        g, imp = _score_split(enrol, probe, feat_cols, model=model, seed=seed)
        if len(g) == 0 or len(imp) == 0:
            continue
        eer, a = _eer_auc(g, imp)
        eers.append(eer); aucs.append(a); ng += len(g); ni += len(imp)
        details[sess] = {"eer": round(eer, 4), "auc": round(a, 4),
                         "n_subjects": int(enrol.subject_id.nunique())}
    return EvalResult("within_session", combo, float(np.mean(eers)), float(np.mean(aucs)),
                      ng, ni, d.subject_id.nunique(), details)


def cross_session(df: pd.DataFrame, combo: tuple[str, ...], seed: int,
                  model: str = "template") -> EvalResult:
    """Enrol on one session, probe on a DIFFERENT session; average over all ordered pairs."""
    feat_cols = _combo_columns(df, combo)
    d = df[_combo_mask(df, combo)]
    sessions = sorted(d.session_id.unique())
    eers, aucs, ng, ni, details = [], [], 0, 0, {}
    for enrol_sess in sessions:
        for probe_sess in sessions:
            if enrol_sess == probe_sess:
                continue
            enrol = d[d.session_id == enrol_sess]
            probe = d[d.session_id == probe_sess]
            # only subjects present in BOTH sessions (closed-set)
            common = set(enrol.subject_id) & set(probe.subject_id)
            if len(common) < 2:
                continue
            enrol = enrol[enrol.subject_id.isin(common)]
            probe = probe[probe.subject_id.isin(common)]
            g, imp = _score_split(enrol, probe, feat_cols, model=model, seed=seed)
            if len(g) == 0 or len(imp) == 0:
                continue
            eer, a = _eer_auc(g, imp)
            eers.append(eer); aucs.append(a); ng += len(g); ni += len(imp)
            details[f"{enrol_sess}->{probe_sess}"] = {
                "eer": round(eer, 4), "auc": round(a, 4), "n_subjects": len(common)}
    return EvalResult("cross_session", combo, float(np.mean(eers)), float(np.mean(aucs)),
                      ng, ni, d.subject_id.nunique(), details)
