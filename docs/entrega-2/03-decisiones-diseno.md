# 03 — Justificación de las principales decisiones de diseño

Documento de decisiones arquitectónicas (formato **ADR**: *Architecture Decision
Record*). Cada decisión incluye contexto, alternativas evaluadas, justificación,
consecuencias y trazabilidad. El objetivo es demostrar que el diseño responde a
restricciones reales del cliente y no a preferencias tecnológicas.

---

## 1. Contexto y restricciones

| Restricción | Origen | Implicancia en el diseño |
|-------------|--------|--------------------------|
| R-01 | Municipalidad | La respuesta debe ser **verificable**: el ciudadano necesita saber de qué dependencia proviene la información. |
| R-02 | Municipalidad | El contenido cambia (ordenanzas, horarios, programas). Actualizar debe ser una operación de datos, no de código. |
| R-03 | Presupuesto | No hay financiamiento para infraestructura de IA dedicada ni para vectores gestionados. |
| R-04 | Privacidad | No se deben almacenar consultas ciudadanas ni datos personales (Ley 19.628 y su reforma 21.719). |
| R-05 | Operación | El equipo de informática municipal administra servidores Linux, no plataformas de MLOps. |
| R-06 | Plazo | El incremento debía estar operativo en un sprint de dos semanas. |
| R-07 | Cobertura | El servicio es público y anónimo: es un objetivo atractivo para abuso y *scraping*. |

---

## 2. Resumen de decisiones

| ID | Decisión | Alternativa descartada | Atributo principalmente beneficiado |
|----|----------|------------------------|-------------------------------------|
| D-01 | Arquitectura RAG sobre base de conocimiento curada | *Fine-tuning* de un modelo | Adecuación funcional · Mantenibilidad |
| D-02 | Arquitectura en capas con *composition root* en `api/` | Monolito de un archivo | Mantenibilidad · Testabilidad |
| D-03 | Chroma persistente local | Pinecone / pgvector gestionado | Portabilidad · Costo |
| D-04 | Embeddings multilingües locales en CPU | API de embeddings de terceros | Privacidad · Costo · Latencia |
| D-05 | LLM detrás de un cliente OpenAI-compatible | SDK propietario por proveedor | Portabilidad · Mantenibilidad |
| D-06 | Servicio *stateless*, sin historial ni cuentas | Sesiones con base de datos | Privacidad · Simplicidad |
| D-07 | Respuesta JSON completa (sin *streaming*) | SSE / WebSocket | Simplicidad · Fiabilidad |
| D-08 | Degradación controlada con mensaje institucional | Propagar el error 5xx | Fiabilidad · Usabilidad |
| D-09 | Defensa en profundidad: cuota por IP + captcha | Solo captcha | Seguridad · Disponibilidad |
| D-10 | Ingesta idempotente con criterio *fail-open* en datos incompletos | Filtrar registros incompletos | Integridad del contenido |
| D-11 | Configuración tipada por entorno (`pydantic-settings`) | Constantes en código | Seguridad · Portabilidad |
| D-12 | Frontend mínimo sin librería de estado | Redux / Zustand | Simplicidad · Usabilidad |

---

## 3. Decisiones detalladas

### D-01 — Usar RAG en lugar de *fine-tuning*

**Contexto.** El dominio es acotado (trámites municipales) pero **volátil**: cambian
horarios, dependencias y requisitos. Se necesita que la respuesta sea rastreable a una
fuente institucional.

**Decisión.** Recuperar los `k = 5` fragmentos más similares de Chroma, inyectarlos como
`CONTEXTO` en el *prompt* y restringir el modelo con un *system prompt* que prohíbe
inventar datos y obliga a derivar a OIRS cuando no hay información.

**Alternativas evaluadas.**

| Alternativa | Por qué se descartó |
|-------------|---------------------|
| *Fine-tuning* del modelo | Cada cambio de una pregunta frecuente exigiría reentrenar; no permite citar fuentes; costo de GPU; riesgo de olvido catastrófico. |
| Solo búsqueda por palabras clave (BM25) | No resuelve paráfrasis del ciudadano ("¿dónde saco el permiso de circulación?" vs. "pago de patente"). |
| LLM sin recuperación | Alucinaciones inaceptables en un servicio público. |

