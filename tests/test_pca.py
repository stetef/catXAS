"""Tests for ``catxas.pca`` -- PCA / TruncatedSVD of a XANES spectra matrix.

Driven by the same data and calls as ``notebooks/Example 5.0 - XAS Analysis -
PCA.ipynb``: the committed ``sample results/SnO2_TPR_NormXANES.csv`` (energy on
the index, one column per spectrum) is decomposed with ``perform_pca_analysis``.
The interactive range-selection widget is skipped; we feed the full matrix.
"""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

# catxas.pca needs the optional 'notebooks' extra (scikit-learn, kneed, ...);
# skip the whole module if those aren't installed rather than erroring.
pca = pytest.importorskip("catxas.pca")

REPO_ROOT = Path(__file__).resolve().parent.parent
NORM_XANES = REPO_ROOT / "sample results" / "SnO2_TPR_NormXANES.csv"


@pytest.fixture(scope="module")
def xanes_df():
    if not NORM_XANES.exists():
        pytest.skip("SnO2_TPR_NormXANES.csv not available")
    # Loaded exactly as the Example 5.0 notebook does.
    return pd.read_csv(NORM_XANES, sep=",", index_col=0, header=None, skiprows=1)


def test_pca_result_structure(xanes_df):
    n_energy, n_spectra = xanes_df.shape
    r = pca.perform_pca_analysis(xanes_df, mean_center=True, n_components=None)
    assert r["mean_centered"] is True
    # scores: spectra x components; eigenspectra: components x energy
    assert r["scores"].shape == (n_spectra, n_spectra)
    assert r["eigenspectra"].shape == (n_spectra, n_energy)
    for key in ("df_scores", "df_eigenspectra", "df_cve",
                "explained_variance_ratio", "covariance", "model"):
        assert key in r


def test_pca_variance_is_ordered_and_complete(xanes_df):
    r = pca.perform_pca_analysis(xanes_df, mean_center=True, n_components=None)
    evr = r["explained_variance_ratio"]
    # Explained variance is non-increasing across components ...
    assert np.all(np.diff(evr) <= 1e-12)
    # ... the cumulative curve is monotonic and (full rank) reaches 1.
    assert np.all(np.diff(r["cve"]) >= -1e-12)
    assert r["cve"][-1] == pytest.approx(1.0, abs=1e-6)


def test_pca_full_reconstruction_recovers_data(xanes_df):
    r = pca.perform_pca_analysis(xanes_df, mean_center=True, n_components=None)
    # scores @ eigenspectra + mean should rebuild the (transposed) input.
    recon = r["scores"] @ r["eigenspectra"] + r["model"].mean_
    np.testing.assert_allclose(recon, xanes_df.T.values, atol=1e-8)


def test_pca_n_components_truncates(xanes_df):
    r = pca.perform_pca_analysis(xanes_df, mean_center=True, n_components=4)
    assert r["scores"].shape[1] == 4
    assert r["eigenspectra"].shape[0] == 4


def test_svd_path_without_mean_centering(xanes_df):
    n_energy, n_spectra = xanes_df.shape
    r = pca.perform_pca_analysis(xanes_df, mean_center=False, n_components=5)
    assert r["mean_centered"] is False
    assert r["scores"].shape == (n_spectra, 5)
    assert r["eigenspectra"].shape == (5, n_energy)


def test_save_pca_results_writes_files(xanes_df, tmp_path):
    r = pca.perform_pca_analysis(xanes_df, mean_center=True, n_components=5)
    saved = pca.save_pca_results(r, str(tmp_path), "TEST_PCA")
    assert set(saved) == {"eigenspectra", "cve", "scores"}
    for path in saved.values():
        assert Path(path).exists()
    # Mean-centered runs carry the mean spectrum alongside the eigenspectra.
    eig = pd.read_csv(saved["eigenspectra"], index_col=0)
    assert "PCA_Mean" in eig.columns
