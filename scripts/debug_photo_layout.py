"""Debug layout function in isolation."""
from pathlib import Path

from docx.oxml.ns import qn
from docxtpl import DocxTemplate

from backend.core.docx_formatting import apply_photo_annex_page_layout
from backend.core.parser_excel import parse_excel
from backend.core.parser_images import attach_images_to_anomalies
from backend.core.photo_generator import build_photo_report
from backend.core.text_generator import build_sections
from backend.core.word_generator import build_context, _inject_inline_images
from backend.models.inspection import InspectionReport, ReportMetadata

DRAWING = f".//{qn('w:drawing')}"
base = Path("backend/tests/fixtures")
anomalies, _ = parse_excel(base / "inspection.xlsx")
anomalies, _ = attach_images_to_anomalies(anomalies, base / "images")
groups = build_sections(anomalies)
photo_report = build_photo_report(anomalies, groups=groups)
report = InspectionReport(
    metadata=ReportMetadata(
        excel_path=base / "inspection.xlsx",
        images_dir=base / "images",
        template_path=base / "report_template.docx",
        bridge_id="E116",
    ),
    anomalies=anomalies,
    groups=groups,
    photo_report=photo_report,
)

doc = DocxTemplate(str(base / "report_template.docx"))
context = build_context(report)
_inject_inline_images(doc, context)
doc.render(context)

apply_photo_annex_page_layout(doc.docx)

paragraphs = list(doc.docx.paragraphs)
annex_idx = next(
    i for i, p in enumerate(paragraphs) if "ANEXO" in p.text.upper() and "FOTOGR" in p.text.upper()
)
img_indices = [
    i for i, p in enumerate(paragraphs) if i > annex_idx and p._element.findall(DRAWING)
]
print("images", img_indices)
for n, img_idx in enumerate(img_indices):
    blanks = 0
    for i in range(img_idx - 1, annex_idx, -1):
        if not paragraphs[i].text.strip():
            blanks += 1
        else:
            break
    print(f"photo {n + 1}: blanks before = {blanks}")
