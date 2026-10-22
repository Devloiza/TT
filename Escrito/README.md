# Escrito — tesina del TT

| Ruta | Qué es |
|:--|:--|
| [`tesina/`](tesina/) | **El escrito real.** Lo que está aquí es lo que se entrega. |
| [`pruebas/`](pruebas/) | Pruebas de LaTeX y del revisor (p. ej. `prueba_revisor.tex`, con errores sembrados a propósito). **No es contenido de la tesina**: no se cita, no se revisa como tal y su texto no refleja el estado del proyecto. |
| [`revision.sty`](revision.sty) | Marcas de revisión `\sobra`, `\falta` y `\sugerencia`, compartidas por ambas carpetas. |
| [`CODIGOS_REVISION.md`](CODIGOS_REVISION.md) | Referencia de las marcas: qué significa cada una y qué hacer con ella. |

Desde `tesina/` o `pruebas/`, el paquete se carga con:

```latex
\usepackage{../revision}
```

Los auxiliares de compilación y los PDF no se versionan (ver `.gitignore`); se regeneran desde los `.tex`.
