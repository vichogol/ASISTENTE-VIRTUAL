# Estado del Proyecto — Asistente Virtual Municipalidad de Peñalolén

Última actualización: 2026-10-30

## Objetivo
Chatbot RAG en español para resolver dudas sobre trámites municipales: cuál tomar según circunstancia, a dónde acudir, horarios, teléfonos, ubicaciones y links. Sin login, sin persistencia de conversaciones.

## Stack
- Backend: FastAPI + Uvicorn (Python 3.13), venv en `backend/.venv`
- Frontend: React + Vite + TypeScript
- Embeddings: sentence-transformers `paraphrase-multilingual-MiniLM-L12-v2` (local, CPU)
- Vector store: Chroma (persistente en `data/processed/chroma`)
- IA: FreeLLMAPI (router OpenAI-compatible, model `auto`) — no apto para producción según su autor; migrar a paid si escala
- Seguridad: Cloudflare Turnstile (backend listo, frontend pendiente de site key) + slowapi rate limit + CORS
- Despliegue: VPS municipal

## Base de conocimiento
- Archivo: `data/raw/preguntas_frecuentes_penalolen.xlsx`
- 191 filas ingested (filtradas por isActivo). Columnas: preguntaFrecuenteID, categoriaPreguntaFrecuente, nombrePreguntaFrecuente, descripcionPreguntaFrecuente, tagPreguntaFrecuente, Direccion, fechaCreacionPreguntaFrecuente, usuarioCreadorPreguntaFrecuente, isMostrarEnPortal, isActivo, Rango Etáreo, Sexo
- Rango Etáreo y Sexo solo "general" en 2 filas; resto NaN → tratado como "general" (aplica a todos)
- 14 filas sin isActivo/isMostrarEnPortal → tratadas como activas y mostrables por defecto
- Sin PII

## Estructura
```
backend/
  app/ (config, main, api/, core/, services/)
  scripts/ingest.py
  requirements.txt, .env.example, .gitignore
frontend/ (Vite + React, .env.example)
data/raw/, data/processed/
infra/, docs/
ESTADO_PROYECTO.md
```

## Hecho
- [x] Estructura inicial
- [x] Ingesta Excel → Chroma (191 docs) verificada
- [x] Backend FastAPI: /health, /api/chat (RAG), rate limit, Turnstile verify, CORS, sanitización
- [x] Manejo de error de conexión a IA (respuesta amigable)
- [x] Frontend React+Vite: chat UI, streaming no (JSON), variables de color
- [x] Frontend build OK
- [x] .env.example (backend y frontend), .gitignore

## Pendiente
- [x] Colores institucionales aplicados (#222858, #0450C0, #FF8500, #FFFFFF) en `frontend/src/App.css`
- [ ] FreeLLMAPI: instalar/ejecutar en VPS, cargar provider keys, generar unified key → `backend/.env`
- [ ] Cloudflare: crear site, obtener site key + secret key; activar Turnstile en frontend (invisible) y backend
- [ ] Implementar Turnstile invisible en frontend (actualmente backend listo)
- [ ] Definir límites exactos de rate limit (actual 30/min)
- [ ] CORS a dominio de producción
- [ ] Despliegue VPS (systemd/docker), HTTPS, Cloudflare delante
- [ ] Pruebas (unitarias retriever, integración endpoint, carga)
- [ ] Fallback humano (derivación a OIRS)
- [ ] README de despliegue

## Dónde dejar la API key (FreeLLMAPI)
- Archivo: `backend/.env`
- Variables:
  - `FREELLMAPI_BASE_URL=http://localhost:3001/v1` (o host del FreeLLMAPI en VPS)
  - `FREELLMAPI_API_KEY=<unified key generada en el dashboard de FreeLLMAPI>`
  - `FREELLMAPI_MODEL=auto`
- La key es la "Unified API key" del dashboard de FreeLLMAPI, no las keys de proveedores upstream.
- FreeLLMAPI corre como servicio local (Node 20+): `git clone ... && npm install && npm run dev` (puerto 3001 por defecto).
- Nunca exponer la key al frontend; solo backend la usa.

## Notas
- Sin persistencia de conversaciones; sesiones en cookies (frontend puede generar session_id).
- Prompt injection mitigado por system prompt + separación de roles.
- RAG top-k=5, temperatura 0.2.
- Backend probado: /health OK, /api/chat falla solo si FreeLLMAPI no corre (manejado con mensaje amigable).
