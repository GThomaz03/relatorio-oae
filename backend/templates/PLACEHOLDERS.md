# Contrato de placeholders — report_template.docx (modelo RSP)

Template baseado em `RSP-116RJ-233-243-ACA-FUN-RT-L1-001-R00.docx`, renderizado com [docxtpl](https://docxtpl.readthedocs.io/).

## Secção ANOMALIAS CONSTATADAS

Estrutura hierárquica com estilos Word originais:

| Nível | Estilo Word | Placeholder |
|-------|-------------|-------------|
| Macrosecção | Heading 4 | `{{ macro.title }}` — ex. SUPERESTRUTURA |
| Elemento | Heading 4 | `{{ element.title }}` — ex. Viga longarina |
| Item | Normal | `{{ item.text }}` — bullet `-\t...` com referência de fotos |

```jinja2
{% for macro in anomaly_macros %}
{{ macro.title }}
{% for element in macro.elements %}
{{ element.title }}
{% for line in element.lines %}
{{ line.line }}
{% endfor %}
{% endfor %}
{% endfor %}
```

### Campos

- `anomaly_macros[]` — lista de macrosecções
  - `title` — SUPERESTRUTURA, MESOESTRUTURA, …
  - `elements[]`
    - `title` — Viga longarina, Pilares, …
      - `lines[]`
      - `line` — linha completa com bullet e `(Fotos …)`

## ANEXO VI — RELATÓRIO FOTOGRÁFICO

| Campo | Estilo | Descrição |
|-------|--------|-----------|
| `{{ photo.image }}` | Normal | Imagem embutida (InlineImage) |
| `{{ photo.code }}` | Caption | Código do ficheiro, ex. E116K244710F001S |
| `{{ photo.location_line }}` | Normal | Linha da obra, ex. Ponte sobre o Rio … |
| `{{ photo.description_line }}` | Normal | Vista/descrição, ex. Vista Superior da OAE. |

```jinja2
{% for photo in photos %}
{{ photo.image }}
{{ photo.code }}
{{ photo.location_line }}
{{ photo.description_line }}
{% endfor %}
```

## Variáveis globais (opcionais)

| Placeholder | Descrição |
|-------------|-----------|
| `{{ bridge_id }}` | Identificador da obra |
| `{{ bridge_location_line }}` | Linha padrão de localização |
| `{{ total_anomalies }}` | Total de anomalias |
| `{{ total_photos }}` | Total de fotografias |

## Template Word

O template base fica em `backend/templates/report_template.docx`. Para alterar placeholders ou layout, edite esse arquivo diretamente (ou substitua por uma versão RSP atualizada).

## Notas de formatação (aplicada em `docx_formatting.py`)

- **Fotos:** 12 cm × 9 cm (`PHOTO_WIDTH_MM` / `PHOTO_HEIGHT_MM` em `config.py`)
- **Corpo e legendas:** Arial 10 pt (estilos `Normal`, `Caption`)
- **Títulos:** mantêm estilo original do template (`Heading 2/4`, `Title`)
- **Anexo fotográfico:** parágrafos centralizados a partir de `ANEXO VI — RELATÓRIO FOTOGRÁFICO`
- **Quebra de página:** inserida antes do anexo (template + pós-processamento)

## Notas (gerais)

- Estilos, cabeçalhos e rodapés permanecem no `.docx` base.
- Cada item de anomalia inclui referências `(Foto …)` / `(Fotos … e …)` geradas automaticamente.
- Para alterar frases técnicas, edite `backend/rules/descriptions.yaml`.
