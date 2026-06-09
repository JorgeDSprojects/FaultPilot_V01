### FASE 0 — Diseño y Arquitectura (antes de tocar código)

**Qué aprendes:** cómo se diseña un sistema antes de escribir una línea.

- Definir el scope funcional exacto: qué puede hacer el asistente, qué NO puede hacer
- Elegir el stack tecnológico y justificarlo (vector store, embeddings, LLM, framework)
- Diseñar la arquitectura del pipeline RAG (ingestión → retrieval → generación)
- Definir la estructura del repositorio
- Mapear los 9 opcionales contra componentes concretos del sistema
- Escribir el README esqueleto con la descripción del proyecto

**Entregable:** documento de diseño + estructura del repo vacía


## FASE 0 — 

# Diseño
#### Objetivo inicial
Un servicio que en base a la informacion de los manuales tecnicos, podamos consultar cual es la alarma y si existe algun tipo de actuacion a realizar.

#### A quien va dirigido
El asistente sirve para los dos perfiles, y el query routing se encarga de adaptar la respuesta.

**A) Un técnico de mantenimiento en planta** — está delante de la máquina, tiene un código de alarma en la pantalla, necesita saber qué significa y cómo resolverlo. Quiere respuestas rápidas, concretas, accionables. No le importa la teoría.

**B) Un ingeniero/integrador** — está diseñando, configurando o haciendo commissioning. Necesita entender el sistema más a fondo: cómo programar el PLC, cómo se relacionan los componentes, qué significan los parámetros.

#### elegir las maquinas

Tenemos 3 manuales de 3 máquinas distintas. Hay dos formas de plantear la experiencia:

**A) El usuario elige su equipo antes de preguntar** — al entrar, selecciona "estoy trabajando con un Fanuc / Bosch / GE Fanuc". Todas las respuestas se filtran a ese contexto. Más preciso, menos ruido. Simula una herramienta real de planta donde sabes en qué máquina estás.

**B) El usuario pregunta libremente y el sistema se busca la vida** — no hay selección previa. Si pregunta "AL-09" el sistema sabe que es Fanuc por el formato. Si pregunta "motor overheating" busca en todos. Más flexible, pero puede devolver resultados mezclados de distintos fabricantes.

**C) Filtro opcional** — hay un dropdown de fabricante pero viene en "Todos" por defecto. El usuario puede restringirlo si quiere, pero no está obligado. Combina flexibilidad con precisión cuando el usuario la necesita.

Por ahora vamos a usar la opcion C, porque de esta manera usamos la interfaz para que el usuario haga el trabajo, menos tokens.

### REQUISITOS FUNCIONALES
#### qué puede hacer 
**Funcionalidades:**

1. **Búsqueda de códigos de alarma** — "¿Qué es AL-09?" → respuesta estructurada con código, causa, remedio. Esto es el core.
2. **Troubleshooting por síntomas** — "El motor se sobrecalienta" → el sistema busca alarmas y procedimientos relacionados. También core.
3. **Referencia de programación PLC** — "¿Cómo usar un timer en ladder?" → extrae la info del manual GE Fanuc. Tercer pilar.
4. **Respuesta multilingüe** — el usuario pregunta en español, el contexto está en inglés (Fanuc/Bosch), el sistema traduce y responde en español. Y viceversa.
5. **Trazabilida de la informacion** — en la respuesta nos de que manual y paginas esta usando para saber que la respuesta es real.

#### Que no puede hacer

**Fuera de scope:**

1. **No conectividad en tiempo real** — no se conecta a PLCs, SCADA ni lee alarmas en vivo. Solo trabaja con la documentación offline indexada a traves de la interfaz de gradio.
2. **No historial conversacional** — cada pregunta es independiente. No hay "¿y en el otro modelo?" que referencie turnos anteriores.
3. **No comparación entre modelos** — no genera tablas comparativas ni contrasta alarmas entre equipos. Si el usuario quiere comparar, hace dos preguntas.
4. **No genera imágenes ni diagramas** — solo respuestas de texto con citación de fuentes.
5. **No fine-tuning de modelos** — usa LLMs y embeddings preentrenados tal cual.
6. **No procesamiento de documentos del usuario** — el knowledge base son los 3 manuales pre-indexados. El usuario no sube sus propios PDFs.
7. **No voz** — solo texto, ni speech input ni output.

