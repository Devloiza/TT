# Guion de sesión del conductor (boceto)

> **Boceto hecho por Claude a petición del autor (2026-11-22). El autor lo revisa y lo ajusta.** Lo marcado con **[DECIDIR]** es decisión del autor. Diseño de la sesión en [`Metodologia/obj3_base_de_datos.md`](../../Metodologia/obj3_base_de_datos.md) §4.1 y §4.5.

Este guion es para que los dos conductores hagan la sesión igual con todos los participantes. Las frases entre comillas se dicen tal cual. Lo demás es para el conductor.

## 1. Antes de que llegue la persona (unos 10 min)

- [ ] Computadora conectada a la corriente y con las notificaciones apagadas (modo "No molestar").
- [ ] UMC202HD conectada con el AT2020 en su entrada y los +48 V encendidos. **[DECIDIR]** Ganancia de referencia anotada para todas las sesiones.
- [ ] Micrófono a la distancia fija **[DECIDIR: cuántos cm]** de la boca, con el filtro antipop si se usa. Ponerlo un poco de lado para que no reciba el aire directo.
- [ ] Celulares de todos en silencio y lejos del micrófono, no solo vibrando.
- [ ] Puerta cerrada y aviso afuera de "Grabando, no tocar".
- [ ] Sonómetro en dB(A), respuesta lenta, en la posición de la persona. Tomar la lectura del ruido de fondo. Si pasa de **35 dB(A)**, esperar o buscar la fuente del ruido.
- [ ] Hay espacio libre en `Descargas/BD_VOZ` y el disco duro externo está a la mano.
- [ ] Dos formatos de consentimiento impresos (uno para la persona y uno para el proyecto) y pluma.
- [ ] Agua para la persona.
- [ ] Cerrar programas que hagan ruido o usen el audio.

## 2. Bienvenida y consentimiento (bloque a, 2–3 min)

> "Hola, gracias por venir. Soy [nombre] y estoy haciendo mi Trabajo Terminal en la UPIITA. Vamos a grabar tu voz para entrenar un sistema que ayude a entender el habla en lugares con ruido. Dura unos 25 minutos."

> "Antes de empezar, te pido que leas este consentimiento. Si tienes cualquier duda, pregúntame. La publicación de tu voz es aparte y es opcional: si no la autorizas, tu voz solo se usa dentro del proyecto."

- Esperar a que lo lea y lo firme. Resolver dudas.
- Si no acepta, se agradece y no se graba.

> "Vas a ver todo en esta pantalla. Yo voy a manejar el teclado, tú solo vas a hablar. Si en algún momento quieres parar, me dices y paramos."

- Correr el programa: `python Exploration/Prueba_BD/presentador_frases.py`.
- Llenar los datos en la consola: edad, sexo, lugar, ganancia, sonómetro, conductor y notas.
- **Prueba de nivel:** pedirle una frase con su voz normal y revisar que no se acerque a 0 dBFS.

> "Dime en voz normal qué desayunaste hoy."

- Si satura, bajar la ganancia y anotar el valor nuevo. **[DECIDIR]** Si se ajusta la ganancia en cada persona o se deja fija.

## 3. Silencio de referencia (bloque b, 30 s)

> "Primero vamos a guardar silencio 30 segundos para grabar el ruido del lugar. Arriba verás una barra que muestra cuánto falta. Trata de no moverte."

- El conductor tampoco habla ni se mueve.

## 4. Barras y calibración (2 min)

- Al terminar el silencio, la pantalla explica las barras. Leérselo en voz alta si es necesario:

> "La barra delgada te dice cuántas frases faltan para descansar. Cuando aparezca una barra grande que dice «Descanso», no hay nada que leer, solo espera."

> "Ahora lee cada frase en voz alta, a tu ritmo normal, como si se la leyeras a alguien. Si te equivocas, no pasa nada: sigue con la siguiente."

- Presionar **Espacio** justo cuando termine cada frase. Así se mide su ritmo.

## 5. Frases (bloque c, 6–8 min)

> "Ahora las frases van a cambiar solas. Solo léelas conforme aparezcan."

- No intervenir. Los errores de lectura se quedan.
- **R** solo si hay un ruido externo fuerte e inesperado (un portazo, una alarma).
- **M** para marcar una frase dudosa (tos, una palabra omitida, un ruido leve).
- **P** si la persona necesita parar.

## 6. Lectura continua y secuencias (bloques d y e, 2 min)

> "Ahora vas a leer un texto corto completo, a tu ritmo."

- **Espacio** cuando termine de leer.
- Luego la pantalla pide contar del 1 al 20 y decir los días de la semana. **Espacio** al terminar cada uno.

## 7. Habla libre (bloque f, 12–13 min)

> "Ya terminamos de leer. Ahora vas a hablar libremente. No hay respuestas correctas ni incorrectas, lo importante es que hables."

**Imágenes (3 min)**

> "Describe la imagen con todo el detalle que puedas: qué ves, qué crees que está pasando."

- Si termina rápido, **Espacio** para pasar a otra imagen. Si va despacio, dejarla.

**Estilos guiados (unos 4 min)**

- La pantalla indica el estilo: fuerte, baja y susurro.
- Antes del susurro:

> "Ahora en susurro, sin voz, como si no quisieras que nadie más te oyera."

- Si se queda sin qué decir, **Espacio** para otra pregunta.

**Plática (5 min)**

> "Imagina que estás platicando conmigo. Contesta con calma, con tu voz normal."

- **[DECIDIR]** El conductor no habla mientras graba, para que no quede su voz en la grabación. Puede asentir o sonreír para que la persona se sienta escuchada.
- **Espacio** para cambiar de pregunta si una no funciona.
- En medio, pedir otros estilos con **F** (fuerte), **B** (baja), **S** (susurro) y **N** (normal). La pantalla lo indica sola. **[DECIDIR]** Cuántos cambios y en qué momentos, para que todas las sesiones sean parecidas.

## 8. Cierre (2 min)

> "¡Terminamos! Muchas gracias por tu tiempo, nos ayudas muchísimo."

- Darle su copia del consentimiento. **[DECIDIR]** Si la copia lleva su código (P01, P02…) y un contacto, para que pueda retirar su autorización después.
- **Después de que se vaya:**
  - [ ] revisar que se creó la carpeta `Descargas/BD_VOZ/<código>_<fecha>/` con `audio.wav`, `frases.csv` y `sesion.json`;
  - [ ] escuchar unos segundos del inicio, del susurro y del final;
  - [ ] copiar la carpeta al disco duro externo;
  - [ ] guardar el consentimiento firmado en el lugar acordado, separado de las grabaciones;
  - [ ] anotar cualquier incidente en las notas de la sesión.

## 9. Si algo sale mal

| Situación | Qué hacer |
|:--|:--|
| Ruido externo fuerte durante una frase | **R** para repetirla |
| Ruido fuerte en el habla libre | **M** y seguir; si es muy largo, **P** y reanudar |
| La persona tose o se ríe | **M** y seguir |
| La persona quiere parar | **P**. Si no quiere seguir, **Esc**: se guarda lo grabado |
| El programa se cierra solo | Lo grabado en esa sesión se pierde, porque el audio se escribe al final. **[DECIDIR]** Si se repite la sesión completa con la misma persona; anotarlo en las notas |
