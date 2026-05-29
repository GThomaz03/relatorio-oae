"""Geração de descrições técnicas e agrupamento de anomalias."""

from __future__ import annotations

import logging
import re
from pathlib import Path

import yaml

from backend.config import DEFAULT_DESCRIPTIONS
from backend.models.anomaly import Anomaly
from backend.models.inspection import AnomalyGroup
from backend.models.structure import (
    format_local_with_number,
    format_locals_list,
    hierarchy_for_code,
    is_pavement_code,
    parse_local_code,
    preposition_for_code,
    structural_label_lower_pt,
    structural_label_pt,
)
from backend.rules.grouping import (
    anomaly_report_sort_key,
    clean_anomaly_type,
    resolve_template_key,
    sort_locals,
    structural_prefix,
)


def _anomaly_clean_label(anomaly: Anomaly) -> str:
    if anomaly.semantics:
        return anomaly.semantics.formatted_label
    return clean_anomaly_type(anomaly.anomaly_type)


def _modifiers_part(anomaly: Anomaly) -> str:
    if anomaly.semantics and anomaly.semantics.modifier_labels:
        return " com " + " e ".join(anomaly.semantics.modifier_labels)
    return ""


def _template_key_for(anomaly: Anomaly) -> str:
    if anomaly.semantics:
        return anomaly.semantics.template_key
    return resolve_template_key(anomaly.anomaly_type)

logger = logging.getLogger(__name__)

BULLET_PREFIX = "-\t"

PHOTO_REF_SUFFIX = re.compile(
    r"\s*\((?:Foto|Fotos)\s[^)]+\)",
    re.IGNORECASE,
)

FACE_PROSE_MAP: dict[str, str] = {
    "sobre a obra": "superior",
}

DIRECTION_FACES = frozenset({"norte", "sul", "leste", "oeste"})

PLACEHOLDER_ALIASES: dict[str, str] = {
    "vão": "vao",
    "vão/ap": "vao",
    "núm": "num",
    "número": "num",
}


def load_description_catalog(path: Path | None = None) -> dict[str, object]:
    catalog_path = path or DEFAULT_DESCRIPTIONS
    with catalog_path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data if isinstance(data, dict) else {}


def _canonical_description_override(members: list[Anomaly]) -> str | None:
    """
    Legenda do bullet em ANOMALIAS CONSTATADAS (não do anexo fotográfico).

    Em duplicatas, usa só a legenda da anomalia original; cada foto no relatório
    fotográfico mantém o description_override da sua entrada no layout.
    """
    originals = [m for m in members if not m.source_anomaly_client_id]
    for candidate in originals + members:
        if candidate.description_override and str(candidate.description_override).strip():
            return str(candidate.description_override).strip().rstrip(".;")
    return None


def format_photo_references(codes: list[str]) -> str:
    """Formata referência com códigos RSP completos: (Foto E78K124F001S) ou (Fotos ... e ...)."""
    labels = list(dict.fromkeys(c.strip() for c in codes if c and str(c).strip()))
    if not labels:
        return ""
    label = "Foto" if len(labels) == 1 else "Fotos"
    if len(labels) == 1:
        return f" ({label} {labels[0]})"
    if len(labels) == 2:
        return f" ({label} {labels[0]} e {labels[1]})"
    return f" ({label} {', '.join(labels[:-1])} e {labels[-1]})"


def _resolve_photo_codes(
    image_paths: list[str],
    photo_code_map: dict[str, str] | None = None,
) -> list[str]:
    codes: list[str] = []
    for path in image_paths:
        if not path:
            continue
        if photo_code_map and path in photo_code_map:
            codes.append(photo_code_map[path])
        else:
            codes.append(Path(path).stem)
    return codes


def normalize_face_for_prose(face: str | None, structural_code: str | None = None) -> str | None:
    if not face:
        return None
    if is_pavement_code(structural_code):
        return None
    normalized = face.strip().lower()
    mapped = FACE_PROSE_MAP.get(normalized, face.strip())
    if mapped.lower() in ("superior", "inferior"):
        return mapped.lower()
    if mapped.lower() in DIRECTION_FACES:
        return mapped.capitalize()
    return mapped


def _face_part(face: str | None, structural_code: str | None = None) -> str:
    prose_face = normalize_face_for_prose(face, structural_code)
    if not prose_face:
        return ""
    return f", face {prose_face}"


def _normalize_span_token(span: str | None) -> str | None:
    if not span:
        return None
    span_text = str(span).strip()
    if not span_text:
        return None
    if span_text.lower().startswith("vão"):
        match = re.search(r"vão\s*(.+)", span_text, re.IGNORECASE)
        return match.group(1).strip() if match else span_text
    if span_text.upper().startswith("V") and span_text[1:].isdigit():
        return span_text[1:]
    return span_text


def _span_part(span: str | None) -> str:
    token = _normalize_span_token(span)
    if not token:
        return ""
    return f", vão {token}"


