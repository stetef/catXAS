"""Smoke tests for ``catxas.plot`` under the headless Agg backend.

These assert the plotting helpers run end-to-end on real groups and produce a
figure; they intentionally do not inspect pixels.
"""

import matplotlib.pyplot as plt

from catxas import plot as pfcts


def _first_sample_group(experiment):
    key = list(experiment.spectra.keys())[0]
    return experiment.spectra[key]["Absorption Spectra"]["mu Sample"]


def test_plot_xanes_runs_and_creates_figure(processed_experiment):
    group = _first_sample_group(processed_experiment)
    n_before = len(plt.get_fignums())
    pfcts.plot_XANES([group], 29170, 29250, spectra="flat", deriv=False, e0_line=False, filtering=False)
    assert len(plt.get_fignums()) > n_before
    plt.close("all")


def test_plot_ft_runs(processed_experiment):
    group = _first_sample_group(processed_experiment)
    pfcts.plot_FT([group], 0, 6)
    assert len(plt.get_fignums()) > 0
    plt.close("all")
