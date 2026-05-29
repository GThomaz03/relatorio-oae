"""Testes do parser Excel."""

from pathlib import Path

import pandas as pd
import pytest

from backend.core.parser_excel import _canonical_column_name, parse_excel
from backend.core.validators import ExcelStructureError, Severity


def test_parse_excel_success(sample_excel: Path) -> None:
    anomalies, issues = parse_excel(sample_excel)
    assert len(anomalies) == 3
    assert anomalies[0].local == "VL1"
    assert anomalies[0].image_range_start in ("00136", "136")
    assert anomalies[0].photo_count_expected == 3
    assert all(i.severity != Severity.ERROR for i in issues)


def test_parse_excel_missing_columns(tmp_path: Path) -> None:
    path = tmp_path / "bad.xlsx"
    pd.DataFrame({"Local": ["VL1"], "Face": ["Sup"]}).to_excel(path, index=False)
    with pytest.raises(ExcelStructureError):
        parse_excel(path)


def test_canonical_column_mojibake() -> None:
    assert _canonical_column_name("Nm.") == "Núm."
    assert _canonical_column_name("Vao/AP") == "Vão/AP"
