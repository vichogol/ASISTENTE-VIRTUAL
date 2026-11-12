# 01 — Diagramas de secuencia de las principales funcionalidades

Los diagramas se expresan en **Mermaid** (renderizable en GitHub, GitLab, VS Code y
Draw.io). Cada uno describe el comportamiento real del código del repositorio,
incluyendo rutas alternativas y de excepción.

| ID | Funcionalidad | RF | Tipo de flujo |
|----|---------------|----|---------------|
| DS-01 | Consulta ciudadana resuelta con RAG | RF-01, RF-02 | Flujo principal |
| DS-02 | Consulta sin respaldo en la base de conocimiento | RF-03 | Alternativo |
| DS-03 | Caída del proveedor LLM (degradación controlada) | RNF-03 | Excepción |
| DS-04 | Bloqueo por límite de tasa | RF-06 | Excepción |
| DS-05 | Verificación Turnstile | RF-06 | Alternativo |
| DS-06 | Ingesta / actualización de la base de conocimiento | RF-05 | Proceso batch |
| DS-07 | Monitoreo de disponibilidad | RF-04 | Proceso de soporte |

---

## DS-01 — Consulta ciudadana resuelta con RAG (flujo principal)

**Precondición:** el servicio está en ejecución, el índice Chroma contiene la colección
`faq_penalolen` y el router FreeLLMAPI responde.
**Postcondición:** el ciudadano recibe una respuesta en español junto con las fuentes
(pregunta frecuente y dependencia) utilizadas.

```mermaid
sequenceDiagram
    autonumber
    actor C as Ciudadano
    participant SPA as SPA React<br/>(App.tsx)
    participant API as FastAPI<br/>api/chat.py
    participant RL as RateLimiter<br/>(slowapi)
    participant TS as Turnstile<br/>(core/turnstile.py)
    participant RAG as RAGService<br/>(services/rag.py)
    participant EMB as Embedder<br/>(vector_store.py)
    participant DB as Chroma<br/>(faq_penalolen)
    participant LLM as LLMClient<br/>(services/llm.py)
    participant RTR as FreeLLMAPI<br/>(router OpenAI-compatible)

    C->>SPA: Escribe consulta y presiona Enter
    SPA->>SPA: valida text.trim() y loading == false
    SPA->>SPA: agrega mensaje del usuario al estado
    SPA->>API: POST /api/chat {message}
    API->>API: valida ChatRequest (1..1000 caracteres)
    API->>RL: consume cuota por IP (30/minuto)
    RL-->>API: cuota disponible
    API->>TS: verify_turnstile(token, client_ip)
    TS-->>API: true
    API->>API: normaliza espacios en blanco del mensaje
    API->>RAG: await answer(message)
    RAG->>EMB: embed([message])
    EMB->>EMB: SentenceTransformer.encode(normalize=True)
    EMB-->>RAG: vector[384]
    RAG->>DB: query(query_embeddings, n_results=top_k=5)
    DB-->>RAG: documents[5] + metadatas[5]
    RAG->>RAG: construye CONTEXTO y lista de sources
    RAG->>LLM: chat_completion(SYSTEM_PROMPT, user_prompt)
    LLM->>RTR: POST /v1/chat/completions (model=auto, temp=0.2)
    RTR-->>LLM: completion
    LLM-->>RAG: texto (strip)
    RAG-->>API: {answer, sources}
    API-->>SPA: 200 {answer, sources}
    SPA->>SPA: agrega burbuja assistant + lista de fuentes
    SPA-->>C: Respuesta visible
```

**Observaciones de diseño**

- El `session_id` se acepta en el contrato pero **no se utiliza**: el servicio es
  *stateless* y no mantiene historial (decisión D-06).
- El contexto se limita a `top_k = 5` fragmentos para acotar el costo por token y la
  latencia del proveedor.
- La temperatura `0.2` reduce la variabilidad de la redacción municipal.

---

## DS-02 — Consulta sin respaldo en la base de conocimiento

