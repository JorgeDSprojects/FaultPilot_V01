---
name: gradio-stream-isolation
description: Previene cuelgues al integrar respuestas en streaming (yield) del LLM en Gradio.
license: MIT
compatibility: opencode
---

## Qué hago
Establezco un protocolo de prueba seguro para implementar respuestas generativas (streaming) sin bloquear los WebSockets ni la UI de Gradio.

## Cuándo usarme
Usa esta habilidad al implementar la función generadora (streaming) del RAG o al conectar tu grafo de LangGraph al componente Chatbot de Gradio.

## Reglas de ejecución
1. **Aislamiento síncrono:** Antes de conectar el generador a Gradio, crea un script temporal (`test_stream.py`) que invoque el LangGraph y haga un `print` iterativo de los tokens en la terminal. Solo cuando esto funcione sin bloqueos, pásalo a la UI.
2. **Carga en segundo plano:** Asegúrate de que las consultas lentas (ChromaDB, Reranker) se resuelvan *antes* de iniciar el `yield` del LLM, para evitar que la UI lance un timeout esperando el primer token.