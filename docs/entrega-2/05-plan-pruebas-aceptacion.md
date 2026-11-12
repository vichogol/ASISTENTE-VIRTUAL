# 05 — Estrategia y plan de pruebas de aceptación

**Versión:** 1.0 · **Sprint:** 2 · **Responsable:** equipo de desarrollo
**Stakeholder aceptante:** contraparte municipal (Dirección de Informática / OIRS)

---

## 1. Objetivo y alcance

**Objetivo.** Definir, ejecutar y evidenciar las pruebas que demuestran que el primer
incremento del Asistente Virtual satisface los requerimientos acordados y los atributos
de calidad priorizados, con criterios de aceptación verificables y trazables.

**En alcance**

- Endpoint `POST /api/chat` (flujo RAG, validaciones, cuota, captcha, contingencia).
- Endpoint `GET /health`.
- Interfaz de chat del ciudadano (envío, estado de carga, render de fuentes, errores).
- Pipeline de ingesta `scripts/ingest.py`.
- Controles de seguridad del incremento (rate limit, Turnstile backend, CORS, secretos).

**Fuera de alcance (Sprint 3+)**

- Autenticación de funcionarios y panel de administración de contenido.
- Analítica de consultas y derivación automática a OIRS por API.
- Pruebas de penetración formales y auditoría WCAG completa.
- Canal WhatsApp / telefonía.

---

## 2. Estrategia de pruebas

Se aplica una **pirámide de pruebas** con automatización prioritaria en la base, porque
las dependencias de IA son costosas y no deterministas.

```
        ┌──────────────────────────┐
        │  Aceptación (manual)     │  23 casos · stakeholder
        ├──────────────────────────┤
        │  Sistema / E2E (manual)  │  flujo real con Chroma + LLM
        ├──────────────────────────┤
        │  Integración (auto)      │  TestClient sobre FastAPI
        ├──────────────────────────┤
        │  Unitaria (auto)         │  28 pruebas · pytest
        └──────────────────────────┘
```

| Nivel | Objetivo | Técnica | Automatización | Herramienta |
|-------|----------|---------|----------------|-------------|
| Unitaria | Verificar lógica de RAG, configuración, captcha y reglas de ingesta | Caja blanca, partición de equivalencia, valores límite | 100 % | `pytest` |
| Integración | Verificar contrato HTTP, códigos de estado, validación y cuota | Caja negra sobre `TestClient` | 100 % | `pytest` + `fastapi.testclient` |
| Sistema | Verificar el flujo completo con modelo real y proveedor real | Caja negra, escenario end-to-end | Manual (script reproducible) | Navegador + `curl` |
| Aceptación | Verificar valor para el ciudadano y criterios del stakeholder | Caja negra guiada por casos | Manual | Checklist firmado |
| No funcional | Latencia, carga, accesibilidad, seguridad básica | Medición y análisis | Parcial | k6, Lighthouse, OWASP ZAP |

### 2.1 Técnicas de diseño de casos

- **Partición de equivalencia:** longitud del mensaje (0 / 1..1000 / >1000);
  `isActivo` (activo / inactivo / nulo / no numérico).
- **Valores límite:** 1 y 1000 caracteres; 30.ª y 31.ª solicitud por minuto.
- **Tabla de decisión:** `turnstile_enabled` × `turnstile_token` × `secreto` (8 combinaciones,
  se prueban las 4 representativas).
- **Transición de estados:** `idle → loading → success | error` en el SPA.
- **Prueba de humo:** `/health` + una consulta conocida tras cada despliegue.

---

## 3. Entornos y datos de prueba

| Entorno | Composición | Uso |
|---------|-------------|-----|
| Local (dev) | FastAPI + Chroma local + FreeLLMAPI en `:3001`; CORS `localhost:5173` | Desarrollo y pruebas unitarias/integración |
| Staging (VPS) | Nginx + Uvicorn + FreeLLMAPI como servicio; Turnstile activo | Sistema y aceptación |
| Producción | Igual a staging, dominio municipal y HTTPS | Operación |

**Datos de prueba**

