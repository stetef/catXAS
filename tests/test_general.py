"""Unit tests for the pure helpers in ``catxas.general``."""

import numpy as np
import pandas as pd
import pytest

from catxas import general as fcts


def test_find_nearest_returns_index_and_value():
    idx, val = fcts.find_nearest([1.0, 5.0, 10.0], 6.0)
    assert idx == 1
    assert val == 5.0


def test_find_nearest_exact_match():
    idx, val = fcts.find_nearest(np.array([0, 10, 20, 30]), 20)
    assert idx == 2
    assert val == 20


@pytest.mark.parametrize(
    "name, expected",
    [
        ("20210614_SnO2_H2_TPR_Sn_EXAFS_92.tra_0013", 13),
        ("scan_0001", 1),
        ("file_42", 42),
        ("no_number_here", None),
    ],
)
def test_get_trailing_number(name, expected):
    assert fcts.get_trailing_number(name) == expected


def test_parse_list_chunks_with_remainder():
    chunks = fcts.parse_list(["a", "b", "c", "d", "e"], 2)
    assert chunks == [["a", "b"], ["c", "d"], ["e"]]


def test_parse_list_evenly_divisible():
    assert fcts.parse_list([1, 2, 3, 4], 2) == [[1, 2], [3, 4]]


def test_mergeindex_interpolates_numeric_onto_target_index():
    base = pd.date_range("2021-06-14 16:00:00", periods=3, freq="100s")
    src = pd.date_range("2021-06-14 16:00:00", periods=5, freq="50s")
    df1 = pd.DataFrame({"x": [0, 0, 0]}, index=base)
    df2 = pd.DataFrame({"signal": np.arange(5.0)}, index=src)

    out = fcts.mergeindex(df1, df2)

    # Reindexed onto df1's index, numeric column interpolated in time.
    assert list(out.index) == list(df1.index)
    assert out["signal"].iloc[0] == pytest.approx(0.0)
    assert out["signal"].iloc[1] == pytest.approx(2.0)  # halfway -> value 2.0


def test_mergeindex_tolerates_string_columns():
    """Regression: pandas 3.x raises on interpolating str columns; mergeindex
    must skip non-numeric columns instead of blowing up."""
    base = pd.date_range("2021-06-14 16:00:00", periods=3, freq="100s")
    src = pd.date_range("2021-06-14 16:00:00", periods=3, freq="100s")
    df1 = pd.DataFrame({"x": [0, 0, 0]}, index=base)
    df2 = pd.DataFrame({"signal": [1.0, 2.0, 3.0], "label": ["a", "b", "c"]}, index=src)

    out = fcts.mergeindex(df1, df2)  # must not raise

    assert "label" in out.columns
    assert out["signal"].tolist() == pytest.approx([1.0, 2.0, 3.0])