def _collect_span_tokens(members: list[Anomaly]) -> list[str]:
    seen: set[str] = set()
    tokens: list[str] = []
    for member in members:
        token = _normalize_span_token(member.span)
        if token and token not in seen:
            seen.add(token)
            tokens.append(token)
    return tokens


def _sort_span_tokens(tokens: list[str]) -> list[str]:
    def sort_key(token: str) -> tuple[int, int | str]:
        if token.isdigit():
            return (0, int(token))
        return (1, token)

    return sorted(tokens, key=sort_key)


def _format_spans_part(tokens: list[str]) -> str:
    if not tokens:
        return ""
    if len(tokens) == 1:
        return f", vão {tokens[0]}"
    if len(tokens) == 2:
        return f", vãos {tokens[0]} e {tokens[1]}"
    return f", vãos {', '.join(tokens[:-1])} e {tokens[-1]}"


def _spans_part_from_members(members: list[Anomaly]) -> str:
    return _format_spans_part(_sort_span_tokens(_collect_span_tokens(members)))


def _crack_width_part(crack_width: str | None) -> str:
    if not crack_width:
        return "0,10mm"
    width = str(crack_width).strip()
    if width.upper().startswith("W"):
        width = width[1:]
    width = width.replace(" ", "")
    if "mm" not in width.lower():
        return f"{width}mm"
    return width


def _observations_suffix(anomalies: list[Anomaly]) -> str:
    obs = [a.observations for a in anomalies if a.observations]
    if not obs:
        return ""
    unique = list(dict.fromkeys(obs))
    return ". " + "; ".join(unique)


def _formatted_locals(members: list[Anomaly]) -> list[str]:
    return sort_locals(
        [format_local_with_number(m.local, m.number) for m in members]
    )


def _resolve_effective_template_key(template_key: str, structural_code: str | None) -> str:
    if is_pavement_code(structural_code):
        if template_key == "acumulo_detritos":
            return "acumulo_detritos_pavimento"
        if template_key == "ausencia_taxa_refletiva":
            return "ausencia_taxa_refletiva_pavimento"
    return template_key


def _build_context(
    members: list[Anomaly],
    photo_code_map: dict[str, str] | None = None,
    include_photos: bool = True,
) -> dict[str, str]:
    locals_sorted = _formatted_locals(members)
    first = members[0]
    code = parse_local_code(first.local)
    label = structural_label_pt(code) if code else "elemento estrutural"
    label_lower = structural_label_lower_pt(code) if code else "elemento estrutural"
    anomaly_clean = _anomaly_clean_label(first)

    all_images: list[str] = []
    for member in members:
        all_images.extend(member.images)

    return {
        # Placeholders amigáveis (nomes de colunas da planilha)
        "local": first.local,
        "num": first.number or "",
        "anomalia": first.anomaly_type,
        "vao": (
            (joined := " e ".join(sorted_tokens))
            if len(sorted_tokens := _sort_span_tokens(_collect_span_tokens(members))) > 1
            else (_normalize_span_token(first.span) or "")
        ),
        "vista": first.view or "",
        "w": _crack_width_part(first.crack_width),
        "quant": "" if first.quantity is None else str(first.quantity),
        "comp_m": "" if first.length is None else str(first.length),
        "larg_m": "" if first.width is None else str(first.width),
        "area_m2_m": "" if first.area is None else str(first.area),
        "observacoes": first.observations or "",
        "cam_inicial": first.image_range_start,
        "cam_final": first.image_range_end,
        # Placeholders legados
        "locals": format_locals_list(locals_sorted),
        "structural_label": label or "elemento estrutural",
        "structural_phrase": label_lower or "elemento estrutural",
        "structural_label_lower": label_lower or "elemento estrutural",
        "prep": preposition_for_code(code),
        "face": first.face,
        "view": first.view or "",
        "anomaly_type": first.anomaly_type,
        "anomaly_type_clean": anomaly_clean,
        "modifiers_part": _modifiers_part(first),
        "face_part": _face_part(first.face, code),
        "span_part": _spans_part_from_members(members),
        "photos_part": (
            format_photo_references(_resolve_photo_codes(all_images, photo_code_map))
            if include_photos
            else ""
        ),
        "crack_width": _crack_width_part(first.crack_width),
        "observations_suffix": _observations_suffix(members),
        "observations": first.observations or "",
    }


def _render_template(template: str, context: dict[str, str]) -> str:
    for source, target in PLACEHOLDER_ALIASES.items():
        template = template.replace(f"{{{source}}}", f"{{{target}}}")
    try:
        return template.format(**context)
    except KeyError as exc:
        logger.warning("Placeholder ausente no template: %s", exc)
        return template


def _normalize_description_body(body: str) -> str:
    """Remove espaços duplos gerados por placeholders vazios."""
    return re.sub(r" {2,}", " ", body.strip())


