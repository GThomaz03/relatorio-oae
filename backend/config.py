"""Configuração global, constantes e logging estruturado."""

from __future__ import annotations

import logging
import os
import re
import shutil
import sys
from pathlib import Path

# Diretório do pacote Python (código)
PACKAGE_ROOT = Path(__file__).resolve().parent

# Resolvidos em _resolve_paths() conforme ambiente desktop (AppData) ou testes locais
BUNDLE_ROOT: Path = PACKAGE_ROOT
DATA_ROOT: Path = PACKAGE_ROOT.parent
TEMPLATES_DIR: Path = PACKAGE_ROOT / "templates"
RULES_DIR: Path = PACKAGE_ROOT / "rules"
OUTPUT_DIR: Path = PACKAGE_ROOT / "output"
SAMPLES_DIR: Path = PACKAGE_ROOT / "samples"
DEFAULT_TEMPLATE: Path = TEMPLATES_DIR / "report_template.docx"
DEFAULT_DESCRIPTIONS: Path = RULES_DIR / "descriptions.yaml"
LOGS_DIR: Path = DATA_ROOT / "logs"

# Formatos suportados
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}
EXCEL_EXTENSION = ".xlsx"
DOCX_EXTENSION = ".docx"

# Colunas obrigatórias (spec §4.1)
REQUIRED_COLUMNS: tuple[str, ...] = (
    "Local",
    "Núm.",
    "Face",
    "Anomalia",
    "Quant Fotos",
    "Disp.",
    "Cam inicial",
    "Cam final",
)

OPTIONAL_COLUMNS: tuple[str, ...] = (
    "Vão/AP",
    "Vista",
    "W",
    "Quant.",
    "Comp (m)",
    "Larg (m)",
    "Observações",
    "Área m²-m",
    "nr_foto",
)

# Aliases para variações comuns em planilhas reais
COLUMN_ALIASES: dict[str, str] = {
    "Num.": "Núm.",
    "Num": "Núm.",
    "Núm": "Núm.",
    "Comp(m)": "Comp (m)",
    "Larg(m)": "Larg (m)",
    "Area m2-m": "Área m²-m",
    "Observacoes": "Observações",
    "Cam Inicial": "Cam inicial",
    "Cam Final": "Cam final",
    "Quant fotos": "Quant Fotos",
}

# Padrão de nome de imagem: E116K244710F001S.jpg
IMAGE_FILENAME_PATTERN = re.compile(
    r"^(?P<prefix>.+?)(?P<seq>\d{3,6})(?P<suffix>[A-Za-z]*)$",
    re.IGNORECASE,
)

# Planilha db_ficha: Cam 98 -> IMG_0398.JPG (offset +300)
IMG_FILENAME_PATTERN = re.compile(r"^IMG_(?P<num>\d+)$", re.IGNORECASE)
IMAGE_CAM_OFFSET = int(os.environ.get("IMAGE_CAM_OFFSET", "300"))

# Token numérico em Cam inicial/final (ex.: 00136, F001)
CAM_TOKEN_PATTERN = re.compile(r"(\d{3,6})")

MAX_IMAGE_RANGE_SPAN = 500
PHOTO_WIDTH_MM = 120   # 12 cm
PHOTO_HEIGHT_MM = 90   # 9 cm

# Layout do anexo fotográfico (2 fotos por página)
PHOTOS_PER_PAGE = 2
PHOTO_PAGE_LEADING_BLANK_LINES = 2
PHOTO_PAGE_MIDDLE_BLANK_LINES = 4
PHOTO_BLOCK_PARAGRAPH_COUNT = 4  # imagem, código, localização, descrição

REPORT_PHOTOS_DIR_NAME = "fotos_relatorio"
SEQUENTIAL_IMG_WIDTH = 4

LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_RULES_SEED_FILES = (
    "descriptions.yaml",
    "anomaly_catalog.yaml",
    "runtime_settings.json",
    "legenda.yaml",
)


def bundle_root() -> Path:
    """Raiz read-only dos assets empacotados (PyInstaller _MEIPASS ou código fonte)."""
    env = os.environ.get("OAE_BUNDLE_DIR")
    if env:
        return Path(env)
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return PACKAGE_ROOT


def data_root() -> Path:
    """Raiz gravável (AppData no desktop; raiz do repo em testes sem OAE_DATA_DIR)."""
    env = os.environ.get("OAE_DATA_DIR")
    if env:
        return Path(env)
    return PACKAGE_ROOT.parent


def is_desktop_mode() -> bool:
    return bool(os.environ.get("OAE_DATA_DIR"))


def bundle_asset_dir(name: str) -> Path:
    """Resolve assets no layout dev (backend/templates) ou PyInstaller (_MEIPASS/backend/templates)."""
    nested = BUNDLE_ROOT / "backend" / name
    if nested.exists():
        return nested
    return BUNDLE_ROOT / name


def _resolve_paths() -> None:
    global BUNDLE_ROOT, DATA_ROOT, TEMPLATES_DIR, RULES_DIR, OUTPUT_DIR
    global SAMPLES_DIR, DEFAULT_TEMPLATE, DEFAULT_DESCRIPTIONS, LOGS_DIR

    BUNDLE_ROOT = bundle_root()
    DATA_ROOT = data_root()

    if is_desktop_mode():
        TEMPLATES_DIR = bundle_asset_dir("templates")
        RULES_DIR = DATA_ROOT / "rules"
        OUTPUT_DIR = DATA_ROOT / "output"
        SAMPLES_DIR = bundle_asset_dir("samples")
        LOGS_DIR = DATA_ROOT / "logs"
    else:
        TEMPLATES_DIR = PACKAGE_ROOT / "templates"
        RULES_DIR = PACKAGE_ROOT / "rules"
        OUTPUT_DIR = PACKAGE_ROOT / "output"
        SAMPLES_DIR = PACKAGE_ROOT / "samples"
        LOGS_DIR = DATA_ROOT / "logs"

    DEFAULT_TEMPLATE = TEMPLATES_DIR / "report_template.docx"
    DEFAULT_DESCRIPTIONS = RULES_DIR / "descriptions.yaml"


