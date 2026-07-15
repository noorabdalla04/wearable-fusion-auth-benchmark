"""Regenerate the three publication figures from the frozen benchmark CSVs.

Uses matplotlib only (no house-style dependency) so the repo is self-contained.
Run: python -m wfab.make_figures
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from .repro import REPO_ROOT, get_logger

log = get_logger(__name__)
FOCAL, CROSS = "#2166ac", "#b2182b"
TOUCH, FACE = 2e-5, 1e-6


def _load(ds):
    return pd.read_csv(Path(REPO_ROOT) / "results" / f"{ds}_benchmark.csv")


def _wc(df):
    w = df[df.protocol == "within_session"].set_index("combination").eer
    c = df[df.protocol == "cross_session"].set_index("combination").eer
    order = w.sort_values().index.tolist()
    return w.reindex(order), c.reindex(order)


def fig1(rf1, rf2, out):
    w1, c1 = _wc(rf1); w2, c2 = _wc(rf2)
    fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.6))
    for ax, (w, c, t) in zip(axes, [(w1, c1, "Blasco 2018  (PPG+ECG+GSR, cross-activity)"),
                                     (w2, c2, "Exam-Stress  (PPG+GSR+ACC, cross-day)")]):
        y = np.arange(len(w))
        ax.hlines(y, w.values, c.values, color="#bbb", lw=1.5, zorder=1)
        ax.scatter(w.values, y, color=FOCAL, s=34, zorder=3, label="within-session")
        ax.scatter(c.values, y, color=CROSS, s=34, zorder=3, label="cross-session")
        ax.set_yticks(y); ax.set_yticklabels(w.index)
        ax.set_xlim(0, 0.5); ax.set_xlabel("Equal error rate (EER)")
        ax.set_title(t, fontsize=8, loc="left")
    axes[0].legend(loc="center right", frameon=False, fontsize=7)
    axes[1].set_yticklabels([])
    fig.suptitle("Within-session accuracy does not transfer across sessions",
                 fontsize=10, weight="bold", y=1.02)
    fig.tight_layout(); fig.savefig(out, dpi=300, bbox_inches="tight"); plt.close(fig)


def fig2(rf1, rf2, out):
    w1, c1 = _wc(rf1); _, c2 = _wc(rf2)
    pts = [("Face ID", FACE, "#888"), ("Touch ID", TOUCH, "#888"),
           ("Fusion, within-session\n(Blasco, best)", float(w1.min()), FOCAL),
           ("Fusion, cross-activity\n(Blasco, best)", float(c1.min()), CROSS),
           ("Fusion, cross-day\n(Exam-Stress, best)", float(c2.min()), CROSS)]
    labels = [p[0] for p in pts]; vals = [p[1] for p in pts]; cols = [p[2] for p in pts]
    y = np.arange(len(pts))[::-1]
    fig, ax = plt.subplots(figsize=(6.8, 3.6))
    ax.hlines(y, 1e-6, vals, color="#ccc", lw=1.0, zorder=0)
    ax.scatter(vals, y, color=cols, s=70, zorder=3)
    for yi, v, col in zip(y, vals, cols):
        txt = f"{v:.0e}".replace("e-0", "e-") if v < 1e-3 else f"{v:.2f}"
        ax.annotate(txt, (v, yi), xytext=(0, 9), textcoords="offset points",
                    ha="center", fontsize=6.8, color=col)
    ax.set_xscale("log"); ax.set_xlim(5e-7, 1.3); ax.set_ylim(-0.6, len(pts) - 0.4)
    ax.set_yticks(y); ax.set_yticklabels(labels, fontsize=7.5)
    ax.set_xlabel("False-accept rate at the equal-error operating point  (log scale)")
    ax.set_xticks([1e-6, 1e-5, 1e-4, 1e-3, 1e-2, 1e-1, 1])
    ax.set_xticklabels(["1e-6", "1e-5", "1e-4", "1e-3", "1e-2", "0.1", "1"])
    ax.axvspan(5e-7, TOUCH, color="#e8f0e8", zorder=-1)
    ax.text(np.sqrt(5e-7 * TOUCH), -0.45, "device-unlock\nregime", ha="center",
            va="bottom", fontsize=6.3, color="#4a7a4a", style="italic")
    fig.suptitle("Honest cross-session fusion is 4 to 5 orders of magnitude short of a real device unlock",
                 fontsize=8.8, weight="bold", y=1.03)
    fig.tight_layout(); fig.savefig(out, dpi=300, bbox_inches="tight"); plt.close(fig)


def fig3(rf1, rf2, out):
    def singles(df, proto):
        return df[(df.n_signals == 1) & (df.protocol == proto)].set_index("combination").eer
    w1, c1 = singles(rf1, "within_session"), singles(rf1, "cross_session")
    w2, c2 = singles(rf2, "within_session"), singles(rf2, "cross_session")
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.2), sharey=True)
    for ax, (w, c, t) in zip(axes, [(w1, c1, "Blasco (cross-activity)"),
                                    (w2, c2, "Exam-Stress (cross-day)")]):
        sigs = list(w.index); x = np.arange(len(sigs))
        ax.bar(x - 0.19, [w[s] for s in sigs], 0.36, label="within-session", color="#cfd8dc", edgecolor="#607d8b")
        ax.bar(x + 0.19, [c[s] for s in sigs], 0.36, label="cross-session", color=CROSS, edgecolor="#333")
        ax.axhline(0.5, color="#e0e0e0", lw=0.8, zorder=0)
        ax.text(len(sigs) - 0.5, 0.5, "chance", fontsize=6, color="#999", va="bottom", ha="right")
        ax.set_xticks(x); ax.set_xticklabels([s.upper() for s in sigs])
        ax.set_ylim(0, 0.55); ax.set_title(t, fontsize=8.5)
    axes[0].set_ylabel("EER"); axes[0].legend(frameon=False, fontsize=7, loc="upper left")
    fig.suptitle("No single signal survives the move across sessions",
                 fontsize=9.5, weight="bold", y=1.02)
    fig.tight_layout(); fig.savefig(out, dpi=300, bbox_inches="tight"); plt.close(fig)


def main():
    rf1 = _load("blasco2018"); rf2 = _load("exam_stress")
    rf1 = rf1[rf1.model == "rf"]; rf2 = rf2[rf2.model == "rf"]
    fdir = Path(REPO_ROOT) / "figures"; fdir.mkdir(exist_ok=True)
    fig1(rf1, rf2, fdir / "fig1_collapse.png")
    fig2(rf1, rf2, fdir / "fig2_security_bar.png")
    fig3(rf1, rf2, fdir / "fig3_per_signal.png")
    log.info("wrote 3 figures to %s", fdir)


if __name__ == "__main__":
    main()
