# Sistema de localización acústica multimicrófono bioinspirado en escorpiones

**Trabajo Terminal** · Ingeniería Biónica · UPIITA-IPN · Semestre 2026/2 · Proyecto `DTA.MI.2026-2.5BM1.LMP.01`

> *Sistema de localización acústica multimicrófono basado en mecanismos de detección vibracional de escorpiones para la mejora de la inteligibilidad del habla en entornos acústicamente adversos.*

| | |
|:--|:--|
| **Alumnos** | Deloiza Rodríguez Arturo · Jiménez Jiménez Atenea |
| **Asesores** | Ing. Carlos Ríos Ramírez · Dr. Álvaro Anzueto Ríos · Dr. Carlos Carrizales Velázquez (externo) |
| **Profesora titular** | Dra. Lilia Martínez Pérez |
| **Versión del sistema** | `v0.2.0`: adquisición de 8 micrófonos estable en PC y Raspberry Pi (ver [`CHANGELOG.md`](CHANGELOG.md)) |

---

## Índice

1. [Qué es](#1-qué-es)
2. [Qué será: el sistema completo](#2-qué-será-el-sistema-completo)
3. [Estado actual](#3-estado-actual)
4. [Mapa de documentación](#4-mapa-de-documentación)
5. [Estructura del repositorio](#5-estructura-del-repositorio)
6. [Inicio rápido](#6-inicio-rápido)
7. [Convenciones de trabajo](#7-convenciones-de-trabajo)

---

## 1. Qué es

En ambientes ruidosos (cafeterías, aulas, calles) la voz que interesa llega mezclada con otras fuentes y la inteligibilidad cae. Un **arreglo de micrófonos** puede "escuchar en una dirección": estima de dónde viene la voz y combina los canales para reforzarla frente al ruido (*beamforming*).

Este proyecto diseña ese arreglo **inspirado en las *slit sensilla* del escorpión**, órganos que detectan vibraciones del sustrato y le permiten al escorpión localizar a su presa por **diferencias de tiempo y amplitud** entre sensores distribuidos en sus patas. La adaptación es **funcional, no una réplica**. Lo que se traslada al dominio acústico es el principio de *muestreo espacial diferencial*: 8 micrófonos en **4 pares con separaciones y pesos diferenciados**, en una disposición **no lineal y no uniforme**.

**Hipótesis** (textual en [`CONTEXTO.md` §2.1](CONTEXTO.md#21-hipótesis-textual-del-protocolo)). Con SNR de entrada entre **−5 y 10 dB**, el sistema debe lograr:

| | Criterio comprometido | Contra qué se mide |
|:--:|:--|:--|
| C1 | **≥ 10 %** de mejora en STOI (inteligibilidad) | Señal degradada con ruido |
| C2 | **≥ 10 %** de mejora en PESQ (calidad percibida) | Señal degradada con ruido |
| C3 | **≥ 3 dB** de mejora de SNR | **Arreglo lineal uniforme** de 8 mics con *delay-and-sum* convencional, mismo hardware, mismas condiciones |

Los 8 objetivos específicos, los compromisos de diseño implícitos (D1–D10) y el presupuesto están en [`CONTEXTO.md` §2](CONTEXTO.md#2-el-compromiso).

---

## 2. Qué será: el sistema completo

Cadena de bloques del protocolo (Fig. 2), con el estado de cada bloque:

```
 Arreglo de 8 mics ICS-43434 (4 pares LR, geometría no lineal)    🟡 PCBs listas en bases movibles; forma final (collar) pendiente
            │
            ▼
 Adquisición: 2× ESP32-S3 (I2S → USB CDC, SYNC por hardware)       🟢 funcionando (PCB)       
            │
            ▼
 Sincronización en Python → frame (512, 8) a 16 kHz                🟢 funcionando (PC y Raspberry Pi)
            │
            ├──────────────────────────────┐
            ▼                              ▼
 Clasificación habla / ruido      Estimación de dirección (DOA)    🔴 / 🔴 pendiente
            │                              │
            └──────────────┬───────────────┘
                           ▼
            Beamforming (DAS con pesos diferenciados)              🔴 pendiente
                           │
                           ▼
            Señal de salida mejorada
                           │
                           ▼
 Evaluación: PESQ, STOI, mejora de SNR vs. arreglo lineal uniforme  🔴 pendiente
```

Además del sistema, el protocolo compromete:

- **Base de datos propia**: habla, ruido y habla + ruido, que combina mezclas sintéticas de bases públicas con grabaciones hechas con el dispositivo.
- **PCB del sistema de adquisición** (✅ ya implementada).
- **Comparación contra el baseline** (arreglo lineal uniforme) usando **el mismo hardware reconfigurado**.

---

## 3. Estado actual

> Resumen. La tabla detallada y autoritativa es [`CONTEXTO.md` §3.4](CONTEXTO.md#34-dónde-estamos-actualizar-conforme-avance); si difieren, manda `CONTEXTO.md`.

| Obj. | Qué | Estado | Dónde está el detalle |
|:--:|:--|:--|:--|
| 1 | Geometría bioinspirada no uniforme | 🟡 **Parcial**: 4 pares LR definidos; mics en **bases movibles** (la geometría se reconfigura por prueba sin reimprimir). Pendientes: la **forma final (collar)** y las medidas reales $d_1$–$d_4$ en `geometria.json` (hoy placeholders). | [`Documentation.md` §5](Avances/Documentation.md#5-archivo-geometriajson) |
| 2 | Dispositivo de adquisición | 🟢 **Cerrado**: electrónica en **PCB definitiva** (meta 5; sin cambios planeados por ahora): PCB de los ESP32-S3 + PCB acondicionada por micrófono, unidas por cables. 8 mics + SYNC estables en PC y Raspberry Pi 4/5, 0 underruns. | [`Documentation.md` §1–4, §10, §12](Avances/Documentation.md) |
| 3 | Base de datos habla / ruido | 🔴 No iniciado. Es la meta más larga de TT1 (10 semanas). | [`CONTEXTO.md` D6, D7](CONTEXTO.md#25-compromisos-de-diseño-fáciles-de-perder-de-vista) |
| 4 | Clasificador habla / ruido | 🔴 No iniciado (depende del Obj. 3). | — |
| 5 | DOA + beamforming | 🔴 No iniciado. Punto de inserción identificado: `hilo_sincronizador` en `monitor_8LR.py`. Depende de la geometría medida (Obj. 1). | [`Documentation.md` §6](Avances/Documentation.md#6-punto-de-extensión-das-beamforming) |
| 6 | Integración de módulos | 🔴 No iniciado (depende de 4 y 5). | — |
| 7 | Comparación vs. arreglo lineal uniforme | 🔴 No iniciado. | [`CONTEXTO.md` §4.1](CONTEXTO.md#41-beck-et-al-2016-como-referencia-externa) |
| 8 | Evaluación PESQ / STOI / SNR | 🔴 No iniciado (depende del Obj. 7). | — |

### Hitos

| Fecha | Hito | Referencia |
|:--|:--|:--|
| 18/05/2026 | Propuesta del TT | `PROTOCOLO_TT.pdf` |
| 26/06/2026 | Protocolo entregado y firmado | `PROTOCOLO_TT.pdf` |
| 06/09/2026 | **v0.1.0**: adquisición de 8 mics estable, tras reconstruir el sistema por etapas (causa raíz: baud compartido `Serial`/`Serial0`) | [`Documentation.md` §10](Avances/Documentation.md#10-reconstrucción-por-etapas-sept-2026) |
| 07/09/2026 | **v0.2.0**: despliegue en Raspberry Pi con autoarranque (systemd) y correcciones de sincronización | [`Documentation.md` §12](Avances/Documentation.md#12-despliegue-en-raspberry-pi-sept-2026) |
| 09/2026 | Alcance destilado del protocolo en `CONTEXTO.md`; Beck et al. (2016) verificado como referencia externa | [`CONTEXTO.md`](CONTEXTO.md) |
### Lo que sigue (ruta crítica)

1. **Medir la geometría real** ($d_1$–$d_4$) y registrarla en `Avances/geometria.json`, verificando que sea no lineal (D1). Es lo que desbloquea el DAS ([`CONTEXTO.md` R1](CONTEXTO.md#5-riesgos-conocidos)).
2. **Arrancar la base de datos** (Obj. 3): es la meta más larga de TT1 y bloquea al clasificador.
3. **Pregunta abierta:** ¿se mantiene la alineación temporal entre las dos ESP32-S3 a lo largo de una grabación larga? ([`CONTEXTO.md` R8](CONTEXTO.md#5-riesgos-conocidos)).

---

## 4. Mapa de documentación

Cada documento responde una pregunta distinta. Si dos se contradicen, gana el de más arriba:

| Nivel | Documento | Responde | Leer cuando… |
|:--:|:--|:--|:--|
| 1 | `PROTOCOLO_TT.pdf` *(no versionado)* | Lo comprometido ante la academia | Hay duda sobre el alcance oficial |
| 2 | [`CONTEXTO.md`](CONTEXTO.md) | **Qué** hay que construir, con qué criterios y en qué orden; compromiso vs. extensión; riesgos | **Antes de cualquier decisión de alcance** |
| 3 | [`Avances/Documentation.md`](Avances/Documentation.md) | **Cómo** está implementado el sistema oficial: hardware, protocolo serie, hilos, despliegue y bitácora | Se trabaja sobre el sistema de adquisición |
| 3 | READMEs de carpeta ([`Avances/`](Avances/README.md), [`Exploration/`](Exploration/README.md), [`SALIDAS/`](SALIDAS/README.md)) | Qué hay en cada carpeta y para qué sirve | Se busca un archivo |
| — | [`CHANGELOG.md`](CHANGELOG.md) | Qué cambió entre versiones | Se corta una versión o se busca cuándo cambió algo |
| — | [`CLAUDE.md`](CLAUDE.md) y [`.claude/agents/`](.claude/agents/) | Guía del repo para Claude Code y agentes del proyecto (`buscador`, `programador`, `redactor`) | Se trabaja con Claude Code |

---

## 5. Estructura del repositorio

```
.
├── README.md                 ← este archivo: qué es, qué será, cómo va
├── CONTEXTO.md               ← fuente de verdad de alcance (destila el protocolo)
├── CHANGELOG.md              ← historial de versiones
├── CLAUDE.md                 ← guía para Claude Code
├── requirements.txt
├── Avances/                  ← SISTEMA OFICIAL (validado)
│   ├── Documentation.md      ← documentación técnica y bitácora
│   ├── monitor_8LR.py        ← adquisición + sincronización + audio en vivo
│   ├── esp32_8micLR.txt      ← firmware Master/Slave (Arduino, renombrar a .ino)
│   ├── geometria.json        ← posiciones de los 8 mics (placeholders por ahora)
│   └── analisis.py, listar_audio.py, visualizar.py
├── Exploration/              ← PROTOTIPOS (no producción)
│   ├── reconstruccion_sept2026/  ← reconstrucción por etapas + diagnóstico de transporte
│   └── Primeros_intentos/        ← primeros prototipos (1–4 mics), históricos
├── SALIDAS/                  ← resultados generados (.npy, .png), no versionados
└── .claude/                  ← agentes y configuración compartida de Claude Code
```

---

## 6. Inicio rápido

### Entorno

```bash
python -m venv venv
venv\Scripts\activate            # Windows  (Linux/Pi: source venv/bin/activate)
pip install -r requirements.txt
```

El `venv` no se versiona: hay que crearlo en cada máquina.

### Adquisición en vivo (requiere hardware)

Conectar **ambos** ESP32-S3 por USB **antes** de arrancar:

```bash
python Avances/monitor_8LR.py                 # teclas: 1–4 par de mics · g grabar · q salir
```

Puertos (`ESP1_PORT`, `ESP2_PORT`), audio (`AUDIO_DEVICE_INDEX`, `SKIP_AUDIO`), modo demo (`AUTO_CYCLE_SECONDS`) y despliegue en Raspberry Pi: [`Documentation.md` §4 y §12](Avances/Documentation.md#4-arquitectura-python-monitor_8lrpy).

### Análisis offline de una grabación

Ajustar `ARCHIVO` y `MIC_ACTIVO` en `Avances/analisis.py` y correr `python Avances/analisis.py`.

---

## 7. Convenciones de trabajo

- **Compromiso antes que extensión.** Lo que está en el protocolo se cierra primero; lo demás solo refuerza ([`CONTEXTO.md` §0](CONTEXTO.md#0-regla-de-oro)).
- **`Exploration/` → `Avances/`.** Se prototipa en `Exploration/`; solo lo verificado se promueve a `Avances/`.
- **Resultados a `SALIDAS/`**, nunca a la raíz ni a `Avances/`.
- **Python + NumPy vectorizado**, sin loops de Python por muestra en tiempo real. La decisión de no usar Rust está en [`Documentation.md` §14.1](Avances/Documentation.md#141-python-vs-rust-vs-híbrido-sept-2026).
- **Commits** en español con prefijo convencional (`feat:`, `fix:`, `docs:`, `perf:`, `chore:`). El `CHANGELOG.md` se consolida al cortar cada versión.
- **Mantener sincronizados** `CONTEXTO.md` §3.4 y la tabla de la [§3](#3-estado-actual) de este README cuando cambie el estado de un objetivo.
