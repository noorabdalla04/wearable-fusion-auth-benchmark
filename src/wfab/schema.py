"""Common, data-source-agnostic schema for multi-signal wearable recordings.

Every dataset loader maps its raw files into this one representation so that all
downstream code (cleaning, feature extraction, evaluation) is dataset-independent.

Design
------
A dataset is a collection of ``Recording`` objects. One ``Recording`` is a single
continuous capture from one subject in one session/condition, holding one or more
time-aligned signal channels sampled at a known rate.

The identity axes that matter for leakage-free evaluation are explicit fields:

- ``subject_id`` : the person (never split across train/test).
- ``session_id`` : a recording occasion. For single-day datasets with multiple
  activity states, ``session_id`` encodes the *condition* (e.g. "rest", "walk").
  For true multi-day datasets it encodes the *day/visit*. The evaluation harness
  decides "within-session" vs "cross-session" by comparing this field.
- ``condition`` : human-readable activity/state label (redundant with session_id
  for single-day sets, but kept separate so cross-activity and cross-day can be
  distinguished in analysis).

Signals are stored as a dict ``{channel_name: np.ndarray}`` at a single common
``fs`` (Hz). Channel names are canonical: ``PPG``, ``ECG``, ``ACC`` (or ``ACC_X`` etc.),
``GSR``. A loader only populates the channels a dataset actually provides.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterator

import numpy as np

CANONICAL_CHANNELS = {"PPG", "ECG", "GSR", "ACC", "ACC_X", "ACC_Y", "ACC_Z", "TEMP", "EDA"}


@dataclass
class Recording:
    """One continuous multi-signal capture from one subject in one session/condition."""

    subject_id: str
    session_id: str
    condition: str
    fs: float                              # sampling rate in Hz (common to all channels)
    signals: dict[str, np.ndarray]         # channel_name -> 1D float array
    dataset: str = ""                      # source dataset name
    meta: dict = field(default_factory=dict)  # age, sex, device, provenance, etc.

    def __post_init__(self) -> None:
        if self.fs <= 0:
            raise ValueError(f"fs must be positive, got {self.fs}")
        if not self.signals:
            raise ValueError("Recording has no signals")
        lengths = {name: len(arr) for name, arr in self.signals.items()}
        if len(set(lengths.values())) != 1:
            raise ValueError(f"channels must be equal length (time-aligned); got {lengths}")
        for name in self.signals:
            if name not in CANONICAL_CHANNELS:
                raise ValueError(f"non-canonical channel '{name}'; allowed: {sorted(CANONICAL_CHANNELS)}")
            self.signals[name] = np.asarray(self.signals[name], dtype=float)

    @property
    def channels(self) -> list[str]:
        return sorted(self.signals)

    @property
    def n_samples(self) -> int:
        return len(next(iter(self.signals.values())))

    @property
    def duration_s(self) -> float:
        return self.n_samples / self.fs

    def __repr__(self) -> str:
        return (f"Recording(dataset={self.dataset!r}, subject={self.subject_id!r}, "
                f"session={self.session_id!r}, condition={self.condition!r}, "
                f"fs={self.fs}, channels={self.channels}, dur={self.duration_s:.0f}s)")


class Dataset:
    """A collection of Recordings from one source, with convenience accessors."""

    def __init__(self, name: str, recordings: list[Recording]):
        self.name = name
        self.recordings = recordings

    def __len__(self) -> int:
        return len(self.recordings)

    def __iter__(self) -> Iterator[Recording]:
        return iter(self.recordings)

    @property
    def subjects(self) -> list[str]:
        return sorted({r.subject_id for r in self.recordings})

    @property
    def sessions(self) -> list[str]:
        return sorted({r.session_id for r in self.recordings})

    @property
    def conditions(self) -> list[str]:
        return sorted({r.condition for r in self.recordings})

    def channel_coverage(self) -> dict[str, int]:
        """How many recordings contain each channel."""
        cov: dict[str, int] = {}
        for r in self.recordings:
            for ch in r.channels:
                cov[ch] = cov.get(ch, 0) + 1
        return dict(sorted(cov.items()))

    def summary(self) -> dict:
        return {
            "name": self.name,
            "n_recordings": len(self.recordings),
            "n_subjects": len(self.subjects),
            "sessions": self.sessions,
            "conditions": self.conditions,
            "channel_coverage": self.channel_coverage(),
            "fs": sorted({r.fs for r in self.recordings}),
        }
