# Códigos de revisión de redacción

Marcas que deja el agente `redactor` al revisar la tesina, para que decidas antes de aceptar o borrar nada. Las define [`revision.sty`](revision.sty).

## Uso en LaTeX

`tesina/Principal.tex` ya lo carga. En el preámbulo de cualquier otro documento en `tesina/` o `pruebas/`:

```latex
\usepackage{../revision}          % borrador: marcas visibles
% \usepackage[final]{../revision} % entrega: oculta las marcas y avisa en el log si queda alguna
```

| Código | Significa | Se ve como | Qué haces tú |
|---|---|---|---|
| `\sobra{texto}` | El texto no aporta: redundancia, muletilla, repetición o algo ya dicho | Texto **azul** con resaltado amarillo | Borrar la marca y el texto, o conservar el texto quitando solo `\sobra{...}` |
| `\falta{qué falta}` | Falta contenido: una cifra, una cita, una definición, un paso del argumento | **[FALTA: qué falta]** en **rojo** con resaltado amarillo | Escribir lo que falta en lugar de la marca |
| `\duda{texto}` | Texto existente (p. ej. de la plantilla) que quizá sobra o no aplica, pero sobre el que hay duda. **No se borra**: se conserva marcado hasta que decidas | Texto **rojo** con resaltado **rosa** | Decidir: conservarlo quitando la marca, o borrarlo |
| `\sugerencia{qué y por qué}` | Corrección de fondo propuesta: una cifra, afirmación o criterio que contradice el protocolo o el repo, con su razón. Sin límite de extensión, pero no es para reescribir párrafos | **[SUGERENCIA: …]** en **verde** con resaltado verde claro | Decidir: aplicar la corrección con tus palabras o descartarla, y borrar la marca |

`\falta` lleva una nota breve (unas doce palabras como máximo). `\sugerencia` puede extenderse lo que haga falta para explicar la razón.

Ejemplo:

```latex
\sobra{Cabe mencionar que} el arreglo emplea ocho micrófonos ICS-43434
y mejora la SNR en \falta{cifra medida y condición de SNR de entrada}.
Se espera una mejora de \sobra{5~dB respecto a la señal sin procesar}%
\sugerencia{3~dB respecto a un arreglo lineal uniforme con DAS convencional:
así lo fija el criterio C3 del protocolo}.
```

Para proponer el reemplazo de un fragmento erróneo, el revisor marca el original con `\sobra` y pone justo después `\sugerencia` con la corrección.

`\sobra` frente a `\duda`: `\sobra` significa "esto se puede quitar" (redundancia clara). `\duda` significa "quizá sobra, decide tú" y se usa sobre todo con texto heredado de la plantilla.

**En archivos sin salida visual** (`.sty`, `.cls`, `.bib`) no se pueden usar estas marcas. Ahí lo dudoso se señala con un comentario `% [DUDA] motivo` en la línea anterior y no se borra.

## Lo que no se marca

- **Ortografía y puntuación** (acentos, comas, mayúsculas, erratas): el revisor las corrige directamente y las lista en su reporte. Las ves con `git diff`.
- **Terminología**: si un término tiene variantes en el texto (p. ej. "beamforming" / "conformación de haz"), el revisor unifica hacia el término que ya usan `CONTEXTO.md` y el repo y lo reporta. Si no hay término establecido, pregunta en el reporte en vez de elegir.
- **Afirmaciones no respaldadas** por el código o los datos del repo: se marcan con `\falta{respaldo: ...}`.
- **Errores de fondo** (cifras, criterios o afirmaciones que contradicen el protocolo o el repo): el revisor no los corrige; los propone con `\sugerencia`.

## Antes de entregar

1. Cambia a `\usepackage[final]{../revision}` y compila.
2. Busca en el log `Package revision Warning`. Cada advertencia es una marca sin resolver.

## En Markdown (`Documentation.md`, README)

Markdown no admite colores, así que solo se usa el resaltado:

- Sobra: `<mark>[SOBRA] texto</mark>`
- Falta: `<mark>[FALTA: qué falta]</mark>`
- Sugerencia: `<mark>[SUGERENCIA: qué y por qué]</mark>`
- Duda: `<mark>[DUDA] texto</mark>`
