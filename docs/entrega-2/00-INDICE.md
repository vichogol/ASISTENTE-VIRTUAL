# Entrega 2 — Sprint Review | Índice de documentación técnica

**Proyecto:** Asistente Virtual — Municipalidad de Peñalolén
**Asignatura:** TICS331 — Diseño y Calidad de Software
**Semestre:** 2 — 2026
**Incremento documentado:** Sprint 1 + Sprint 2 (primer incremento funcional)

---

## 1. Propósito

Este directorio consolida la evidencia técnica de la Entrega 2. Cada documento es
autocontenido, está trazado contra el backlog y utiliza exclusivamente componentes
que existen en el repositorio (`backend/`, `frontend/`, `data/`, `infra/`).

| # | Documento | Entregable del curso que cubre |
|---|-----------|--------------------------------|
| 01 | [Diagramas de secuencia](01-diagramas-secuencia.md) | Diagrama de secuencia de las principales funcionalidades |
| 02 | [Diagrama de componentes](02-diagrama-componentes.md) | Diagrama de componentes |
| 03 | [Decisiones de diseño](03-decisiones-diseno.md) | Justificación de las principales decisiones de diseño / Responsabilidades, cohesión y acoplamiento |
| 04 | [Atributos de calidad ISO/IEC 25010](04-atributos-calidad-iso25010.md) | Atributos de calidad |
| 05 | [Plan de pruebas de aceptación](05-plan-pruebas-aceptacion.md) | Plan de pruebas de aceptación y estrategia de pruebas |
| 06 | [Evidencia de pruebas unitarias](06-evidencia-pruebas-unitarias.md) | Reporte 1.ª evidencia de pruebas unitarias |
| 07 | [Matriz de riesgos de seguridad](07-matriz-riesgos-seguridad.md) | Matriz de riesgos de seguridad |

---

## 2. Alcance funcional del incremento

El producto es un asistente conversacional **RAG** (Retrieval-Augmented Generation) que
responde consultas ciudadanas sobre trámites municipales usando como única fuente de
verdad la base de preguntas frecuentes de la Municipalidad (191 registros activos).
No requiere autenticación y no persiste conversaciones.

### 2.1 Requerimientos funcionales del incremento

| ID | Requerimiento | Estado Sprint 2 |
|----|---------------|-----------------|
| RF-01 | El ciudadano formula una consulta en lenguaje natural desde el navegador | Implementado |
| RF-02 | El sistema responde en español, fundamentado en la base de conocimiento y mostrando fuentes | Implementado |
| RF-03 | Si no existe información suficiente, el sistema lo declara y deriva a OIRS / portal de trámites | Implementado (vía *system prompt*) |
| RF-04 | El sistema expone un endpoint de salud para monitoreo | Implementado |
| RF-05 | El equipo municipal puede reindexar la base de conocimiento desde el Excel de origen | Implementado (`scripts/ingest.py`) |
| RF-06 | El sistema se protege contra abuso: límite de tasa por IP y verificación Turnstile | Implementado en backend; Turnstile en frontend **pendiente** |

### 2.2 Requerimientos no funcionales priorizados

| ID | Atributo (ISO/IEC 25010) | Meta del incremento |
|----|--------------------------|---------------------|
| RNF-01 | Eficiencia de desempeño | p95 de respuesta ≤ 5 s con caché de modelo caliente |
| RNF-02 | Seguridad | Sin secretos en el cliente; *prompt injection* mitigada; cuota por IP activa |
| RNF-03 | Fiabilidad | Degradación controlada ante caída del proveedor LLM (sin error 500) |
| RNF-04 | Mantenibilidad | Cambio de proveedor LLM sin tocar capa API; cobertura unitaria ≥ 80 % |
| RNF-05 | Portabilidad | Despliegue en VPS Linux con Python 3.13 + Node 20 |
| RNF-06 | Usabilidad | Interfaz de chat de una sola pantalla, responsive, sin registro |

---

## 3. Arquitectura en una vista

```
Navegador (React + Vite + TS)
        │  HTTPS / JSON
        ▼
Cloudflare (TLS, WAF, Turnstile)  ──(planificado)──
        │
        ▼
FastAPI (Uvicorn, Python 3.13)
   ├── api/health      GET  /health
   ├── api/chat        POST /api/chat
   ├── core/           rate_limit · turnstile · config
   └── services/       rag · vector_store · llm
        │                    │              │
        │                    │              └──► FreeLLMAPI (router OpenAI-compatible) ──► proveedores
        │                    └──► Chroma (persistente, coseno) + SentenceTransformer local
        └── Ingesta offline: data/raw/*.xlsx ──► scripts/ingest.py
```

---

## 4. Trazabilidad global

| Requerimiento | Secuencia | Componente | Decisión de diseño | Caso de aceptación | Prueba unitaria |
|---------------|-----------|------------|--------------------|--------------------|-----------------|
| RF-01 | DS-01 | `frontend/App.tsx` | D-06, D-07 | CA-01 | `test_chat_ok_y_normaliza_espacios` |
| RF-02 | DS-01, DS-02 | `services/rag.py` | D-01, D-04 | CA-02, CA-04 | `test_respuesta_incluye_fuentes_y_usa_top_k` |
| RF-03 | DS-02 | `services/rag.py` | D-01, D-08 | CA-05 | `test_sin_contexto_usa_marcador` |
| RF-04 | DS-06 | `api/health.py` | D-02 | CA-14 | `test_health_ok` |
| RF-05 | DS-05 | `scripts/ingest.py` | D-03 | CA-15 | `test_is_active`, `test_is_active_serie_pandas` |
| RF-06 | DS-03, DS-04 | `core/rate_limit.py`, `core/turnstile.py` | D-09 | CA-08…CA-12 | `test_rate_limit_bloquea_peticion_31`, `test_token_valido`, `test_token_invalido` |

---

## 5. Cómo reproducir la evidencia

```powershell
cd backend
.\.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest --cov=app --cov-report=term-missing
```

Resultado esperado al cierre de este incremento: **28 pruebas aprobadas, 0 fallidas,
88 % de cobertura de líneas** sobre `backend/app`.
