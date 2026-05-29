"""Testes da camada de validação."""

from pathlib import Path

import pytest

from backend.core.parser_images import expand_image_range
from backend.core.validators import (
    InvalidImageRangeError,
    Severity,
    validate_missing_columns,
)


def test_validate_missing_columns() -> None:
    issues = validate_missing_columns({"Local", "Face"}, ("Local", "Núm.", "Face"))
    assert len(issues) == 1
    assert issues[0].severity == Severity.ERROR
    assert "Núm." in issues[0].message


def test_expand_image_range() -> None:
    result = expand_image_range("00136", "00138")
    assert result == ["00136", "00137", "00138"]


def test_expand_image_range_invalid() -> None:
    with pytest.raises(InvalidImageRangeError):
        expand_image_range("00140", "00136")
