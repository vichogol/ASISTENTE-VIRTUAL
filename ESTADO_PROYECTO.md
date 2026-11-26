
# Estado de Peñalolín, asistente municipal de Peñalolén

Actualizado el 26 de noviembre de 2026.

## Entrega web

- Interfaz adaptable con el lema municipal, avatar original inspirado en montaña y sol, y animación que sigue la preferencia de movimiento reducido. El chat incluye accesos rápidos, fuentes, acciones, derivación y valoración.
- Fondo y encabezado institucional `#252D6B` con texto blanco y acentos `#FF8500` y `#0450C0`. Las tarjetas y las fichas del mapa comparten la misma fotografía y su crédito.
- Catálogo de 15 recintos con dirección consultable. Doce fichas tienen una ubicación 3D vinculada a OpenStreetMap, incluyendo recintos que comparten emplazamiento. CAF, Bodega y Mediación tienen enlace para llegar con su dirección publicada y quedan pendientes de coordenadas confirmadas.
- Three.js se carga al abrir el visor. La escena incorpora elevación real, red vial, parques y árboles representativos. El foco de cámara se anima al elegir un recinto, y pasa directamente a la nueva vista con movimiento reducido. La lista, las fotos y los enlaces permanecen disponibles si WebGL no funciona.
- Chimkowe, Consistorial y Yunus tienen modelos diferenciados a partir de huellas cartográficas y referencias visuales. Fachadas, cubiertas, materiales y jardinería tienen un nivel de detalle orientativo.
- Peñalolín se presenta antes de la recuperación RAG cuando recibe un saludo o una pregunta como «¿Quién eres?». Las consultas abreviadas combinan intención y palabras clave. La búsqueda difusa corrige cambios de una letra y transposiciones si el vocabulario de las fichas ofrece una interpretación clara.
- Recuperación con el Excel oficial y opción de añadir Chroma. La base se consulta en modo lectura. El servicio ofrece derivación en caso de incertidumbre, ausencia de evidencia o consultas sobre expedientes particulares.
- Historial auditable en SQLite, con feedback por sesión, umbrales y control de vigencia por versión de ficha. El sistema ajusta la recuperación de fichas municipales existentes.
- La lógica en `backend/app/services/` queda disponible para futuros canales. El alcance de esta entrega es la aplicación web y su API.

## Archivos por componente

| Componente | Archivos |
| --- | --- |
| Lectura de Excel, normalización y evidencias | `backend/app/services/knowledge.py` |
| Búsqueda y composición de respuesta | `retrieval.py`, `rag.py` y `vector_store.py` dentro de `backend/app/services/` |
| Directorio y derivación | `backend/app/services/place_catalog.py` y `backend/app/services/municipal.py` |
| Feedback, promoción y revocación | `backend/app/services/learning.py` |
| Interfaz, fotos y visor | `frontend/src/MapViewport.tsx`, `mapScene.ts`, `mapBuildings.ts`, `mapLandscape.ts` y `frontend/public/recintos/` |
| Pruebas | `backend/tests/` y `frontend/tests/` |

La puesta en producción requiere configurar el origen HTTPS y, si se activan, el captcha y el proveedor de IA. Mantén los contactos y recintos alineados con los enlaces oficiales guardados en el catálogo. Los enlaces de una ficha provienen del Excel. La derivación usa el directorio oficial para indicar dónde confirmar información que cambia con el tiempo.

## Fotografías y cartografía

- Consistorial usa la fotografía del encargo. El render adjunto de Chimkowe sirvió de referencia para la cubierta y el basamento. La fotografía de Chimkowe es de Carlos Figueroa Rojas, en resolución reducida por Wikimedia Commons, con licencia CC BY-SA 4.0. [Archivo original](https://commons.wikimedia.org/wiki/File:Centro_Cultural_Chimkowe,_Pe%C3%B1alol%C3%A9n,_Santiago_20260916_03.jpg) · [Licencia](https://creativecommons.org/licenses/by-sa/4.0/).
- Las otras fotografías identifican el CAV, la Piscina, el interior de San Luis, el acceso compartido a KINTUN y Centro de Adulto Mayor, la fachada de Ictinos 1626 y las vistas aéreas rotuladas de Yunus y Registro Civil. Las fichas distinguen las fotografías interiores y de contexto. [CAV](https://gubbinsarquitectos.cl/galeria-cav) · [Piscina](https://deportespenalolen.cl/blog/2020/11/26/piscina-temperada-reabre-sus-puertas-la-primera-semana-de-diciembre/) · [San Luis](https://chimkowe.cl/wp-content/uploads/2021/10/Ficha-Tecnica-CCCSL.pdf#page=4) · [KINTUN](https://www.flickr.com/photos/penalolen/10192400613/in/album-72157636399494125/) · [Ictinos](https://www.penalolen.cl/wp-content/uploads/2024/05/Revista-Nosotras-Nov-2024.pdf#page=8) · [Catastro del Centro Cívico](https://participa.penalolen.cl/uploads/archivos/a-PSCC_CATASTRO_URBANO_CENTRO_CIVICO_PENALOLEN_Art%2072_230623.pdf).
- CAF, Bodega Municipal, Edificio Orientales y Juzgado muestran su ficha y dirección mientras falta confirmar una fotografía del recinto. [Sucursales municipales](https://tramites.penalolen.cl/Sucursales/listar) · [Edificios municipales](https://www.penalolen.cl/edificios-municipales/).
- Las calles, parques y huellas se extraen de OpenStreetMap con licencia ODbL 1.0. La malla se generó a partir de teselas Terrarium de Mapzen en zoom 12, índices X 1244–1245 e Y 2452–2453, con alturas de USGS/NASA SRTM. Los colores del suelo y la ubicación de los árboles se usan para representar el paisaje en el visor. [OpenStreetMap](https://www.openstreetmap.org/copyright) · [Mapzen y créditos del relieve](https://github.com/tilezen/joerd/blob/master/docs/attribution.md).
- Maravedies 1076 es la dirección que publica el portal de sucursales y la que usa el catálogo para Bodega Municipal. [Portal de sucursales](https://tramites.penalolen.cl/Sucursales/listar).

Consulta la [guía de instalación y pruebas](README.md).
