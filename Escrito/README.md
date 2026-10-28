# Escrito — tesina del TT

| Ruta | Qué es |
|:--|:--|
| [`tesina/`](tesina/) | **El escrito real**, sobre la plantilla oficial de UPIITA (UpiiTeXis 2023). Lo que está aquí es lo que se entrega. |
| [`pruebas/`](pruebas/) | Pruebas de LaTeX y del revisor (p. ej. `prueba_revisor.tex`, con errores sembrados a propósito). **No es contenido de la tesina**: no se cita, no se revisa como tal y su texto no refleja el estado del proyecto. |
| [`revision.sty`](revision.sty) | Marcas de revisión `\sobra`, `\falta`, `\sugerencia` y `\duda`, compartidas por ambas carpetas. |
| [`CODIGOS_REVISION.md`](CODIGOS_REVISION.md) | Referencia de las marcas: qué significa cada una y qué hacer con ella. |
| [`PLANTILLA.md`](PLANTILLA.md) | Mapa de la plantilla: qué hace cada archivo y sección, y el registro de sus problemas con su estado. |

## La tesina (`tesina/`)

- **Archivo principal:** `Principal.tex`. Datos de portada y acta, orden de capítulos y `\usepackage{../revision}`.
- **Contenido:**
  - `preliminares/`: resumen, abstract, introducción, nomenclatura, dedicatoria y agradecimientos;
  - `capitulos/`: los capítulos;
  - `apendices/`: apéndices y anexos;
  - `XBiblioteca.bib`: la bibliografía.
- **Formato:** `upiita.cls` y `configuracion/upiitatesis.sty`.
- **Compilar:** con LaTeX Workshop (latexmk). [`tesina/latexmkrc`](tesina/latexmkrc) agrega la regla que genera la nomenclatura; sin ella esa página sale vacía.

**Qué se puede modificar** (decisión del autor, 2026-10-27):
- **Contenido sí:** todo el texto normal.
- **Forma no:** los estilos, los títulos y divisiones preestablecidos de la plantilla, y los datos de la universidad.
- **Ante la duda, no se borra:** se marca con `\duda{...}` (o con `% [DUDA]` en `.sty`, `.cls` y `.bib`) y se pregunta.

El original de la plantilla está en `TT_UPIITA_2023.zip`, en esta carpeta.

Los auxiliares de compilación y el PDF de cada documento no se versionan (ver `.gitignore`); se regeneran desde los `.tex`. Los PDF de `logos/` e `imagenes/` sí se versionan, porque son parte del documento.
