"""Numeração sequencial de fotos no padrão RSP (E116K244710F001S)."""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass

from backend.models.anomaly import Anomaly
from backend.models.inspection import AnomalyGroup
from backend.models.structure import format_local_with_number, hierarchy_for_code, parse_local_code
from backend.rules.photo_section_order import (
    sort_groups_for_photo_report,
    sort_members_for_photo_report,
)

logger = logging.getLogger(__name__)

DEFAULT_PHOTO_START = 1
DEFAULT_PHOTO_DIRECTION = "S"
DEFAULT_PHOTO_SEQ_WIDTH = 3


def build_photo_prefix(bridge_id: str, photo_km: str) -> str:
    """Monta prefixo fixo: E116 + K + 244710 -> E116K244710."""
    bridge = bridge_id.strip().upper()
    km = photo_km.strip().replace("+", "").replace(" ", "")
    return f"{bridge}K{km}"


def build_rsp_photo_code(
    prefix: str,
    seq: int,
    direction: str = DEFAULT_PHOTO_DIRECTION,
    width: int = DEFAULT_PHOTO_SEQ_WIDTH,
) -> str:
    """Gera código RSP completo: E116K244710F001S."""
    return f"{prefix}F{seq:0{width}d}{direction}"


@dataclass(frozen=True)
class PhotoAssignment:
    image_path: str
    report_code: str
    figure_number: int
    anomaly: Anomaly
    group: AnomalyGroup


def _nest_groups_by_document(
    groups: list[AnomalyGroup],
) -> dict[str, dict[str, list[AnomalyGroup]]]:
    nested: dict[str, dict[str, list[AnomalyGroup]]] = defaultdict(lambda: defaultdict(list))

    for group in groups:
        code = group.structural_prefix or None
        if code is None and group.members:
            code = parse_local_code(group.members[0].local)
        macro, element = hierarchy_for_code(code)
        nested[macro][element].append(group)

    return nested


def iter_groups_document_order(groups: list[AnomalyGroup]) -> list[AnomalyGroup]:
    """
    Ordem técnica fixa do registro fotográfico (independente do Excel ou macros Word).
    """
    return sort_groups_for_photo_report(groups)


def assign_photo_codes_from_anomalies(
    anomalies: list[Anomaly],
    groups: list[AnomalyGroup],
    prefix: str,
    start: int = DEFAULT_PHOTO_START,
    direction: str = DEFAULT_PHOTO_DIRECTION,
) -> tuple[list[PhotoAssignment], dict[str, str]]:
    """
    Numera fotos na ordem explícita das anomalias (layout do utilizador).

    Cada anomalia gera no máximo uma entrada no anexo; grupos servem só para descrição textual.
    """
    group_by_member = {id(member): group for group in groups for member in group.members}
    code_map: dict[str, str] = {}
    assignments: list[PhotoAssignment] = []
    seen_in_report: set[str] = set()
    next_seq = start

    for member in anomalies:
        group = group_by_member.get(id(member))
        if group is None:
            group = AnomalyGroup(
                group_id="G000",
                section_id=member.structural_code or "GERAL",
                anomaly_type=member.anomaly_type,
                face=member.face,
                view=member.view,
                structural_prefix=member.structural_code,
                members=[member],
                locals=[format_local_with_number(member.local, member.number)],
                description="",
            )

        for image_path in member.images:
            if not image_path:
                continue

            if image_path not in code_map:
                code_map[image_path] = build_rsp_photo_code(prefix, next_seq, direction=direction)
                next_seq += 1

            if image_path in seen_in_report:
                continue

            seen_in_report.add(image_path)
            assignments.append(
                PhotoAssignment(
                    image_path=image_path,
                    report_code=code_map[image_path],
                    figure_number=len(assignments) + 1,
                    anomaly=member,
                    group=group,
                )
            )
            break

    return assignments, code_map


def assign_photo_codes(
    groups: list[AnomalyGroup],
    prefix: str,
    start: int = DEFAULT_PHOTO_START,
    direction: str = DEFAULT_PHOTO_DIRECTION,
) -> tuple[list[PhotoAssignment], dict[str, str]]:
    """
    Atribui códigos RSP sequenciais na ordem documental.

    Returns:
        assignments: lista ordenada (1ª foto do texto = 1ª do anexo)
        code_map: image_path -> report_code (deduplica referências)
    """
    code_map: dict[str, str] = {}
    assignments: list[PhotoAssignment] = []
    seen_in_report: set[str] = set()
    next_seq = start

    for group in iter_groups_document_order(groups):
        members = sort_members_for_photo_report(group.members)
        for member in members:
            for image_path in member.images:
                if not image_path:
                    continue

                if image_path not in code_map:
                    code_map[image_path] = build_rsp_photo_code(prefix, next_seq, direction=direction)
                    next_seq += 1

                if image_path in seen_in_report:
                    continue

                seen_in_report.add(image_path)
                assignments.append(
                    PhotoAssignment(
                        image_path=image_path,
                        report_code=code_map[image_path],
                        figure_number=len(assignments) + 1,
                        anomaly=member,
                        group=group,
                    )
                )

    logger.info(
        "Numeração RSP: %d foto(s), códigos F%03d–F%03d",
        len(code_map),
        start,
        max(start, next_seq - 1),
    )
    return assignments, code_map
