# 07 — Matriz de riesgos de seguridad

**Activo evaluado:** Asistente Virtual Municipal — API `POST /api/chat`, base de
conocimiento, credenciales del router LLM e interfaz web.
**Metodología:** análisis de riesgos cualitativo (ISO/IEC 27005) con catálogo de
amenazas **OWASP Top 10 (2021)**, **OWASP Top 10 for LLM Applications (2025)** y
**OWASP ASVS 4.0** como referencia de controles.
**Fecha de evaluación:** 2026-11-12 · **Próxima revisión:** cierre Sprint 3.

---

## 1. Metodología

**Nivel de riesgo = Probabilidad × Impacto**, ambos en escala 1-5.

| Probabilidad | Criterio |
|:---:|----------|
| 5 | Ocurre con certeza o es trivial de ejecutar (herramienta pública, sin autenticación) |
| 4 | Altamente probable en un servicio público expuesto a Internet |
| 3 | Posible con conocimiento técnico medio |
| 2 | Poco probable; requiere condiciones específicas |
| 1 | Excepcional; requiere acceso físico o insider con privilegios |

| Impacto | Criterio |
|:---:|----------|
| 5 | Daño institucional grave, exposición de datos sensibles o indisponibilidad total |
| 4 | Información errónea con consecuencia para el ciudadano o costo económico relevante |
| 3 | Degradación del servicio o exposición limitada |
| 2 | Molestia menor, sin pérdida de información |
| 1 | Impacto despreciable |

| Nivel | Rango | Tratamiento exigido |
|-------|:-----:|---------------------|
| **Crítico** | 16-25 | Mitigación obligatoria antes de producción; aceptación solo por el stakeholder |
| **Alto** | 10-15 | Mitigación planificada con plazo; seguimiento en el sprint |
| **Medio** | 5-9 | Mitigación cuando sea costo-efectiva; monitoreo |
| **Bajo** | 1-4 | Aceptar y revisar |

**Apetito de riesgo:** el servicio es un canal oficial de información municipal; se
acepta riesgo **bajo** en exactitud de la información y **medio-bajo** en disponibilidad.
No se acepta ningún riesgo crítico sin control compensatorio documentado.

---

## 2. Activos y superficies de exposición

| ID | Activo | Descripción | Criticidad |
|----|--------|-------------|:---:|
| A-01 | Base de conocimiento | 191 preguntas frecuentes con dependencias y contactos | Alta |
| A-02 | Credenciales LLM | `FREELLMAPI_API_KEY` (clave unificada) y claves de proveedores upstream | Crítica |
| A-03 | Capacidad de cómputo / cuota | Tokens y cuota del proveedor gratuito | Alta |
| A-04 | Servicio de consulta | Endpoint público sin autenticación | Alta |
| A-05 | Reputación institucional | Exactitud y tono de las respuestas | Crítica |
| A-06 | Consultas ciudadanas | Texto potencialmente sensible en tránsito (no persistido) | Alta |
| A-07 | Servidor y volumen de datos | VPS, índice Chroma, `.env` | Alta |

**Superficies de ataque:** navegador → Cloudflare → Nginx → FastAPI; FastAPI →
FreeLLMAPI (`localhost:3001`); FastAPI → Chroma (disco); FastAPI → Cloudflare
`siteverify`; repositorio Git y pipeline de despliegue.

---

## 3. Matriz de riesgos

