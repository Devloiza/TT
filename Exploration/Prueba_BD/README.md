# Prueba_BD: preparación de la adquisición de voz (Obj. 3)

Diseño completo en [`Metodologia/obj3_base_de_datos.md`](../../Metodologia/obj3_base_de_datos.md).

| Archivo | Qué es |
|:--|:--|
| `Lists_SHARVARD.txt` | Las 70 listas de 10 frases del corpus *Sharvard*. Las líneas "a." son propuestas de adaptación del autor |
| `Lists_SHARVARD_MX.txt` | Versión adaptada al español de México: una frase final por número. Es la que usa el programa |
| `adaptaciones_SHARVARD_MX.csv` | Registro de las 51 frases adaptadas: original, adaptada y motivo |
| `calibracion.txt` | 10 frases propias para medir el ritmo de lectura. No son de *Sharvard* |
| `preguntas.txt` | Indicaciones y banco de 30 preguntas del habla libre (§4.3). Solo se muestran en pantalla |
| `textos_prueba/El_viento_norte_y_el_sol.txt` | Texto de la lectura continua (§4.1, bloque d), versión de Coloma. Lo eligió el autor |
| `fuentes_imagenes.csv` | Fuente de cada imagen para describir: archivo, URL de Pexels, fotógrafo y licencia |
| `configurar_audio.py` | Prueba de habla (micrófono) una vez por máquina; guarda la elección en `config_audio.json`. Hecho por Claude con la especificación del autor |
| `presentador_frases.py` | Programa de sesión: hecho por Claude con la especificación del autor. Uso y teclas en su encabezado |
| `guion_sesion.md` | Boceto del guion del conductor, hecho por Claude a petición del autor; el autor lo revisa |

No se versionan:

- `image/`: las imágenes para describir (Pexels, unos 66 MB). Se reconstruyen con `fuentes_imagenes.csv`. La licencia de Pexels permite usarlas sin dar crédito, pero no redistribuirlas en otras plataformas de fotos;
- `config_audio.json`: los dispositivos de cada máquina;
- las grabaciones, que van a `Descargas/BD_VOZ/`, fuera del repo y de OneDrive, con copia en un disco duro externo.

## Atribución y licencia de *Sharvard*

Las frases de `Lists_SHARVARD.txt` y su adaptación `Lists_SHARVARD_MX.txt` provienen del *Sharvard Corpus*. El dataset se distribuye en Edinburgh DataShare con licencia **Creative Commons Attribution 4.0 International (CC BY 4.0)**. Esa licencia permite redistribuir y adaptar, siempre que se cite la fuente y se indiquen los cambios.

- **Artículo:** V. Aubanel, M. L. García Lecumberri y M. Cooke, "The Sharvard Corpus: A phonemically-balanced Spanish sentence resource for audiology", *International Journal of Audiology*, vol. 53, núm. 9, pp. 633–638, 2014.
- **Dataset:** Edinburgh DataShare. *Pendiente: agregar la cita exacta del dataset, con su DOI o identificador, desde su ficha.*
- **Cambios:** `Lists_SHARVARD_MX.txt` es una adaptación hecha para este proyecto. Los cambios están documentados uno por uno en `adaptaciones_SHARVARD_MX.csv`.
