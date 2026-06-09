---
name: architectural-storytelling
description: Estructura la documentacion tecnica como material educativo explicando el por que de las decisiones.
license: MIT
compatibility: opencode
---

## Qué hago
Transformo la documentación técnica básica en material educativo avanzado ("Tutor Mode"), explicando el razonamiento detrás de las decisiones de arquitectura de software.

## Cuándo usarme
Usa esta habilidad siempre que estés redactando archivos Markdown dentro de la carpeta `training/` o explicando conceptos complejos de arquitectura RAG al usuario.

## Reglas de ejecución
Estructura cada explicación técnica usando este formato:
1. **El Problema:** Describe la limitación técnica u objetivo inicial.
2. **Alternativas Evaluadas:** Qué otra opción existía y por qué se descartó (ej. "PyPDF2 vs pdfplumber").
3. **La Decisión:** La solución elegida.
4. **Implementación:** Muestra el fragmento de código clave que lo resuelve.