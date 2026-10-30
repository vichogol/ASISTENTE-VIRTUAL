# Base de conocimiento (preguntas frecuentes)

## Dónde subir el Excel
Coloca el archivo en:

```
data/raw/preguntas_frecuentes_penalolen.xlsx
```

## Formato esperado (columnas)
| Columna | Tipo | Notas |
|---|---|---|
| preguntaFrecuenteID | int/str | Identificador único |
| categoriaPreguntaFrecuente | str | Categoría del trámite |
| nombrePreguntaFrecuente | str | Título corto de la pregunta |
| descripcionPreguntaFrecuente | str | Respuesta detallada |
| tagPreguntaFrecuente | str | Tags separados por coma |
| Direccion | str | Dependencia/ubicación a la que acudir |
| Rango Etáreo | str | Rango de edad aplicable (ej. "18-65", "Todos") |
| Sexo | str | "M", "F", "Todos" |

## Reglas
- Un archivo por versión; no editar en producción, se re-ingesta.
- Sin datos personales.
- Encoding UTF-8 al exportar a CSV si aplica.
- No renombrar columnas sin avisar (rompe el pipeline de ingesta).