**Justificación.** RAG separa **conocimiento** (datos) de **capacidad lingüística**
(modelo). Actualizar el contenido es reejecutar `ingest.py`, sin desplegar código ni
tocar el modelo. Además, los metadatos recuperados permiten devolver `sources`, lo que
satisface R-01.

**Consecuencias.**
- (+) Contenido actualizable en minutos; respuestas citables; costo de inferencia acotado.
- (−) La calidad depende de la recuperación: sin umbral de similitud, un documento
  irrelevante puede colarse en el contexto (mitigado por el *system prompt*, ver R-05).
- (−) No hay memoria conversacional: una pregunta de seguimiento ("¿y cuánto cuesta?")
  pierde el referente.

**Evidencia.** `services/rag.py`, `tests/test_rag.py::test_respuesta_incluye_fuentes_y_usa_top_k`.

---

### D-02 — Arquitectura en capas con *composition root* en `api/`

**Contexto.** El equipo es pequeño y el proyecto debe poder evaluarse y mantenerse por
terceros. Se requiere poder probar la lógica sin levantar el modelo de embeddings.

**Decisión.** Tres capas con dependencias unidireccionales:

```
api/      → adaptadores de entrada (HTTP, validación, políticas)
services/ → lógica de aplicación (RAG, vector store, LLM)
core/     → infraestructura transversal (config, rate limit, captcha)
```

`api/chat.py` actúa como *composition root*: es el único lugar donde se combinan
seguridad, validación y dominio.

**Justificación.** Aplica **SRP** y **DIP** de forma pragmática: `RAGService` depende de
funciones (`embed`, `get_collection`, `chat_completion`) que pueden sustituirse por
dobles de prueba. Esto se verificó empíricamente: `test_rag.py` prueba el 100 % de
`rag.py` sin cargar SentenceTransformer ni llamar a un LLM.

**Consecuencias.**
- (+) Cobertura unitaria alta con pruebas rápidas; cambio de proveedor LLM en un archivo.
- (−) `chat.py` concentra validación + cuota + captcha: cohesión mixta aceptada por ser
  el punto de composición. Si crece, se extraerá un `ChatPolicy` en `core/`.

---

### D-03 — Chroma persistente local en lugar de base vectorial gestionada

**Contexto.** 191 documentos, crecimiento esperado < 5.000, un solo servidor, sin
presupuesto cloud (R-03) y sin equipo MLOps (R-05).

**Decisión.** `chromadb.PersistentClient` sobre `data/processed/chroma`, colección
`faq_penalolen` con métrica **coseno** y HNSW por defecto.

**Alternativas evaluadas.**

| Alternativa | Motivo del descarte |
|-------------|---------------------|
| Pinecone / Weaviate Cloud | Costo recurrente y dependencia de red para un corpus diminuto. |
| pgvector | Requiere operar PostgreSQL; no hay otras necesidades relacionales. |
| FAISS en memoria | Sin persistencia ni metadatos; obligaría a reindexar en cada arranque. |

**Justificación.** Para 191 vectores de 384 dimensiones la búsqueda exacta sería
instantánea; HNSW añade margen de crecimiento. El costo marginal es **cero** y el
índice es un artefacto reproducible desde el Excel (no requiere respaldo).

**Consecuencias.**
- (+) Despliegue sin servicios adicionales; portabilidad total.
- (−) Un solo escritor: la ingesta debe ejecutarse fuera de línea, no en caliente.
- (−) Escalar a varias réplicas exigiría un almacén compartido.

---

### D-04 — Embeddings multilingües locales

**Contexto.** Las consultas son en español informal chileno y contienen términos
administrativos. Enviar cada consulta a una API externa expondría el texto del
ciudadano (R-04).

**Decisión.** `sentence-transformers` con
`paraphrase-multilingual-MiniLM-L12-v2` (384 dimensiones), normalizado, cargado una
sola vez por proceso (`_model` global) y ejecutado en CPU.

