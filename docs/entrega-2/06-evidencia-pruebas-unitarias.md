# 06 — Reporte de la 1.ª evidencia de pruebas unitarias

**Proyecto:** Asistente Virtual — Municipalidad de Peñalolén
**Sprint:** 2 · **Fecha de ejecución:** 2026-11-12
**Commit evaluado:** `ecd5f8b`
**Responsable:** equipo de desarrollo

---

## 1. Resumen ejecutivo

| Indicador | Resultado |
|-----------|-----------|
| Pruebas recolectadas | 28 |
| Pruebas aprobadas | **28** |
| Pruebas fallidas | 0 |
| Pruebas omitidas | 0 |
| Tiempo de ejecución | 38,08 s |
| Cobertura de líneas (`backend/app`) | **88 %** (107 / 122 sentencias) |
| Módulos con 100 % de cobertura | 11 de 13 (7 con lógica efectiva) |
| Defectos de producto detectados | 0 |

**Conclusión:** la suite valida el contrato HTTP, las reglas de negocio del RAG, la
degradación ante fallos del proveedor, la política de cuota y captcha, la configuración
por entorno y la regla de filtrado de la ingesta. El incremento cumple el umbral de
cobertura definido (≥ 80 %).

---

## 2. Entorno de ejecución

| Elemento | Versión / valor |
|----------|-----------------|
| Sistema operativo | Windows (`platform win32`) |
| Python | 3.13.3 |
| pytest | 9.2.0 |
| pytest-cov | 7.1.0 |
| FastAPI | 0.162.0 |
| Pydantic | 2.14.2 |
| ChromaDB | 1.5.9 |
| Ejecutor | `.venv` del backend (aislado) |

**Configuración de la suite** (`backend/pytest.ini`)

```ini
[pytest]
pythonpath = .
testpaths = tests
addopts = -v --tb=short
filterwarnings = ignore::DeprecationWarning
```

`backend/tests/conftest.py` fija variables de entorno seguras y reinicia el contador de
*rate limit* antes y después de cada prueba, garantizando aislamiento y repetibilidad.

---

## 3. Comando de ejecución

```powershell
cd backend
.\.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest --cov=app --cov-report=term-missing
```

**Salida completa:** [`evidencias/pytest-sprint2.txt`](evidencias/pytest-sprint2.txt)

```text
============================= test session starts =============================
platform win32 -- Python 3.13.3, pytest-9.2.0, pluggy-1.7.0
configfile: pytest.ini
testpaths: tests
plugins: anyio-4.15.1, cov-7.1.0
collected 28 items

tests/test_chat_api.py ..........                                       [ 28%]
tests/test_config.py ....                                               [ 42%]
tests/test_ingest.py ...........                                        [ 78%]
tests/test_rag.py ...                                                   [ 89%]
tests/test_turnstile.py ...                                             [100%]

=============================== tests coverage ================================
Name                           Stmts   Miss  Cover   Missing
------------------------------------------------------------
app\__init__.py                    0      0   100%
app\api\__init__.py                0      0   100%
app\api\chat.py                   27      0   100%
app\api\health.py                  5      0   100%
app\config.py                     14      0   100%
app\core\__init__.py               0      0   100%
app\core\rate_limit.py             4      0   100%
app\core\turnstile.py              8      0   100%
app\main.py                       14      0   100%
app\services\__init__.py           0      0   100%
app\services\llm.py               10      5    50%   10-15, 19-27
app\services\rag.py               20      0   100%
app\services\vector_store.py      20     10    50%   15-17, 22-25, 30-34
------------------------------------------------------------
TOTAL                            122     15    88%
============================= 28 passed in 38.08s =============================
```

---

## 4. Inventario de pruebas

### 4.1 `tests/test_chat_api.py` — contrato HTTP e integración (8)

