"""Integration tests: the example-notebook pipeline on the 5-spectrum subset.

These assert physical/structural invariants ("properties") plus a light golden
snapshot of the LCF amplitudes. Strict numeric golden comparison against the
full committed ``sample results/`` lives in the slow ``test_full_dataset``.
"""

import numpy as np
import pandas as pd
import pytest

from conftest import EXPECTED_DIR

SCAN_PREFIX = "20210614_SnO2_H2_TPR_Sn_EXAFS_92.tra_"
EXPECTED_TOS = [0.0, 1269.0, 2541.0, 3814.0, 5190.0]


def sample_group(experiment, key):
    return experiment.spectra[key]["Absorption Spectra"]["mu Sample"]


# ---- import / organize / calculate ---------------------------------------


def test_import_loads_all_subset_spectra(processed_experiment):
    assert len(processed_experiment.spectra) == 5


def test_spectra_sorted_by_acquisition_time(processed_experiment):
    keys = list(processed_experiment.spectra.keys())
    scan_numbers = [int(k.replace(SCAN_PREFIX, "")) for k in keys]
    assert scan_numbers == sorted(scan_numbers)
    assert scan_numbers == [1, 13, 25, 37, 50]


def test_time_on_stream_monotonic_from_zero(processed_experiment):
    tos = processed_experiment.summary["XAS Spectra Files"]["TOS [s]"].tolist()
    assert tos[0] == 0.0
    assert tos == pytest.approx(EXPECTED_TOS)
    assert all(np.diff(tos) > 0)


def test_calculate_spectra_produces_mu(processed_experiment):
    key = list(processed_experiment.spectra.keys())[0]
    g = sample_group(processed_experiment, key)
    assert g.energy.shape == g.mu.shape
    assert g.energy.shape[0] > 1000
    assert np.all(np.isfinite(g.mu))


# ---- calibration / normalization -----------------------------------------


def test_e0_near_sn_k_edge(processed_experiment):
    for key in processed_experiment.spectra:
        e0 = sample_group(processed_experiment, key).e0
        assert 29195 < e0 < 29207


def test_normalization_edge_step_and_flat(processed_experiment):
    key = list(processed_experiment.spectra.keys())[0]
    g = sample_group(processed_experiment, key)
    assert hasattr(g, "norm") and hasattr(g, "flat")
    assert 0.5 < g.edge_step < 2.0
    above_edge = g.energy > (g.e0 + 100)
    assert np.mean(g.flat[above_edge]) == pytest.approx(1.0, abs=0.05)


# ---- EXAFS / FT -----------------------------------------------------------


def test_exafs_extraction(processed_experiment):
    key = list(processed_experiment.spectra.keys())[0]
    g = sample_group(processed_experiment, key)
    assert hasattr(g, "k") and hasattr(g, "chi")
    assert g.k.shape == g.chi.shape
    assert g.k.max() > 10  # kmax=13 requested


def test_fourier_transform_first_shell_peak(processed_experiment):
    key = list(processed_experiment.spectra.keys())[0]
    g = sample_group(processed_experiment, key)
    assert hasattr(g, "chir_mag")
    peak_r = g.r[np.argmax(g.chir_mag)]
    assert 1.0 < peak_r < 3.0  # Sn-O / Sn-Sn first shell region


# ---- process-stream correlation -------------------------------------------


def test_process_correlation_shape_and_columns(processed_experiment):
    pp = processed_experiment.summary["XAS Spectra Process Params"]
    assert pp.shape[0] == 5
    for col in ("File Name", "TOS [s]", "H2"):
        assert col in pp.columns
    assert pp["TOS [s]"].notna().all()


# ---- LCF ------------------------------------------------------------------


def test_lcf_summary_basics(processed_experiment):
    fs = processed_experiment.analysis["LCF"]["Fit 2"]["Fit Summary"]
    assert len(fs) == 5
    assert fs["Sum Amp"].to_numpy() == pytest.approx(1.0, abs=0.01)


def test_lcf_basis_members_self_fit(processed_experiment):
    """Basis = first/middle/last scan; each should recover ~100% of itself."""
    fs = processed_experiment.analysis["LCF"]["Fit 2"]["Fit Summary"]
    assert fs.loc[0, "Amp1"] == pytest.approx(1.0, abs=1e-3)
    assert fs.loc[2, "Amp2"] == pytest.approx(1.0, abs=1e-3)
    assert fs.loc[4, "Amp3"] == pytest.approx(1.0, abs=1e-3)
    # Self-fits are essentially exact.
    assert fs.loc[0, "Chi2"] < 1e-6


def test_lcf_reduction_trend_is_monotonic(processed_experiment):
    """Oxidized endmember (Amp1) should fall and reduced (Amp3) rise across
    the temperature-programmed reduction -- the physics, inferred from 5 scans.
    """
    fs = processed_experiment.analysis["LCF"]["Fit 2"]["Fit Summary"]
    amp1 = fs["Amp1"].to_numpy()
    amp3 = fs["Amp3"].to_numpy()
    assert np.all(np.diff(amp1) <= 1e-6)
    assert np.all(np.diff(amp3) >= -1e-6)


# ---- light golden snapshot ------------------------------------------------


def test_lcf_amplitudes_match_golden(processed_experiment):
    golden_path = EXPECTED_DIR / "lcf_fit_summary.csv"
    if not golden_path.exists():
        pytest.skip("golden snapshot not generated yet")
    golden = pd.read_csv(golden_path)
    fs = processed_experiment.analysis["LCF"]["Fit 2"]["Fit Summary"]
    for col in ("Amp1", "Amp2", "Amp3", "Sum Amp"):
        np.testing.assert_allclose(fs[col].to_numpy(), golden[col].to_numpy(), atol=1e-4)
