"""Lógica de negócio para configuração global (Gerenciamento)."""

from __future__ import annotations

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import yaml

from backend.api.management_schemas import (
    AnomalyCatalogPayload,
    AnomalyCatalogResponse,
    CatalogBaseEntry,
    CatalogModifierEntry,
    CatalogPreviewResponse,
    ColumnSchemaItem,
    DescriptionPreviewResponse,
    ExcelValidateResponse,
    InputSchemaResponse,
    LegendaEntry,
    LegendaPayload,
    ManagementChecklistItem,
    ManagementExportPayload,
    ManagementSummaryResponse,
    PhotoSectionItem,
)
from backend.config import (
    COLUMN_ALIASES,
    DEFAULT_DESCRIPTIONS,
    OPTIONAL_COLUMNS,
    REQUIRED_COLUMNS,
    RULES_DIR,
)
from backend.core.parser_excel import PREFERRED_SHEET_NAMES, _find_inspection_sheet, _normalize_column_names, parse_excel
from backend.core.runtime_settings import DEFAULT_RUNTIME_SETTINGS, load_runtime_settings, save_runtime_settings
from backend.core.text_generator import _build_context, _normalize_description_body, _render_template, load_description_catalog
from backend.core.validators import Severity, validate_missing_columns
from backend.models.anomaly import Anomaly
from backend.rules.anomaly_parser import clear_catalog_cache, parse_anomaly_text
from backend.rules.legenda import LEGENDA_YAML_PATH, clear_legenda_cache, load_legenda, save_legenda_entries
from backend.rules.photo_section_order import PHOTO_SECTION_LABELS, PHOTO_SECTION_ORDER

CATALOG_PATH = RULES_DIR / "anomaly_catalog.yaml"

COLUMN_EXAMPLES: dict[str, str] = {
    "Local": "LB",
    "Núm.": "1",
    "Face": "Inferior",
    "Anomalia": "1.10 - Fissuras verticais",
    "Quant Fotos": "3",
    "Disp.": "Sim",
    "Cam inicial": "00136",
    "Cam final": "00138",
    "Vão/AP": "Vão 2",
    "Vista": "Longitudinal",
    "W": "0,15 mm",
    "nr_foto": "00136",
}

DESCRIPTION_TEMPLATE_TOKENS: list[dict[str, str]] = [
    {"token": "{local}", "label": "Local"},
    {"token": "{num}", "label": "Núm."},
    {"token": "{face}", "label": "Face"},
    {"token": "{anomalia}", "label": "Anomalia"},
    {"token": "{vao}", "label": "Vão/AP"},
    {"token": "{vista}", "label": "Vista"},
    {"token": "{w}", "label": "W"},
    {"token": "{quant}", "label": "Quant."},
    {"token": "{comp_m}", "label": "Comp (m)"},
    {"token": "{larg_m}", "label": "Larg (m)"},
    {"token": "{area_m2_m}", "label": "Área m²-m"},
    {"token": "{observacoes}", "label": "Observações"},
    {"token": "{cam_inicial}", "label": "Cam inicial"},
    {"token": "{cam_final}", "label": "Cam final"},
    {"token": "{structural_phrase}", "label": "Elemento (frase)"},
    {"token": "{structural_label}", "label": "Elemento (rótulo)"},
    {"token": "{prep}", "label": "Preposição (na/no)"},
    {"token": "{anomaly_type_clean}", "label": "Anomalia (limpa)"},
    {"token": "{face_part}", "label": "Trecho da face"},
    {"token": "{span_part}", "label": "Trecho do vão"},
    {"token": "{photos_part}", "label": "Referência fotos"},
    {"token": "{crack_width}", "label": "Abertura (W)"},
    {"token": "{observations_suffix}", "label": "Sufixo observações"},
]


def _aliases_for_column(canonical: str) -> list[str]:
    return sorted(alias for alias, target in COLUMN_ALIASES.items() if target == canonical)


def get_input_schema() -> InputSchemaResponse:
    required = [
        ColumnSchemaItem(
            name=name,
            required=True,
            aliases=_aliases_for_column(name),
            example=COLUMN_EXAMPLES.get(name, ""),
        )
        for name in REQUIRED_COLUMNS
    ]
    optional = [
        ColumnSchemaItem(
            name=name,
            required=False,
            aliases=_aliases_for_column(name),
            example=COLUMN_EXAMPLES.get(name, ""),
        )
        for name in OPTIONAL_COLUMNS
    ]
    return InputSchemaResponse(
        required_columns=required,
        optional_columns=optional,
        default_sheet_names=list(PREFERRED_SHEET_NAMES),
        reference_fields=DESCRIPTION_TEMPLATE_TOKENS,
    )


