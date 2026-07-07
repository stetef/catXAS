"""Unit tests for ``catxas.xas`` math helpers."""

import numpy as np
import pytest

from catxas import xas as xfcts


def test_calc_mu_ratio_without_log():
    num = np.array([2.0, 4.0, 8.0])
    den = np.array([1.0, 2.0, 2.0])
    mu = xfcts.calc_mu(num, den, log=False)
    assert mu == pytest.approx([2.0, 2.0, 4.0])


def test_calc_mu_log_of_ratio():
    num = np.array([np.e, np.e**2])
    den = np.array([1.0, 1.0])
    mu = xfcts.calc_mu(num, den, log=True)
    assert mu == pytest.approx([1.0, 2.0])


def test_calc_mu_accepts_lists():
    mu = xfcts.calc_mu([10.0, 20.0], [10.0, 10.0], log=False)
    assert mu == pytest.approx([1.0, 2.0])


def test_calc_mu_flip_negates_ratio():
    # ``flip`` negates the (log) absorption rather than inverting the ratio;
    # this is the original author's intended semantics for swapped I0/I.
    num = np.array([2.0, 8.0])
    den = np.array([1.0, 2.0])
    mu = xfcts.calc_mu(num, den, log=False, flip=True)
    assert mu == pytest.approx([-2.0, -4.0])  # -1 * (N/D)


def test_calc_mu_flip_with_log():
    num = np.array([1.0])
    den = np.array([np.e])
    mu = xfcts.calc_mu(num, den, log=True, flip=True)
    assert mu == pytest.approx([1.0])  # -1 * ln(|N/D|) = -ln(1/e) = 1


def test_calc_mu_log_uses_abs_of_ratio():
    # A negative ratio (e.g. background-subtracted signal dipping below zero)
    # would produce NaN without the abs guard inside the log.
    mu = xfcts.calc_mu(np.array([-np.e]), np.array([1.0]), log=True)
    assert mu == pytest.approx([1.0])  # ln(|-e|) = 1


def test_create_larch_spectrum_has_energy_and_mu():
    energy = np.linspace(29000, 29500, 50)
    num = np.linspace(1.0, 2.0, 50)
    den = np.full(50, 1.0)
    g = xfcts.create_larch_spectrum(energy, num, den, log=True)
    assert g.energy.shape == energy.shape
    assert g.mu.shape == energy.shape
    # Energy is stored ascending.
    assert g.energy[0] < g.energy[-1]