**Justificación.**
- **Privacidad:** el texto de la consulta nunca sale del servidor municipal para ser vectorizado.
- **Costo:** sin cargo por token de embeddings.
- **Latencia:** ~10-40 ms por consulta en CPU con el modelo caliente, sin RTT de red.
- **Idioma:** modelo multilingüe; funciona con sinónimos y paráfrasis en español.

**Consecuencias.**
- (+) Sin dependencia externa en la ruta crítica de recuperación.
- (−) Primer *request* paga la carga del modelo (segundos); se mitiga con *warm-up* en
  el arranque (deuda registrada).
- (−) 384 dimensiones limitan la precisión frente a modelos de 1024; suficiente para
  un corpus de preguntas frecuentes.

---

### D-05 — LLM detrás de un cliente OpenAI-compatible

**Contexto.** El proveedor de inferencia puede cambiar (costo, cuota, disponibilidad).
FreeLLMAPI es un router que expone el protocolo OpenAI y que su propio autor declara
**no apto para producción**; migrar es un escenario probable, no hipotético.

**Decisión.** `services/llm.py` encapsula `AsyncOpenAI` apuntando a
`FREELLMAPI_BASE_URL`, con `model`, `temperature=0.2` y cliente *singleton*.

**Justificación.** El protocolo OpenAI es el estándar *de facto*: permite sustituir
FreeLLMAPI por OpenAI, Azure OpenAI, Groq, Together o un servidor vLLM cambiando
**variables de entorno**, sin modificar `rag.py` ni la API.

**Consecuencias.**
- (+) Portabilidad de proveedor y prueba con dobles (`monkeypatch` de `chat_completion`).
- (−) Se depende de la compatibilidad del router; funciones avanzadas (herramientas,
  JSON *schema*) no se usan para mantener el mínimo común denominador.
- (−) La clave del router vive solo en el backend (RNF-02); nunca se expone al SPA.

---

### D-06 — Servicio *stateless*: sin cuentas ni historial persistente

**Contexto.** El trámite consultado puede revelar situación personal (subsidios,
licencias médicas, violencia intrafamiliar). Almacenar conversaciones crearía un activo
de datos sensibles sin beneficio funcional.

**Decisión.** El backend no persiste mensajes, no usa cookies de sesión y no autentica.
El `session_id` existe en el contrato para futuras extensiones, pero **no se usa**.

**Alternativas evaluadas.**
- Historial en base de datos para "continuidad": descartado por riesgo y por la
  obligación de definir retención, cifrado y derecho de supresión.
- Historial en `localStorage`: descartado por exposición en equipos compartidos
  (bibliotecas, cajeros ciudadanos).

**Justificación.** Minimización de datos (*privacy by design*). Sin almacenamiento no
hay brecha que notificar ni plazo de retención que administrar.

**Consecuencias.**
- (+) Cumplimiento simplificado; superficie de ataque reducida; escalado horizontal trivial.
- (−) Sin contexto multi-turno; el ciudadano debe reformular.
- (−) Sin métricas de uso persistentes: la analítica deberá ser agregada y anónima
  (contadores, no contenido).

---

### D-07 — Respuesta JSON completa en lugar de *streaming*

**Contexto.** El SPA necesita mostrar la respuesta y las fuentes de forma consistente.

**Decisión.** `POST /api/chat` devuelve `{answer, sources}` cuando el LLM termina.

**Justificación.** El *streaming* (SSE) exige manejar reconexión, *buffering* de proxy y
estados parciales en el cliente; además, las fuentes solo se conocen tras la
recuperación y el modelo puede citarlas al final. Para respuestas de 3-6 líneas, la
percepción de velocidad no justifica la complejidad en el primer incremento.

**Consecuencias.**
- (+) Contrato simple, errores atómicos, pruebas triviales.
- (−) El ciudadano espera sin retroalimentación progresiva; se mitiga con el indicador
  "Escribiendo…" y con la meta p95 ≤ 5 s.