| Conjunto | Descripción | Uso |
|----------|-------------|-----|
| D-01 | Índice real de 191 preguntas activas | Sistema / aceptación |
| D-02 | Conjunto dorado de 30 consultas con respuesta esperada y fuente | CA-04 (evaluación de calidad) |
| D-03 | Consultas fuera de dominio (clima, farándula, política) | CA-05 |
| D-04 | Entradas maliciosas (XSS, *prompt injection*, 1.001 caracteres) | CA-07, CA-20 |
| D-05 | Excel con filas `isActivo = 0`, `NaN` y texto | CA-15 |

**Consideración ética:** los datos de prueba no contienen información personal real.
Las consultas del conjunto dorado son ficticias y de dominio público.

---

## 4. Criterios de entrada y salida

**Entrada (para iniciar la ejecución de aceptación)**

1. Build de frontend y backend desplegado en staging.
2. Índice Chroma reconstruido con el Excel vigente.
3. Pruebas unitarias y de integración en verde.
4. Casos de aceptación revisados y aprobados por el stakeholder.

**Salida (criterios de aceptación del incremento)**

| Criterio | Umbral |
|----------|--------|
| Casos de aceptación críticos y altos aprobados | 100 % |
| Casos de aceptación medios aprobados | ≥ 90 % |
| Pruebas unitarias/integración | 100 % en verde |
| Cobertura de líneas del backend | ≥ 80 % |
| Defectos abiertos severidad 1 y 2 | 0 |
| Latencia p95 (modelo caliente) | ≤ 5 s |
| Respuestas 5xx en la suite de aceptación | 0 |

---

## 5. Roles y responsabilidades

| Rol | Responsabilidad |
|-----|-----------------|
| Líder técnico | Aprobar estrategia, revisar defectos críticos, firmar el reporte |
| Desarrollador backend | Pruebas unitarias/integración, corrección de defectos |
| Desarrollador frontend | Pruebas de interfaz, accesibilidad y compatibilidad |
| Encargado de contenido (municipal) | Validar el conjunto dorado y la vigencia de las respuestas |
| Stakeholder | Ejecutar/observar los casos de aceptación y firmar la conformidad |

---

## 6. Casos de aceptación

**Prioridad:** `Crítica` (bloquea el incremento) · `Alta` · `Media`.
**Estado:** `Auto` = cubierto por prueba automatizada · `Manual` = requiere ejecución humana · `Pendiente`.

