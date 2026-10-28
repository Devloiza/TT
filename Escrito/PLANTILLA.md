# Mapa de la plantilla UPIITA (`tesina/`)

Qué hace cada archivo y cada sección de la plantilla oficial (UpiiTeXis 2023), y el **registro de problemas** con su estado. Sirve para decidir con información qué se corrige, qué se conserva y qué se elimina.

**Regla** (decisión del autor, 2026-10-27):
- **Contenido sí:** todo el texto normal se modifica.
- **Forma no:** no se tocan los estilos, los títulos y divisiones preestablecidos ni los datos de la universidad.
- **Nada se borra sin preguntar.** Lo dudoso se marca con `\duda{...}` o con `% [DUDA]` (ver [`CODIGOS_REVISION.md`](CODIGOS_REVISION.md)).

> Los números de línea son del **2026-10-28** y se recorren cuando un archivo cambia. Si no coinciden, busca el nombre del comando.

---

## 1. Cómo se arma el documento

```
Principal.tex ──► upiita.cls                       (clase: tamaño de página, capítulos, secciones, índices, pies de página)
       │      ──► configuracion/upiitatesis.sty    (paquetes, portada, acta, nombres, nomenclatura, bibliografía)
       │      ──► ../revision.sty                  (marcas de revisión; agregado, no es de la plantilla)
       └──► preliminares/*.tex, capitulos/*.tex, apendices/*.tex   (contenido)

Compilación (LaTeX Workshop → latexmk):
  pdflatex ──► bibtex (XBiblioteca.bib) ──► makeindex (índice alfabético)
           ──► makeindex -s nomencl.ist (nomenclatura; regla en latexmkrc) ──► pdflatex
```

## 2. Orden del documento

Lo que aparece en el PDF, en orden, y de dónde sale.

