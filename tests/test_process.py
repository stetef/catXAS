"""Unit tests for the process-stream readers in ``catxas.process``."""

import pandas as pd

from catxas import process

from conftest import LV_FILE, MS_FILE


def test_read_ms_data_returns_timeindexed_frame():
    ms = process.ReadMSData(str(MS_FILE))
    assert isinstance(ms, pd.DataFrame)
    assert len(ms) > 0
    assert isinstance(ms.index, pd.DatetimeIndex)
    # Mass-spec gas channels expected for this experiment.
    assert "H2" in ms.columns


def test_read_lv_data_returns_timeindexed_frame():
    lv = process.ReadLVData(str(LV_FILE))
    assert isinstance(lv, pd.DataFrame)
    assert len(lv) > 0
    assert isinstance(lv.index, pd.DatetimeIndex)
    # LabView log carries the reactor step and many sensor columns.
    assert "Stepnumber" in lv.columns
    assert lv.shape[1] > 10


def test_ms_index_is_monotonic():
    ms = process.ReadMSData(str(MS_FILE))
    assert ms.index.is_monotonic_increasing
