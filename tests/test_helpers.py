"""Small tests for the helper functions. Run with:  python -m pytest"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.clean import keep_valid
from src.eda import iqr_outliers
from src.state import CLEAN_LOG, reset_state
from src.utils import clean_text, md_table, strip_accents


def test_strip_accents():
    assert strip_accents("São Paulo") == "Sao Paulo"


def test_clean_text_trims_lowercases_removes_accents_and_title_cases():
    s = pd.Series([" São PAULO ", "sao paulo", "SAO PAULO "])
    assert clean_text(s).tolist() == ["Sao Paulo"] * 3


def test_iqr_outliers_finds_the_extreme_value():
    n_out, upper, biggest = iqr_outliers(pd.Series([1, 2, 3, 4, 5, 6, 7, 8, 9, 1000]))
    assert n_out == 1 and biggest == 1000 and upper < 1000


def test_keep_valid_removes_orphans_and_logs_them():
    reset_state()
    child = pd.DataFrame({"order_id": ["a", "b", "ghost"], "x": [1, 2, 3]})
    kept = keep_valid(child, "order_id", pd.Series(["a", "b"]), "order_items", "orders")
    assert kept["order_id"].tolist() == ["a", "b"]
    assert CLEAN_LOG[-1][2] == 1          # one orphan row was removed


def test_md_table_has_header_and_rows():
    table = md_table(pd.DataFrame({"a": [1, 2], "b": ["x", "y"]}))
    assert table.splitlines()[0] == "| a | b |"
    assert len(table.splitlines()) == 4
