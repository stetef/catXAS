"""Tests for ``catxas.mcrals`` -- initial-guess selection and MCR-ALS.

Driven by the same data and calls as ``notebooks/Example 5.1 - XAS Analysis -
MCR-ALS.ipynb``: seeds are picked from ``SnO2_TPR_NormXANES.csv`` with the
unique-spectra selectors, then ``run_mcr_als`` resolves the components. A small
column subset keeps the fit fast; ``perturb_initial=False`` keeps it
deterministic (the notebook perturbs initial guesses with unseeded noise).
"""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

# catxas.mcrals needs the optional 'notebooks' extra (pymcr, scikit-learn, ...);
# skip the whole module if those aren't installed rather than erroring.
mcrals = pytest.importorskip("catxas.mcrals")

REPO_ROOT = Path(__file__).resolve().parent.parent
NORM_XANES = REPO_ROOT / "sample results" / "SnO2_TPR_NormXANES.csv"

SELECTORS = [
    mcrals.get_unique_spectra_kmeans,
    mcrals.get_unique_spectra_pca,
    mcrals.get_unique_spectra_dissimilarity,
    mcrals.get_unique_spectra_simplisma,
]


@pytest.fixture(scope="module")
def xanes_subset():
    if not NORM_XANES.exists():
        pytest.skip("SnO2_TPR_NormXANES.csv not available")
    df = pd.read_csv(NORM_XANES, sep=",", index_col=0, header=None, skiprows=1)
    # Every 5th spectrum -> 10 spectra: enough to exercise a 3-component fit fast.
    return df.iloc[:, ::5].copy()


@pytest.mark.parametrize("selector", SELECTORS, ids=lambda f: f.__name__)
def test_unique_spectra_selectors(selector, xanes_subset):
    n = 3
    sub, meta = selector(xanes_subset, n)
    assert sub.shape == (xanes_subset.shape[0], n)
    idx = meta["column_indices"]
    assert len(idx) == n
    assert all(0 <= int(i) < xanes_subset.shape[1] for i in idx)
    assert len(meta["column_names"]) == n


def test_calculate_diversity(xanes_subset):
    diverse, _ = mcrals.get_unique_spectra_dissimilarity(xanes_subset, 3)
    identical = xanes_subset.iloc[:, [0, 0, 0]]
    d_diverse = mcrals.calculate_diversity(diverse)
    d_identical = mcrals.calculate_diversity(identical)
    # Three copies of one spectrum have zero diversity; a spread-out selection
    # is strictly more diverse.
    assert d_identical == pytest.approx(0.0, abs=1e-9)
    assert -1e-9 <= d_diverse <= 1.0 + 1e-9
    assert d_diverse > d_identical


def test_run_mcr_als_structure_and_constraints(xanes_subset):
    n_spectra = xanes_subset.shape[1]
    n_energy = xanes_subset.shape[0]
    res = mcrals.run_mcr_als(
        xanes_subset,
        initial_spectra_indices=[1, 5, 10],  # 1-based, per the API
        perturb_initial=False,
        fast_solve=True,
        max_iter=2000,
        verbose=False,
    )
    assert res["n_components"] == 3
    assert res["C"].shape == (n_spectra, 3)
    assert res["ST"].shape == (3, n_energy)
    assert res["R"].shape == (n_spectra, n_energy)
    assert res["D"].shape == (n_spectra, n_energy)
    # Reconstruction and residual identities hold by construction.
    np.testing.assert_allclose(res["D_reconstructed"], res["C"] @ res["ST"], atol=1e-12)
    np.testing.assert_allclose(res["R"], res["D"] - res["D_reconstructed"], atol=1e-12)
    # Default constraints enforce non-negativity on both matrices.
    assert (res["C"] >= -1e-9).all()
    assert (res["ST"] >= -1e-9).all()
    assert isinstance(res["converged"], (bool, np.bool_))
    assert len(res["err_history"]) >= 1
    np.testing.assert_array_equal(res["energy"], xanes_subset.index.values)


def test_run_mcr_als_rejects_out_of_range_index(xanes_subset):
    with pytest.raises(ValueError):
        mcrals.run_mcr_als(
            xanes_subset,
            initial_spectra_indices=[1, 999],
            perturb_initial=False,
            verbose=False,
        )


def test_run_mcr_als_captures_structure(xanes_subset):
    """A 3-component MCR fit from diverse seeds should reconstruct the data far
    better than a single mean spectrum -- i.e. the decomposition is real."""
    _, meta = mcrals.get_unique_spectra_dissimilarity(xanes_subset, 3)
    seeds = [int(i) + 1 for i in meta["column_indices"]]  # 0-based -> 1-based
    res = mcrals.run_mcr_als(
        xanes_subset,
        initial_spectra_indices=seeds,
        perturb_initial=False,
        fast_solve=True,
        max_iter=5000,
        tol_err_change=1e-15,
        tol_increase=10000,
        tol_n_increase=10**9,
        tol_n_above_min=10**9,
        verbose=False,
    )
    D = res["D"]
    mcr_rms = np.sqrt(np.mean(res["R"] ** 2))
    mean_rms = np.sqrt(np.mean((D - D.mean(axis=0, keepdims=True)) ** 2))
    assert mcr_rms < 0.5 * mean_rms


def test_create_results_dataframes(xanes_subset):
    res = mcrals.run_mcr_als(
        xanes_subset, initial_spectra_indices=[1, 5, 10],
        perturb_initial=False, fast_solve=True, max_iter=2000, verbose=False,
    )
    dfs = mcrals.create_results_dataframes(res)
    assert set(dfs) == {"df_C", "df_ST", "df_R"}
    assert list(dfs["df_C"].columns) == ["Component_1", "Component_2", "Component_3"]
    assert dfs["df_ST"].shape == (xanes_subset.shape[0], 3)
    np.testing.assert_array_equal(dfs["df_ST"].index.values, xanes_subset.index.values)


def test_save_mcr_results_writes_files(xanes_subset, tmp_path):
    res = mcrals.run_mcr_als(
        xanes_subset, initial_spectra_indices=[1, 5, 10],
        perturb_initial=False, fast_solve=True, max_iter=2000, verbose=False,
    )
    saved = mcrals.save_mcr_results(res, str(tmp_path), "TEST_MCR")
    assert set(saved) == {"concentrations", "spectra", "residuals", "summary"}
    for path in saved.values():
        assert Path(path).exists()
