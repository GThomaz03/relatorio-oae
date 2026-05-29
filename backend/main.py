"""CLI de geração de relatórios OAE."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from backend.config import DEFAULT_TEMPLATE, OUTPUT_DIR, SAMPLES_DIR, setup_logging
from backend.core.validators import ExcelStructureError, ImageNotFoundError
from backend.services.report_pipeline import ReportConfig, generate_report


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Gerador automatizado de relatórios técnicos de inspeção OAE",
    )
    parser.add_argument(
        "--excel",
        type=Path,
        default=SAMPLES_DIR / "inspection.xlsx",
        help="Caminho da planilha Excel (.xlsx)",
    )
    parser.add_argument(
        "--images",
        type=Path,
        default=SAMPLES_DIR / "images",
        help="Pasta com imagens de inspeção",
    )
    parser.add_argument(
        "--template",
        type=Path,
        default=DEFAULT_TEMPLATE,
        help="Template Word (.docx) com placeholders docxtpl",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=OUTPUT_DIR,
        help="Diretório de saída do relatório gerado",
    )
    parser.add_argument(
        "--excel-sheet",
        type=str,
        default=None,
        help="Nome da aba Excel (padrão: detecta db_ficha automaticamente)",
    )
    parser.add_argument(
        "--bridge-id",
        type=str,
        default=None,
        help="Identificador da obra (usado no nome do arquivo)",
    )
    parser.add_argument(
        "--bridge-location",
        type=str,
        default="Ponte — BR —  — Km —",
        help="Linha de localização da obra no anexo fotográfico",
    )
    parser.add_argument(
        "--title",
        type=str,
        default="Relatório de Inspeção OAE",
        help="Título do relatório",
    )
    parser.add_argument(
        "--output-filename",
        type=str,
        default=None,
        help="Nome do arquivo DOCX de saída (opcional)",
    )
    parser.add_argument(
        "--photo-km",
        type=str,
        default=None,
        help="Km compacto para código RSP (ex.: 244710 para Km 244+710). Requer --bridge-id.",
    )
    parser.add_argument(
        "--photo-direction",
        type=str,
        default="S",
        help="Sufixo de sentido da obra no código RSP (default: S)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Falha em avisos de validação (imagens ausentes, etc.)",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Nível de logging",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    setup_logging(args.log_level)

    config = ReportConfig(
        excel_path=args.excel,
        images_dir=args.images,
        template_path=args.template,
        output_dir=args.output,
        excel_sheet=args.excel_sheet,
        bridge_id=args.bridge_id,
        title=args.title,
        bridge_location_line=args.bridge_location,
        photo_km=args.photo_km,
        photo_direction=args.photo_direction,
        strict=args.strict,
        output_filename=args.output_filename,
    )

    try:
        result = generate_report(config)
        print(f"Relatório gerado: {result.output_path}")
        print(
            f"Resumo: {len(result.report.anomalies)} anomalia(s), "
            f"{len(result.report.groups)} grupo(s), "
            f"{result.report.photo_report.total_photos if result.report.photo_report else 0} foto(s) "
            f"em {result.elapsed_seconds:.2f}s"
        )
        if result.warnings:
            print(f"Avisos: {result.warnings}")
        return 0
    except (ExcelStructureError, ImageNotFoundError, FileNotFoundError) as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Erro inesperado: {exc}", file=sys.stderr)
        raise


if __name__ == "__main__":
    sys.exit(main())