def validate_excel_upload(content: bytes, preferred_sheet: str | None = None) -> ExcelValidateResponse:
    settings = load_runtime_settings()
    sheet_pref = preferred_sheet or settings.get("excel_preferred_sheet") or None
    if sheet_pref == "":
        sheet_pref = None

    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)

    try:
        import pandas as pd

        with pd.ExcelFile(tmp_path, engine="openpyxl") as xl:
            sheet_names = list(xl.sheet_names)

        try:
            sheet_name = _find_inspection_sheet(tmp_path, preferred=sheet_pref)
        except Exception as exc:
            with pd.ExcelFile(tmp_path, engine="openpyxl") as xl:
                sheet_names = list(xl.sheet_names)
            return ExcelValidateResponse(
                ok=False,
                sheet_names=sheet_names,
                issues=[{"severity": "error", "message": str(exc)}],
            )

        preview = pd.read_excel(tmp_path, sheet_name=sheet_name, engine="openpyxl", nrows=5)
        preview.columns = _normalize_column_names(preview.columns)
        found = set(preview.columns)
        missing_issues = validate_missing_columns(found, REQUIRED_COLUMNS)
        missing = [i.message.split(":")[-1].strip() for i in missing_issues if "Coluna obrigatória ausente" in i.message]
        missing_cols = []
        for col in REQUIRED_COLUMNS:
            if col not in found:
                missing_cols.append(col)

        expected = set(REQUIRED_COLUMNS) | set(OPTIONAL_COLUMNS)
        extra = sorted(found - expected)

        preview_rows: list[dict[str, str]] = []
        for _, row in preview.head(3).iterrows():
            preview_rows.append(
                {col: "" if pd.isna(row.get(col)) else str(row.get(col)) for col in preview.columns}
            )

        parse_warnings = 0
        try:
            _, parse_issues = parse_excel(tmp_path, sheet_name=sheet_name)
            parse_warnings = sum(1 for i in parse_issues if i.severity == Severity.WARNING)
        except Exception:
            pass

        issues = [
            {
                "severity": i.severity.value,
                "code": i.code,
                "message": i.message,
            }
            for i in missing_issues
        ]

        return ExcelValidateResponse(
            ok=len(missing_cols) == 0,
            sheet_name=sheet_name,
            sheet_names=sheet_names,
            found_columns=sorted(found),
            missing_columns=missing_cols,
            extra_columns=extra,
            row_count=int(preview.shape[0]),
            preview_rows=preview_rows,
            issues=issues,
            parse_warnings=parse_warnings,
        )
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            pass


def _read_descriptions_yaml() -> str:
    if not DEFAULT_DESCRIPTIONS.is_file():
        return ""
    return DEFAULT_DESCRIPTIONS.read_text(encoding="utf-8")


def read_description_rules() -> list[dict[str, str]]:
    yaml_text = _read_descriptions_yaml()
    if not yaml_text.strip():
        return []
    try:
        raw = yaml.safe_load(yaml_text)
    except yaml.YAMLError:
        return []
    if not isinstance(raw, dict):
        return []

    rules: list[dict[str, str]] = []
    for key, value in raw.items():
        template = ""
        if isinstance(value, dict):
            template = str(value.get("template", "")).strip()
        elif isinstance(value, str):
            template = value.strip()
        if template:
            rules.append({"key": str(key), "template": template})
    return rules


def write_description_rules(rules: list[dict[str, str]]) -> str:
    errors = validate_description_rules(rules)
    if errors:
        raise ValueError(errors[0])

    normalized: list[tuple[str, str]] = []
    seen: set[str] = set()
    for rule in rules:
        key = str(rule.get("key", "")).strip()
        template = str(rule.get("template", "")).strip()
        if not key or not template or key in seen:
            continue
        seen.add(key)
        normalized.append((key, template))

    if not normalized:
        normalized = [
            (
                "default",
                "{anomaly_type_clean} {prep} {structural_phrase} {locals}{face_part}{span_part}{photos_part}",
            )
        ]

    output: dict[str, object] = {}
    for key, template in normalized:
        if key == "default":
            output[key] = template
        else:
            output[key] = {"template": template}

    yaml_text = yaml.safe_dump(
        output,
        allow_unicode=True,
        sort_keys=False,
        default_flow_style=False,
    )
    DEFAULT_DESCRIPTIONS.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_DESCRIPTIONS.write_text(yaml_text, encoding="utf-8")
    return yaml_text


def list_template_keys() -> list[str]:
    rules = read_description_rules()
    keys = sorted({r["key"] for r in rules if r.get("key")})
    if "default" not in keys:
        keys.insert(0, "default")
    return keys