| # | Prueba | Qué verifica | CA |
|---|--------|--------------|----|
| 1 | `test_health_ok` | `GET /health` responde 200 con `{"status":"ok"}` | CA-14 |
| 2 | `test_chat_ok_y_normaliza_espacios` | `POST /api/chat` responde 200 y colapsa espacios múltiples del mensaje | CA-01 |
| 3 | `test_mensaje_vacio_rechazado` | Mensaje vacío → 422 (validación Pydantic) | CA-06 |
| 4 | `test_mensaje_demasiado_largo_rechazado` | 1.001 caracteres → 422 | CA-07 |
| 5 | `test_rate_limit_bloquea_peticion_31` | 30 solicitudes OK; la 31.ª → 429 con mensaje institucional | CA-08 |
| 6 | `test_turnstile_habilitado_sin_token_devuelve_400` | Captcha activo y sin token → 400 | CA-10 |
| 7 | `test_turnstile_token_invalido_devuelve_400` | Token rechazado por Cloudflare → 400 | CA-11 |
| 8 | `test_turnstile_token_valido_permite_paso` | Token válido → 200 y flujo normal | CA-12 (backend) |

**Técnica:** `TestClient` sobre la app real; el servicio RAG se sustituye por un doble
para no depender del modelo ni del proveedor. Se ejercita el *middleware*, el
*exception handler* de slowapi y la inyección de dependencias de FastAPI.

### 4.2 `tests/test_config.py` — configuración (4)

| # | Prueba | Qué verifica |
|---|--------|--------------|
| 9 | `test_valores_por_defecto` | `top_k=5`, modelo `auto`, embeddings multilingües, Turnstile deshabilitado, cuota 30/min |
| 10 | `test_cors_origins_multiple` | Parseo de orígenes separados por coma, ignorando vacíos |
| 11 | `test_api_key_se_lee_desde_entorno` | La clave del LLM se toma de la variable de entorno |
| 12 | `test_api_key_por_defecto_vacia` | Sin entorno ni `.env`, la clave por defecto es vacía (no hay secreto embebido) |

### 4.3 `tests/test_ingest.py` — regla de negocio de la ingesta (11)

| # | Prueba | Qué verifica |
|---|--------|--------------|
| 13-21 | `test_is_active[...]` (9 parametrizaciones) | `1`, `1.0`, `"1"` → activo; `0`, `0.0`, `"0"` → inactivo; `NaN`, `None`, `"texto"` → activo (*fail-open*) |
| 22 | `test_is_active_serie_pandas` | El criterio se aplica correctamente sobre una `Series` con nulos |

**Técnica:** partición de equivalencia + valores límite sobre el dominio de `isActivo`,
que determina qué contenido llega al ciudadano.

### 4.4 `tests/test_rag.py` — lógica del servicio RAG (3)

| # | Prueba | Qué verifica |
|---|--------|--------------|
| 23 | `test_respuesta_incluye_fuentes_y_usa_top_k` | Usa `top_k` de configuración; arma el contexto; el *prompt* contiene la pregunta y la restricción "SOLO en español"; devuelve `sources` con id, pregunta y dirección |
| 24 | `test_sin_contexto_usa_marcador` | Sin documentos recuperados, el contexto usa `(sin contexto)` y `sources` queda vacío |
| 25 | `test_fallback_amigable_si_el_llm_falla` | Si el LLM lanza excepción, la respuesta es un mensaje con OIRS y no se propaga el error |

**Técnica:** dobles de prueba (`FakeCollection`) e intercepción de funciones con
`monkeypatch`, lo que permite probar el 100 % de `rag.py` sin cargar SentenceTransformer.

### 4.5 `tests/test_turnstile.py` — verificación anti-bot (3)

| # | Prueba | Qué verifica |
|---|--------|--------------|
| 26 | `test_sin_secret_key_permite_paso` | Sin secreto configurado, la verificación se omite (comportamiento documentado) |
| 27 | `test_token_valido` | Envía `secret`, `response` y `remoteip` al endpoint correcto; `success=true` → `True` |
| 28 | `test_token_invalido` | `success=false` → `False` |