- (−) *Deuda aceptada:* migrar a SSE cuando las respuestas superen ~10 s.

---

### D-08 — Degradación controlada ante fallo del LLM

**Contexto.** El proveedor es gratuito y puede fallar, agotar cuota o responder con
lentitud. Un error 500 en un servicio municipal es inaceptable.

**Decisión.** `RAGService.answer` captura cualquier excepción del LLM, registra el
evento con `logging.exception` y devuelve un mensaje institucional con el teléfono de
OIRS y el portal de trámites. El SPA aplica la misma estrategia ante errores de red o
`!res.ok`.

**Justificación.** Un fallo de un componente auxiliar no debe degradar la utilidad del
servicio: el ciudadano siempre recibe un canal alternativo. Se prioriza **fiabilidad
percibida** sobre exactitud del mensaje de error.

**Consecuencias.**
- (+) Sin 5xx visibles; el monitor puede detectar el evento por logs.
- (−) Un fallo persistente se vuelve "invisible" en la interfaz; se requiere alerta
  sobre la tasa de mensajes de contingencia (deuda).
- (−) El mensaje de contingencia devuelve `sources` aunque no se usaron; se corregirá
  en el próximo incremento.

**Evidencia.** `tests/test_rag.py::test_fallback_amigable_si_el_llm_falla`.

---

### D-09 — Defensa en profundidad: cuota por IP + Turnstile

**Contexto.** Endpoint público, sin login, con costo variable por token. Un script
puede agotar la cuota del proveedor y dejar sin servicio a la ciudadanía (R-07).

**Decisión.** Dos controles independientes:

1. `slowapi` con `30/minute` por IP (`get_remote_address`), configurable por entorno.
2. Cloudflare Turnstile verificado *server-side* contra `siteverify`, con `remoteip`.

**Justificación.** El captcha detiene automatización masiva; la cuota detiene abuso
manual y ráfagas. Ninguno basta solo: el captcha es resoluble por *farmers* y la cuota
por IP es eludible con proxies.

**Consecuencias.**
- (+) Reduce el riesgo de denegación de servicio económica.
- (−) La cuota es **en memoria del proceso**: con N réplicas el límite efectivo se
  multiplica (R-06). Requiere Redis al escalar.
- (−) `get_remote_address` requiere que el proxy propague la IP real (`X-Forwarded-For`
  confiable); mal configurado, todos los ciudadanos comparten una sola cuota.
- (−) Turnstile en el frontend aún no está integrado: el control está operativo pero
  inactivo en el flujo real (deuda del Sprint 3).

**Evidencia.** `tests/test_chat_api.py::test_rate_limit_bloquea_peticion_31`,
`tests/test_turnstile.py` (3 casos).

---

### D-10 — Ingesta idempotente y criterio *fail-open* en datos incompletos

**Contexto.** El Excel institucional tiene 191 filas, con columnas opcionales y
registros con `isActivo` vacío. Un error de filtrado podría eliminar contenido válido.

**Decisión.** `is_active()` considera activo todo valor `NaN`, `None` o no numérico, y
solo excluye el valor numérico `0`. La colección se **elimina y recrea** en cada
ejecución, y cada documento incluye pregunta, respuesta, categoría, dependencia y tags.

**Justificación.** En un servicio público, un falso negativo (ocultar un trámite válido)
es más costoso que un falso positivo (mostrar un trámite dado de baja). La recreación
total garantiza que el índice refleje exactamente el Excel, sin residuos de versiones
anteriores.

**Consecuencias.**
- (+) Reindexación reproducible y sin estado oculto.
- (−) Ventana de indisponibilidad parcial durante la ingesta; se ejecuta fuera de horario.
- (−) El criterio *fail-open* puede indexar contenido no publicado; requiere revisión
  periódica del Excel (R-08 en la matriz de riesgos).

**Evidencia.** `tests/test_ingest.py` (10 casos, incluye `NaN`, `None`, texto y `0`).

---

### D-11 — Configuración tipada por entorno

**Decisión.** `pydantic-settings` con `Settings` y `.env`, con valores por defecto
seguros: `turnstile_enabled = False`, `freellmapi_api_key = ""`, CORS restringido a
`localhost:5173`.

