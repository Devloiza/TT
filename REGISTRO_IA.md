# Registro de apoyo de IA

**Control interno. No se incluye en la tesina.** Sirve para tener a la mano, si se pide declararlo, qué hizo el autor y en qué apoyó la IA (Claude, vía Claude Code). Las reglas de ese apoyo están en `CLAUDE.md`, sección "Rol de Claude y de los agentes".

Cómo se llena:
- Claude agrega una fila cada vez que contribuye a algo del repo y describe solo su propio aporte.
- **"Aporte del autor" lo completa el autor.** Claude no lo llena, salvo que el autor se lo dicte.
- Las filas anteriores a este registro se reconstruyeron con `git log`: los commits en que participó Claude llevan `Co-Authored-By: Claude`. El commit dice que hubo participación, no cuánta; por eso esas filas dicen "por completar".

| Fecha | Commit(s) | Qué | Aporte del autor | Apoyo de IA |
|:--|:--|:--|:--|:--|
| 2026-06-26 | `fbbea6a`, `43b7425` | Primer commit y subida general con `Documentation.md` | _(por completar)_ | Sin coautoría de IA registrada |
| 2026-09-06 | `9ed3eca` | Ajustes de documentación (color de LEDs) | _(por completar)_ | Sin coautoría de IA registrada |
| 2026-09-06 | `7354974`, `7036848`, `fb1e02d`, `80ced89`, `c509810`, `3692ccd` | Sistema base de adquisición de 8 mics, corrección de sincronización, soporte de Raspberry Pi, `SKIP_AUDIO`, vectorización y bug de paridad de byte | _(por completar)_ | Coautoría registrada en los commits; alcance por completar |
| 2026-09-07 | `85b2b38`, `4a2178f`, `702322e`, `a07ab4c`, `e09d594`, `ae86442` | Selección de dispositivo de audio, guía de uso, changelog v0.2.0, `DEBUG`, corrección de systemd, `AUTO_CYCLE_SECONDS` | _(por completar)_ | Coautoría registrada en los commits; alcance por completar |
| 2026-09-08 | `dec1b99`, `b50053c` | Anclar `Documentation.md` al protocolo; decisión Python vs Rust | _(por completar)_ | Coautoría registrada en los commits; alcance por completar |
| 2026-10-07 | `c014e0d` | Simulación de DAS/DOA (`Exploration/beamforming_algorithms/`) | _(por completar)_ | Hecha casi por completo por Claude. **Eliminada** en `610d0c6`; no forma parte del trabajo del TT |
| 2026-10-07 | `f8dd431`, `639c545` | `CONTEXTO.md`, `CLAUDE.md`, agentes de Claude Code y reorganización de la documentación | _(por completar)_ | Coautoría registrada en los commits; alcance por completar |
| 2026-10-21 | `610d0c6` | Eliminación de la simulación de DAS/DOA y de sus menciones en la documentación | Decidió eliminarla y aprobó qué se borraba | Localizó las referencias y ejecutó la eliminación |
| 2026-10-21 | El siguiente a `610d0c6` | Herramientas de trabajo, no evaluables: configuración de agentes, paquete `Escrito/revision.sty`, `Escrito/CODIGOS_REVISION.md`, separación de `Escrito/` en `tesina/` y `pruebas/`, y este registro | Definió los requisitos: el rol de los agentes, los códigos de marca y sus colores, las reglas de apoyo, la aplicación rígida de `CONTEXTO.md` y la separación de carpetas | Implementó los archivos y probó el agente revisor con un texto de prueba |
