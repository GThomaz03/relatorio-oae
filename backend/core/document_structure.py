"""Montagem da hierarquia de secções do relatório Word (modelo RSP)."""

from __future__ import annotations

from backend.core.photo_numbering import _nest_groups_by_document
from backend.models.inspection import AnomalyGroup
from backend.models.structure import (
    MACRO_SECTION_ORDER,
    MACRO_WITHOUT_ELEMENT_SUBHEADING,
)
from backend.rules.photo_section_order import build_group_photo_sort_key


def build_anomaly_macros(groups: list[AnomalyGroup]) -> list[dict[str, object]]:
    """
    Agrupa descrições no formato do relatório de referência:
    MACRO (Heading 4) -> elemento (Heading 4) -> itens (Normal com bullet).
    """
    nested_groups = _nest_groups_by_document(groups)

    macros: list[dict[str, object]] = []
    for macro_title in MACRO_SECTION_ORDER:
        elements_map = nested_groups.get(macro_title)
        if not elements_map:
            continue

        def _sorted_element_titles() -> list[str]:
            return sorted(
                elements_map.keys(),
                key=lambda title: build_group_photo_sort_key(elements_map[title][0]),
            )

        if macro_title in MACRO_WITHOUT_ELEMENT_SUBHEADING:
            all_lines: list[dict[str, str]] = []
            for element_title in _sorted_element_titles():
                for group in sorted(
                    elements_map[element_title],
                    key=build_group_photo_sort_key,
                ):
                    all_lines.append({"line": group.description})
            elements: list[dict[str, object]] = [{"title": "", "lines": all_lines}]
        else:
            elements = []
            for element_title in _sorted_element_titles():
                lines = [
                    {"line": group.description}
                    for group in sorted(
                        elements_map[element_title],
                        key=build_group_photo_sort_key,
                    )
                ]
                elements.append(
                    {
                        "title": element_title,
                        "lines": lines,
                    }
                )

        macros.append({"title": macro_title, "elements": elements})

    return macros