**Justificación.** Evita secretos en el repositorio, permite el mismo artefacto en
desarrollo y producción, y valida tipos al arrancar (falla temprano).

**Consecuencias.**
- (+) Un solo binario por entorno; rotación de claves sin recompilar.
- (−) Un `.env` mal configurado deshabilita controles silenciosamente
  (`turnstile_enabled=False` en producción); se mitiga con una verificación de arranque
  (deuda).

---

### D-12 — Frontend mínimo sin librería de estado

**Contexto.** Una pantalla, un endpoint, sin autenticación ni rutas.

**Decisión.** `useState` local en `App.tsx`; sin router, sin Redux, sin React Query.
Variables CSS institucionales para color y tipografía.

**Justificación.** El estado es un arreglo de mensajes y un booleano de carga. Introducir
un *store* añadiría dependencias sin resolver ningún problema real (YAGNI).

**Consecuencias.**
- (+) Bundle pequeño, curva de mantención mínima, accesible por teclado (Enter envía).
- (−) Al crecer (historial, adjuntos, multichat) habrá que extraer componentes y un
  hook `useChat`; el archivo actual ya concentra presentación y lógica de red.

---

## 4. Matriz decisión ↔ atributo de calidad

| Decisión | Adecuación funcional | Eficiencia | Fiabilidad | Seguridad | Mantenibilidad | Portabilidad |
|----------|:---:|:---:|:---:|:---:|:---:|:---:|
| D-01 RAG | ●●● | ●● | ●● | ●● | ●●● | ●●● |
| D-02 Capas | ●● | ● | ●● | ●● | ●●● | ●●● |
| D-03 Chroma local | ●● | ●●● | ●● | ●● | ●● | ●●● |
| D-04 Embeddings locales | ●●● | ●●● | ●● | ●●● | ●● | ●● |
| D-05 Cliente OpenAI | ●● | ●● | ●●● | ●● | ●●● | ●●● |
| D-06 *Stateless* | ● | ●●● | ●●● | ●●● | ●● | ●●● |
| D-07 JSON sin streaming | ●● | ● | ●●● | ● | ●●● | ●●● |
| D-08 Degradación | ●● | ● | ●●● | ● | ●● | ●● |
| D-09 Cuota + captcha | ● | ●● | ●●● | ●●● | ●● | ●● |
| D-10 Ingesta *fail-open* | ●●● | ●● | ●● | ●● | ●●● | ●● |
| D-11 Config tipada | ● | ● | ●● | ●●● | ●●● | ●●● |
| D-12 Frontend mínimo | ●● | ●●● | ●● | ● | ●●● | ●●● |

`●●●` alto · `●●` medio · `●` bajo

---

## 5. Deuda técnica aceptada y su justificación

| ID | Deuda | Riesgo si no se paga | Sprint objetivo |
|----|-------|----------------------|-----------------|
| DT-01 | Turnstile no integrado en el SPA | Control anti-bot inactivo en producción | 3 |
| DT-02 | Sin umbral de similitud en la recuperación | Respuestas con contexto irrelevante | 3 |
| DT-03 | Cuota en memoria, no distribuida | Límite inefectivo al escalar | 3 |
| DT-04 | Sin *warm-up* del modelo de embeddings | Primera consulta lenta (varios segundos) | 3 |
| DT-05 | Sin *readiness* que valide Chroma y LLM | `/health` puede reportar "ok" con el servicio inútil | 3 |
| DT-06 | `sources` se devuelven incluso en contingencia | Fuentes que no fundamentan la respuesta | 3 |
| DT-07 | Sin analítica de consultas sin respuesta | No se detectan brechas de contenido | 4 |
| DT-08 | FreeLLMAPI no apto para producción | Corte o cambio de política del proveedor | 3 |

Cada deuda está vinculada a un riesgo de la [matriz de seguridad](07-matriz-riesgos-seguridad.md)
o a un caso del [plan de pruebas](05-plan-pruebas-aceptacion.md).
