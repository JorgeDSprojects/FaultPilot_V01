# 01 - Ingestion tutorial (Bosch + Fanuc)

## Objetivo del hito
En este hito construimos la capa de ingestion de FaultPilot para dos manuales reales:
- Fanuc AC Spindle (`ac_spindle_alarm_list.pdf`)
- Bosch CC220/320 (`Error_messages_CC_220107007331804.pdf`)

El objetivo no es aun responder preguntas al usuario final. El objetivo es dejar chunks limpios, trazables y persistidos en JSONL para que Hito 2 pueda indexar sin reprocesar PDFs.

---

## 1) Arquitectura minima del pipeline

Flujo aplicado:

1. CLI de ingestion (`faultpilot-ingest`) recibe rutas y documentos.
2. Pipeline orquesta parser Fanuc y parser Bosch.
3. Cada parser produce `ChunkRecord` normalizado.
4. Se escribe JSONL por documento en `data/processed/`.
5. Se ejecuta gate de validacion critica.
6. Se genera `manifest_hito1.json` con conteos y metadatos.

---

## 2) Decision de contrato de datos

### El Problema
Si cada parser produce estructuras distintas, retrieval y reranking se vuelven fragiles y costosos de mantener.

### Alternativas Evaluadas
- **Alternativa A:** cada parser devuelve su propio schema y se normaliza despues.
  - Descartada por aumentar deuda tecnica y errores silenciosos.
- **Alternativa B:** contrato canonico unico desde el primer paso.
  - Elegida por simplicidad operacional.

### La Decision
Definir `ChunkRecord` como contrato unico con campos obligatorios:
`alarm_code`, `equipment`, `manufacturer`, `source_doc`, `page`.

### Implementacion
```python
@dataclass(frozen=True)
class ChunkRecord:
    content: str
    alarm_code: str | None
    equipment: str
    manufacturer: str
    source_doc: str
    page: int
```

Archivo: `faultpilot/ingestion/contracts.py`

---

## 3) Decision de parser por fabricante

### El Problema
Fanuc y Bosch no comparten formato:
- Fanuc: tablas cortas y encabezados consistentes.
- Bosch: tablas largas con ruido de codificacion y estructura compleja.

### Alternativas Evaluadas
- **Alternativa A:** parser unico generico para ambos documentos.
  - Descartada por baja robustez y reglas demasiado ambiguas.
- **Alternativa B:** parser dedicado por fabricante.
  - Elegida por control fino y debugging mas rapido.

### La Decision
Implementar:
- `faultpilot/ingestion/parsers/fanuc.py`
- `faultpilot/ingestion/parsers/bosch.py`

### Implementacion
```python
def parse_fanuc_pdf(pdf_path: Path) -> list[ChunkRecord]:
    records: list[ChunkRecord] = []
    with pdfplumber.open(pdf_path) as pdf:
        for page_number, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            records.extend(extract_fanuc_chunks_from_lines(text.splitlines(), page_number))
    return records
```

```python
def parse_bosch_pdf(pdf_path: Path) -> tuple[list[ChunkRecord], list[dict[str, int | str]]]:
    # filtra tablas tipo ERROR CAUSE / ERROR REMEDY
    # normaliza ruido y extrae codigo + contenido por fila
```

---

## 4) Decision de chunking table-aware

### El Problema
Si chunking corta una fila en medio, se pierde la relacion causa-remedio.

### Alternativas Evaluadas
- **Alternativa A:** chunking por longitud de caracteres.
  - Descartada por romper semantica de tabla.
- **Alternativa B:** chunking por fila/bloque de error.
  - Elegida por trazabilidad y precision para alarm lookup.

### La Decision
La unidad minima de chunk es la fila de error parseada. Cada chunk conserva:
- codigo (si existe)
- descripcion/causa
- remedy
- pagina y documento fuente

### Implementacion
```python
return ChunkRecord(
    content="\n".join(content_parts),
    alarm_code=alarm_code,
    equipment="CC220/320",
    manufacturer="Bosch",
    source_doc=BOSCH_MANUAL_FILENAME,
    page=page_number,
    raw_table_ref=f"table_{table_index}_row_{row_index}",
)
```

---

## 5) Decision de persistencia

### El Problema
Hito 2 necesita artefactos estables para indexacion BM25/Chroma.

### Alternativas Evaluadas
- **Alternativa A:** `json` gigante por documento.
  - Descartada porque complica procesamiento incremental.
- **Alternativa B:** `jsonl` por documento.
  - Elegida por streaming, debug y trazabilidad linea a linea.

### La Decision
Persistir:
- `data/processed/fanuc_ac_spindle_chunks.jsonl`
- `data/processed/bosch_cc220_chunks.jsonl`
- `data/processed/manifest_hito1.json`
- `data/processed/validation_hito1.json`

### Implementacion
```python
def write_jsonl(path: Path, chunks: Iterable[ChunkRecord]) -> None:
    with path.open("w", encoding="utf-8") as file:
        for chunk in chunks:
            file.write(json.dumps(chunk.to_dict(), ensure_ascii=False) + "\n")
```

---

## 6) Validacion activa del hito

Aplicamos una validacion critica automatica sobre todos los chunks:
- manufacturer presente
- source_doc presente
- page valida (>0)
- equipment presente

Salida:
- `data/processed/validation_hito1.json`

Resultado del run actual:
- `checked_chunks`: 705
- `critical_errors`: 0
- `status`: `ok`

---

## 7) Como ejecutar el pipeline

```bash
uv run faultpilot-ingest --documents bosch fanuc --raw-dir data/raw --processed-dir data/processed --parser-version 0.1.0
```

Pruebas unitarias:

```bash
uv run python -m pytest tests -v
```

---

## 8) Limites conocidos y siguientes mejoras

1. En Bosch aun pueden aparecer artefactos de OCR/encoding en algunos bloques.
2. Faltan reglas de confidencia por fila para marcar chunks dudosos con mayor precision.
3. En Hito 2 conviene agregar normalizacion semantica previa al indexado (por ejemplo, expandir sinonimos de fallos).

Estas limitaciones no bloquean Hito 2, pero son mejoras de calidad recomendadas.