| Parte del PDF | Comando (`Principal.tex`) | Lo define | Contenido en | ¿Se modifica? |
|:--|:--|:--|:--|:--|
| Portada | `\portada` ([117](tesina/Principal.tex#L117)) | `upiitatesis.sty` | Datos de [`Principal.tex:77-109`](tesina/Principal.tex#L77-L109) | Solo los datos (título, alumnos, asesores, fecha) |
| Acta de firmas | `\acta` ([118](tesina/Principal.tex#L118)) | `upiitatesis.sty` | Mismos datos + jurado | Solo los datos |
| Dedicatoria | `\dedicatoria` ([119](tesina/Principal.tex#L119)) | `upiitatesis.sty` | [`preliminares/dedicatoria.tex`](tesina/preliminares/dedicatoria.tex) | Texto sí |
| Agradecimientos | `\agradecimientos` ([120](tesina/Principal.tex#L120)) | `upiitatesis.sty` | [`preliminares/agradecimientos.tex`](tesina/preliminares/agradecimientos.tex) | Texto sí |
| Contenido (índice general) | `\tabladecontenido` ([121](tesina/Principal.tex#L121)) | `upiitatesis.sty` | Automático | No |
| Resumen / Abstract | `\include` ([122-123](tesina/Principal.tex#L122-L123)) | — | [`preliminares/resumen.tex`](tesina/preliminares/resumen.tex), [`abstract.tex`](tesina/preliminares/abstract.tex) | Texto sí; título no |
| Índice de figuras y de tablas | `\listadefiguras`, `\listadetablas` ([124-125](tesina/Principal.tex#L124-L125)) | `upiitatesis.sty` | Automático | No |
| Nomenclatura | `\include` ([127](tesina/Principal.tex#L127)) | `upiitatesis.sty` (`\nomenclatura`) | [`preliminares/nomenclatura.tex`](tesina/preliminares/nomenclatura.tex) | Entradas sí |
| Introducción (inicia numeración arábiga) | `\Introduccion` ([135](tesina/Principal.tex#L135)) | `upiitatesis.sty` (`\mainmatter` + `\include`) | [`preliminares/introduccion.tex`](tesina/preliminares/introduccion.tex) | Texto sí; secciones preestablecidas no |
| Cap. Marco de referencia | `\MarcodeReferencia` ([149](tesina/Principal.tex#L149)) | `upiitatesis.sty` (activa numeración de secciones) | [`capitulos/marcoreferencia.tex`](tesina/capitulos/marcoreferencia.tex) | Texto sí |
| Cap. Diseño del sistema | `\include` ([157](tesina/Principal.tex#L157), [161](tesina/Principal.tex#L161)) | — | [`capitulos/diseconceptual.tex`](tesina/capitulos/diseconceptual.tex) + [`disedetallado.tex`](tesina/capitulos/disedetallado.tex) (continuación, sin `\chapter`) | Texto sí |
| Cap. Implementación | `\include` ([164](tesina/Principal.tex#L164)) | — | [`capitulos/implementacion.tex`](tesina/capitulos/implementacion.tex) | Texto sí |
| Cap. Discusión / Análisis de resultados | `\include` ([168](tesina/Principal.tex#L168)) | — | [`capitulos/discusion.tex`](tesina/capitulos/discusion.tex) | Texto sí |
| Conclusiones (sin numerar secciones) | `\setcounter{secnumdepth}{-1}` + `\include` ([172-174](tesina/Principal.tex#L172-L174)) | — | [`capitulos/conclusiones.tex`](tesina/capitulos/conclusiones.tex) | Texto sí |
| Referencias | `\referencias` ([181](tesina/Principal.tex#L181)) | `upiitatesis.sty` (estilo IEEE) | [`XBiblioteca.bib`](tesina/XBiblioteca.bib) | Entradas sí |
| Apéndices (A, B, C…) | `\part` + `\appendix` + `\include` ([185-189](tesina/Principal.tex#L185-L189)) | `upiita.cls` | [`apendices/apendice*.tex`](tesina/apendices/) | Texto sí |
| Anexos | `\part` + `\anexo` + `\include` ([190-194](tesina/Principal.tex#L190-L194)) | `upiita.cls` | [`apendices/anexo*.tex`](tesina/apendices/) | Texto sí |
| Índice alfabético | `\IndiceAlfabetico` ([198](tesina/Principal.tex#L198)) | `upiitatesis.sty` | Entradas `\index{...}` en el texto | Entradas sí |

---

## 3. Archivo por archivo

### 3.1 `Principal.tex` — documento maestro

| Líneas | Qué hace | ¿Se modifica? |
|:--|:--|:--|
| [1-65](tesina/Principal.tex#L1-L65) | Comentarios (1-64): descripción de archivos, créditos y licencia (LPPL / CC-BY-SA); la 65 es el `\typeout` de los créditos | No: la licencia pide conservar la atribución |
| [66](tesina/Principal.tex#L66) | Carga la clase `upiita` (carta, 11 pt) | No |
| [67](tesina/Principal.tex#L67) | `\pagenumbering{arabic}` antes de cargar `hyperref`, para que el visor de PDF muestre los números impresos. **Agregada** ([P08](#4-registro-de-problemas)) | No |
| [68](tesina/Principal.tex#L68) | Carga `configuracion/upiitatesis.sty` | No |
| [69-70](tesina/Principal.tex#L69-L70) | Versión vectorial de la fuente del texto y de la monoespaciada (`lmr`, `lmtt`). **Agregadas** ([P29](#4-registro-de-problemas)) | No |
| [71-74](tesina/Principal.tex#L71-L74) | Declara la combinación de Montserrat que pide la portada (`sbx`) como la negrita que LaTeX ya usaba: mismo aspecto, sin avisos. **Agregadas** ([P15](#4-registro-de-problemas)) | No |
| [75](tesina/Principal.tex#L75) | Carga las marcas de revisión (`../revision.sty`). **Agregada**; para entregar se cambia a `[final]` | Solo la opción `[final]` |
| [77-84](tesina/Principal.tex#L77-L84) | Datos de portada: título, unidad, materia, academia, grado, mes, año | Sí, excepto `\unidad` (dato de la universidad) |
| [86-87](tesina/Principal.tex#L86-L87) | Presidente del jurado y profesor titular (para el acta) | Sí |
| [95-109](tesina/Principal.tex#L95-L109) | Número de alumnos (1-4) y asesores (1-3), con sus nombres. La portada y el acta se acomodan según el número | Sí |
| [111-199](tesina/Principal.tex#L111-L199) | Cuerpo: el orden de la §2 | Solo qué archivos se incluyen |
| [112](tesina/Principal.tex#L112) | Fuerza números romanos en minúscula para las páginas preliminares | No |

### 3.2 `upiita.cls` — clase (forma: no se modifica)

Derivada de la clase estándar `book` de LaTeX.

| Líneas | Qué hace |
|:--|:--|
| [55-147](tesina/upiita.cls#L55-L147) | Opciones de la clase (carta, 11 pt, doble cara, `openright`, español). La opción `latin1` en realidad activa `utf8` ([P17](#4-registro-de-problemas)) |
| [148-168](tesina/upiita.cls#L148-L168) | Carga `babel`, `inputenc` y `fancyhdr`; espaciado y reglas de colocación de figuras |
| [170-212](tesina/upiita.cls#L170-L212) | Estilos de encabezado de página (`headings`, `myheadings`) |
| [213-228](tesina/upiita.cls#L213-L228) | Contadores y numeración (capítulo, sección…) |
| [229-252](tesina/upiita.cls#L229-L252) | `\frontmatter`: numeración romana, encabezado decorado y **pies de página** (UPIITA / IPN / "Ing. Biónica", [P06](#4-registro-de-problemas)) |
| [253-268](tesina/upiita.cls#L253-L268) | `\inicial`, `\media`, `\mainmatter`, `\backmatter`: cuándo se numeran secciones y cuándo empieza la numeración arábiga |
| [269-322](tesina/upiita.cls#L269-L322) | `\part`: páginas de "Apéndices" y "Anexos" |
| [323-377](tesina/upiita.cls#L323-L377) | `\chapter`: aspecto de los títulos de capítulo |
| [378-398](tesina/upiita.cls#L378-L398) | `\section` a `\subparagraph`: aspecto de los títulos (sans serif) |
| [399-461](tesina/upiita.cls#L399-L461) | Listas, `description`, `verse`, `quote` |
| [462-493](tesina/upiita.cls#L462-L493) | Entorno `titlepage` |
| [494-512](tesina/upiita.cls#L494-L512) | `\appendix` y `\anexo`: reinician la numeración y cambian el nombre ("Apéndice" / "Anexo") |
| [513-563](tesina/upiita.cls#L513-L563) | Figuras, tablas y pies de figura (`caption`) |
| [564-572](tesina/upiita.cls#L564-L572) | Comandos de fuente antiguos (`\bf`, `\it`…) |
| [573-654](tesina/upiita.cls#L573-L654) | Índice general, índice de figuras y de tablas |
| [655-681](tesina/upiita.cls#L655-L681) | Bibliografía (la agrega al índice como "Referencias") |
| [682-702](tesina/upiita.cls#L682-L702) | Índice alfabético (a dos columnas) |
| [703-711](tesina/upiita.cls#L703-L711) | Notas al pie |
| [712-726](tesina/upiita.cls#L712-L726) | Nombres ("Contenido", "Lista de Figures"…) y `\today` en inglés ([P11](#4-registro-de-problemas)) |
| [727-730](tesina/upiita.cls#L727-L730) | Parche: quita la palabra "Parte" en las páginas de `\part` |

### 3.3 `configuracion/upiitatesis.sty` — configuración (forma: no se modifica)

| Líneas | Qué hace |
|:--|:--|
| [10-29](tesina/configuracion/upiitatesis.sty#L10-L29) | Interlineado: queda en 1.5. Define el entorno `singlespace` |
| [30-89](tesina/configuracion/upiitatesis.sty#L30-L89) | Paquetes: fuentes (Montserrat, símbolos), formato, `hyperref` ([P08](#4-registro-de-problemas)), figuras y tablas. Carpeta de imágenes: `imagenes/` |
| [90-128](tesina/configuracion/upiitatesis.sty#L90-L128) | Nombres institucionales (`\Ipn`, `\upiita`) y comandos para los datos de portada (`\alumnoa`, `\asesora`, `\grado`…) |
| [142-156](tesina/configuracion/upiitatesis.sty#L142-L156) | `\LogosVL`: columna de logos IPN/UPIITA con líneas verticales (portada y acta) |
| [157-167](tesina/configuracion/upiitatesis.sty#L157-L167) | Márgenes de la portada ([P10](#4-registro-de-problemas)) |
| [168-196](tesina/configuracion/upiitatesis.sty#L168-L196) | Bloques de firma de alumnos y asesores, según cuántos son |
| [197-247](tesina/configuracion/upiitatesis.sty#L197-L247) | `\portada` |
| [248-342](tesina/configuracion/upiitatesis.sty#L248-L342) | `\acta`: hoja con firmas de alumnos, asesores, presidente del jurado y profesor titular |
| [343-367](tesina/configuracion/upiitatesis.sty#L343-L367) | `\dedicatoria` y `\agradecimientos` (con `\newgeometry`, [P10](#4-registro-de-problemas); página fija, [P12](#4-registro-de-problemas)) |
| [368-375](tesina/configuracion/upiitatesis.sty#L368-L375) | Redefine `\cleardoublepage`: las páginas en blanco para empezar capítulo en página impar quedan sin encabezado |
| [376-383](tesina/configuracion/upiitatesis.sty#L376-L383) | Punto como separador decimal, activa el índice alfabético y los encabezados |
| [384-409](tesina/configuracion/upiitatesis.sty#L384-L409) | Entornos tipo teorema en español (`teorema`, `definicion`, `ejemplo`…) |
| [410-418](tesina/configuracion/upiitatesis.sty#L410-L418) | Nombres en español: "Contenido", "Índice de tablas", "Figura" ([P11](#4-registro-de-problemas)) |
| [419-435](tesina/configuracion/upiitatesis.sty#L419-L435) | `\tabladecontenido`, `\listadefiguras`, `\listadetablas`, `\IndiceAlfabetico` (los agregan al índice y a los marcadores del PDF) |
| [436-462](tesina/configuracion/upiitatesis.sty#L436-L462) | Nomenclatura: tres grupos, A = acrónimos, B = símbolos, C = variables físicas con unidades |
| [464-468](tesina/configuracion/upiitatesis.sty#L464-L468) | `\Introduccion` y `\MarcodeReferencia` |
| [470-473](tesina/configuracion/upiitatesis.sty#L470-L473) | `\referencias`: estilo IEEE, solo las obras citadas ([P03](#4-registro-de-problemas)), archivo `XBiblioteca.bib` ([P04](#4-registro-de-problemas)) |
| [475-491](tesina/configuracion/upiitatesis.sty#L475-L491) | `\cambiamargen`: márgenes del cuerpo del documento ([P10](#4-registro-de-problemas)) |
| [493-555](tesina/configuracion/upiitatesis.sty#L493-L555) | Código comentado (márgenes PDF/papel, cesión de derechos, página en blanco) |

### 3.4 Otros archivos de `configuracion/`

| Archivo | ¿Se usa? | Qué es |
|:--|:--|:--|
| `romanidx.sty` | Sí | Parche para que el índice alfabético funcione en español con páginas en números romanos |

Las copias viejas de paquetes estándar (`etoolbox`, `fncychap`, `makeidx`, `montserrat`, `anyfontsize`, `layouts`, `margenes`), `estilodoc.tex` y `texput.log` se eliminaron el 2026-10-28 ([P22](#4-registro-de-problemas)). LaTeX usaba las de la instalación y el PDF sale idéntico sin ellas. Siguen en el historial de git (commit `eafaa96`).

### 3.5 Contenido

Todo el contenido actual es **de ejemplo**, tomado de otras tesis ([P24](#4-registro-de-problemas)).

| Archivo | Títulos preestablecidos (no se cambian) | Contenido actual |
|:--|:--|:--|
| `preliminares/resumen.tex`, `abstract.tex` | Resumen / Abstract | Palabras clave de un robot bípedo |
| `preliminares/dedicatoria.tex` | — | "bla bla bla" |
| `preliminares/agradecimientos.tex` | — | Agradecimiento al CONACYT por una beca de maestría |
| `preliminares/introduccion.tex` | Definición del problema, Justificación, Objetivo, **Enfoque mecatrónico**, Antecedentes, Capitulado | Vacío ([P26](#4-registro-de-problemas)) |
| `preliminares/nomenclatura.tex` | — | Acrónimos y símbolos de otras tesis (residuos, catarinas, "angels") |
| `capitulos/marcoreferencia.tex` | Marco de referencia (con errata, [P25](#4-registro-de-problemas)): marco teórico, **metodología mecatrónica**, marco procedimental | Vacío |
| `capitulos/diseconceptual.tex` | Diseño del sistema → Diseño conceptual: necesidades, arquitectura funcional y física, propuestas, validación, selección | Vacío ([P09](#4-registro-de-problemas), [P19](#4-registro-de-problemas)) |
| `capitulos/disedetallado.tex` | Diseño detallado por módulo, **integración/validación del sistema mecatrónico** | Vacío ([P19](#4-registro-de-problemas), [P25](#4-registro-de-problemas)) |
| `capitulos/implementacion.tex` | Implementación y verificación por módulo | Vacío ([P25](#4-registro-de-problemas)) |
| `capitulos/discusion.tex` | Análisis de ingeniería, de costos y de valor | Vacío |
| `capitulos/conclusiones.tex` | Conclusiones; Recomendaciones y trabajo futuro | "una conclusión" |
| `apendices/apendice1-3.tex` | Apéndice 1-3 | Texto genérico; títulos y frases en alemán |
| `apendices/anexo1-3.tex` | Anexo 1-3 | Texto genérico sobre hojas de datos ([P20](#4-registro-de-problemas)) |

### 3.6 Bibliografía y recursos

| Ruta | Qué es | Notas |
|:--|:--|:--|
| `XBiblioteca.bib` | Bibliografía (BibTeX, estilo IEEE) | 40 entradas de ejemplo ([P01](#4-registro-de-problemas), [P02](#4-registro-de-problemas)) |
| `logos/` | Logos IPN y UPIITA de la portada y el acta | Necesarios; se versionan |
| `imagenes/` | Carpeta predeterminada de figuras | `img106.jpg` es de ejemplo |
| `latexmkrc` | Regla para generar la nomenclatura al compilar | **Agregado** el 2026-10-27 ([P05](#4-registro-de-problemas)) |
| `adicionales/` | Manuales de LaTeX en PDF y diccionarios ortográficos (`es.zip`, `es_MX.zip`) | Material de consulta, no se compila ([P23](#4-registro-de-problemas)) |
| `Estructura de -libro.jpg` | Imagen de referencia sobre la estructura del documento | No se compila ([P23](#4-registro-de-problemas)) |

---

## 4. Registro de problemas

Estado: **Pendiente** (sin decidir) · **Resuelto** (con fecha y cómo) · **Se conserva** (decidido no cambiar).

Tipo:
- **Error:** rompe algo o da un resultado incorrecto.
- **Aviso:** funciona, pero da problemas o avisos.
- **Forma:** tocarlo cambiaría estilo o títulos; lo decide el autor.
- **Sobrante:** archivo o código que no se usa.
- **Ejemplo:** contenido de otra tesis que se reemplaza.

| ID | Dónde | Problema | Tipo | Estado |
|:--:|:--|:--|:--:|:--|
| P01 | [`XBiblioteca.bib:21-43`](tesina/XBiblioteca.bib#L21-L43) | Molde `@BOOK{,` vacío. En el original traía 18 caracteres invisibles `DEL` (`0x7F`), uno por campo: eran los "caracteres inválidos", y ya no están (se eliminaron al guardar el archivo el 2026-10-27). Además, BibTeX lo procesaba como referencia real y salía una referencia [3] vacía | Error | **Resuelto** 2026-10-27: molde desactivado y conservado, con cada línea comentada con `%`. `@comment` se descartó porque rompe el lector de bibliografía de LaTeX Workshop. **Ojo:** en un `.bib`, `%` no es comentario para BibTeX; cualquier `@`, aunque esté en una línea con `%`, inicia una entrada |
| P02 | [`XBiblioteca.bib:239`](tesina/XBiblioteca.bib#L239) | A la entrada `TR02` le falta una coma tras `title`: error de BibTeX | Error | **Resuelto** 2026-10-27 por el autor: agregó la coma |
| P03 | [`upiitatesis.sty:472`](tesina/configuracion/upiitatesis.sty#L472) | `\nocite{*}` mete todas las entradas del `.bib` en las referencias, citadas o no | Error | **Resuelto** 2026-10-27: quitado por decisión del autor; solo se listan las obras citadas con `\cite`. Sin ninguna `\cite`, BibTeX avisa "I found no \citation commands" y las referencias salen vacías. Desde `116301c` hay una cita de prueba del autor (`\cite{AR17}` en `conclusiones.tex`) |
| P04 | [`upiitatesis.sty:473`](tesina/configuracion/upiitatesis.sty#L473) | `\bibliography{xbiblioteca}` contra `XBiblioteca.bib`: falla en Linux y Overleaf | Error | **Resuelto** 2026-10-27: el `.sty` ahora dice `\bibliography{XBiblioteca}` |
| P05 | Compilación | La nomenclatura no se generaba | Error | **Resuelto** 2026-10-27: `latexmkrc` |
| P06 | [`upiita.cls:252`](tesina/upiita.cls#L252) | "Ing. Mecatrónica" fijo en el pie de página | Forma | **Resuelto** 2026-10-28: el pie dice "Ing. Biónica" (solo cambia el texto; tipografía y posición iguales) |
| P07 | [`upiitatesis.sty:455-456`](tesina/configuracion/upiitatesis.sty#L455-L456) | `S\'MBOLOS`, `F\'SICAS`: salen "SḾBOLOS" y "FŚICAS" | Error | **Resuelto** 2026-10-27: `S\'IMBOLOS` y `F\'ISICAS`; el PDF dice "SÍMBOLOS" y "VARIABLES FÍSICAS" |
| P08 | [`upiitatesis.sty:58`](tesina/configuracion/upiitatesis.sty#L58) | `hyperref` se carga antes de unos diez paquetes; opciones `pdftex` y `pdfstartpage=3`; desactiva la numeración de páginas en el visor de PDF | Aviso | **Resuelto** 2026-10-28: `\pagenumbering{arabic}` en `Principal.tex` (el visor muestra i, ii... y 1, 2...) y sin `pdfstartpage=3` (el PDF abre en la portada). El orden de carga de `hyperref` se conserva |
| P09 | [`diseconceptual.tex:14`](tesina/capitulos/diseconceptual.tex#L14) | Título con matemáticas: avisos de `hyperref` en los marcadores del PDF | Aviso | Pendiente: desaparece cuando el autor reescriba ese título. Si un título lleva matemáticas, usar `\texorpdfstring{$M_1$}{M1}` |
| P10 | `upiitatesis.sty` [158-167](tesina/configuracion/upiitatesis.sty#L158-L167), [346](tesina/configuracion/upiitatesis.sty#L346), [475-491](tesina/configuracion/upiitatesis.sty#L475-L491) | Márgenes definidos de tres formas. **Diagnóstico 2026-10-28** (valores reales medidos en el PDF): portada y acta usan `\cambiamargen` (izquierdo 50.7 mm en impares y 25.4 mm en pares, texto de 153.9 mm); desde la dedicatoria hasta el final rige el `\newgeometry` de la dedicatoria, que nunca se revierte (30/30 mm, texto de 155.9 mm). El cuerpo es consistente. **Efecto visible:** el encabezado y el pie miden 170 mm (los 17 cm de la línea 159, tomados al activar `fancyhdr`) y sobresalen 14 mm hacia el margen exterior | Forma | **Se conserva** 2026-10-28, por decisión del autor: forma original de la plantilla |
| P11 | `upiita.cls` [713-714](tesina/upiita.cls#L713-L714), [723-726](tesina/upiita.cls#L723-L726); [`upiitatesis.sty:415`](tesina/configuracion/upiitatesis.sty#L415) | Nombres. **Diagnóstico 2026-10-28:** las listas salen bien ("Contenido", "Índice de figuras", "Índice de tablas"); los nombres en inglés de la clase no se usan. `\today` no se usa en ningún archivo. **Queda:** cada figura se rotula "Imagen 3.1" mientras la lista se titula "Índice de figuras" (línea 415) | Forma | **Resuelto** 2026-10-28: `\figurename` pasa a "Figura" (línea 415); el pie dice "Figura 3.1", verificado con una figura de prueba |
| P12 | [`upiitatesis.sty:363`](tesina/configuracion/upiitatesis.sty#L363) | `\setcounter{page}{7}` fijo en agradecimientos | Aviso | **Se conserva** 2026-10-28, por decisión del autor: no cambia nada visible |
| P13 | `upiitatesis.sty` [46-47](tesina/configuracion/upiitatesis.sty#L46-L47), [79](tesina/configuracion/upiitatesis.sty#L79) | `color` y `xcolor` duplicados; `subfigure` obsoleto | Aviso | **Se conserva** 2026-10-28, por decisión del autor: no cambia nada visible |
| P14 | [`Principal.tex:68`](tesina/Principal.tex#L68) | Carga por ruta (`configuracion/upiitatesis`): aviso de nombre de paquete | Aviso | **Se conserva** 2026-10-28, por decisión del autor: no cambia nada visible |
| P15 | Portada | La negrita de Montserrat (`sbx`) no existe y se sustituye | Aviso | **Resuelto** 2026-10-28: `\bf` + `\fontseries{sb}` pide `sbx` (semibold + negrita), que no existe, y LaTeX usaba la negrita. Se declaró `sbx` como esa misma negrita en `Principal.tex`. Probado: 0 avisos y PDF idéntico en las 56 páginas. Se descartó forzar la semibold porque cambia la forma de portada y acta |
| P16 | [`upiitatesis.sty:360`](tesina/configuracion/upiitatesis.sty#L360) | Errata `\marcadorAgradecimients` | Aviso | **Se conserva** 2026-10-28, por decisión del autor: no cambia nada visible |
| P17 | [`upiita.cls:138-143`](tesina/upiita.cls#L138-L143) | La opción `latin1` activa `utf8` | Aviso | **Se conserva** 2026-10-28, por decisión del autor: no cambia nada visible |
| P18 | `\acta` ([`upiitatesis.sty:249-342`](tesina/configuracion/upiitatesis.sty#L249-L342)) | El acta de firmas mide 59 pt más de lo que cabe (54 pt con 2 alumnos y 3 asesores, los datos reales). No se corta nada: la última línea (jurado) invade el margen inferior y queda más baja que en la portada | Forma | **Se conserva** 2026-10-28, por decisión del autor: no se corta nada |
| P19 | [`diseconceptual.tex:1`](tesina/capitulos/diseconceptual.tex#L1), [`disedetallado.tex:1`](tesina/capitulos/disedetallado.tex#L1) | Declaraban `% !TeX encoding = ISO-8859-1`, pero son UTF-8: TeXstudio y TeXworks los abrirían con caracteres raros (VS Code no lee esa línea) | Error | **Resuelto** 2026-10-27: ahora declaran `UTF-8` |
| P20 | [`anexo2.tex:13`](tesina/apendices/anexo2.tex#L13), [`anexo3.tex:10`](tesina/apendices/anexo3.tex#L10) | `\verb+\+bigskip` imprime literalmente "\bigskip" | Error | **Resuelto** 2026-10-27: `\bigskip`, como en `anexo1.tex` |
| P21 | `Principal.tex`, encabezado (líneas 24 y 31-32 del original, `eafaa96`) | Los comentarios mencionan `config.tex` y `mecatexis.prj`, que no existen | Sobrante | **Resuelto** 2026-10-28: se quitaron las menciones a `config.tex` y `mecatexis.prj`; el bloque de licencia y créditos se conserva |
| P22 | `configuracion/` | Copias de paquetes no usadas, `estilodoc.tex` comentado, `texput.log` | Sobrante | **Resuelto** 2026-10-28: eliminados. Probado: el PDF sale idéntico en las 56 páginas sin ellos; siguen en git (`eafaa96`) |
| P23 | `adicionales/`, `Estructura de -libro.jpg` | Material de consulta que no se compila | Sobrante | **Se conserva** 2026-10-28, por decisión del autor: `adicionales/` se queda local, fuera de git; `Estructura de -libro.jpg` se queda |
| P24 | Contenido (§3.5), `XBiblioteca.bib`, `imagenes/img106.jpg` | Contenido de ejemplo de otras tesis | Ejemplo | Pendiente |
| P25 | `marcoreferencia.tex:1`, `disedetallado.tex`, `implementacion.tex` | Erratas en títulos preestablecidos: "referencíal", "M{l}" (letra L por el número 1), "módulo 2 (M{n})", paréntesis faltante, sección duplicada. Además, numeración con niveles saltados ("4.0.1" en `discusion.tex`, "3.1.0.1" en `implementacion.tex`), porque usan una subsección sin sección | Forma | Pendiente: lo resuelve el autor al reestructurar los títulos con la estructura de sus indicaciones (2026-10-28). Los títulos actuales solo ilustran el uso de capítulos y secciones |
| P26 | `introduccion.tex`, `marcoreferencia.tex`, `disedetallado.tex` | Títulos pensados para Mecatrónica ("Enfoque mecatrónico", "Metodología mecatrónica", "sistema mecatrónico") | Forma | **Marcado** 2026-10-28 con `\duda` (y `% [DUDA]` en el código) en los 4 títulos que dicen "mecatrónico", los únicos sin equivalente en la estructura de `PROTOCOLO_TT.pdf`. Lo adapta el autor; los demás títulos sí tienen equivalente |
| P27 | `apendices/*.tex` | `\stepcounter{chapter}`. **Diagnóstico 2026-10-28:** los títulos llevan el número escrito a mano ("Apéndice 1"); el `\stepcounter` numera las figuras y tablas internas (Apéndice 1 → "Imagen A.1"). **Problema:** los anexos repiten las letras de los apéndices (la figura del Anexo 1 también es "A.1"), así que una referencia "Imagen A.1" es ambigua | Forma | **Se conserva** 2026-10-28, por decisión del autor. Al citar figuras de anexos, conviene nombrar el anexo en el texto para evitar la ambigüedad |
| P28 | [`Principal.tex:77-109`](tesina/Principal.tex#L77-L109) | Datos de ejemplo: nombres ficticios, Mecatrónica, "Mes", "Año" | Ejemplo | Pendiente: llenar |
| P29 | Fuentes del texto principal | **El texto se genera con fuentes de mapa de bits (Type 3)**, porque la fuente estándar en codificación T1 necesita `cm-super`, que no está instalado. Efectos: el texto se ve borroso con zoom, y al buscar o copiar en el PDF se pierden las ligaduras ("figuras" → "guras", "ficha" → "cha"). Probado: `\rmdefault{lmr}` (más `\ttdefault{lmtt}` para `\verb`) deja el texto vectorial y buscable, sin mover saltos de línea ni páginas y conservando Montserrat en los títulos. `lmodern` completo se descartó porque cambia la fuente de los títulos | Error | **Resuelto** 2026-10-28: `\rmdefault{lmr}` y `\ttdefault{lmtt}` en `Principal.tex`. Verificado: 0 fuentes de mapa de bits, búsqueda y copiado correctos, 56 páginas y Montserrat en los títulos |
| P30 | [`upiitatesis.sty:279`](tesina/configuracion/upiitatesis.sty#L279), [`:294`](tesina/configuracion/upiitatesis.sty#L294) | El acta dice "Presenta:" (singular) con 3 y con 2 alumnos; la portada dice bien "Presentan:". Afecta los datos reales (2 alumnos) | Error | **Resuelto** 2026-10-28: "Presentan:" en los casos de 3 y 2 alumnos del acta |

---

## 5. Avance y pendientes

Método acordado para cada problema: Claude explica qué hace la pieza, prueba las opciones en una copia aislada (con imágenes del PDF cuando aplica) y el autor decide. Después se aplica, se compila la tesina real y se actualiza el estado en la §4.

### Sesión 2026-10-27

- Plantilla examinada y movida de `Escrito/TT_UPIITA_2023/` a `Escrito/tesina/`. El `.zip` original se conserva local, fuera de git.
- Herramientas agregadas:
  - `latexmkrc`, para la nomenclatura (P05);
  - carga de las marcas de revisión en `Principal.tex`;
  - marca `\duda`;
  - este mapa;
  - `.gitignore` para los auxiliares de LaTeX, el `.zip` y `adicionales/`.
- **Resueltos: P01, P02 (por el autor), P03, P04, P05, P07, P19, P20.** Con eso no queda ningún problema de tipo Error.
- Hallazgos que conviene recordar:
  - En un `.bib`, `%` no es comentario para BibTeX y cualquier `@` inicia una entrada.
  - LaTeX Workshop no entiende `@comment`.
  - Sin ninguna `\cite`, BibTeX avisa "I found no \citation commands" y las referencias salen vacías (efecto esperado de P03). Hoy hay una cita de prueba del autor (`\cite{AR17}` en `conclusiones.tex`).
  - Al escribir la bibliografía propia: los autores institucionales van entre llaves dobles, `{{...}}`, y los nombres propios de los títulos se protegen, `{M}éxico`.

### Sesión 2026-10-28

- Primera revisión del agente `verificador`: 8 hallazgos, ninguna contradicción. Se aplicaron los mecánicos: commits en `REGISTRO_IA.md`, líneas del `.bib` en este mapa, `PLANTILLA.md` en el árbol del README y aclaración del `.zip`.
- Diagnosticados en el PDF, con mediciones y pruebas en copias: P10, P11, P18 y P27.
- **Problemas nuevos:** P29 (fuentes de mapa de bits) y P30 ("Presenta:" en el acta). También se amplió P25 con los niveles de numeración saltados.
- **Decisiones del autor:**
  - **Resueltos:** P11 ("Figura"), P29 (fuentes vectoriales) y P30 ("Presentan:").
  - **Se conservan como en el original:** P10, P18 y P27.
- Títulos marcados con `\duda` contra la estructura de `PROTOCOLO_TT.pdf` (P26). P25 lo resuelve el autor al reestructurar.
- Más decisiones del autor:
  - **Resueltos:** P06 ("Ing. Biónica"), P08 (números de página en el visor; abre en la portada), P21 y P22.
  - **Se conservan:** P12 a P14, P16, P17 y P23. P15, que se había conservado, se resolvió después (sin avisos y con el mismo aspecto).
- **Con esto se cerró la revisión de la plantilla.** Lo pendiente (P09, P24, P25, P26, P28) se resuelve al escribir la tesina.

### Pendientes, en el orden propuesto

1. **Inicio de la tesina real** ← **Retomar aquí.** Lo que queda lo resuelve el autor al escribir:
   - P24: reemplazar el contenido de ejemplo;
   - P28: datos reales de portada;
   - P25 y P26: títulos, que ya están marcados;
   - P09: un título con matemáticas.