### REQUISITOS NO FUNCIONALES

**Rendimiento:**

1. **Tiempo de respuesta** — desde que el usuario envía la query hasta que empieza a ver texto. Con streaming, lo crítico es el "time to first token".
   Consideramos que hay: routing (~1s), retrieval (~1-2s en CPU), reranking (~1s en CPU), y luego el LLM empieza a streamear.
   Estamos hablando de **3-5 segundos hasta el primer token**.

   Sabemos que la experiencia de usuario se vera afectada, pero dependemos de factores externos, el primero es que el despliegue
   es en HF Spaces free tier, esto limita.
   en este momento estamos mas centrado en que tal es el desempeño
   

3. **Coste por sesión** — el curso exige que el usuario pueda probar todo con menos de $0.50. Con GPT-4o-mini estimamos ~$0.05 por 30 queries. Esto lo cumplimos de sobra.

**Infraestructura:**

3. **HF Spaces free tier** — esto condiciona mucho. Significa CPU only (no GPU), RAM limitada (~16GB), y disco limitado. Los modelos de embeddings y el reranker tienen que correr en CPU. ¿Tienes HF Pro o vamos con el free tier?

4. **Persistencia** — ChromaDB persiste en disco. Pero en HF Spaces free tier, el filesystem se resetea cuando el Space se duerme por inactividad. Esto significa que el vector store debe reconstruirse al arrancar o incluirse pre-construido en el repo. ¿Cuál prefieres?
   - **A)** Incluir el ChromaDB pre-construido en el repo (arranca rápido, pero el repo pesa más)
   - **B)** Reconstruir al arrancar desde los JSONs (repo ligero, pero tarda ~2-3 min en arrancar)

Escogemos A porque el proyecto busca validar lo realizado en el curso, no es un despliegue real.

**Seguridad:**

5. **API keys** — nunca se almacenan, nunca se loguean, solo se usan en memoria para la sesión. Esto ya lo tenemos claro.

6. **Coste del usuario** — no ejecutar pipelines costosos con la key del usuario. Solo routing + generación. Retrieval, embeddings y reranking corren localmente.

¿Cómo lo ves? Necesito tu decisión sobre el punto 3 (free tier vs Pro) y el punto 4 (ChromaDB pre-built vs rebuild on start).


# Arquitectura





Voy a construir todo el diseño fundacional antes de tocar código. Empiezo por analizar el stack y diseñar la arquitectura.

### 0.1 — Decisiones de Stack

Como interfaz gradio
Primero, las elecciones tecnológicas y por qué:

| Componente | Elección | Por qué |
|---|---|---|
| **Vector Store** | ChromaDB | Ligero, sin servidor, persiste en disco, funciona en HF Spaces sin infra extra |
| **Embeddings** | `sentence-transformers/all-MiniLM-L6-v2` | Buen balance rendimiento/tamaño, funciona en CPU (HF Spaces free tier), 384 dims |
| **BM25** | `rank_bm25` | Librería pura Python, sin dependencias, ideal para búsqueda exacta de códigos |
| **Reranker** | `cross-encoder/ms-marco-MiniLM-L-6-v2` | Ligero, corre en CPU, buen rendimiento en reranking |
| **LLM** | OpenAI / Gemini / Claude (API key del usuario) | El curso lo exige, soportamos los 3 |
| **UI** | Gradio | Requisito del curso, nativo en HF Spaces |
| **PDF parsing** | `pdfplumber` + `pdftoppm` (rasterización) | pdfplumber para tablas/texto, rasterización para los PDFs con encoding roto |
| **Framework RAG** | Sin framework (vanilla Python) | Para un proyecto de portfolio, mostrar que entiendes los componentes es más valioso que esconderte detrás de LangChain |



