# Sprint Plan - Hito 1 (Setup y Parsers PDF)

## Objetivo del hito
Dejar lista la base de ingestion para los manuales:
- Bosch CC220/320 (`Error_messages_CC_220107007331804.pdf`)
- Fanuc AC Spindle (`ac_spindle_alarm_list.pdf`)

El resultado de este hito debe producir chunks estructurados y validados en formato JSONL, listos para indexacion en Hito 2 (BM25 + ChromaDB).

## Alcance aprobado
- Incluye: setup del modulo de ingestion, parser Fanuc, parser Bosch, chunking table-aware, validacion de calidad y documentacion del hito.
- Excluye: GE Fanuc, retrieval hibrido, router de intents, pipeline RAG completo, UI final.

## Estructura objetivo del hito (sin implementar aun)
- `data/raw/` (entrada): PDFs originales.
- `data/processed/fanuc_ac_spindle_chunks.jsonl` (salida)
- `data/processed/bosch_cc220_chunks.jsonl` (salida)
- `data/processed/manifest_hito1.json` (conteos, fecha, version parser, incidencias)

## Contrato de datos de chunk
Cada linea JSONL debe incluir como minimo:
- `alarm_code`
- `equipment`
- `manufacturer`
- `source_doc`
- `page`

Campos recomendados para mejorar retrieval posterior:
- `category`
- `description`
- `language`
- `raw_table_ref`

Reglas minimas:
- `source_doc` y `page` son obligatorios en todos los chunks.
- No se aceptan chunks sin `manufacturer`.
- Si no existe `alarm_code` explicito, registrar `null` y mantener trazabilidad de tabla/pagina.

## Tareas exactas del Hito 1

### T1 - Setup de ingestion
**Meta:** preparar entorno y estructura para parsing reproducible en CPU.

Pasos:
1. Definir estructura de carpetas/modulos para `ingestion/`.
2. Registrar dependencias de parsing PDF necesarias en el proyecto.
3. Definir comando de ejecucion del pipeline de ingestion.
4. Verificar instalacion y arranque basico sin errores.

Entregables:
- Base de proyecto preparada para ejecutar parsers por documento.

Criterio de aceptacion:
- Entorno reproducible y comando de ingestion ejecutable localmente.

### T2 - Esquema y normalizacion de metadatos
**Meta:** establecer un contrato unico para todos los chunks.

Pasos:
1. Definir tipos esperados por campo obligatorio y recomendado.
2. Definir reglas de limpieza de texto y normalizacion de codigos de alarma.
3. Definir politicas de fallback para campos faltantes.

Entregables:
- Especificacion formal del esquema usado por ambos parsers.

Criterio de aceptacion:
- Todos los chunks de salida validan contra el contrato definido.

### T3 - Parser Fanuc AC Spindle
**Meta:** extraer filas tabulares con maxima fidelidad semantica.

Entrada:
- `data/raw/ac_spindle_alarm_list.pdf`

Pasos:
1. Extraer tablas por pagina.
2. Mapear columnas a campos del contrato (`alarm_code`, causa/descripcion, equipo).
3. Normalizar valores y generar chunks por fila semantica.
4. Persistir salida en `fanuc_ac_spindle_chunks.jsonl`.

Entregables:
- JSONL completo de Fanuc con trazabilidad por pagina.

Criterio de aceptacion:
- Cobertura de filas esperadas sin perdida de columnas criticas.

### T4 - Parser Bosch CC220/320 (tablas complejas)
**Meta:** reconstruir tablas complejas sin corromper relaciones codigo-descripcion-procedimiento.

Entrada:
- `data/raw/Error_messages_CC_220107007331804.pdf`

Pasos:
1. Implementar extraccion principal de texto/tablas por pagina.
2. Definir fallback para paginas conflictivas (tablas partidas, celdas rotas o ruido OCR).
3. Reensamblar bloques semanticos por alarma/error.
4. Persistir salida en `bosch_cc220_chunks.jsonl`.
5. Registrar paginas con baja confianza para revision.

Entregables:
- JSONL de Bosch con incidencias trazadas.

Criterio de aceptacion:
- Muestra representativa validada manualmente sin ruptura de tablas criticas.

### T5 - Chunking table-aware
**Meta:** evitar que el chunking rompa filas o contexto de resolucion.

Pasos:
1. Definir unidad minima de chunk (fila o bloque de error completo).
2. Garantizar que cada chunk conserva contexto suficiente para responder en Hito 3.
3. Enriquecer chunks con metadatos de idioma (`en` para Fanuc, segun contenido real para Bosch).

Entregables:
- Chunks estables, trazables y coherentes para retrieval hibrido.

Criterio de aceptacion:
- Ningun chunk critico queda sin `source_doc` y `page`.

### T6 - Validacion de calidad (gate obligatorio antes de Hito 2)
**Meta:** verificar integridad estructural y semantica de salida.

Pasos:
1. Ejecutar muestreo de chunks Bosch y Fanuc.
2. Validar por muestra:
   - JSON valido
   - metadatos obligatorios completos
   - fuente/pagina correctas
   - tabla no corrompida
3. Documentar incidencias y aplicar correcciones de parser si procede.

Entregables:
- Reporte de validacion del hito.

Criterio de aceptacion:
- 0 errores criticos de esquema/trazabilidad.

### T7 - Persistencia y manifiesto
**Meta:** cerrar salidas consumibles por Hito 2.

Pasos:
1. Consolidar archivos JSONL finales en `data/processed/`.
2. Generar `manifest_hito1.json` con:
   - cantidad de chunks por documento
   - fecha de generacion
   - version de parser
   - incidencias conocidas

Entregables:
- Artefactos finales de ingestion listos para indexacion.

Criterio de aceptacion:
- Hito 2 puede arrancar sin reprocesar PDF manualmente.

### T8 - Documentacion del hito
**Meta:** asegurar trazabilidad tecnica y transferencia de conocimiento.

Pasos:
1. Actualizar `Documentation/changelog.md` con decisiones y cambios.
2. Crear `Documentation/Training/01_ingestion_tutorial.md` explicando que, como y por que.
3. Incluir decisiones de arquitectura y alternativas descartadas.

Entregables:
- Changelog del hito actualizado.
- Tutorial de training listo para onboarding tecnico.

Criterio de aceptacion:
- Un tercero puede reproducir la ingestion siguiendo la documentacion.

## Definition of Done - Hito 1
- Parsers Bosch + Fanuc ejecutables y validados.
- Chunks JSONL generados y revisados.
- Metadatos obligatorios completos en todos los registros.
- Manifiesto de salida creado en `data/processed/manifest_hito1.json`.
- Documentacion del hito preparada para pasar a Hito 2.
