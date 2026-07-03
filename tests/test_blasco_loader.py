"""Tests for the common schema and the Blasco 2018 loader.

The loader tests are skipped automatically if the raw data is not present, so the
suite passes in CI without committing data.
"""
import os
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from wfab.schema import Dataset, Recording  # noqa: E402
from wfab.loaders import blasco2018  # noqa: E402

DATA_ROOT = Path(__file__).resolve().parents[1] / "data" / "blasco2018"
HAVE_DATA = (DATA_ROOT / "LowCostSensorsBiometrics").is_dir()


# ---- schema tests (no data needed) ----

def test_recording_validates_equal_length():
    with pytest.raises(ValueError):
        Recording("s1", "rest", "rest", 100.0,
                   {"PPG": np.zeros(10), "ECG": np.zeros(9)})


def test_recording_rejects_noncanonical_channel():
    with pytest.raises(ValueError):
        Recording("s1", "rest", "rest", 100.0, {"BOGUS": np.zeros(10)})


def test_recording_properties():
    r = Recording("s1", "rest", "rest", 100.0, {"PPG": np.zeros(200), "ECG": np.ones(200)})
    assert r.n_samples == 200
    assert r.duration_s == pytest.approx(2.0)
    assert r.channels == ["ECG", "PPG"]


def test_dataset_accessors():
    recs = [Recording(f"s{i}", "rest", "rest", 100.0, {"PPG": np.zeros(100)},
                       dataset="d") for i in range(3)]
    ds = Dataset("d", recs)
    assert len(ds) == 3
    assert ds.subjects == ["s0", "s1", "s2"]
    assert ds.channel_coverage() == {"PPG": 3}


# ---- loader tests (need raw data) ----

@pytest.mark.skipif(not HAVE_DATA, reason="Blasco raw data not present")
def test_blasco_loads_expected_shape():
    ds = blasco2018.load(DATA_ROOT)
    # 25 subjects x 3 states = 75 recordings
    assert len(ds) == 75
    assert len(ds.subjects) == 25
    assert set(ds.conditions) == {"rest_seated", "walking", "rest_after_stroll"}
    # every recording has PPG, GSR, ECG at 100 Hz
    for r in ds:
        assert set(r.channels) == {"ECG", "GSR", "PPG"}
        assert r.fs == 100.0
        assert r.n_samples > 0


@pytest.mark.skipif(not HAVE_DATA, reason="Blasco raw data not present")
def test_blasco_subject_appears_in_all_states():
    ds = blasco2018.load(DATA_ROOT)
    from collections import Counter
    per_subject = Counter(r.subject_id for r in ds)
    # each subject should have exactly 3 recordings (one per state)
    assert set(per_subject.values()) == {3}
