
# Peñalolín · Peñalolén, tu asistente virtual municipal

Aplicación web en español para consultar trámites y servicios de la Municipalidad de Peñalolén, identificar dónde hacerlos y encontrar el canal oficial para recibir atención. El frontend usa React, Vite y TypeScript. El backend usa FastAPI y un servicio de consultas independiente de HTTP.

## Levantar el proyecto

Se recomienda Python 3.13 o 3.14 y Node.js 22.12 o superior. Conserva la carpeta `data/` junto a `backend/` y `frontend/`.

**Terminal 1 · API en Windows**

~~~powershell
cd backend
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-dev.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
~~~

En macOS o Linux, usa `python3 -m venv .venv` y `.venv/bin/python` para los dos comandos siguientes.

**Terminal 2 · Interfaz**

~~~powershell
cd frontend
npm ci
npm run dev
~~~

Abre [el asistente](http://localhost:5173) o [la documentación interactiva de la API](http://127.0.0.1:8000/docs). Vite reenvía `/api` al backend local. En producción, sirve `frontend/dist/` tras `npm run build` y reenvía `/api` al backend desde el mismo origen, o establece `VITE_API_URL` durante el build y configura `CORS_ORIGINS` en el backend.

## Consultas y respaldo municipal

- El Excel original permanece en `data/raw/preguntas_frecuentes_penalolen.xlsx` y es idéntico al adjunto «20.07.2026 preguntasfrecuentes Equipos.xlsx». El lector prioriza 843 fichas de la hoja visible «Revisdas» y conserva 191 fichas activas de la hoja oculta «preguntasfrecuentes» como referencia histórica. Las fichas históricas se presentan con el contacto para confirmar vigencia. Las fuentes identifican hoja, número de ficha, dependencia y revisión.
- El buscador distingue coincidencia exacta, equivalencia tras normalizar expresiones en español y similitud léxica ponderada. Comprueba que la ficha cubra la intención consultada, por ejemplo costo, horario, documentos o pago. Ante resultados incompatibles o detalles sin respaldo, indica el canal de atención en lugar de extrapolar.
- El asistente saluda, responde a agradecimientos y propone preguntas cuando el tema es amplio. Por ejemplo, «piscina» pide elegir entre ubicación, horarios y talleres. «Horario piscina» combina el recinto y la intención para abrir la ficha revisada correspondiente. También entiende expresiones como «carnet para manejar» y «permiso del auto». Las sugerencias envían la pregunta canónica del Excel y los saludos y turnos de aclaración se manejan fuera del historial de aprendizaje.
- `app.services.rag.answer(message, session=None)` puede llamarse desde otros adaptadores. Devuelve un campo `answer` de texto y campos estructurados para secciones, fuentes, enlaces, recintos, derivación y valoración. `GET /api/buildings` entrega el catálogo. `PUT /api/chat/{interaction_id}/feedback` permite registrar o corregir una valoración en su sesión. `GET /health` sigue disponible.
- El catálogo reúne 15 recintos. `place_catalog.py` registra direcciones, ubicaciones verificadas y fotos con fuente. `municipal.py` vincula nombres y dependencias con las fichas. La vista Three.js combina calles y huellas de OpenStreetMap, elevación de Mapzen y modelos arquitectónicos de referencia. Permite girar, acercar, seleccionar un recinto, revisar sus servicios, llevar un trámite al chat y abrir indicaciones externas mediante la dirección publicada. [Portal de recintos y trámites](https://tramites.penalolen.cl/Tramites/buscar) · [Directorio municipal](https://www.penalolen.cl/directorio-telefonico/) · [OpenStreetMap](https://www.openstreetmap.org/copyright).
- La derivación aplica reglas explícitas por tema y dependencia. Muestra los datos disponibles de la unidad o, cuando faltan, el canal central de la OIRS. [Atención vecinal](https://participa.penalolen.cl/p/4-informacion-y-atencion-vecinal) · [Preguntas frecuentes municipales](https://tramites.penalolen.cl/Preguntas/ver) · [Directorio del portal](https://tramites.penalolen.cl/Telefonos).

Para actualizar la fuente, reemplaza el Excel por la versión autorizada con los mismos encabezados. También puedes indicar `FAQ_PATH` en `backend/.env`. Si activaste Chroma, vuelve a generar su índice después del cambio. Las promociones guardadas se aplican solo mientras la revisión de la ficha siga vigente.

## Mejora continua

El registro SQLite local, por defecto `data/processed/interactions.sqlite3`, guarda consultas con enmascarado básico de correos, RUT y números largos, similitud y ficha propuesta, valoraciones y eventos de promoción/revocación. Usa un hash del identificador de sesión. Para promover una formulación se requieren al menos tres sesiones distintas, una similitud de al menos 0,84 en cada voto favorable y al menos un 85 % de apoyo. Los votos duplicados de una sesión cuentan una vez y una valoración posterior puede revocar una promoción.

La promoción conserva una copia de la respuesta oficial y las referencias a las interacciones que la respaldan. Solo refuerza candidatos de la misma revisión que coincidan de forma independiente con la intención y términos de la consulta. Las formulaciones cercanas también pueden beneficiarse. El Excel sigue siendo la fuente de las respuestas públicas.

Mantén el archivo SQLite fuera del control de versiones y restringe su acceso en el servidor. El enmascarado automático es parcial y pueden quedar datos personales escritos en texto libre. Acuerda con el equipo responsable el acceso, la retención y el borrado antes de habilitar el registro en una instalación pública. `LEARNING_ENABLED=false` deshabilita el registro y las valoraciones. `LEARNING_PATH` cambia la ubicación; si hay que reiniciar el aprendizaje, detén el backend y mueve la base fuera de la ruta configurada.

## Opciones del backend

Copia `backend/.env.example` a `backend/.env` para ajustar estas opciones.

| Opción | Uso |
| --- | --- |
| `SEMANTIC_SEARCH=true` | Añade similitud vectorial al ranking de candidatos que ya cuentan con respaldo léxico. Instala `requirements-semantic.txt` en el mismo entorno y ejecuta `python scripts/ingest.py` desde `backend/`. El índice corresponde a la versión del Excel y del modelo. |
| `AI_SUMMARY_ENABLED=true` | Un servidor compatible con OpenAI elige una frase introductoria entre extractos de la ficha. Configura `FREELLMAPI_BASE_URL`, `FREELLMAPI_API_KEY` y `FREELLMAPI_MODEL`. Solo se envían fragmentos y la pregunta canónica del Excel. |
| `TURNSTILE_ENABLED=true` | Configura `TURNSTILE_SECRET_KEY` en el backend y `VITE_TURNSTILE_SITE_KEY` en el frontend con sus credenciales de Cloudflare. |
| `RATE_LIMIT` | Límite de peticiones por IP, con valor inicial de 30 por minuto. Configura además el proxy y el origen CORS de tu despliegue. |

El modo local funciona con el Excel sin descargar modelos, instalar Chroma ni configurar un proveedor de IA. Si el índice falta o el proveedor falla, la búsqueda y la presentación locales siguen disponibles.

## Verificar y preparar para Git

~~~powershell
cd backend
.\.venv\Scripts\python.exe -m pytest
cd ..\frontend
npm ci
npx playwright install chromium
npm run lint
npm run build
npm test
~~~

Para reutilizar Edge instalado en Windows, ejecuta `$env:PLAYWRIGHT_CHANNEL='msedge'` antes de `npm test`. Si Uvicorn está en el puerto 8000 con aprendizaje habilitado, `$env:RUN_LIVE_API='1'` activa también la prueba que consulta la API real y guarda una valoración. `npm test` levanta su propio Vite en el puerto 5174.

### Publicar cambios en el repositorio compartido

La carpeta extraída del Escritorio es una copia del proyecto. Para publicar los cambios y conservar el historial compartido, aplica el parche completo en un clon limpio.

~~~powershell
git clone https://github.com/vichogol/ASISTENTE-VIRTUAL.git
cd ASISTENTE-VIRTUAL
git switch -c mejora/asistente-conversacional
$parche = 'C:\ruta\mejora-asistente-municipal.patch'
git apply --check $parche
git apply $parche
git status --short
git add -A
git diff --cached --stat
git commit -m "Mejora el asistente municipal y sus respuestas"
git push -u origin mejora/asistente-conversacional
~~~

Cambia la ruta del parche por la ubicación real del archivo descargado. Si la comprobación del parche falla, revisa en qué rama estás y si ese trabajo ya estaba aplicado. Después del push, abre el repositorio en GitHub y crea un pull request desde `mejora/asistente-conversacional` hacia `main`. Si tu cuenta carece de acceso de escritura, publica la rama en un fork y abre el pull request hacia el repositorio compartido.

Consulta [el estado y los límites de la entrega](ESTADO_PROYECTO.md) y [la documentación de las entregas anteriores](docs/entrega-2/00-INDICE.md).
