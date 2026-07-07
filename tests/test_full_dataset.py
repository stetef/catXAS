"""Slow regression: the full 50-spectrum dataset through the same pipeline.

Deselected by default (``addopts = -m 'not slow'``); run explicitly with::

    uv run pytest -m slow

It scales the subset's property checks to the whole experiment and pins the LCF
amplitudes against a committed golden generated from the same pipeline. Note the
golden is produced by :func:`conftest.build_experiment`, not the interactive
notebooks, so it is self-consistent with this test rather than tied to the
notebook-generated ``sample results/`` files.
"""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from conftest import EXPECTED_DIR, build_experiment

REPO_ROOT = Path(__file__).resolve().parent.parent
FULL_RAW = REPO_ROOT / "sample data" / "Raw Data"
FULL_MS = REPO_ROOT / "sample data" / "SnO2_TPR_MS.csv"
FULL_LV = REPO_ROOT / "sample data" / "SnO2_TPR_LV.txt"

pytestmark = pytest.mark.slow


@pytest.fixture(scope="module")
def full_experiment():
    return build_experiment(FULL_RAW, ms_file=FULL_MS, lv_file=FULL_LV)


def test_all_fifty_spectra_loaded(full_experiment):
    assert len(full_experiment.spectra) == 50


def test_time_on_stream_monotonic(full_experiment):
    tos = full_experiment.summary["XAS Spectra Files"]["TOS [s]"].to_numpy()
    assert tos[0] == 0.0
    assert np.all(np.diff(tos) > 0)


def test_all_e0_near_edge(full_experiment):
    for key in full_experiment.spectra:
        e0 = full_experiment.spectra[key]["Absorption Spectra"]["mu Sample"].e0
        assert 29190 < e0 < 29210


def test_lcf_weights_sum_to_one(full_experiment):
    fs = full_experiment.analysis["LCF"]["Fit 2"]["Fit Summary"]
    assert len(fs) == 50
    assert fs["Sum Amp"].to_numpy() == pytest.approx(1.0, abs=0.02)


def test_overall_reduction_progression(full_experiment):
    """First scan should be dominantly the oxidized endmember, the last scan
    dominantly the reduced one -- net reduction across the TPR."""
    fs = full_experiment.analysis["LCF"]["Fit 2"]["Fit Summary"]
    assert fs.loc[0, "Amp1"] > 0.9
    assert fs.loc[len(fs) - 1, "Amp3"] > 0.9


def test_lcf_amplitudes_match_full_golden(full_experiment):
    golden_path = EXPECTED_DIR / "lcf_fit_summary_full.csv"
    if not golden_path.exists():
        pytest.skip("full-dataset golden not generated yet")
    golden = pd.read_csv(golden_path)
    fs = full_experiment.analysis["LCF"]["Fit 2"]["Fit Summary"]

    # Compare the build-stable quantities against the golden: the total
    # amplitude, the oxidized-endmember fraction (Amp1, well-conditioned), and
    # the combined reduced fraction (Amp2 + Amp3). The Amp2/Amp3 split itself is
    # NOT pinned: the middle and last basis members are nearly collinear, so for
    # the intermediate scans that split is ill-conditioned and BLAS/build
    # sensitive (differs by up to ~0.5 across environments) while its sum stays
    # stable to <1e-3. See test_experiment_pipeline for the same rationale.
    np.testing.assert_allclose(fs["Sum Amp"].to_numpy(), golden["Sum Amp"].to_numpy(), atol=1e-3)
    np.testing.assert_allclose(fs["Amp1"].to_numpy(), golden["Amp1"].to_numpy(), atol=1e-3)
    np.testing.assert_allclose(
        (fs["Amp2"] + fs["Amp3"]).to_numpy(),
        (golden["Amp2"] + golden["Amp3"]).to_numpy(),
        atol=1e-3,
    )
