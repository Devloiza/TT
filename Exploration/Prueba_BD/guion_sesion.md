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
- [ ] Con `python Exploration/Prueba_BD/espectro_ruido.py --vivo`, revisar el ruido y que la voz no sature. Cerrarlo antes de grabar.
- [ ] Espectro del ruido: `python Exploration/Prueba_BD/espectro_ruido.py`. Compararlo con el de otras sesiones con la misma ganancia. **[DECIDIR]** Qué valor hace que se espere o se busque la fuente.
- [ ] Hay espacio libre en `Descargas/BD_VOZ` y el disco duro externo está a la mano.
- [ ] Dos formatos de consentimiento impresos (uno para la persona y uno para el proyecto) y pluma.
- [ ] Agua para la persona.
- [ ] Cerrar programas que hagan ruido o usen el audio.

## 2. Bienvenida y consentimiento (bloque a, 2–3 min)

> "Hola, gracias por venir. Soy [nombre] y estoy haciendo mi Trabajo Terminal en la UPIITA. Vamos a grabar tu voz para entrenar un sistema que ayude a entender el habla en lugares con ruido. Dura unos 20 minutos."

> "Antes de empezar, te pido que leas este consentimiento. Si tienes cualquier duda, pregúntame. La publicación de tu voz es aparte y es opcional: si no la autorizas, tu voz solo se usa dentro del proyecto."

- Esperar a que lo lea y lo firme. Resolver dudas.
- Si no acepta, se agradece y no se graba.

> "Vas a ver todo en esta pantalla. Yo voy a manejar el teclado, tú solo vas a hablar. Si en algún momento quieres parar, me dices y paramos."

- **Voz normal y voz fuerte:** con `espectro_ruido.py --vivo` abierto, pedirle la misma frase en cada voz y comparar el nivel de 80–8000 Hz. La fuerte debe subir al menos **[DECIDIR: cuántos dB]** sin saturar; si no, explicarle otra vez. Cerrar el monitor.
- Correr el programa: `python Exploration/Prueba_BD/presentador_frases.py`.
- Si aparece el aviso de que la entrada no es **WASAPI**, corregirla antes de seguir (`configurar_audio.py`).
- Llenar los datos en la consola: edad, sexo, lugar, ganancia, sonómetro, conductor y notas. En una sesión de prueba (P00) se llenan solos.
- **Prueba de nivel:** pedirle una frase con su voz normal y revisar que no se acerque a 0 dBFS.

> "Dime en voz normal qué desayunaste hoy."

- Si satura, bajar la ganancia y anotar el valor nuevo. **[DECIDIR]** Si se ajusta la ganancia en cada persona o se deja fija.

- La primera pantalla lo explica: **en negro y sin recuadro lo que se lee en voz alta; en un recuadro azul, las instrucciones y las preguntas**. Confirmar que se entendió.
- **Seña:** en las pantallas de espera, la persona hace una seña con la mano cuando termina de leer. Esperarla antes de presionar **Espacio**. Acordar la seña al inicio, para que sea silenciosa:

> "Cuando termines de leer cada instrucción, levanta la mano, sin hablar, y yo continúo."

- **Espacio** siempre con una pulsación corta. Si se deja presionada, cuenta una sola vez.

## 3. Silencio de referencia (bloque b, 30 s)

> "Primero vamos a guardar silencio 30 segundos para grabar el ruido del lugar. Arriba verás una barra que muestra cuánto falta. Trata de no moverte."

- El conductor tampoco habla ni se mueve.

## 4. Barras y calibración (2 min)

- Al terminar el silencio, la pantalla explica las barras. Leérselo en voz alta si es necesario:

> "La barra delgada te dice cuántas frases faltan para descansar. Cuando aparezca una barra grande que dice «Descanso», no hay nada que leer, solo espera."

> "Lee en voz alta cada frase en cuanto aparezca, con tu voz y ritmo normales. Si te equivocas, no la repitas: continúa."

- Presionar **Espacio** justo cuando termine cada frase. Así se mide su ritmo.

## 5. Frases (bloque c, 6–8 min)

> "Ahora las frases cambiarán solas. Lee cada una una sola vez. Con la pantalla en blanco, guarda silencio."

- No intervenir. Los errores de lectura se quedan.
- **R** solo si hay un ruido externo fuerte e inesperado (un portazo, una alarma).
- **M** para marcar una frase dudosa (tos, una palabra omitida, un ruido leve).
- **P** si la persona necesita parar.

## 6. Lectura continua y secuencias (bloques d y e, 2–3 min)

> "Ahora lee en voz alta todo el texto, con tu voz y ritmo normales. Si te equivocas, continúa."

- **Espacio** cuando termine de leer.
- Luego la pantalla pide contar del 1 al 20 y decir los días de la semana, cada uno con voz normal y después con voz fuerte. **Espacio** al terminar cada uno y en las pantallas de espera entre voces. Entre los números y los días, la pantalla pide regresar a la voz normal.

## 7. Habla libre (bloque f, 5–6 min)

> "Ya terminamos de leer. Ahora vas a hablar libremente. No hay respuestas correctas ni incorrectas, lo importante es que hables."

La pantalla dice siempre qué voz usar: **primero normal y luego fuerte**. Antes de cada cambio hay una pantalla de espera: aprovecharla para que la persona descanse y continuar con **Espacio**.

**Imágenes (1 min en cada voz)**

> "Describe en voz alta la imagen: personas, objetos, lugar y qué está pasando. Sigue hablando hasta que cambie. Primero con tu voz normal."

- Si termina rápido, **Espacio** para pasar a otra imagen. Si va despacio, dejarla.

**Preguntas (1 min 30 s en cada voz)**

> "Contesta como si platicaras conmigo, primero con tu voz normal. No leas la pregunta. Da todos los detalles que puedas."

- **Espacio** para cambiar de pregunta si una no funciona.
- **[DECIDIR]** El conductor no habla mientras graba, para que no quede su voz en la grabación. Puede asentir o sonreír para que la persona se sienta escuchada.

**Antes de cada cambio a voz fuerte,** en la pantalla de espera:

> "Ahora lo mismo con voz fuerte, como si yo estuviera al otro lado del salón. Sin gritar ni acercarte al micrófono."

## 8. Cierre (2 min)

> "¡Terminamos! Muchas gracias por tu tiempo, nos ayudas muchísimo."

- Darle su copia del consentimiento. **[DECIDIR]** Si la copia lleva su código (P01, P02…) y un contacto, para que pueda retirar su autorización después.
- **Después de que se vaya:**
  - [ ] revisar que se creó la carpeta `Descargas/BD_VOZ/<código>_<fecha>/` con `audio.wav`, `frases.csv` y `sesion.json`;
  - [ ] escuchar unos segundos del inicio, de la voz fuerte y del final;
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