| ID | RF | Caso | Precondición | Resultado esperado | Prioridad | Tipo | Estado |
|----|----|------|--------------|--------------------|-----------|------|--------|
| CA-01 | RF-01 | Consulta válida en lenguaje natural | Servicio operativo | 200 con respuesta en español ≤ 5 s | Crítica | Funcional | Auto + Manual |
| CA-02 | RF-02 | Visualización de fuentes | Respuesta con coincidencias | Se listan pregunta y dependencia bajo la burbuja | Alta | Funcional | Manual |
| CA-03 | RF-02 | Consulta con paráfrasis y errores ortográficos | Índice cargado | Respuesta pertinente (misma intención) | Alta | Funcional | Manual |
| CA-04 | RF-02 | Calidad sobre conjunto dorado (30 consultas) | D-02 definido | ≥ 80 % de respuestas correctas y citadas | Crítica | Calidad | Pendiente |
| CA-05 | RF-03 | Consulta fuera de dominio | D-03 listo | Declara no tener la información y deriva a OIRS | Crítica | Funcional | Manual |
| CA-05b | RF-03 | Documento bajo umbral de similitud | Umbral implementado | Derivación determinista sin invocar al LLM | Media | Funcional | Pendiente (DT-02) |
| CA-06 | RF-01 | Mensaje vacío o solo espacios | — | El botón queda deshabilitado; el servidor responde 422 | Alta | Borde | Auto |
| CA-07 | RF-01 | Mensaje de 1.001 caracteres | — | 422 sin invocar al LLM | Alta | Borde | Auto |
| CA-08 | RF-06 | 31.ª solicitud en un minuto desde una IP | Cuota activa | 429 con mensaje "Demasiadas solicitudes" | Crítica | Seguridad | Auto |
| CA-09 | RF-06 | Recuperación tras la ventana de cuota | Esperar 60 s | La solicitud vuelve a responder 200 | Media | Seguridad | Manual |
| CA-10 | RF-06 | Captcha habilitado sin token | `TURNSTILE_ENABLED=true` | 400 "Captcha inválido" | Alta | Seguridad | Auto |
| CA-11 | RF-06 | Token de captcha inválido | `TURNSTILE_ENABLED=true` | 400 "Captcha inválido" | Alta | Seguridad | Auto |
| CA-12 | RF-06 | Captcha invisible no intrusivo | Turnstile integrado en SPA | El ciudadano consulta sin interacción adicional | Alta | Seguridad/UX | Pendiente (DT-01) |
| CA-13 | RNF-03 | Proveedor LLM caído | Router detenido | 200 con mensaje de contingencia y OIRS; sin 5xx | Crítica | Fiabilidad | Auto |
| CA-14 | RF-04 | Health check | Proceso vivo | 200 `{"status":"ok"}` | Alta | Operación | Auto |
| CA-15 | RF-05 | Reindexación desde Excel | Excel vigente | Índice con 191 documentos; `isActivo=0` excluido | Crítica | Datos | Auto + Manual |
| CA-16 | RNF-01 | Flujo real end-to-end | Chroma + LLM reales | Respuesta coherente con la fuente citada | Crítica | Sistema | Manual |
| CA-17 | RNF-02 | CORS restringido | Origen no autorizado | El navegador bloquea la petición | Alta | Seguridad | Manual |
| CA-18 | RNF-06 | Usabilidad con 5 ciudadanos | Guion de tareas | ≥ 4/5 completan la consulta sin ayuda | Alta | Usabilidad | Pendiente |
| CA-19 | RNF-06 | Accesibilidad WCAG 2.2 AA | Lighthouse + revisión | Sin errores críticos de contraste/teclado/etiquetas | Media | Accesibilidad | Pendiente |
| CA-20 | RNF-02 | Entrada maliciosa (XSS / *prompt injection*) | — | El texto se muestra escapado; el modelo no cambia de rol ni revela el *prompt* | Crítica | Seguridad | Manual |
| CA-21 | RNF-01 | Carga de 10 req/s durante 1 minuto | Staging | Sin 5xx; p95 ≤ 5 s; cuota responde 429 al exceder | Media | Carga | Pendiente |
| CA-22 | RNF-06 | Interfaz en móvil (360 px) | — | Sin desbordes; campo y botón operables | Media | Compatibilidad | Pendiente |

### 6.1 Casos en formato Gherkin (los tres críticos)

**CA-01 — Consulta válida**

```gherkin
Característica: Consulta ciudadana resuelta
  Como ciudadano de Peñalolén
  Quiero preguntar por un trámite en lenguaje natural
  Para obtener una respuesta oficial sin ir a la municipalidad

  Escenario: Consulta con coincidencia en la base de conocimiento
    Dado que el servicio está operativo y el índice contiene 191 preguntas
    Cuando envío "¿Dónde pago el permiso de circulación?"
    Entonces recibo una respuesta en español en menos de 5 segundos
    Y la respuesta menciona la dependencia responsable
    Y veo al menos una fuente con pregunta y dirección
```

**CA-08 — Límite de tasa**

```gherkin
  Escenario: Bloqueo de la solicitud número 31
    Dado que ya envié 30 consultas en el último minuto desde mi IP
    Cuando envío una consulta adicional
    Entonces el servidor responde 429
    Y el mensaje indica "Demasiadas solicitudes. Intenta en un momento."
    Y no se invoca al proveedor de IA
```

**CA-13 — Contingencia por caída del LLM**

```gherkin
  Escenario: El proveedor de IA no responde
    Dado que el router FreeLLMAPI está detenido
    Cuando envío una consulta válida
    Entonces recibo una respuesta 200
    Y el texto me sugiere contactar a la OIRS (+562 2486 8000)
    Y no se muestra ningún error técnico
```

---

## 7. Matriz de trazabilidad requerimiento ↔ caso