| ID | Activo | Amenaza / vector | Causa raíz | P | I | Nivel | Control implementado o previsto | Estado | Residual |
|----|--------|------------------|--------|:-:|:-:|:-----:|--------------------------------|--------|:--------:|
| R-01 | A-05, A-04 | ***Prompt injection*** directa: el ciudadano pide ignorar instrucciones, cambiar de rol o revelar el *prompt* | El texto del usuario se concatena al contexto del LLM | 4 | 4 | **16 Crítico** | Separación `system`/`user`; instrucción explícita de no revelar ni cambiar de rol; sin herramientas ni agencia (el modelo no ejecuta acciones); salida renderizada como texto | Implementado | 8 Medio |
| R-02 | A-02 | Extracción del *system prompt* o de la configuración interna | Filtración por respuesta del modelo | 3 | 2 | 6 Medio | El *prompt* no contiene secretos; las claves viven en `.env` y nunca se incluyen en el contexto | Implementado | 3 Bajo |
| R-03 | A-03, A-04 | **Denegación de servicio económica**: automatización que agota la cuota del proveedor | Endpoint público sin autenticación y con costo por token | 4 | 4 | **16 Crítico** | Cuota `30/min` por IP (slowapi) + Turnstile server-side + límite de 1.000 caracteres + `top_k=5` | Parcial (Turnstile sin integrar en SPA) | 9 Medio |
| R-04 | A-02 | Fuga de credenciales del router LLM | Commit accidental, log, exposición del backend | 3 | 5 | **15 Alto** | `.env` en `.gitignore`; `.env.example` sin valores; claves solo en backend; el SPA nunca las recibe | Implementado | 5 Medio |
| R-05 | A-05 | **Alucinación**: respuesta plausible pero falsa con apariencia oficial | Recuperación sin umbral de similitud; modelo generativo | 4 | 5 | **20 Crítico** | RAG restringido al contexto; *system prompt* prohíbe inventar datos; se muestran fuentes; mensaje de derivación a OIRS | Parcial | 12 Alto |
| R-06 | A-04 | Elusión de la cuota por IP mediante proxies o cabecera `X-Forwarded-For` falsificada | Identificación del cliente por IP | 3 | 3 | 9 Medio | Cuota por IP; se prevé `ProxyHeadersMiddleware` con proxies de confianza | Pendiente | 9 Medio |
| R-07 | A-04 | Indisponibilidad por caída del proveedor LLM (gratuito, sin SLA) | Dependencia de un servicio sin garantías | 4 | 3 | **12 Alto** | Cliente desacoplado; timeout; degradación a mensaje institucional (D-08); `/health` para monitoreo | Implementado (timeout pendiente) | 6 Medio |
| R-08 | A-01, A-05 | Indexación de contenido obsoleto o no publicado | Criterio *fail-open* de `isActivo`; Excel desactualizado | 3 | 4 | **12 Alto** | Reindexación idempotente; revisión del Excel por el encargado de contenido; metadatos de categoría | Parcial | 8 Medio |
| R-09 | A-04 | **XSS** por inyección de HTML/JS en la respuesta o en el mensaje del usuario | Render inseguro en el cliente | 2 | 3 | 6 Medio | React escapa por defecto; no se usa `dangerouslySetInnerHTML`; validación de longitud en servidor | Implementado | 3 Bajo |
| R-10 | A-06 | Exposición de datos personales en logs o trazas | Registro del contenido de la consulta | 2 | 5 | **10 Alto** | No se registra el mensaje; solo la excepción del LLM; sin persistencia de conversaciones (D-06) | Implementado | 4 Bajo |
| R-11 | A-07 | **Cadena de suministro**: dependencia comprometida (npm, PyPI, modelo de Hugging Face) | Instalación de paquetes de terceros | 3 | 4 | **12 Alto** | Versiones fijadas en `requirements.txt`/`package-lock.json`; revisión de dependencias; despliegue desde artefacto construido | Parcial (sin `pip-audit`/`npm audit` en CI) | 8 Medio |
| R-12 | A-06 | Interceptación del tráfico (MITM) o ausencia de TLS en staging | HTTP sin cifrado | 3 | 4 | **12 Alto** | HTTPS terminado en Cloudflare/Nginx (previsto); HSTS pendiente | Pendiente (staging) | 6 Medio |
| R-13 | A-04 | CORS permisivo (`allow_origins=*`) en producción | Configuración por entorno mal ajustada | 3 | 3 | 9 Medio | `CORS_ORIGINS` por entorno; valor por defecto `localhost:5173`; `allow_credentials=True` | Implementado (validar en prod) | 4 Bajo |
| R-14 | A-04 | Turnstile desactivado silenciosamente por secreto vacío | *Fail-open* de configuración | 3 | 3 | 9 Medio | `TURNSTILE_ENABLED` explícito; se prevé verificación de arranque que falle en producción | Pendiente | 6 Medio |
| R-15 | A-07 | Modelo de embeddings alterado en origen | Descarga desde repositorio público sin verificación de hash | 2 | 3 | 6 Medio | Descarga única durante el despliegue; se prevé fijar revisión y hash del modelo | Pendiente | 4 Bajo |
| R-16 | A-07 | Acceso no autorizado al VPS o al volumen de Chroma | Credenciales débiles, puertos expuestos | 2 | 4 | 8 Medio | FreeLLMAPI en `localhost`; SSH con clave; firewall (previsto); sin puerto de Chroma expuesto | Parcial | 4 Bajo |
| R-17 | A-01 | *Scraping* sistemático del contenido institucional | Consultas automatizadas sucesivas | 3 | 3 | 9 Medio | Cuota por IP; captcha; contenido ya es público en el portal municipal | Implementado | 6 Medio |
| R-18 | A-01 | *Data poisoning*: inserción de contenido malicioso en el Excel fuente | Origen de datos no controlado | 2 | 4 | 8 Medio | El Excel proviene de un sistema municipal interno; revisión antes de ingestar; sin carga desde Internet | Implementado (proceso) | 4 Bajo |
| R-19 | A-04 | Manipulación del `session_id` para acceder a conversaciones ajenas | El campo existe en el contrato pero no se usa | 1 | 2 | 2 Bajo | El backend es *stateless*: no hay conversaciones almacenadas que proteger | Implementado | 1 Bajo |
| R-20 | A-06 | *Overreliance*: el ciudadano asume que la respuesta es una resolución oficial vinculante | Presentación de la respuesta como asesoría definitiva | 4 | 3 | **12 Alto** | Texto de bienvenida que declara el rol; derivación a OIRS; se prevé *disclaimer* visible y enlace al portal oficial | Parcial | 8 Medio |

