# Cómo funciona este proyecto (guía simple)

Esta guía explica **qué hace el código**, **por qué está armado así** y **cómo probarlo**, sin asumir que sabés de robots o de DDS.

Si solo querés correrlo ya, saltá a [Cómo probarlo](#cómo-probarlo).

---

## La idea en una frase

Le decís una de **8 palabras** en español argentino (por teclado o voz) y el robot **Ottoman** (Unitree G1) hace la **seña** correspondiente (aproximación de LSA).

```
palabra  →  se busca en un diccionario  →  se mueve el brazo y los dedos
```

---

## Las 8 palabras

| Palabra   | Idea de la seña (resumen)                          |
|-----------|----------------------------------------------------|
| `hola`    | Mano abierta cerca de la cabeza, saluda            |
| `gracias` | Mano hacia el mentón y “entrega” hacia adelante     |
| `chau`    | Brazo alto, mueve la muñeca (adios)                |
| `si`      | Puño que asiente (sube/baja)                       |
| `no`      | Solo el índice, niega de lado a lado               |
| `ayuda`   | Puño sobre la otra palma, las dos suben            |
| `agua`    | Forma tipo “W” cerca de la cara, dos toques        |
| `amigo`   | Las dos manos al centro, como enganchando índices  |

**Importante:** en el simulador las señas son **aproximaciones**. No son LSA perfecta (sobre todo mentón y forma W se ven mejor con zoom). En el robot real, los dedos los mueve la mano **Inspire** (5 dedos).

---

## Dos mundos: simulador vs robot real

| | Simulador (MuJoCo) | Robot real (Ottoman) |
|---|---|---|
| Dónde | En tu Mac, ventana 3D | En el lab, G1 físico |
| Para qué | Desarrollar y practicar | Demo / prueba con el profe |
| Dedos | Cápsulas articulares en el modelo | Mano Inspire vía red DDS |
| Comando típico | `--modo simulacion` o `--dataset` | `--modo real --interfaz eth0` |

El **mismo diccionario de palabras** se usa en los dos. Cambia solo **quién ejecuta el movimiento**.

---

## Cómo está organizado el código

Hay **dos carpetas** que te importan:

### 1) `mi_desarrollo/` — el TP “de siempre” + dataset

```
mi_desarrollo/
  mi_tp07.py              ← programa principal del alumno
  ejecutor.py             ← convierte la intención en movimiento
  vocabulario_dataset.py  ← las 8 palabras + alias (chau/adios, etc.)
  speech_to_text.py       ← micrófono → texto (modo --voz)
  robot.py                ← conexión con el simulador (no lo toques)
```

**Flujo cuando escribís `hola`:**

1. `mi_tp07.py` recibe el texto.
2. El clasificador dice: “esto es SENAS”.
3. El extractor saca la palabra (`hola`).
4. `ejecutor.py` busca `hola` en el diccionario de poses.
5. Manda una **secuencia de poses** (varios fotogramas) al robot/sim.
6. El sim anima brazo + dedos.

Pensalo como un **flipbook**: cada pose es un dibujo; al pasarlas rápido parece un gesto.

### 2) `tp07_lsa/` — capa limpia sim / real (Inspire)

```
tp07_lsa/
  main.py                          ← elegís --modo simulacion o real
  senas/diccionario.py             ← palabra → frames (brazo + manos)
  poses/mano.py                    ← 0=cerrado … 1=abierto (Inspire)
  poses/manos_dataset.py           ← forma de dedos por palabra
  poses/mujoco_dedos.py            ← pasa eso a ángulos del simulador
  simulador/ejecutor_pose.py       ← ejecuta en MuJoCo
  robot_real/ejecutor_pose_real.py ← ejecuta en el G1 real
  README.md                        ← detalles técnicos / supuestos
```

¿Por qué dos carpetas?  
`mi_desarrollo` es el TP original. `tp07_lsa` se agregó para poder hablarle al **robot real** sin romper lo que ya andaba en clase.

---

## Qué es una “pose”

Una pose es un diccionario de **ángulos de articulaciones**.

Ejemplo (simplificado):

```text
brazo:
  right_shoulder_pitch = -1.2
  right_elbow = -0.8
  ...

mano derecha (Inspire, 0 a 1):
  pinky=1, ring=1, middle=1, index=1, thumb=1   ← abierta
  pinky=0, ring=0, ...                          ← puño cerrado
```

- En el **sim**, esos números mueven joints de MuJoCo.
- En el **real**, los de la mano se mandan por red al topic `rt/inspire/cmd`.

Orden de dedos Inspire (oficial Unitree):  
`meñique, anular, medio, índice, pulgar (doblar), pulgar (rotar)`.

---

## Cómo probarlo

### A) Simulador + dataset (lo más usado)

**Terminal 1 — abrir el robot en 3D** (macOS necesita `mjpython`):

```bash
cd /Users/candel4/Ottoman_IA/IA-Ottoman_Act/UadeRobotLab-main/05LaboratoriosTPs/TP07_Inteligencia_Artificial/entorno
/Users/candel4/Library/Python/3.9/bin/mjpython -m sim --robot g1 --materia tp07
```

O:

```bash
cd .../TP07_Inteligencia_Artificial
./INICIAR_SIMULADOR.sh
```

(Elegí **1 = G1**. Dejá esa ventana abierta.)

**Terminal 2 — mandar las señas** (Cursor u otra terminal):

```bash
cd /Users/candel4/Ottoman_IA/IA-Ottoman_Act/UadeRobotLab-main/05LaboratoriosTPs/TP07_Inteligencia_Artificial
python3 mi_desarrollo/mi_tp07.py --dataset --demo
```

Eso recorre las 8 palabras solos.

Interactivo (vos escribís):

```bash
python3 mi_desarrollo/mi_tp07.py --dataset
```

Con micrófono (hace falta internet + `pip install -r mi_desarrollo/requirements-voz.txt`):

```bash
python3 mi_desarrollo/mi_tp07.py --dataset --voz
```

### B) Paquete `tp07_lsa` (sim o real)

```bash
cd .../TP07_Inteligencia_Artificial/tp07_lsa

# Simulación
python3 main.py --modo simulacion --demo

# Robot real (solo en el lab, Linux + red del G1)
python3 main.py --modo real --interfaz eth0 --demo
```

---

## Qué hace falta el día del robot real

1. Ottoman encendido, en la red del lab (`192.168.123.x`).
2. Notebook del lab en la misma red.
3. Interfaz Ethernet correcta (`eth0`, `enp0s31f6`, …).
4. SDK instalado:

```bash
pip install cyclonedds==0.10.2
git clone https://github.com/unitreerobotics/unitree_sdk2_python
pip install -e unitree_sdk2_python
```

5. Servicio de la mano Inspire corriendo en el robot (`inspire_g1` / `dfx_inspire_service`).  
   Sin eso, el cuerpo puede existir pero **los dedos no se mueven**.

Detalle y “supuestos a confirmar”: `tp07_lsa/README.md`.

---

## Por qué a veces “no se ve” el mentón o la W

- El simulador **no toca** la cara de verdad: solo acerca el brazo.
- Los dedos del sim son **cápsulas simples** (1 articulación), no una mano Inspire real.
- De lejos se pierde el detalle → usá zoom (rueda del mouse) y mirá de perfil.

En el robot físico con Inspire se va a notar mucho más la forma de la mano.

---

## Mapa mental rápido

```
          vos (texto o voz)
                 │
                 ▼
        mi_tp07.py / tp07_lsa/main.py
                 │
                 ▼
     diccionario de señas (poses)
                 │
        ┌────────┴────────┐
        ▼                 ▼
   simulador MuJoCo    G1 real + Inspire
   (ventana 3D)        (lab, DDS)
```

---

## Archivos que más vas a tocar si afinás señas

| Qué querés cambiar | Archivo |
|--------------------|---------|
| Movimiento de **brazo** | `mi_desarrollo/ejecutor.py` (keyframes) |
| Forma de **dedos** | `tp07_lsa/poses/manos_dataset.py` |
| Lista de **palabras** | `mi_desarrollo/vocabulario_dataset.py` |
| Conexión al robot **real** | `tp07_lsa/robot_real/ejecutor_pose_real.py` |

---

## Resumen para el informe / el profe

1. Entrada: 8 palabras (texto o voz `es-AR`).
2. Traducción: diccionario de poses LSA aproximadas.
3. Sim: MuJoCo G1 con manos articuladas.
4. Real: mismo pipeline, salida por DDS a mano Inspire.
5. Objetivo pedagógico: validar en sim y desplegar en Ottoman con el menor cambio posible (`--modo`).

Si algo no arranca, lo primero a chequear: **¿está abierto el simulador?** y **¿estás en la carpeta correcta?** (no uses `.../` literal; usá la ruta completa de arriba).
