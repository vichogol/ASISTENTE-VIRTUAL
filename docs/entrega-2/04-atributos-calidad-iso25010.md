# 04 — Atributos de calidad según ISO/IEC 25010

Se adopta el modelo de calidad de producto de **ISO/IEC 25010:2011** (8 características,
31 subcaracterísticas). Se deja constancia de que la revisión **ISO/IEC 25010:2023**
incorpora *Safety* como característica adicional; para este sistema, la seguridad física
de las personas no está en el alcance del producto, por lo que se documenta como
restricción de dominio y no como atributo medible.

Para cada atributo se define: **escenario de calidad** (fuente, estímulo, artefacto,
respuesta, medida), **táctica de diseño** aplicada y **evidencia o estado de medición**.
Los estados posibles son: `Medido`, `Verificado por prueba`, `Diseñado (sin medición)`,
`Pendiente`.

---

## 1. Escenarios de calidad priorizados

| ID | Característica | Escenario | Medida (respuesta esperada) | Estado |
|----|----------------|-----------|-----------------------------|--------|
| EC-01 | Eficiencia de desempeño | Un ciudadano envía una consulta con el modelo caliente y el proveedor LLM operativo | p95 ≤ 5 s; p50 ≤ 2,5 s | Pendiente (medición de carga) |
| EC-02 | Fiabilidad | El proveedor LLM no responde en 30 s | El 100 % de las solicitudes devuelve un mensaje útil con canal alternativo; 0 respuestas 5xx | Verificado por prueba |
| EC-03 | Seguridad | Un script envía 500 consultas/minuto desde una IP | A partir de la solicitud 31 se responde 429; el proveedor no recibe más de 30 llamadas/minuto por IP | Verificado por prueba |
| EC-04 | Adecuación funcional | Un ciudadano pregunta por un trámite presente en la base | La respuesta cita al menos una fuente recuperada y no inventa teléfonos ni horarios | Verificado por prueba (contrato) / Pendiente (evaluación con juicio humano) |
| EC-05 | Usabilidad | Un ciudadano mayor sin experiencia previa abre el sitio | Completa una consulta en ≤ 3 pasos sin instrucciones externas; interfaz operable por teclado | Diseñado / Pendiente (prueba con usuarios) |
| EC-06 | Mantenibilidad | Se requiere cambiar de proveedor LLM | El cambio se realiza en ≤ 1 archivo + variables de entorno; cobertura unitaria ≥ 80 % | Verificado por prueba (88 %) |
| EC-07 | Portabilidad | Se migra del entorno de desarrollo al VPS municipal | El mismo artefacto arranca cambiando solo `.env`; sin cambios de código | Diseñado |
| EC-08 | Compatibilidad | El ciudadano usa Chrome, Edge, Firefox o Safari móvil | La interfaz funciona sin errores de consola en las 4 plataformas | Pendiente (matriz de navegadores) |

---

## 2. Evaluación por característica

### 2.1 Adecuación funcional (*Functional suitability*)

| Subcaracterística | Cómo se aborda en el sistema | Evidencia |
|-------------------|------------------------------|-----------|
| Completitud funcional | Cubre el ciclo consulta → recuperación → respuesta → fuentes → derivación. | DS-01, DS-02 |
| Corrección funcional | Respuesta restringida al contexto; prohibición explícita de inventar datos. | `SYSTEM_PROMPT` en `services/rag.py` |
| Pertinencia funcional | Devuelve `sources` con pregunta y dependencia, lo que permite al ciudadano verificar. | `tests/test_rag.py` |

**Limitación declarada:** la corrección factual no es verificable automáticamente; se
requiere una **evaluación con juicio humano** sobre un conjunto dorado de 30 consultas
(CA-04, pendiente para el Sprint 3).

---

### 2.2 Eficiencia de desempeño (*Performance efficiency*)

| Subcaracterística | Táctica aplicada | Métrica objetivo |
|-------------------|------------------|------------------|
| Comportamiento temporal | Modelo de embeddings cargado una vez por proceso; `top_k=5`; `temperature=0.2`; cliente HTTP reutilizado | p95 ≤ 5 s (EC-01) |
| Utilización de recursos | Embeddings en CPU (sin GPU); índice HNSW en disco local | RAM < 1,5 GB por worker |
| Capacidad | Cuota de 30 req/min por IP; diseño *stateless* escalable horizontalmente | Sostener 10 req/s con 2 workers (por validar) |

