# descripcion
FaultPilot: **"OT Troubleshooting Assistant"** — un asistente RAG que ayuda a técnicos de mantenimiento a diagnosticar alarmas y fallos en equipos industriales (CNC, variadores, PLCs).


# caso de uso
Queremos validar la generacion de un sistema que sea capaz de identificar las alarmas que provienen desde un sistema OT
Para esto hemos planteado de manera un par de premisas de importancia

+ multiples marcas: por lo general vamos a tener un monton de modelos en las fabricas, por lo que debemos poder cribar la informacion de manera precisa.
+ Manuales con diferentes contenidos: la ingestion de los manuales plantea retos particulares por fabricante, pero tambien por su contenido.
+ Tamaños grandes de contexto, mas de 100 paginas


  - **Fanuc AC Spindle Alarms** (3 págs) — listas de alarmas por modelo de variador, formato tabular limpio
  - **Bosch CC 220/320 Error Messages** (146 págs) — manual extenso de errores de CNC Bosch con códigos, descripciones y procedimientos de resolución, incluye tablas con estructura compleja
  - **GE Fanuc Series 90-30/20/Micro** (248 págs, en español) — manual completo de PLC con programación, troubleshooting, instrucciones ladder, y tabla de fallos


Aquí va cómo encaja cada opcional en este escenario concreto con estos documentos:

**Los 7+ que te recomiendo implementar:**

1. **Streaming** — directo con Gradio `yield`.

2. **Dominio específico** — mantenimiento industrial / troubleshooting de equipos CNC y PLC. Nada que ver con un tutor de AI.

3. **Dos fuentes de datos adicionales** — ya tienes tres PDFs de fabricantes distintos (Fanuc, Bosch, GE Fanuc). Son tres fuentes reales de tu industria.

4. **Procesamiento de PDFs** — los tres documentos son PDFs. El de Bosch tiene tablas con encoding roto (los `ÁÁÁÁ` que vi), así que vas a necesitar rasterizar páginas y parsear con visión o pdfplumber. El de GE Fanuc está en español. Esto demuestra que manejas documentos reales con sus problemas.

5. **Structured JSON outputs** — durante la ingestión, cada chunk se estructura como:
```json
{
  "alarm_code": "AL-09",
  "equipment": "A06B-6055-Hxxx",
  "manufacturer": "Fanuc",
  "category": "thermal",
  "description": "Radiator for power semiconductor overheat",
  "source_doc": "ac_spindle_alarm_list.pdf",
  "page": 1,
  "language": "en"
}
```
Esto alimenta el metadata filtering directamente.

6. **Hybrid search** — BM25 para cuando el técnico busca un código exacto ("AL-09", "error 354") + dense retrieval para consultas semánticas ("el motor se sobrecalienta"). Esencial en este dominio porque los códigos de error son búsquedas exactas.

7. **Reranker** — cross-encoder sobre los resultados combinados. Importante porque un código como "AL-01" aparece en múltiples modelos Fanuc con significados ligeramente distintos, y el reranker prioriza el contexto correcto.

8. **Metadata filtering** — filtrar por fabricante (Fanuc / Bosch / GE), tipo de equipo (spindle drive / CNC / PLC), idioma (EN/ES). El usuario puede seleccionar en la UI "estoy trabajando con un equipo Bosch CC220" y los resultados se filtran.

9. **Query routing** — tres rutas claras:
  - Dual-layer query router: regex-based local classifier (free, handles alarm codes) + LLM-based classifier (for ambiguous queries). 
   - Routes to alarm_lookup (BM25 priority), troubleshooting (dense priority), or programming (GE Fanuc filter). 
   - Implemented with LangChain LCEL RunnableLambda.