**Disparador:** la consulta es ajena al dominio municipal o no tiene coincidencia
semántica útil.
**Comportamiento actual:** no existe umbral de similitud; Chroma siempre devuelve los
`top_k` vecinos más cercanos. La decisión de "no tengo esa información" recae en el
modelo, guiado por el *system prompt* (decisión D-01 y riesgo R-05).

```mermaid
sequenceDiagram
    autonumber
    actor C as Ciudadano
    participant SPA as SPA React
    participant API as FastAPI
    participant RAG as RAGService
    participant DB as Chroma
    participant LLM as LLMClient
    participant RTR as FreeLLMAPI

    C->>SPA: "¿Cuándo se inaugura el metro en Peñalolén?"
    SPA->>API: POST /api/chat {message}
    API->>RAG: answer(message)
    RAG->>DB: query(n_results=5)
    DB-->>RAG: 5 documentos de baja relevancia
    RAG->>RAG: arma CONTEXTO (sin filtrar por score)
    RAG->>LLM: chat_completion(system, user)
    LLM->>RTR: POST /v1/chat/completions
    RTR-->>LLM: completion
    Note over LLM: El system prompt ordena:<br/>"Si no está en el contexto, di que no tienes<br/>esa información y sugiere OIRS / tramites.penalolen.cl"
    LLM-->>RAG: "No tengo esa información… contacta a la OIRS (+562 2486 8000)"
    RAG-->>API: {answer, sources}
    API-->>SPA: 200 {answer, sources}
    SPA-->>C: Respuesta con derivación institucional
```

**Deuda técnica asociada:** incorporar un umbral de distancia coseno (p. ej. `0.35`)
y un mensaje determinista de derivación cuando ningún documento lo supere. Registrado
como CA-05b en el plan de pruebas y R-05 en la matriz de riesgos.

---

## DS-03 — Caída del proveedor LLM (degradación controlada)

**Disparador:** timeout, error HTTP o cuota agotada en FreeLLMAPI / proveedor upstream.
**Resultado:** el endpoint responde `200` con un mensaje institucional, nunca `500`.

```mermaid
sequenceDiagram
    autonumber
    actor C as Ciudadano
    participant SPA as SPA React
    participant API as FastAPI
    participant RAG as RAGService
    participant LLM as LLMClient
    participant RTR as FreeLLMAPI

    C->>SPA: consulta
    SPA->>API: POST /api/chat
    API->>RAG: answer(message)
    RAG->>LLM: chat_completion(system, user)
    LLM->>RTR: POST /v1/chat/completions
    RTR--xLLM: ConnectionError / Timeout
    LLM--xRAG: excepción propagada
    RAG->>RAG: logging.exception("Error al llamar al LLM")
    RAG->>RAG: text = mensaje de contingencia con OIRS
    RAG-->>API: {answer: contingencia, sources: [...]}
    API-->>SPA: 200 (sin error visible para el ciudadano)
    SPA-->>C: "No pude conectarme al servicio de IA…"

    Note over SPA,API: Si falla la red o el backend devuelve != 2xx,<br/>el SPA captura la excepción y muestra el mismo mensaje de contingencia.
```

---

## DS-04 — Bloqueo por límite de tasa

**Disparador:** la misma IP supera `30` solicitudes por minuto (configurable con
`RATE_LIMIT`).

```mermaid
sequenceDiagram
    autonumber
    actor A as Cliente (IP)
    participant API as FastAPI
    participant RL as RateLimiter
    participant H as ExceptionHandler

    A->>API: POST /api/chat (solicitud N.º 31 en el minuto)
    API->>RL: consume cuota por IP
    RL--xAPI: RateLimitExceeded
    API->>H: handler registrado en main.py
    H-->>A: 429 {"detail": "Demasiadas solicitudes. Intenta en un momento."}
    Note over RL: Almacenamiento en memoria del proceso.<br/>No distribuido: requiere Redis si se escala a N réplicas (R-06).
```

---

## DS-05 — Verificación Turnstile

**Disparador:** `TURNSTILE_ENABLED=true` (producción) y el cliente envía
`turnstile_token`. Si el secreto no está configurado, la verificación se omite
(*fail-open* controlado por configuración, no por omisión).