| RF | Casos | Cobertura |
|----|-------|-----------|
| RF-01 | CA-01, CA-06, CA-07, CA-22 | Completa |
| RF-02 | CA-01, CA-02, CA-03, CA-04, CA-16 | Completa |
| RF-03 | CA-05, CA-05b | Parcial (umbral pendiente) |
| RF-04 | CA-14 | Completa |
| RF-05 | CA-15 | Completa |
| RF-06 | CA-08, CA-09, CA-10, CA-11, CA-12, CA-17, CA-20 | Parcial (frontend Turnstile pendiente) |
| RNF-01 | CA-16, CA-21 | Pendiente medición |
| RNF-03 | CA-13 | Completa |
| RNF-06 | CA-18, CA-19, CA-22 | Pendiente |

---

## 8. Gestión de defectos

| Severidad | Definición | Ejemplo | Plazo de corrección |
|-----------|-----------|---------|---------------------|
| S1 — Crítica | El servicio no responde o entrega información errónea con riesgo institucional | 500 en `/api/chat`; respuesta con teléfono inventado | Inmediato (bloquea release) |
| S2 — Alta | Funcionalidad principal degradada sin alternativa | Fuentes no se muestran; captcha bloquea a usuarios legítimos | Antes del release |
| S3 — Media | Defecto con solución alternativa | Error de estilo en móvil; mensaje de validación poco claro | Próximo sprint |
| S4 — Baja | Detalle cosmético o de redacción | Acento faltante; espaciado | Backlog |

**Flujo:** detección → registro (ID, caso, evidencia, entorno) → triage de severidad →
corrección → **prueba de regresión** → cierre con evidencia adjunta.

---

## 9. Métricas del plan

| Métrica | Fórmula | Meta |
|---------|---------|------|
| Tasa de aprobación | casos aprobados / ejecutados | ≥ 95 % |
| Densidad de defectos | defectos / caso ejecutado | ≤ 0,2 |
| Efectividad de pruebas | defectos hallados en pruebas / total | ≥ 80 % |
| Cobertura de requerimientos | RF con ≥ 1 caso aprobado / RF total | 100 % |
| Cobertura de código | líneas cubiertas / líneas totales | ≥ 80 % |

---

## 10. Estado actual del plan (cierre Sprint 2)

| Nivel | Casos | Ejecutados | Aprobados | Observación |
|-------|-------|-----------|-----------|-------------|
| Unitaria | 28 | 28 | 28 | 100 % en verde, 88 % de cobertura |
| Integración (contrato HTTP) | 7 | 7 | 7 | Incluye cuota y captcha |
| Aceptación | 23 | 8 | 8 | Resto planificado para Sprint 3 (CA-01 y CA-12 parcialmente cubiertos) |
| No funcional | 4 | 0 | 0 | Carga, accesibilidad y usabilidad pendientes |

**Bloqueos para cerrar la aceptación:** integración de Turnstile en el SPA (DT-01),
umbral de similitud (DT-02), despliegue en staging con dominio y HTTPS.

**Riesgos del plan**

| Riesgo | Mitigación |
|--------|-----------|
| Respuestas no deterministas del LLM | Evaluación con conjunto dorado y criterio de pertinencia, no de texto exacto |
| Proveedor gratuito inestable durante la aceptación | Ejecutar CA-16 con *reintentos* y registrar la tasa de contingencia |
| Falta de disponibilidad del stakeholder | Sesión de aceptación agendada con checklist firmable en una hora |

---

## 11. Entregables de la ejecución

| Entregable | Formato | Ubicación |
|------------|---------|-----------|
| Suite de pruebas unitarias e integración | Código Python | `backend/tests/` |
| Reporte de ejecución y cobertura | Markdown + salida de consola | [06-evidencia-pruebas-unitarias.md](06-evidencia-pruebas-unitarias.md) |
| Checklist de aceptación firmado | PDF | Repositorio (`docs/entrega-2/evidencias/`) |
| Registro de defectos | Tabla en el tablero del sprint | GitHub Projects |
| Acta de conformidad del stakeholder | PDF firmado | Repositorio |

## 12. Aprobación

| Rol | Nombre | Fecha | Firma |
|-----|--------|-------|-------|
| Líder técnico | | | |
| Encargado de contenido municipal | | | |
| Stakeholder (Informática / OIRS) | | | |