def generate_group_description(
    members: list[Anomaly],
    catalog: dict[str, object] | None = None,
    photo_code_map: dict[str, str] | None = None,
    include_photos: bool = True,
) -> str:
    """Gera descrição técnica PT-BR no formato RSP (bullet + referência de fotos)."""
    if not members:
        return ""

    catalog = catalog or load_description_catalog()
    first = members[0]
    code = parse_local_code(first.local)
    template_key = _template_key_for(first)
    template_key = _resolve_effective_template_key(template_key, code)
    context = _build_context(members, photo_code_map=photo_code_map, include_photos=include_photos)

    custom_body = _canonical_description_override(members)
    if custom_body is not None:
        photos_part = context["photos_part"] if include_photos else ""
        body = _normalize_description_body(f"{custom_body}{photos_part}")
        body = body.rstrip(".;") + ";"
        return f"{BULLET_PREFIX}{body}"

    entry = catalog.get(template_key)
    if isinstance(entry, dict) and "template" in entry:
        template = str(entry["template"]).strip()
        body = _render_template(template, context)
    else:
        default_tpl = str(catalog.get("default", "")).strip()
        if default_tpl:
            body = _render_template(default_tpl, context)
        else:
            body = (
                f"{context['anomaly_type_clean']} {context['prep']} {context['structural_phrase']} "
                f"{context['locals']}{context['face_part']}{context['span_part']}{context['photos_part']}"
            )
        logger.warning(
            "Tipo de anomalia sem template dedicado: %s (chave: %s)",
            members[0].anomaly_type,
            template_key,
        )

    body = _normalize_description_body(body)
    body = body.rstrip(".;") + ";"
    return f"{BULLET_PREFIX}{body}"


def description_from_group_bullet(description: str) -> str:
    """
    Extrai texto da legenda fotográfica a partir do bullet de ANOMALIAS CONSTATADAS.

    Remove prefixo '-\\t' e referências '(Foto(s) ...)'.
    """
    text = description.lstrip("-\t").strip()
    text = PHOTO_REF_SUFFIX.sub("", text).rstrip(".;").strip()
    return text


def description_body_for_anomaly(
    anomaly: Anomaly,
    catalog: dict[str, object] | None = None,
    photo_code_map: dict[str, str] | None = None,
) -> str:
    """Texto descritivo sem bullet (para legendas fotográficas)."""
    full = generate_group_description(
        [anomaly],
        catalog=catalog,
        photo_code_map=photo_code_map,
        include_photos=False,
    )
    return full.lstrip("-\t").rstrip(";").strip()


def rebuild_group_descriptions(
    groups: list[AnomalyGroup],
    photo_code_map: dict[str, str] | None = None,
) -> list[AnomalyGroup]:
    """Regenera descrições dos grupos com códigos RSP nas referências fotográficas."""
    catalog = load_description_catalog()
    return [
        group.model_copy(
            update={
                "description": generate_group_description(
                    group.members,
                    catalog=catalog,
                    photo_code_map=photo_code_map,
                )
            }
        )
        for group in groups
    ]


def group_anomalies(anomalies: list[Anomaly]) -> list[AnomalyGroup]:
    """
    Agrupa anomalias com a mesma chave semântica (inclui duplicatas fotográficas).

    Preserva a ordem de primeira aparição na lista de entrada (layout fotográfico).
    """
    from backend.rules.grouping import grouping_key

    catalog = load_description_catalog()
    buckets: dict[tuple, list[Anomaly]] = {}
    bucket_order: list[tuple] = []

    for anomaly in anomalies:
        key = grouping_key(anomaly)
        if key not in buckets:
            buckets[key] = []
            bucket_order.append(key)
        buckets[key].append(anomaly)

    bucket_order.sort(key=lambda key: anomaly_report_sort_key(buckets[key][0]))

    groups: list[AnomalyGroup] = []
    for idx, key in enumerate(bucket_order, start=1):
        members = buckets[key]
        first = members[0]
        element_label = format_local_with_number(first.local, first.number)
        section_id = structural_prefix(first.local) or "GERAL"
        locals_sorted = sort_locals(
            list(dict.fromkeys(format_local_with_number(m.local, m.number) for m in members))
        )
        description = generate_group_description(members, catalog=catalog)

        groups.append(
            AnomalyGroup(
                group_id=f"G{idx:03d}",
                section_id=section_id,
                anomaly_type=_anomaly_clean_label(first),
                face=first.face,
                view=first.view,
                structural_prefix=structural_prefix(first.local),
                members=members,
                locals=locals_sorted,
                description=description,
            )
        )

    logger.info(
        "Relatório de anomalias: %d grupo(s) a partir de %d registro(s) fotográfico(s)",
        len(groups),
        len(anomalies),
    )
    return groups


def build_sections(anomalies: list[Anomaly]) -> list[AnomalyGroup]:
    """Gera seções textuais — uma entrada por anomalia."""
    return group_anomalies(anomalies)
