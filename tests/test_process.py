"""Unit tests for the process-stream readers in ``catxas.process``."""

import warnings
from pathlib import Path

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


def test_lv_valve_setpoints_mapped_to_numbers():
    """Regression: the 'A'/'B'/position string setpoints must be mapped to
    1/2/0. Under pandas copy-on-write the old replace(inplace=True) silently
    left them as strings."""
    lv = process.ReadLVData(str(LV_FILE))
    for col in ("SV1 SP", "SV1 Feedback", "SV2 SP", "SV2 Feedback"):
        if col in lv.columns:
            values = set(lv[col].dropna().unique())
            assert values <= {0, 1, 2}, f"{col} still has unmapped values: {values}"


def test_process_module_has_no_invalid_escape_sequences():
    """Regex/format strings must be raw strings: a bare '\\d' triggers a
    SyntaxWarning today and is slated to become a SyntaxError."""
    source = Path(process.__file__).read_text()
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        compile(source, process.__file__, "exec")
    invalid = [str(w.message) for w in caught if issubclass(w.category, SyntaxWarning)]
    assert not invalid, invalid
