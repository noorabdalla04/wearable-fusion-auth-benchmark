"""Tests for the PhysioNet Exam-Stress loader (skipped if data absent)."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from wfab.loaders import exam_stress  # noqa: E402

DATA_ROOT = Path(__file__).resolve().parents[1] / "data" / "exam_stress"
HAVE_DATA = any(DATA_ROOT.rglob("S1/Final")) if DATA_ROOT.exists() else False


@pytest.mark.skipif(not HAVE_DATA, reason="Exam-Stress raw data not present")
def test_exam_stress_shape():
    ds = exam_stress.load(DATA_ROOT)
    assert len(ds.subjects) == 10
    assert set(ds.sessions) == {"midterm1", "midterm2", "final"}
    # cross-day axis: each subject in all 3 sessions
    from collections import Counter
    assert set(Counter(r.subject_id for r in ds).values()) == {3}
    for r in ds:
        assert set(r.channels) == {"ACC", "GSR", "PPG"}
        assert r.fs == 64.0
        assert r.n_samples > 64 * 10  # >=10 s