```mermaid
sequenceDiagram
    autonumber
    participant SPA as SPA React<br/>(pendiente: widget invisible)
    participant API as FastAPI
    participant TS as core/turnstile.py
    participant CF as Cloudflare<br/>siteverify

    SPA->>SPA: obtiene token del widget invisible
    SPA->>API: POST /api/chat {message, turnstile_token}
    API->>API: valida ChatRequest
    API->>TS: verify_turnstile(token, ip)
    alt sin turnstile_secret_key
        TS-->>API: true (verificación deshabilitada)
    else con secreto
        TS->>CF: POST /turnstile/v0/siteverify (secret, response, remoteip)
        CF-->>TS: {success}
        TS-->>API: success
    end
    alt success == false
        API-->>SPA: 400 {"detail": "Captcha inválido"}
    else success == true
        API->>API: continúa flujo DS-01
        API-->>SPA: 200 {answer, sources}
    end
```

**Estado:** backend implementado y probado; la integración del widget en el SPA es
deuda del Sprint 3 (CA-11, CA-12).

---

## DS-06 — Ingesta / actualización de la base de conocimiento

**Disparador:** el equipo municipal actualiza `data/raw/preguntas_frecuentes_penalolen.xlsx`
y ejecuta `python scripts/ingest.py` (operación batch, fuera de línea).

```mermaid
sequenceDiagram
    autonumber
    actor OP as Equipo municipal
    participant ING as scripts/ingest.py
    participant PANDAS as pandas
    participant EMB as Embedder
    participant CH as Chroma (PersistentClient)

    OP->>ING: python scripts/ingest.py
    ING->>PANDAS: read_excel(preguntas_frecuentes_penalolen.xlsx)
    PANDAS-->>ING: DataFrame
    ING->>ING: filtra is_active(isActivo)
    Note over ING: NaN, texto o valores no numéricos<br/>se consideran activos (decisión D-10)
    ING->>ING: compone texto enriquecido<br/>(pregunta, respuesta, categoría, dependencia, tags)
    ING->>ING: construye metadatos<br/>(id, pregunta, categoria, direccion, rango_etareo, sexo)
    ING->>CH: delete_collection("faq_penalolen") si existe
    ING->>CH: create_collection(metadata={hnsw:space: cosine})
    ING->>EMB: embed(docs)
    EMB-->>ING: matriz de embeddings normalizados
    ING->>CH: add(ids, documents, embeddings, metadatas)
    CH-->>ING: confirmación
    ING-->>OP: "Ingestadas N preguntas en <chroma_path>"
```

**Características:** idempotente (recrea la colección), determinista para el mismo
Excel y sin dependencia del LLM. Duración típica: ~30 s para 191 documentos en CPU.

---

## DS-07 — Monitoreo de disponibilidad

```mermaid
sequenceDiagram
    autonumber
    participant MON as Monitor<br/>(systemd / uptime / Cloudflare)
    participant API as FastAPI
    participant H as api/health.py

    loop cada 60 s
        MON->>API: GET /health
        API->>H: health()
        H-->>API: {"status": "ok"}
        API-->>MON: 200
    end
    Note over MON,H: El health check es de liveness (proceso vivo).<br/>No verifica Chroma ni FreeLLMAPI: se propone readiness separado (R-07).
```

---

## Resumen de rutas alternativas

| Escenario | Código de respuesta | Mensaje al ciudadano | Diagrama |
|-----------|--------------------|----------------------|----------|
| Consulta válida y LLM disponible | 200 | Respuesta fundamentada + fuentes | DS-01 |
| Consulta fuera de alcance | 200 | "No tengo esa información… OIRS" | DS-02 |
| LLM caído | 200 | Mensaje de contingencia con OIRS | DS-03 |
| Cuota excedida | 429 | "Demasiadas solicitudes…" | DS-04 |
| Captcha inválido | 400 | "Captcha inválido" | DS-05 |
| Cuerpo inválido (vacío o > 1000) | 422 | Error de validación estándar | — |
| Error de red en el navegador | — | Mensaje de contingencia local | DS-03 |
