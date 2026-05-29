# OAE Report Generator

## Overview

OAE Report Generator is a **Windows desktop application** (Electron + FastAPI) designed to automate the creation of technical inspection reports for OAEs (Obras de Arte Especiais).

The current manual process involves:

- Receiving inspection spreadsheets
- Organizing hundreds of photos
- Writing repetitive technical descriptions
- Formatting Word documents manually
- Creating photographic reports
- Reviewing layout and pagination

The objective of this project is to automate most of this workflow.

---

# Business Problem

Currently, engineers and technical teams spend many hours:

- organizing images
- writing repetitive descriptions
- formatting Word files
- creating photo legends
- grouping anomalies
- maintaining report standards

This process is:

- repetitive
- error-prone
- hard to scale
- highly manual

The system aims to reduce report generation time from hours to minutes.

---

# Main Goal

Transform:

- Excel inspection spreadsheets
- inspection image folders
- Word templates

into:

- standardized technical Word reports

with minimal manual editing.

---

# Expected Workflow

## Input

### Excel Inspection Spreadsheet

Contains:

- structural elements
- anomaly types
- locations
- dimensions
- crack openings
- observations
- photo references

---

### Inspection Images

Image naming pattern:

E116K244710F001S.jpg

The spreadsheet determines:

- initial image
- final image

The system must automatically map all related images.

---

### Word Template

A standardized `.docx` template with:

- styles
- headers
- footers
- pagination
- placeholders

---

# Output

Generated `.docx` report containing:

- technical descriptions
- grouped anomalies
- organized chapters
- automatic photo report
- captions
- formatted sections
- preserved template formatting

---

# Technical Goals

The system must:

- automate at least 90% of the report
- preserve formatting consistency
- reduce repetitive work
- improve scalability
- reduce human error

---

# Architecture Philosophy

The system must be:

- modular
- scalable
- maintainable
- backend-first
- template-driven
- data-oriented

---

# Recommended Stack

## Backend

- Python 3.12+
- pandas
- openpyxl
- python-docx
- docxtpl
- Pillow
- pydantic

---

## Frontend (Future)

- React
- TypeScript
- Tailwind
- Tauri or Electron

---

# Core Concepts

## Anomaly

An anomaly represents:

- a structural issue
- a deterioration
- a technical occurrence

Examples:

- vertical cracks
- mapped cracks
- erosion
- exposed reinforcement
- moisture stains
- displacement
- deterioration

---

## Structural Elements

Examples:

| Code | Meaning            |
| ---- | ------------------ |
| VL   | Viga Longarina     |
| VT   | Viga Transversina  |
| LB   | Laje em Balanço    |
| P    | Pilar              |
| JD   | Junta de Dilatação |
| BR   | Barreira Rígida    |

---

# Key Requirement

The system MUST NOT generate Word files from scratch.

Instead:

- a template `.docx` must be used
- placeholders must be injected dynamically
- styles and formatting must remain untouched

---

# Processing Pipeline

Excel
→ Parsing
→ Normalization
→ Data Models
→ Grouping
→ Text Generation
→ Photo Organization
→ Word Template Injection
→ DOCX Export

---

# Future Possibilities

## AI Integration

- automatic technical writing
- severity classification
- grammar correction
- summarization

---

## Computer Vision

- crack detection
- anomaly classification
- OCR extraction
- automated damage recognition

---

# Development Philosophy

The project should prioritize:

1. Robust backend
2. Clean architecture
3. Data validation
4. Reusable modules
5. Scalability
6. Separation of concerns

UI should only be developed after the backend engine is stable.

---

# Expected End Result

A professional system capable of generating engineering inspection reports automatically and consistently.