---

## 4. Mapa de calor

| Probabilidad ↓ / Impacto → | 1 | 2 | 3 | 4 | 5 |
|:---:|:---:|:---:|:---:|:---:|:---:|
| **5** | | | | | |
| **4** | | | R-07 | R-01, R-03 | R-05, R-20 |
| **3** | | R-02 | R-06, R-13, R-14, R-17 | R-08, R-11, R-12 | R-04 |
| **2** | | | R-09, R-15 | R-16, R-18 | R-10 |
| **1** | | R-19 | | | |

**Distribución:** 2 críticos · 7 altos · 9 medios · 2 bajos.
Los dos riesgos críticos (R-01 y R-05) son **inherentes a la tecnología LLM** y no se
eliminan con controles perimetrales: se gestionan con diseño de producto (fuentes
visibles, derivación, ausencia de agencia) y requieren **validación humana del contenido**.

---

## 5. Correspondencia con OWASP

### 5.1 OWASP Top 10 for LLM Applications

| Categoría | Riesgo asociado | Control en el sistema |
|-----------|-----------------|----------------------|
| LLM01 *Prompt Injection* | R-01 | Separación de roles; *system prompt* con prohibición explícita; sin herramientas |
| LLM02 *Sensitive Information Disclosure* | R-02, R-10 | Sin secretos en el *prompt*; sin logging de consultas; sin persistencia |
| LLM03 *Supply Chain* | R-11, R-15 | Versiones fijadas; revisión de dependencias; despliegue desde artefacto |
| LLM04 *Data and Model Poisoning* | R-18 | Fuente de datos controlada internamente; revisión previa a la ingesta |
| LLM05 *Improper Output Handling* | R-09 | Salida tratada como texto; React escapa; sin `innerHTML` |
| LLM06 *Excessive Agency* | R-01 | El modelo no ejecuta acciones ni accede a sistemas; solo redacta |
| LLM07 *System Prompt Leakage* | R-02 | El *prompt* no contiene información sensible |
| LLM08 *Vector and Embedding Weaknesses* | R-08 | Colección única, reindexación controlada, sin *multi-tenant* |
| LLM09 *Misinformation* | R-05, R-20 | RAG con fuentes, derivación a OIRS, *disclaimer* (pendiente) |
| LLM10 *Unbounded Consumption* | R-03 | Cuota por IP, captcha, límite de entrada, `top_k` acotado |

### 5.2 OWASP Top 10 Web / ASVS

| Categoría | Aplicación |
|-----------|-----------|
| A01 Control de acceso | No hay recursos autenticados; `/api/chat` es público por diseño |
| A02 Fallas criptográficas | TLS en el borde (previsto); secretos fuera del repositorio |
| A03 Inyección | Sin SQL ni shell; validación Pydantic; salida escapada |
| A04 Diseño inseguro | Cuota + captcha + degradación; modelo sin agencia |
| A05 Configuración insegura | Configuración por entorno; CORS restringido; `DEBUG` no expuesto |
| A06 Componentes vulnerables | Versiones fijadas; auditoría pendiente en CI |
| A07 Fallas de identificación | No aplica (servicio anónimo); Turnstile como señal anti-bot |
| A08 Integridad de software/datos | Ingesta idempotente; fuente controlada |
| A09 Fallas de logging | Se registra el fallo sin datos personales; falta alerta (R-07) |
| A10 SSRF | El backend solo llama a URLs configuradas (`FREELLMAPI_BASE_URL`, `siteverify`); no acepta URLs del usuario |

