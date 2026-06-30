"""Shared pytest fixtures and the canonical processing pipeline for catXAS tests.

The example notebooks drive ``catxas.experiment.Experiment`` through a fixed
sequence of steps; :func:`build_experiment` reproduces that sequence so both the
fast subset tests and the slow full-dataset regression run the *same* pipeline.
"""

import matplotlib

# Headless backend so plotting smoke-tests never try to open a window.
matplotlib.use("Agg")

from pathlib import Path

import pytest

from catxas import experiment as exp

DATA_DIR = Path(__file__).parent / "data"
RAW_DIR = DATA_DIR / "raw"
MS_FILE = DATA_DIR / "SnO2_TPR_MS.csv"
LV_FILE = DATA_DIR / "SnO2_TPR_LV.txt"
EXPECTED_DIR = DATA_DIR / "expected"

# Beamline data layout for the SSRL SnO2 H2-TPR Sn K-edge QEXAFS scans.
XAS_DATA_STRUCTURE = {
    "time stamp": True,
    "time on line": 5,
    "time format": "# This Scan Create Date:\t%m/%d/%Y %I:%M:%S %p ",
    "padded scan numbers": True,
    "column names": [
        "Encoder",
        "Energy",
        "ADC_01",
        "ADC_02",
        "ADC_03",
        "ADC_04",
        "ADC_05",
        "ADC_06",
        "ADC_07",
        "ADC_08",
    ],
    "energy column": "Energy",
    "sample numerator": "ADC_01",
    "sample denominator": "ADC_02",
    "sample ln": True,
    "sample invert": False,
    "reference numerator": "ADC_02",
    "reference denominator": "ADC_03",
    "reference ln": True,
    "reference invert": False,
    "is QEXAFS": False,
}

# Processing parameters, taken from notebook "2.1 ... Normalized XANES-EXAFS-FT".
NORM_PARAMS = {"pre1": -150, "pre2": -50, "norm1": 75, "norm2": 700, "nnorm": 2, "make_flat": True}
BKG_PARAMS = {
    "rbkg": 1,
    "nknots": None,
    "kmin": 0,
    "kmax": 13,
    "kweight": 1,
    "dk": 0.1,
    "win": "hanning",
    "nfft": 2048,
    "kstep": 0.05,
    "k_std": None,
    "chi_std": None,
    "nclamp": 2,
    "clamp_lo": 1,
    "clamp_hi": 100,
    "err_sigma": 1,
}
FT_PARAMS = {
    "rmax_out": 10,
    "kmin": 3,
    "kmax": 11,
    "kweight": 2,
    "dk": 5,
    "dk2": 5,
    "window": "haning",
    "nfft": 2048,
    "kstep": 0.05,
}

EDGE_ENERGY = 29200  # Sn K-edge (eV)
LCF_FIT = "Fit 2"
LCF_EMIN, LCF_EMAX = 29150, 29250


def build_experiment(raw_dir, ms_file=MS_FILE, lv_file=LV_FILE, do_lcf=True):
    """Run the full sample-side pipeline the notebooks demonstrate.

    import -> organize -> calculate mu -> calibrate e0 -> normalize ->
    EXAFS -> FT -> import process streams -> correlate -> (optional) LCF.

    Only the sample channel ('mu Sample') is normalized/transformed: the
    reference channel needs a separate e0 calibration that the notebooks do
    interactively, and the science of interest (LCF, EXAFS) is on the sample.
    """
    e = exp.Experiment("test")
    e.import_spectra(str(raw_dir), XAS_DATA_STRUCTURE)
    e.organize_RawData(remove_duplicates=True, remove_nan_inf=False, remove_zeros=False)
    e.calculate_spectra(sample_spectra=True, ref_spectra=True)
    e.find_sample_e0(EDGE_ENERGY, energy_range=20, use_mean=True, overlay=False)

    e.load_params("mu Sample", NORM_PARAMS)
    e.normalize_spectra("mu Sample")
    e.load_params("mu Sample", BKG_PARAMS)
    e.extract_EXAFS_spectra("mu Sample")
    e.load_params("mu Sample", FT_PARAMS)
    e.FT_EXAFS_spectra("mu Sample")

    e.import_massspec(str(ms_file))
    e.import_labview(str(lv_file))
    e.correlate_process_params()

    if do_lcf:
        keys = list(e.spectra.keys())
        basis = []
        for bk in (keys[0], keys[len(keys) // 2], keys[-1]):
            group = e.spectra[bk]["Absorption Spectra"]["mu Sample"]
            group.name = bk
            basis.append(group)
        e.load_lcf_basis(basis, LCF_FIT)
        e.fit_LCF(LCF_FIT, LCF_EMIN, LCF_EMAX, weights=None, minvals=0, maxvals=1, arrayname="flat", sum_to_one=True)
        e.lcf_report(LCF_FIT)
    return e


# ---- fixtures -------------------------------------------------------------


@pytest.fixture(scope="session")
def raw_dir():
    return RAW_DIR


@pytest.fixture(scope="session")
def xas_data_structure():
    return dict(XAS_DATA_STRUCTURE)


@pytest.fixture(scope="session")
def processed_experiment():
    """The 5-spectrum subset run through the full pipeline once per session."""
    return build_experiment(RAW_DIR)


@pytest.fixture
def fresh_imported_experiment():
    """A freshly imported (not normalized) experiment, for mutation tests."""
    e = exp.Experiment("fresh")
    e.import_spectra(str(RAW_DIR), XAS_DATA_STRUCTURE)
    e.organize_RawData(remove_duplicates=True, remove_nan_inf=False, remove_zeros=False)
    e.calculate_spectra(sample_spectra=True, ref_spectra=True)
    return e
