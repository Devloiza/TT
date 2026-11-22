# Prueba_BD: preparación de la adquisición de voz (Obj. 3)

Diseño completo en [`Metodologia/obj3_base_de_datos.md`](../../Metodologia/obj3_base_de_datos.md).

| Archivo | Qué es |
|:--|:--|
| `Lists_SHARVARD.txt` | Las 70 listas de 10 frases del corpus *Sharvard*. Las líneas "a." son propuestas de adaptación del autor |
| `Lists_SHARVARD_MX.txt` | Versión adaptada al español de México: una frase final por número. Es la que usa el programa |
| `adaptaciones_SHARVARD_MX.csv` | Registro de las 51 frases adaptadas: original, adaptada y motivo |
| `calibracion.txt` | 10 frases propias para medir el ritmo de lectura. No son de *Sharvard* |
| `presentador_frases.py` | Programa de sesión: hecho por Claude con la especificación del autor. Uso y teclas en su encabezado |

Las grabaciones van a `SALIDAS/BD_voz/`, que no se versiona.

## Atribución y licencia de *Sharvard*

Las frases de `Lists_SHARVARD.txt` y su adaptación `Lists_SHARVARD_MX.txt` provienen del *Sharvard Corpus*. El dataset se distribuye en Edinburgh DataShare con licencia **Creative Commons Attribution 4.0 International (CC BY 4.0)**. Esa licencia permite redistribuir y adaptar, siempre que se cite la fuente y se indiquen los cambios.

- **Artículo:** V. Aubanel, M. L. García Lecumberri y M. Cooke, "The Sharvard Corpus: A phonemically-balanced Spanish sentence resource for audiology", *International Journal of Audiology*, vol. 53, núm. 9, pp. 633–638, 2014.
- **Dataset:** Edinburgh DataShare. *Pendiente: agregar la cita exacta del dataset, con su DOI o identificador, desde su ficha.*
- **Cambios:** `Lists_SHARVARD_MX.txt` es una adaptación hecha para este proyecto. Los cambios están documentados uno por uno en `adaptaciones_SHARVARD_MX.csv`.