**Análisis de la ruta crítica:** el 80-90 % de la latencia proviene del proveedor LLM
(servicio gratuito, sin SLA). Las optimizaciones locales (embedding, búsqueda) aportan
decenas de milisegundos; por eso la estrategia prioritaria es **caché de respuestas
frecuentes** y **timeout con degradación**, no micro-optimización.

**Riesgo de medición:** el primer *request* incluye la carga del modelo (segundos). La
métrica EC-01 debe medirse con el proceso "caliente" y reportarse por separado el
*cold start* (DT-04).

---

### 2.3 Compatibilidad (*Compatibility*)

| Subcaracterística | Táctica | Estado |
|-------------------|---------|--------|
| Coexistencia | FreeLLMAPI corre como proceso independiente en `localhost:3001`; el backend no asume su ciclo de vida. | Diseñado |
| Interoperabilidad | Contrato HTTP/JSON estándar; protocolo OpenAI para el LLM; `GET /health` consumible por cualquier monitor. | Verificado |

El frontend consume la API mediante `VITE_API_URL`, lo que permite separar origen en
producción (Nginx) sin cambios de código.

---

### 2.4 Usabilidad (*Usability*)

| Subcaracterística | Táctica | Estado |
|-------------------|---------|--------|
| Reconocibilidad de adecuación | Mensaje de bienvenida que declara el rol del asistente y su alcance. | Implementado |
| Capacidad de aprendizaje | Interfaz de una sola pantalla, un campo de texto y un botón. | Implementado |
| Operabilidad | Envío con `Enter`; estado `disabled` durante la carga evita doble envío; foco visible. | Implementado |
| Accesibilidad | Contraste sobre paleta institucional; texto alternativo pendiente en íconos; sin auditoría WCAG formal. | Pendiente |
| Protección contra errores del usuario | Validación de mensaje vacío en cliente y servidor (422). | Verificado |
| Estética | Paleta institucional (#222858, #0450C0, #FF8500); burbujas diferenciadas por rol. | Implementado |

**Deuda:** no se ha ejecutado una prueba de usabilidad con ciudadanos reales ni una
auditoría WCAG 2.2 AA; ambas están planificadas como CA-18 y CA-19.

---

### 2.5 Fiabilidad (*Reliability*)

| Subcaracterística | Táctica | Evidencia |
|-------------------|---------|-----------|
| Madurez | Manejo explícito de excepción del LLM; validación de entrada; sin estado compartido mutable en la ruta de consulta. | `test_fallback_amigable_si_el_llm_falla` |
| Disponibilidad | *Liveness* en `/health`; proceso gestionado por systemd con reinicio automático (despliegue previsto). | `test_health_ok` |
| Tolerancia a fallos | Degradación a mensaje institucional (D-08); el SPA captura errores de red. | DS-03 |
| Capacidad de recuperación | El índice se reconstruye desde el Excel en minutos; no hay datos transaccionales que recuperar. | DS-06 |

**Brecha identificada:** `/health` es *liveness*, no *readiness*: puede responder `ok`
con Chroma inaccesible o el router caído (DT-05, R-07).

---

### 2.6 Seguridad (*Security*)

| Subcaracterística | Táctica | Evidencia |
|-------------------|---------|-----------|
| Confidencialidad | Secretos solo en backend (`.env`, fuera de Git); embeddings locales para no exponer consultas; sin persistencia de conversaciones. | `.gitignore`, `config.py` |
| Integridad | Validación de esquema con Pydantic (tipo, longitud 1-1000); normalización de espacios; salida renderizada como texto por React (sin `dangerouslySetInnerHTML`). | `tests/test_chat_api.py` |
| No repudio | No aplica: servicio anónimo sin transacciones. | — |
| Responsabilidad (*accountability*) | Log del evento de fallo del LLM con `logging.exception`; sin registrar el contenido de la consulta. | `services/rag.py` |
| Autenticidad | Turnstile verifica que el cliente es un navegador legítimo (no autentica identidad). | `tests/test_turnstile.py` |
| Resistencia | Cuota por IP + captcha; límite de longitud de entrada; `top_k` acotado. | `test_rate_limit_bloquea_peticion_31` |

Detalle completo en la [matriz de riesgos de seguridad](07-matriz-riesgos-seguridad.md).

---

### 2.7 Mantenibilidad (*Maintainability*)

| Subcaracterística | Táctica | Métrica | Estado |
|-------------------|---------|---------|--------|
| Modularidad | Capas `api/services/core` con dependencias unidireccionales. | 12 componentes con responsabilidad única | Diseñado |
| Reusabilidad | `RAGService` no depende de HTTP: reutilizable desde CLI o futuros canales. | — | Diseñado |
| Analizabilidad | Nombres explícitos, tipos Pydantic, logs de error, 28 pruebas nombradas por comportamiento. | — | Verificado |
| Capacidad de modificación | Proveedor LLM sustituible en 1 archivo + `.env`. | ≤ 1 archivo | Verificado |
| Capacidad de prueba | Puertos por función sustituibles con `monkeypatch`. | Cobertura **88 %** (122 sentencias, 15 sin cubrir) | Medido |

**Sentencias no cubiertas:** `services/llm.py` (construcción del cliente y llamada real,
requiere integración) y `services/vector_store.py` (carga real del modelo y de Chroma).
Son dependencias de infraestructura, deliberadamente excluidas de las pruebas unitarias
y cubiertas por el plan de integración (CA-16).

---

### 2.8 Portabilidad (*Portability*)

| Subcaracterística | Táctica | Estado |
|-------------------|---------|--------|
| Adaptabilidad | Configuración 100 % por entorno; rutas de Chroma y modelo parametrizadas. | Implementado |
| Instalabilidad | `requirements.txt` + `requirements-dev.txt`; frontend con `npm ci` y build estático. | Implementado |
| Reemplazabilidad | Chroma y FreeLLMAPI están detrás de funciones/puertos; sustituibles sin tocar el dominio. | Diseñado |

**Restricción conocida:** Python 3.13 + `sentence-transformers` requiere wheels
compatibles; se fija la versión de Python en el despliegue para evitar resoluciones
inconsistentes.

---

## 3. Priorización y compromisos (*trade-offs*)

| Prioridad | Atributo | Justificación |
|-----------|----------|---------------|
| 1 (crítico) | Seguridad | Servicio público, datos potencialmente sensibles, costo por token. |
| 2 (crítico) | Fiabilidad | Un error visible en un canal municipal daña la confianza institucional. |
| 3 (alto) | Adecuación funcional | La utilidad depende de responder con información correcta y citable. |
| 4 (alto) | Usabilidad | Público heterogéneo, incluidos adultos mayores. |
| 5 (medio) | Eficiencia | La latencia está dominada por un tercero; se gestiona con degradación. |
| 6 (medio) | Mantenibilidad | Equipo pequeño; el costo de cambio debe ser bajo. |
| 7 (bajo) | Portabilidad | Un solo destino de despliegue previsto. |
| 8 (bajo) | Compatibilidad | Sin integraciones corporativas en este incremento. |

**Compromisos explícitos**

1. **Seguridad vs. usabilidad:** el captcha invisible no debe introducir fricción; si
   Turnstile afecta la conversión, se evaluará modo gestionado con desafío adaptativo.
2. **Eficiencia vs. fiabilidad:** se prefiere una respuesta de contingencia en 2 s antes
   que esperar 30 s a un proveedor degradado (timeout + fallback).
3. **Mantenibilidad vs. rendimiento:** la normalización de embeddings en cada consulta
   añade milisegundos, pero evita inconsistencias de índice.

---

## 4. Plan de medición

| Métrica | Instrumento | Frecuencia | Responsable |
|---------|-------------|------------|-------------|
| p50/p95 de latencia por etapa (embedding, retrieval, LLM) | *timings* en logs + script de carga (k6) | Por release | Desarrollo |
| Tasa de 429 y de mensajes de contingencia | Conteo en logs | Semanal | Operación |
| Cobertura de pruebas | `pytest --cov` | Por commit | Desarrollo |
| Disponibilidad mensual | Monitor externo sobre `/health` | Continuo | Operación |
| Consultas sin respuesta útil | Muestreo manual de 30 consultas | Mensual | Contenido/negocio |
| Accesibilidad | Lighthouse + revisión WCAG 2.2 AA | Por release mayor | UX |

Los umbrales de aceptación se registran en el [plan de pruebas](05-plan-pruebas-aceptacion.md)
y su evidencia actual en el [reporte de pruebas unitarias](06-evidencia-pruebas-unitarias.md).