def read_anomaly_catalog() -> AnomalyCatalogResponse:
    if not CATALOG_PATH.is_file():
        return AnomalyCatalogResponse(bases=[], modifiers=[], template_keys=list_template_keys())

    raw = yaml.safe_load(CATALOG_PATH.read_text(encoding="utf-8")) or {}
    bases = [
        CatalogBaseEntry(
            key=str(key),
            label=str(entry.get("label", key)),
            template_key=str(entry.get("template_key", key)),
            aliases=[str(a) for a in (entry.get("aliases") or [])],
        )
        for key, entry in (raw.get("bases") or {}).items()
        if isinstance(entry, dict)
    ]
    modifiers = [
        CatalogModifierEntry(
            key=str(key),
            label=str(entry.get("label", key)),
            aliases=[str(a) for a in (entry.get("aliases") or [])],
        )
        for key, entry in (raw.get("modifiers") or {}).items()
        if isinstance(entry, dict)
    ]
    return AnomalyCatalogResponse(
        bases=bases,
        modifiers=modifiers,
        template_keys=list_template_keys(),
    )


def write_anomaly_catalog(payload: AnomalyCatalogPayload) -> AnomalyCatalogResponse:
    template_keys = set(list_template_keys())
    for base in payload.bases:
        if base.template_key not in template_keys:
            raise ValueError(
                f"template_key '{base.template_key}' não existe em descriptions.yaml "
                f"(chaves: {', '.join(sorted(template_keys))})"
            )

    seen: set[str] = set()
    for base in payload.bases:
        if base.key in seen:
            raise ValueError(f"Chave duplicada no catálogo: {base.key}")
        seen.add(base.key)

    output: dict[str, object] = {"bases": {}, "modifiers": {}}
    for base in payload.bases:
        output["bases"][base.key] = {  # type: ignore[index]
            "label": base.label,
            "template_key": base.template_key,
            "aliases": base.aliases,
        }
    for mod in payload.modifiers:
        output["modifiers"][mod.key] = {  # type: ignore[index]
            "label": mod.label,
            "aliases": mod.aliases,
        }

    CATALOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CATALOG_PATH.write_text(
        yaml.safe_dump(output, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    clear_catalog_cache()
    return read_anomaly_catalog()


def preview_catalog_match(anomaly_text: str) -> CatalogPreviewResponse:
    semantics = parse_anomaly_text(anomaly_text)
    rendered: str | None = None
    catalog = load_description_catalog()
    template_key = semantics.template_key
    entry = catalog.get(template_key) or catalog.get("default")
    if isinstance(entry, dict):
        template = str(entry.get("template", ""))
    elif isinstance(entry, str):
        template = entry
    else:
        template = ""

    if template:
        sample = Anomaly(
            local="LB",
            number="1",
            face="Inferior",
            span="Vão 2",
            anomaly_type=anomaly_text,
            semantics=semantics,
            image_range_start="001",
            image_range_end="001",
            images=[],
        )
        ctx = _build_context([sample], include_photos=True)
        rendered = _normalize_description_body(_render_template(template, ctx))

    return CatalogPreviewResponse(
        base_key=semantics.base_key,
        base_label=semantics.base_label,
        template_key=semantics.template_key,
        modifier_keys=list(semantics.modifier_keys),
        modifier_labels=list(semantics.modifier_labels),
        formatted_label=semantics.formatted_label,
        rendered_description=rendered,
    )


def read_legenda() -> LegendaPayload:
    data = load_legenda()
    entries = [
        LegendaEntry(code=code, label=label)
        for code, label in sorted(data.items(), key=lambda item: item[0])
    ]
    return LegendaPayload(entries=entries)


def write_legenda(payload: LegendaPayload) -> LegendaPayload:
    seen: set[str] = set()
    normalized: list[LegendaEntry] = []
    for entry in payload.entries:
        code = entry.code.strip().upper()
        label = entry.label.strip()
        if not code or not label:
            continue
        if code in seen:
            raise ValueError(f"Código duplicado na legenda: {code}")
        seen.add(code)
        normalized.append(LegendaEntry(code=code, label=label))

    save_legenda_entries({e.code: e.label for e in normalized})
    clear_legenda_cache()
    return read_legenda()


def preview_description(template: str, sample_row: dict[str, str] | None) -> DescriptionPreviewResponse:
    row = sample_row or {
        "local": "LB",
        "num": "1",
        "face": "Inferior",
        "anomalia": "1.10 - Fissuras verticais com manchas de umidade",
        "vao": "2",
        "vista": "Longitudinal",
        "w": "0,15 mm",
        "quant": "3",
        "comp_m": "2,50",
        "larg_m": "0,30",
        "area_m2_m": "0,75",
        "observacoes": "Monitorar evolução",
        "cam_inicial": "00136",
        "cam_final": "00138",
    }

    semantics = parse_anomaly_text(row.get("anomalia", row.get("Anomalia", "")))
    anomaly = Anomaly(
        local=row.get("local", "LB"),
        number=row.get("num", "1"),
        face=row.get("face", "Inferior"),
        span=row.get("vao") or row.get("vão") or "Vão 2",
        view=row.get("vista"),
        anomaly_type=row.get("anomalia", ""),
        crack_width=row.get("w"),
        observations=row.get("observacoes"),
        image_range_start=row.get("cam_inicial", "001"),
        image_range_end=row.get("cam_final", "001"),
        images=["/preview/sample.jpg"],
        semantics=semantics,
    )
    ctx = _build_context([anomaly], photo_code_map={"/preview/sample.jpg": "E116K244710F001S"})
    rendered = _normalize_description_body(_render_template(template, ctx))
    if not rendered.endswith(";") and not rendered.endswith("."):
        rendered = f"{rendered};"
    return DescriptionPreviewResponse(rendered=rendered)


def get_photo_sections() -> list[PhotoSectionItem]:
    return [
        PhotoSectionItem(
            key=key,
            label=PHOTO_SECTION_LABELS.get(key, key),
            order=rank,
        )
        for key, rank in sorted(PHOTO_SECTION_ORDER.items(), key=lambda item: item[1])
        if key != "outros"
    ]


def build_export_bundle() -> ManagementExportPayload:
    catalog = read_anomaly_catalog()
    return ManagementExportPayload(
        runtime_settings=load_runtime_settings(),
        description_rules=read_description_rules(),
        anomaly_catalog=AnomalyCatalogPayload(bases=catalog.bases, modifiers=catalog.modifiers),
        legenda=read_legenda(),
        exported_at=datetime.now(timezone.utc).isoformat(),
    )


def import_config_bundle(data: dict[str, object]) -> None:
    if "runtime_settings" in data and isinstance(data["runtime_settings"], dict):
        save_runtime_settings({k: str(v) for k, v in data["runtime_settings"].items()})  # type: ignore[arg-type]

    if "description_rules" in data and isinstance(data["description_rules"], list):
        write_description_rules(data["description_rules"])  # type: ignore[arg-type]

    if "anomaly_catalog" in data and isinstance(data["anomaly_catalog"], dict):
        raw = data["anomaly_catalog"]
        payload = AnomalyCatalogPayload(
            bases=[CatalogBaseEntry.model_validate(b) for b in raw.get("bases", [])],  # type: ignore[union-attr]
            modifiers=[CatalogModifierEntry.model_validate(m) for m in raw.get("modifiers", [])],  # type: ignore[union-attr]
        )
        write_anomaly_catalog(payload)

    if "legenda" in data and isinstance(data["legenda"], dict):
        leg = data["legenda"]
        entries = [LegendaEntry.model_validate(e) for e in leg.get("entries", [])]  # type: ignore[union-attr]
        write_legenda(LegendaPayload(entries=entries))


def get_management_summary() -> ManagementSummaryResponse:
    rules = read_description_rules()
    catalog = read_anomaly_catalog()
    legenda = read_legenda()
    has_default = any(r["key"] == "default" for r in rules)

    checklist = [
        ManagementChecklistItem(
            id="default_rule",
            label="Regra default de descrição",
            ok=has_default,
            hint="Mantenha a chave 'default' em Regras de descrição.",
        ),
        ManagementChecklistItem(
            id="catalog",
            label="Catálogo de anomalias",
            ok=len(catalog.bases) > 0,
            hint="Cadastre bases no catálogo para reconhecer textos do Excel.",
        ),
        ManagementChecklistItem(
            id="legenda",
            label="Siglas estruturais (legenda)",
            ok=len(legenda.entries) > 0,
            hint="Defina códigos LB, VL, P, etc.",
        ),
        ManagementChecklistItem(
            id="runtime",
            label="Parâmetros gerais",
            ok=bool(load_runtime_settings()),
            hint="Revise título, localização e legendas de foto.",
        ),
    ]

    return ManagementSummaryResponse(
        checklist=checklist,
        description_rule_count=len(rules),
        catalog_base_count=len(catalog.bases),
        legenda_count=len(legenda.entries),
    )


def validate_description_rules(rules: list[dict[str, str]]) -> list[str]:
    errors: list[str] = []
    seen: set[str] = set()
    has_default = False
    for rule in rules:
        key = rule.get("key", "").strip()
        template = rule.get("template", "").strip()
        if not key or not template:
            errors.append("Todas as regras precisam de chave e template.")
            continue
        if key in seen:
            errors.append(f"Chave duplicada: {key}")
        seen.add(key)
        if key == "default":
            has_default = True
    if not has_default:
        errors.append("Inclua uma regra com chave 'default'.")
    return errors