---

## 6. Controles verificados por prueba

| Control | Evidencia automatizada | Riesgo cubierto |
|---------|------------------------|-----------------|
| Validación de longitud 1-1000 | `test_mensaje_vacio_rechazado`, `test_mensaje_demasiado_largo_rechazado` | R-03, R-09 |
| Cuota por IP (429 desde la 31.ª) | `test_rate_limit_bloquea_peticion_31` | R-03, R-17 |
| Captcha obligatorio con *flag* activo | `test_turnstile_habilitado_sin_token_devuelve_400` | R-03 |
| Rechazo de token inválido | `test_turnstile_token_invalido_devuelve_400` | R-03 |
| Sin secreto embebido en código | `test_api_key_por_defecto_vacia`, `test_api_key_se_lee_desde_entorno` | R-04 |
| Prohibición de inventar datos | `test_respuesta_incluye_fuentes_y_usa_top_k` (verifica el *system prompt*) | R-05 |
| Degradación sin 5xx | `test_fallback_amigable_si_el_llm_falla` | R-07 |
| Filtro de contenido activo | `test_is_active` (9 casos) | R-08, R-18 |

---

## 7. Plan de tratamiento

| Riesgo | Acción | Responsable | Plazo | Criterio de cierre |
|--------|--------|-------------|-------|--------------------|
| R-03 | Integrar Turnstile invisible en el SPA y activar `TURNSTILE_ENABLED=true` | Frontend | Sprint 3 | CA-12 aprobado en staging |
| R-05 | Umbral de similitud + *disclaimer* visible + enlace a OIRS | Backend / UX | Sprint 3 | CA-05b y CA-04 aprobados |
| R-05 | Validación del conjunto dorado por el encargado de contenido | Negocio | Sprint 3 | ≥ 80 % de respuestas correctas |
| R-20 | *Disclaimer* "información referencial, no constituye resolución" | UX | Sprint 3 | Revisión del stakeholder |
| R-06 | Configurar proxies de confianza y `X-Forwarded-For` en Nginx | Operación | Sprint 3 | Prueba de elusión fallida |
| R-07 | Timeout explícito (p. ej. 25 s) y alerta por tasa de contingencia | Backend | Sprint 3 | Alerta configurada |
| R-11 | `pip-audit` + `npm audit` en el pipeline | DevOps | Sprint 3 | Pipeline bloquea vulnerabilidades altas |
| R-12 | HTTPS + HSTS en el dominio municipal | Operación | Sprint 3 | Nota A en SSL Labs |
| R-14 | *Health check* de configuración: fallar el arranque en producción si Turnstile está deshabilitado | Backend | Sprint 3 | Prueba de arranque fallido |
| R-15 | Fijar revisión y hash del modelo de embeddings | Backend | Sprint 4 | Verificación en el despliegue |
| R-16 | Firewall, SSH con clave y principio de mínimo privilegio | Operación | Sprint 3 | Auditoría de puertos |
| R-08, R-18 | Procedimiento documentado de revisión y publicación del Excel | Negocio | Sprint 4 | Procedimiento firmado |

---

## 8. Riesgos residuales aceptados

| Riesgo | Nivel residual | Justificación de aceptación | Aprobado por |
|--------|:--------------:|-----------------------------|--------------|
| R-01 *Prompt injection* | 8 Medio | El modelo no tiene agencia ni acceso a datos; el peor caso es una respuesta fuera de tono, mitigada por el *prompt* y la derivación | Líder técnico |
| R-05 Alucinación | 12 Alto | Se acepta **solo** con fuentes visibles, derivación a OIRS y validación humana del contenido antes de producción | Stakeholder (pendiente de firma) |
| R-17 *Scraping* | 6 Medio | El contenido ya es público en el portal municipal; el costo de extraerlo no supera el de consultarlo | Líder técnico |
| R-19 `session_id` | 1 Bajo | El servicio no almacena estado | Líder técnico |

**Nota de cumplimiento:** el sistema no almacena datos personales, por lo que no genera
un banco de datos que requiera registro ante la Agencia de Protección de Datos en los
términos de la Ley 19.628 y la Ley 21.719. Esta condición debe reevaluarse si se
incorpora historial de conversaciones o autenticación.
