# Asistente Virtual — Municipalidad de Peñalolén

Chatbot que responde consultas ciudadanas sobre trámites municipales (dónde ir,
horarios, requisitos, dependencias) usando **solo** la base de preguntas frecuentes
de la Municipalidad de Peñalolén.

- No requiere registro ni contraseña.
- No guarda conversaciones.
- Cada respuesta muestra la pregunta frecuente y la dependencia en que se basa.

> Esta guía está pensada para alguien que **nunca ha ejecutado el proyecto**.
> Si solo quieres levantarlo rápido, ve directo a
> [6. Ejecutar el proyecto](#6-ejecutar-el-proyecto).

---

## Índice

1. [Qué necesitas instalar](#1-qué-necesitas-instalar)
2. [Cómo está armado el proyecto](#2-cómo-está-armado-el-proyecto)
3. [Descargar el código](#3-descargar-el-código)
4. [Instalar el backend (Python)](#4-instalar-el-backend-python)
5. [Instalar el frontend y el motor de IA](#5-instalar-el-frontend-y-el-motor-de-ia)
6. [Ejecutar el proyecto](#6-ejecutar-el-proyecto)
7. [Comprobar que funciona](#7-comprobar-que-funciona)
8. [Problemas comunes](#8-problemas-comunes)
9. [Estructura del repositorio](#9-estructura-del-repositorio)
10. [Ejecutar las pruebas](#10-ejecutar-las-pruebas)
11. [Documentación técnica](#11-documentación-técnica)

---

## 1. Qué necesitas instalar

| Programa | Versión recomendada | Para qué sirve | Dónde obtenerlo |
|----------|---------------------|----------------|-----------------|
| **Python** | 3.11 a 3.13 | Ejecuta el backend (API y motor de búsqueda) | https://www.python.org/downloads/ |
| **Node.js** | 20 a 24 (LTS) | Ejecuta el frontend y el router de IA | https://nodejs.org/ |
| **Git** | Cualquiera reciente | Descargar el código | https://git-scm.com/downloads |

> **Importante en Windows:** al instalar Python marca la casilla
> **“Add python.exe to PATH”**. Si no lo haces, la terminal no reconocerá `python`.

**Verifica que quedaron instalados.** Abre una terminal nueva (PowerShell) y ejecuta:

```powershell
python --version
node --version
npm --version
git --version
```

Debes ver un número de versión en cada línea. Si alguno dice “no se reconoce”,
reinstala ese programa y **abre una terminal nueva**.

---

## 2. Cómo está armado el proyecto

El sistema son **tres piezas** que se ejecutan al mismo tiempo y se comunican por
`localhost`:

```
┌─────────────────────┐     ┌──────────────────────┐     ┌────────────────────────┐
│  Frontend (React)   │────▶│  Backend (FastAPI)   │────▶│  FreeLLMAPI (router)   │
│  localhost:5173     │     │  localhost:8000      │     │  localhost:3001        │
│  Lo que ve el       │     │  Busca en la base de │     │  Habla con el modelo   │
│  ciudadano          │     │  conocimiento y      │     │  de IA (Groq, Gemini,  │
│                     │     │  arma la respuesta   │     │  OpenRouter, etc.)     │
└─────────────────────┘     └──────────────────────┘     └────────────────────────┘
                                      │
                                      ▼
                            ┌──────────────────────┐
                            │  Chroma (base        │
                            │  vectorial local)    │
                            │  data/processed/     │
                            └──────────────────────┘
```

- **Frontend:** la página del chat.
- **Backend:** recibe la pregunta, busca las preguntas frecuentes más parecidas y
  pide al modelo de IA que redacte la respuesta con esa información.
- **FreeLLMAPI:** un programa que actúa de puente entre el backend y los proveedores
  de IA gratuitos. El backend no habla directamente con OpenAI/Groq: habla con
  FreeLLMAPI, que elige un proveedor disponible.

**Puertos usados**

| Puerto | Servicio | ¿Obligatorio? |
|:------:|----------|----------------|
| 5173 | Frontend (chat) | Sí |
| 8000 | Backend (API) | Sí |
| 3001 | FreeLLMAPI (motor de IA) | Sí, para respuestas reales |
| 5174 | Panel de FreeLLMAPI | Solo para configurar claves |

---

## 3. Descargar el código

```powershell
git clone https://github.com/vichogol/ASISTENTE-VIRTUAL.git
cd ASISTENTE-VIRTUAL
```

Si ya tienes la carpeta del proyecto, simplemente abre una terminal **dentro de ella**:

```powershell
cd C:\ruta\a\ASISTENTE-VIRTUAL
```

Todos los comandos de esta guía se ejecutan desde la raíz del proyecto salvo que se
indique otra carpeta.

---

## 4. Instalar el backend (Python)

### 4.1 Crear el entorno virtual

Un entorno virtual es una carpeta con las librerías del proyecto, aisladas del resto
del computador. Se crea **una sola vez**.

**Windows (PowerShell):**

```powershell
cd backend
python -m venv .venv
```

**macOS / Linux:**

```bash
cd backend
python3 -m venv .venv
```

### 4.2 Activar el entorno virtual

**Windows (PowerShell):**

```powershell
.\.venv\Scripts\Activate.ps1
```

Si aparece un error como *“la ejecución de scripts está deshabilitada”*, ejecuta una
vez:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

y vuelve a intentar la activación.

**macOS / Linux:**

```bash
source .venv/bin/activate
```

Sabrás que está activo porque la línea de la terminal empieza con `(.venv)`.

> Si prefieres no activarlo, puedes usar directamente
> `.\.venv\Scripts\python.exe` (Windows) o `.venv/bin/python` (macOS/Linux)
> en lugar de `python`.

### 4.3 Instalar las dependencias

```powershell
pip install -r requirements.txt
```

> **Aviso:** la descarga pesa **entre 1 y 2 GB** porque incluye PyTorch, el motor que
> ejecuta el modelo de búsqueda semántica. Puede tardar varios minutos. Es normal.

### 4.4 Crear el archivo de configuración

El proyecto trae una plantilla llamada `.env.example`. Cópiala como `.env`:

**Windows:**

```powershell
Copy-Item .env.example .env
```

**macOS / Linux:**

```bash
cp .env.example .env
```

Abre `backend/.env` con un editor de texto y revisa estos valores:

```env
FREELLMAPI_BASE_URL=http://localhost:3001/v1
FREELLMAPI_API_KEY=PEGA-AQUI-TU-UNIFIED-KEY
FREELLMAPI_MODEL=auto

CHROMA_PATH=../data/processed/chroma
EMBEDDING_MODEL=paraphrase-multilingual-MiniLM-L12-v2

TURNSTILE_ENABLED=false
TURNSTILE_SECRET_KEY=

RATE_LIMIT=30/minute
CORS_ORIGINS=http://localhost:5173
TOP_K=5
```

- `FREELLMAPI_API_KEY`: la clave que obtendrás en el paso **5.3**.
- Deja `TURNSTILE_ENABLED=false` mientras desarrollas localmente.
- **No subas `.env` a Git**: contiene secretos.

> **Ojo con las variables de entorno del sistema.** Si existe una variable de
> entorno llamada `FREELLMAPI_API_KEY` en Windows, macOS o Linux, **tiene prioridad
> sobre el archivo `.env`**. Es la causa más común de un error `401 Invalid API key`
> cuando la clave del `.env` es correcta. Para comprobarlo:
>
> ```powershell
> [Environment]::GetEnvironmentVariable("FREELLMAPI_API_KEY","User")
> ```
>
> Si devuelve una clave antigua, elimínala y abre una terminal nueva:
>
> ```powershell
> [Environment]::SetEnvironmentVariable("FREELLMAPI_API_KEY", $null, "User")
> ```

### 4.5 Construir el índice de conocimiento

El backend busca respuestas en una base vectorial que ya viene incluida en
`data/processed/chroma`. Si está vacía o cambiaste el Excel de preguntas frecuentes,
reconstrúyela:

```powershell
python scripts/ingest.py
```

Debe terminar con un mensaje como `Ingestadas 191 preguntas en ../data/processed/chroma`.

> La primera ejecución descarga el modelo de embeddings (~470 MB) desde Hugging Face.
> Necesitas conexión a Internet **solo esta vez**.

---

## 5. Instalar el frontend y el motor de IA

### 5.1 Instalar dependencias del frontend

Abre **otra terminal** en la raíz del proyecto:

```powershell
cd frontend
npm install
```

### 5.2 Instalar FreeLLMAPI (motor de IA)

FreeLLMAPI es el puente hacia los proveedores de IA. Ya viene en la carpeta
`freellmapi/`.

```powershell
cd ..\freellmapi
npm install
```

### 5.3 Configurar FreeLLMAPI (solo la primera vez)

Necesitas dos terminales para esta parte.

**Terminal A — arrancar el servidor de IA** (déjala abierta):

```powershell
cd freellmapi
npm run dev -w server
```

Debe aparecer un mensaje como `Server running on http://[::]:3001`.

**Terminal B — abrir el panel de configuración:**

```powershell
cd freellmapi
npm run dev -w client -- --port 5174
```

Abre en el navegador: **http://localhost:5174**

1. Si es la primera vez, el panel te pedirá **crear una cuenta local**
   (correo y contraseña inventados; no se envía nada a Internet). Si el servidor
   imprime un *setup code* en la Terminal A, ingrésalo.
2. Ve a la página **Keys** y agrega al menos una clave de proveedor gratuito.
   Algunas opciones: **Groq**, **Google AI Studio (Gemini)**, **OpenRouter**,
   **Cerebras**. Cada proveedor te da su clave al registrarte en su sitio.
3. En la cabecera de **Keys** copia la **Unified API key**
   (empieza con `freellmapi-...`). **No** copies las claves de los proveedores.
4. Pega esa clave en `backend/.env`:

   ```env
   FREELLMAPI_API_KEY=freellmapi-tu-clave-aqui
   ```

5. Vuelve a la Terminal B y detén el panel con `Ctrl + C`. **No necesitas dejarlo
   abierto**: solo sirve para configurar.

> **Sin claves de proveedor, el chat responderá** “No pude conectarme al servicio de
> IA…”. Es el comportamiento esperado: el backend funciona, pero no hay modelo que
> redacte la respuesta.

#### Alternativa: usar un proveedor directo (sin FreeLLMAPI)

El backend habla el protocolo estándar de OpenAI, así que puedes apuntarlo
directamente a un proveedor. Por ejemplo, con Groq:

```env
FREELLMAPI_BASE_URL=https://api.groq.com/openai/v1
FREELLMAPI_API_KEY=gsk_tu_clave_de_groq
FREELLMAPI_MODEL=llama-3.3-70b-versatile
```

En ese caso puedes saltarte los pasos 5.2 y 5.3. Revisa en el sitio del proveedor
qué modelos están disponibles para tu cuenta.

---

## 6. Ejecutar el proyecto

Necesitas **tres terminales abiertas al mismo tiempo**. El orden recomendado es:
primero la IA, luego el backend, luego el frontend.

### Terminal 1 — Motor de IA (puerto 3001)

```powershell
cd freellmapi
npm run dev -w server
```

Espera a ver `Server running on ...:3001`. Déjala abierta.

### Terminal 2 — Backend (puerto 8000)

```powershell
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

Debe aparecer `Uvicorn running on http://127.0.0.1:8000`.

> La primera vez tarda **15-25 segundos** porque carga el modelo de embeddings.
> Es normal que la terminal parezca congelada un momento.

### Terminal 3 — Frontend (puerto 5173)

```powershell
cd frontend
npm run dev
```

Debe aparecer `Local: http://localhost:5173/`.

### Abrir el chat

En el navegador entra a:

**http://localhost:5173**

Escribe una consulta, por ejemplo: *“¿Dónde pago el permiso de circulación?”*

### Resumen de comandos

| Terminal | Carpeta | Comando | URL |
|----------|---------|---------|-----|
| 1 | `freellmapi` | `npm run dev -w server` | http://localhost:3001 |
| 2 | `backend` | `.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000` | http://127.0.0.1:8000/health |
| 3 | `frontend` | `npm run dev` | http://localhost:5173 |

### Detener todo

En cada terminal presiona `Ctrl + C`. Si una terminal quedó “pegada”, ciérrala.

---

## 7. Comprobar que funciona

**1. Backend vivo**

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

Respuesta esperada:

```json
{ "status": "ok" }
```

**2. Motor de IA vivo**

```powershell
Invoke-WebRequest http://127.0.0.1:3001/v1/models -Headers @{ Authorization = "Bearer TU_UNIFIED_KEY" }
```

- `200`: la clave es válida.
- `401`: la clave de `backend/.env` no corresponde a la de FreeLLMAPI.

**3. Consulta completa (sin navegador)**

```powershell
Invoke-RestMethod -Method Post http://127.0.0.1:8000/api/chat `
  -ContentType "application/json" `
  -Body '{"message":"¿Dónde pago el permiso de circulación?"}'
```

Debe devolver un objeto con `answer` (texto de la respuesta) y `sources`
(preguntas frecuentes y dependencias usadas).

**4. Documentación interactiva de la API**

Abre http://127.0.0.1:8000/docs

---

## 8. Problemas comunes

| Síntoma | Causa probable | Solución |
|---------|----------------|----------|
| `python` o `npm` “no se reconoce” | No está en el PATH o la terminal es antigua | Reinstala marcando “Add to PATH” y abre una terminal nueva |
| `No se puede cargar el archivo ... porque la ejecución de scripts está deshabilitada` | Política de PowerShell | `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` |
| **502 Bad Gateway** en el navegador al preguntar | El backend no está corriendo, o corre en otro puerto | Verifica la Terminal 2 y que use el puerto 8000 |
| `EADDRINUSE` / “puerto en uso” | Ya hay un proceso usando ese puerto | Cierra la otra terminal o cambia el puerto (`--port 8001`) |
| `429` / “Demasiadas solicitudes” | Se superó el límite de 30 consultas por minuto | Espera un minuto; es el control anti-abuso |
| “No pude conectarme al servicio de IA…” | FreeLLMAPI detenido o sin claves de proveedor | Revisa la Terminal 1 y configura las claves (paso 5.3) |
| `401` al consultar `/v1/models` | La `FREELLMAPI_API_KEY` no es la unified key correcta | Cópiala de nuevo desde el panel y reinicia el backend |
| `401 Invalid API key` aunque la clave del `.env` es correcta | Una variable de entorno del sistema con una clave antigua tiene prioridad sobre `.env` | `[Environment]::SetEnvironmentVariable("FREELLMAPI_API_KEY", $null, "User")`, cierra la terminal y vuelve a abrirla |
| Cambiaste `.env` y el error persiste | El backend guarda el cliente HTTP en memoria y `--reload` solo vigila archivos `.py` | Detén el backend con `Ctrl + C` y vuelve a iniciarlo |
| “Modelo no encontrado” | `FREELLMAPI_MODEL` apunta a un modelo inexistente | Usa `auto` |
| La primera consulta tarda mucho | El modelo de embeddings se está cargando | Espera; las siguientes serán rápidas |
| La búsqueda no encuentra nada | Índice vacío o ruta incorrecta | Ejecuta `python scripts/ingest.py` desde `backend/` |
| El navegador no muestra el chat | El frontend no está corriendo | Revisa la Terminal 3 y abre http://localhost:5173 |

**Regla general:** si algo falla, mira la **terminal del servicio correspondiente**.
Ahí aparece el error real.

---

## 9. Estructura del repositorio

```
ASISTENTE-VIRTUAL/
├── backend/                 API en Python (FastAPI)
│   ├── app/
│   │   ├── api/             Endpoints: /health y /api/chat
│   │   ├── core/            Configuración, límite de solicitudes, captcha
│   │   ├── services/        Lógica RAG, base vectorial y cliente del LLM
│   │   ├── config.py        Lectura de variables de entorno
│   │   └── main.py          Punto de entrada de la aplicación
│   ├── scripts/ingest.py    Convierte el Excel en la base vectorial
│   ├── tests/               Pruebas unitarias y de integración
│   └── requirements.txt     Dependencias de Python
├── frontend/                Interfaz del chat (React + Vite + TypeScript)
├── freellmapi/              Router de proveedores de IA (Node.js)
├── data/
│   ├── raw/                 Excel original de preguntas frecuentes
│   └── processed/chroma/    Índice vectorial generado
├── docs/entrega-2/          Diagramas, decisiones de diseño, pruebas y riesgos
└── README.md
```

---

## 10. Ejecutar las pruebas

```powershell
cd backend
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest --cov=app --cov-report=term-missing
```

Resultado esperado: **28 pruebas aprobadas** y **88 % de cobertura**.

No necesitas FreeLLMAPI ni conexión a Internet para ejecutar las pruebas: las
dependencias externas se reemplazan por dobles de prueba.

---

## 11. Documentación técnica

| Documento | Contenido |
|-----------|-----------|
| [docs/entrega-2/00-INDICE.md](docs/entrega-2/00-INDICE.md) | Índice y alcance del incremento |
| [01-diagramas-secuencia.md](docs/entrega-2/01-diagramas-secuencia.md) | Diagramas de secuencia |
| [02-diagrama-componentes.md](docs/entrega-2/02-diagrama-componentes.md) | Diagrama de componentes |
| [03-decisiones-diseno.md](docs/entrega-2/03-decisiones-diseno.md) | Decisiones de diseño (ADR) |
| [04-atributos-calidad-iso25010.md](docs/entrega-2/04-atributos-calidad-iso25010.md) | Atributos de calidad ISO/IEC 25010 |
| [05-plan-pruebas-aceptacion.md](docs/entrega-2/05-plan-pruebas-aceptacion.md) | Plan de pruebas de aceptación |
| [06-evidencia-pruebas-unitarias.md](docs/entrega-2/06-evidencia-pruebas-unitarias.md) | Evidencia de pruebas unitarias |
| [07-matriz-riesgos-seguridad.md](docs/entrega-2/07-matriz-riesgos-seguridad.md) | Matriz de riesgos de seguridad |

---

## Créditos

Proyecto semestral de **TICS331 — Diseño y Calidad de Software**.
Municipalidad de Peñalolén, Semestre 2 — 2026.