def _merge_missing_legenda_from_bundle() -> None:
    """Inclui siglas novas do bundle sem sobrescrever personalizações do usuário."""
    from backend.rules.legenda import clear_legenda_cache, load_legenda, save_legenda_entries

    user_entries = load_legenda()
    if not user_entries:
        return

    for yaml_candidate in (
        bundle_asset_dir("rules") / "legenda.yaml",
        PACKAGE_ROOT / "rules" / "legenda.yaml",
    ):
        if not yaml_candidate.is_file():
            continue
        import yaml

        raw = yaml.safe_load(yaml_candidate.read_text(encoding="utf-8")) or {}
        bundle_entries: dict[str, str] = {}
        if isinstance(raw, dict) and isinstance(raw.get("entries"), dict):
            bundle_entries = {str(k).upper(): str(v) for k, v in raw["entries"].items()}
        elif isinstance(raw, dict):
            bundle_entries = {str(k).upper(): str(v) for k, v in raw.items() if k != "entries"}

        missing = {code: label for code, label in bundle_entries.items() if code not in user_entries}
        if missing:
            save_legenda_entries({**user_entries, **missing})
            clear_legenda_cache()
        return


def _ensure_legenda_seeded() -> None:
    """Garante legenda.yaml no AppData; repõe a partir do bundle ou legenda.md se vazio."""
    log = logging.getLogger(__name__)
    from backend.rules.legenda import (
        _parse_markdown_legenda,
        clear_legenda_cache,
        load_legenda,
        save_legenda_entries,
    )

    legenda_yaml = RULES_DIR / "legenda.yaml"
    if not legenda_yaml.is_file():
        for source in (
            bundle_asset_dir("rules") / "legenda.yaml",
            PACKAGE_ROOT / "rules" / "legenda.yaml",
        ):
            if source.is_file():
                shutil.copy2(source, legenda_yaml)
                break
        else:
            for md_candidate in (
                bundle_asset_dir("data") / "legenda.md",
                PACKAGE_ROOT.parent / "data" / "legenda.md",
            ):
                if md_candidate.is_file():
                    save_legenda_entries(
                        _parse_markdown_legenda(md_candidate.read_text(encoding="utf-8"))
                    )
                    break

    clear_legenda_cache()
    _merge_missing_legenda_from_bundle()
    if load_legenda():
        return

    log.error("Legenda estrutural não carregada após seed — tentando fallbacks")
    for md_candidate in (
        bundle_asset_dir("data") / "legenda.md",
        PACKAGE_ROOT.parent / "data" / "legenda.md",
        BUNDLE_ROOT / "backend" / "data" / "legenda.md",
        BUNDLE_ROOT / "data" / "legenda.md",
    ):
        if md_candidate.is_file():
            save_legenda_entries(_parse_markdown_legenda(md_candidate.read_text(encoding="utf-8")))
            clear_legenda_cache()
            if load_legenda():
                log.info("Legenda restaurada a partir de %s", md_candidate)
                return

    for yaml_candidate in (
        bundle_asset_dir("rules") / "legenda.yaml",
        PACKAGE_ROOT / "rules" / "legenda.yaml",
    ):
        if yaml_candidate.is_file() and yaml_candidate.resolve() != legenda_yaml.resolve():
            shutil.copy2(yaml_candidate, legenda_yaml)
            clear_legenda_cache()
            if load_legenda():
                log.info("Legenda restaurada a partir de %s", yaml_candidate)
                return

    log.error(
        "Legenda estrutural permanece vazia — descrições usarão fallback 'elemento estrutural'"
    )


def ensure_user_data_layout() -> None:
    """Cria diretórios do usuário e copia regras padrão na primeira execução desktop."""
    _resolve_paths()
    (DATA_ROOT / "workspaces").mkdir(parents=True, exist_ok=True)
    (DATA_ROOT / "logs").mkdir(parents=True, exist_ok=True)
    RULES_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    bundle_rules = bundle_asset_dir("rules")
    for name in _RULES_SEED_FILES:
        target = RULES_DIR / name
        if target.is_file():
            continue
        source = bundle_rules / name
        if source.is_file():
            shutil.copy2(source, target)

    if not DEFAULT_DESCRIPTIONS.is_file() and (PACKAGE_ROOT / "rules" / "descriptions.yaml").is_file():
        shutil.copy2(PACKAGE_ROOT / "rules" / "descriptions.yaml", DEFAULT_DESCRIPTIONS)

    _ensure_legenda_seeded()


def backend_port_file() -> Path:
    return DATA_ROOT / "backend.port"


def setup_logging(level: str | None = None, log_file: Path | None = None) -> None:
    """Configura logging estruturado para todo o pipeline."""
    log_level = (level or os.environ.get("LOG_LEVEL", "INFO")).upper()
    handlers: list[logging.Handler] = [logging.StreamHandler()]
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_file, encoding="utf-8"))
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format=LOG_FORMAT,
        datefmt=LOG_DATE_FORMAT,
        handlers=handlers,
        force=True,
    )


def get_log_level_from_env() -> str:
    return os.environ.get("LOG_LEVEL", "INFO")


_resolve_paths()
