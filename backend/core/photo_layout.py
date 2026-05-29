"""Materializa anomalias e ordem fotográfica a partir do layout do frontend."""

from __future__ import annotations

import logging

from backend.models.anomaly import Anomaly

logger = logging.getLogger(__name__)


class LayoutMaterializationError(Exception):
    """Layout do frontend não pôde ser aplicado por completo."""

    def __init__(
        self,
        message: str,
        *,
        applied: int,
        expected: int,
        skipped_ids: list[str],
    ) -> None:
        super().__init__(message)
        self.applied = applied
        self.expected = expected
        self.skipped_ids = skipped_ids


class PhotoLayoutEntry:
    """Entrada de layout (dict compatível com Pydantic no API)."""

    def __init__(
        self,
        *,
        anomaly_id: str,
        source_anomaly_id: str | None = None,
        row_index: int | None = None,
        selected_photo: str | None = None,
        legend: str | None = None,
    ) -> None:
        self.anomaly_id = anomaly_id
        self.source_anomaly_id = source_anomaly_id
        self.row_index = row_index
        self.selected_photo = selected_photo
        self.legend = legend

    @classmethod
    def from_dict(cls, data: dict) -> PhotoLayoutEntry:
        return cls(
            anomaly_id=str(data["anomaly_id"]),
            source_anomaly_id=data.get("source_anomaly_id"),
            row_index=data.get("row_index"),
            selected_photo=data.get("selected_photo"),
            legend=data.get("legend"),
        )


def _row_index_from_client_id(client_id: str) -> int | None:
    if client_id.startswith("anomaly-dup-"):
        return None
    if client_id.startswith("anomaly-"):
        suffix = client_id.removeprefix("anomaly-").split("-", 1)[0]
        if suffix.isdigit():
            return int(suffix)
    return None


def _client_id_for_anomaly(anomaly: Anomaly, index: int) -> str:
    if anomaly.client_id:
        return anomaly.client_id
    if anomaly.row_index is not None:
        return f"anomaly-{anomaly.row_index}"
    return f"anomaly-{index + 1}"


def _normalize_legend(text: str | None) -> str | None:
    if text is None:
        return None
    value = str(text).strip()
    if not value:
        return None
    return value if value.endswith(".") else f"{value}."


def _apply_layout_legend(anomaly: Anomaly, legend: str | None) -> Anomaly:
    normalized = _normalize_legend(legend)
    if not normalized:
        return anomaly
    return anomaly.model_copy(
        update={"view": normalized, "description_override": normalized},
    )


def _apply_selected_photo(anomaly: Anomaly, token: str | None) -> Anomaly:
    if not token or not str(token).strip():
        return anomaly
    value = str(token).strip()
    return anomaly.model_copy(
        update={
            "nr_foto": value,
            "image_range_start": value,
            "image_range_end": value,
        }
    )


def _clone_anomaly(
    source: Anomaly,
    *,
    client_id: str,
    source_anomaly_client_id: str | None,
    selected_photo: str | None,
    legend: str | None = None,
) -> Anomaly:
    clone = _apply_selected_photo(source, selected_photo)
    clone = clone.model_copy(
        update={"client_id": client_id, "images": []},
        deep=True,
    )
    clone = _apply_layout_legend(clone, legend)
    if source_anomaly_client_id:
        return clone.model_copy(update={"source_anomaly_client_id": source_anomaly_client_id})
    return clone


def _resolve_layout_source(
    entry: PhotoLayoutEntry,
    by_row: dict[int, Anomaly],
    by_client: dict[str, Anomaly],
) -> Anomaly | None:
    if entry.row_index is not None and entry.row_index in by_row:
        return by_row[entry.row_index]
    if entry.source_anomaly_id and entry.source_anomaly_id in by_client:
        return by_client[entry.source_anomaly_id]
    if entry.anomaly_id in by_client:
        return by_client[entry.anomaly_id]
    row = _row_index_from_client_id(entry.anomaly_id)
    if row is not None and row in by_row:
        return by_row[row]
    if entry.source_anomaly_id:
        row = _row_index_from_client_id(entry.source_anomaly_id)
        if row is not None and row in by_row:
            return by_row[row]
    return None


def _selected_photo_token(
    entry: PhotoLayoutEntry,
    selected_photos: dict[str, str] | None,
) -> str | None:
    if entry.selected_photo and str(entry.selected_photo).strip():
        return str(entry.selected_photo).strip()
    if not selected_photos:
        return None
    for key in (entry.anomaly_id, entry.source_anomaly_id):
        if key and key in selected_photos:
            return selected_photos[key]
    if entry.row_index is not None:
        row_key = f"anomaly-{entry.row_index}"
        if row_key in selected_photos:
            return selected_photos[row_key]
    return None


def materialize_anomalies_from_layout(
    base_anomalies: list[Anomaly],
    layout: list[PhotoLayoutEntry] | None,
    selected_photos: dict[str, str] | None = None,
) -> list[Anomaly]:
    """
    Constrói lista ordenada de anomalias (1 foto cada) conforme layout do frontend.

    Duplicatas clonam a anomalia de origem; tokens de foto vêm de selected_photos ou layout.
    """
    if not layout:
        ordered: list[Anomaly] = []
        for index, anomaly in enumerate(base_anomalies):
            client_id = _client_id_for_anomaly(anomaly, index)
            token = (selected_photos or {}).get(client_id) or (selected_photos or {}).get(
                f"anomaly-{index + 1}"
            )
            ordered.append(
                _apply_selected_photo(anomaly, token).model_copy(update={"client_id": client_id})
            )
        return ordered

    by_row: dict[int, Anomaly] = {}
    by_client: dict[str, Anomaly] = {}
    for index, anomaly in enumerate(base_anomalies):
        client_id = _client_id_for_anomaly(anomaly, index)
        base = anomaly.model_copy(update={"client_id": client_id})
        by_client[client_id] = base
        by_client[f"anomaly-{index + 1}"] = base
        if base.row_index is not None:
            by_row[base.row_index] = base

    result: list[Anomaly] = []
    skipped_ids: list[str] = []
    for entry in layout:
        token = _selected_photo_token(entry, selected_photos)
        source = _resolve_layout_source(entry, by_row, by_client)

        if source is None:
            logger.warning(
                "Layout fotográfico: anomalia %s não encontrada na planilha — entrada ignorada",
                entry.anomaly_id,
            )
            skipped_ids.append(entry.anomaly_id)
            continue

        is_duplicate = bool(entry.source_anomaly_id) or entry.anomaly_id.startswith("anomaly-dup-")
        if is_duplicate:
            anomaly = _clone_anomaly(
                source,
                client_id=entry.anomaly_id,
                source_anomaly_client_id=entry.source_anomaly_id,
                selected_photo=token,
                legend=entry.legend,
            )
        else:
            anomaly = _apply_selected_photo(source, token).model_copy(
                update={"client_id": entry.anomaly_id}
            )
            anomaly = _apply_layout_legend(anomaly, entry.legend)

        result.append(anomaly)
        by_client[entry.anomaly_id] = anomaly

    if not result or len(result) < len(layout):
        raise LayoutMaterializationError(
            "Não foi possível aplicar o layout fotográfico enviado pelo frontend. "
            "Volte às telas de análise, salve o rascunho e tente gerar novamente.",
            applied=len(result),
            expected=len(layout),
            skipped_ids=skipped_ids,
        )

    dup_count = sum(1 for e in layout if e.source_anomaly_id)
    logger.info(
        "Layout fotográfico aplicado: %d foto(s) na ordem do utilizador (%d duplicata(s))",
        len(result),
        dup_count,
    )
    return result