---

## 5. Cobertura y análisis de brechas

| Módulo | Cobertura | Justificación de las líneas no cubiertas |
|--------|-----------|------------------------------------------|
| `api/chat.py` | 100 % | — |
| `api/health.py` | 100 % | — |
| `main.py` | 100 % | Se ejercita el handler de 429 vía CA-08 |
| `config.py` | 100 % | — |
| `core/rate_limit.py` | 100 % | — |
| `core/turnstile.py` | 100 % | — |
| `services/rag.py` | 100 % | Incluye la rama de excepción |
| `services/llm.py` | 50 % | Construcción del cliente `AsyncOpenAI` y llamada HTTP real: requiere el router FreeLLMAPI en ejecución → prueba de integración CA-16 |
| `services/vector_store.py` | 50 % | Carga real de `SentenceTransformer` y de `PersistentClient`: dependencias de infraestructura → CA-16 |

**Decisión consciente:** no se simula el modelo de embeddings ni Chroma a nivel de
integración porque una prueba con dobles no aportaría señal sobre la calidad de la
recuperación. Esa dimensión se cubre con la evaluación del conjunto dorado (CA-04) y el
end-to-end (CA-16).

---

## 6. Defectos detectados durante la sesión

| ID | Descripción | Tipo | Acción | Estado |
|----|-------------|------|--------|--------|
| TD-01 | Una aserción dependía del `.env` real del desarrollador, lo que hacía la prueba no reproducible en otro equipo. | Defecto de prueba | Se aisló con `monkeypatch.delenv` y un `_env_file` inexistente. | Corregido |
| TD-02 | El doble de `chat_completion` no replicaba el contrato real (el cliente aplica `strip()` a la respuesta). | Defecto de prueba | Se alineó el doble con el contrato documentado en `llm.py`. | Corregido |

No se detectaron defectos de producto en este incremento. Las brechas funcionales
conocidas (umbral de similitud, `sources` en contingencia, Turnstile en el SPA) están
registradas como deuda técnica y casos de aceptación pendientes, no como fallos de prueba.

---

## 7. Trazabilidad prueba ↔ requerimiento ↔ caso de aceptación

| Requerimiento | Pruebas automatizadas | Caso de aceptación |
|---------------|----------------------|--------------------|
| RF-01 Consulta | #2, #3, #4 | CA-01, CA-06, CA-07 |
| RF-02 Respuesta con fuentes | #23, #24 | CA-01, CA-02, CA-04 |
| RF-03 Derivación | #24, #25 | CA-05 |
| RF-04 Health | #1 | CA-14 |
| RF-05 Ingesta | #13-22 | CA-15 |
| RF-06 Cuota y captcha | #5-8, #26-28 | CA-08, CA-10, CA-11, CA-12 |
| RNF-02 Seguridad | #3, #4, #11, #12, #26-28 | CA-17, CA-20 |
| RNF-03 Fiabilidad | #25 | CA-13 |
| RNF-04 Mantenibilidad | Cobertura 88 % | EC-06 |

---

## 8. Reproducibilidad y próximos pasos

**Reproducir en un equipo limpio**

```powershell
git clone <repo> && cd ASISTENTE-VIRTUAL/backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest --cov=app --cov-report=term-missing
```

**Siguiente evidencia (Sprint 3)**

| Acción | Objetivo |
|--------|----------|
| Prueba de integración real con Chroma + FreeLLMAPI | Cubrir `llm.py` y `vector_store.py` |
| Prueba de contrato del frontend (Vitest + Testing Library) | Cubrir `App.tsx` (estado, error, fuentes) |
| Umbral de similitud + prueba determinista de derivación | Cerrar CA-05b |
| Prueba de carga con k6 (10 req/s) | Cerrar CA-21 |
| Publicación de cobertura en el pipeline (badge) | Visibilidad continua |
