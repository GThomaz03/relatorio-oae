# SPECIFICATION — OAE REPORT GENERATOR

Version: 1.0
Methodology: Spec Driven Development

---

# 1. PURPOSE

Develop a backend system capable of generating standardized OAE technical reports automatically from Excel inspection spreadsheets and inspection images.

---

# 2. SYSTEM SCOPE

The system shall:

- parse Excel inspection files
- normalize inspection data
- map images automatically
- generate technical descriptions
- organize anomalies by sections
- generate photographic reports
- populate Word templates
- export `.docx` reports

---

# 3. NON-GOALS

The MVP will NOT include:

- authentication
- cloud infrastructure
- AI-generated decisions
- image recognition
- multi-user support
- web frontend
- PDF export

---

# 4. INPUT SPECIFICATION

## 4.1 Excel File

Supported format:

- `.xlsx`

Required columns:

| Column      | Required |
| ----------- | -------- |
| Local       | YES      |
| Núm.        | YES      |
| Face        | YES      |
| Vão/AP      | NO       |
| Vista       | NO       |
| Anomalia    | YES      |
| W           | NO       |
| Quant.      | NO       |
| Comp (m)    | NO       |
| Larg (m)    | NO       |
| Quant Fotos | YES      |
| Disp.       | YES      |
| Cam inicial | YES      |
| Cam final   | YES      |
| Observações | NO       |
| Área m²-m   | NO       |

---

## 4.2 Images

Supported formats:

- `.jpg`
- `.jpeg`
- `.png`

Naming pattern:

E116K244710F001S.jpg

---

## 4.3 Word Template

Supported format:

- `.docx`

Must contain placeholders.

---

# 5. OUTPUT SPECIFICATION

Generated file:

- `.docx`

Must contain:

- preserved formatting
- anomaly descriptions
- grouped sections
- inserted images
- captions
- technical structure

---

# 6. DATA MODEL

## 6.1 Anomaly

```python
class Anomaly:
    local: str
    number: str
    face: str
    span: str
    view: str

    anomaly_type: str
    crack_width: str

    quantity: float
    length: float
    width: float
    area: float

    observations: str

    images: list[str]
```

7. SYSTEM MODULES
   7.1 parser_excel.py

Responsibilities:

read spreadsheet
validate structure
normalize fields
create anomaly objects
7.2 parser_images.py

Responsibilities:

locate images
validate image existence
map image ranges
7.3 text_generator.py

Responsibilities:

generate technical descriptions
group similar anomalies
generate report sections
7.4 photo_generator.py

Responsibilities:

generate photo report structure
create captions
organize image sequences
7.5 word_generator.py

Responsibilities:

load Word template
inject placeholders
insert images
export .docx 8. BUSINESS RULES
8.1 Image Range Expansion

Example:

00136 até 00138

Must produce:

00136
00137
00138

8.2 Automatic Grouping

Similar anomalies shall be grouped.

Example:

Input:

VL1
VL2

Output:
"Cracks observed in girders VL1 and VL2."

8.3 Formatting Preservation

The system must preserve:

headers
footers
styles
spacing
pagination 9. ERROR HANDLING

The system shall validate:

missing columns
invalid images
invalid ranges
duplicated references
invalid file formats

Errors must be descriptive.

10. LOGGING

The system shall generate logs for:

parsing
normalization
image mapping
Word generation
export process 11. PERFORMANCE REQUIREMENTS

The system should support:

500+ images
1000+ anomalies

Expected generation time:

under 2 minutes 12. CODE REQUIREMENTS

The project must:

use typing
follow SOLID principles
separate responsibilities
avoid business logic inside UI
use reusable services
support future API integration 13. FUTURE FEATURES
Planned
AI-assisted writing
PDF export
Web interface
Review mode
Severity classification
OCR integration
Computer vision 14. ACCEPTANCE CRITERIA

The MVP is considered complete when:

Excel is parsed correctly
anomalies are grouped
images are inserted automatically
Word report is generated successfully
formatting is preserved
captions are generated automatically
