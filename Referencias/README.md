# Referencias

Artículos y documentos importantes del proyecto. **Los PDF se quedan locales** (no se versionan, por derechos de autor, tamaño o porque son formatos de trabajo). En git solo está este índice. Si clonas el repositorio, consigue los PDF desde el DOI o el enlace de cada fila.

`PROTOCOLO_TT.pdf` está en la raíz del repositorio y tampoco se versiona.

| Archivo | Referencia | Para qué sirve en el TT | Dónde se usa |
|:--|:--|:--|:--|
| `GTCRN-A-Speech-Enhancement-Model-Requiring-Ultralow-Computational-Resources.pdf` | X. Rong, T. Sun, X. Zhang, Y. Hu, C. Zhu y J. Lu, "GTCRN: A Speech Enhancement Model Requiring Ultralow Computational Resources", en *ICASSP 2024*, pp. 971–975, doi: 10.1109/ICASSP48485.2024.10448310 | Arquitectura propuesta para el clasificador del Obj. 4 y posible post-filtro (extensión). Referencia de metodología para la base: SNR de −5 a 15 dB, referencia con 100 ms de reflexiones tempranas, 16 kHz. Sus resultados muestran el techo de STOI (riesgo R9) | [`CONTEXTO.md`](../CONTEXTO.md) §3.4 (Obj. 4), §4.2 y §5 (R9, R11) |
| `CONSENTIMIENTO INFORMADO PARA LA GRABACIÓN Y USO DE MUESTRAS DE VOZ.pdf` | Formato de consentimiento informado del autor (adultos y menores) | Consentimiento de las sesiones de voz del Obj. 3: actividades, datos que se guardan, uso, publicación opcional y retiro. En revisión con los asesores | [`Metodologia/obj3_base_de_datos.md`](../Metodologia/obj3_base_de_datos.md) §3.2 y §8 |
| `Guion.pdf` | Guion de sesión del conductor, del autor (2026-11-26) | Pasos de cada sesión de voz del Obj. 3, iguales para los dos conductores: preparación, consentimiento, bloques y cierre | [`Metodologia/obj3_base_de_datos.md`](../Metodologia/obj3_base_de_datos.md) §8 |

Al agregar un artículo: guarda el PDF aquí, añade una fila con la cita completa y verifica el DOI contra el propio PDF.
