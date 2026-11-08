# TP07 LSA — Ottoman (Unitree G1) + mano Inspire

Pipeline: **palabra** (8 del español argentino) → diccionario de poses
(brazo + 5 dedos) → ejecutor en **simulación MuJoCo** o **robot real**.

No reemplaza `mi_desarrollo/`: reusa `ejecutor.DICCIONARIO_SENAS` (brazos) y
suma control de la mano Inspire RH56.

## Vocabulario

`hola`, `gracias`, `chau`, `si`, `no`, `ayuda`, `agua`, `amigo`

## Estructura

```
tp07_lsa/
  poses/mano.py                 # helpers 0=cerrado .. 1=abierto
  senas/diccionario.py          # palabra -> frames {brazo, mano_*}
  simulador/ejecutor_pose.py    # MuJoCo (brazos) + log manos
  robot_real/ejecutor_pose_real.py  # DDS Inspire G1 real
  main.py
  requirements.txt
  README.md
```

## Modo simulación (default)

**Importante:** el modelo MuJoCo ahora tiene **12 joints de dedos** (cápsulas).
Hay que **cerrar y volver a abrir** el simulador para cargarlos.

1. Abrí el simulador G1 (en macOS con `mjpython`):

```bash
cd ../entorno
mjpython -m sim --robot g1 --materia tp07
```

2. En otra terminal:

```bash
cd ../tp07_lsa
python3 main.py --modo simulacion --demo
# o interactivo:
python3 main.py --modo simulacion
```

Sin MuJoCo abierto: `python3 main.py --modo simulacion --sin-robot --demo`
(solo imprime targets de mano).

El pipeline viejo sigue andando:

```bash
cd ../mi_desarrollo
python3 mi_tp07.py --dataset --demo
```

## Modo real (próxima clase)

### Qué hace falta el día de la prueba

1. G1 **Ottoman** encendido, en la red del lab (`192.168.123.x`).
2. Notebook Linux del lab en la misma red (IP típica documentada en el repo:
   `192.168.123.222`).
3. Interfaz Ethernet correcta (`eth0`, `enp0s31f6`, …). Ver con `ip link`.
4. SDK Python instalado (CycloneDDS **no** anda bien en macOS para el real):

```bash
pip install cyclonedds==0.10.2
git clone https://github.com/unitreerobotics/unitree_sdk2_python
pip install -e unitree_sdk2_python
```

También podés clonar en `UadeRobotLab-main/00SDK/unitree_sdk2_python` (hoy
está vacío en este checkout) y hacer `pip install -e` ahí.

5. **Servicio Inspire en el robot** (`dfx_inspire_service` / `inspire_g1`)
   corriendo. Sin eso, el topic `rt/inspire/cmd` no mueve la mano.
   Repo oficial: https://github.com/unitreerobotics/dfx_inspire_service

### Correr

```bash
cd tp07_lsa
python3 main.py --modo real --interfaz eth0 --demo
python3 main.py --modo real --interfaz eth0 --palabra hola
```

Si falla la conexión, el programa **imprime un mensaje claro** (robot apagado,
interfaz mala, SDK faltante) en vez de un traceback críptico.

## Qué revisamos en el repo UADE

| Tema | Hallazgo |
|------|----------|
| Conexión G1 real | `ChannelFactoryInitialize(0, interfaz)` + `LocoClient` en `02G1/.../g1_taller_alumnos.py` y `entorno/sim/robot.py` |
| Domain DDS | **0** = robot real; **1** = sim MuJoCo oficial |
| Interfaz tipica | `enp0s31f6`, `eth0`, `Ethernet` |
| Topics mano | **No hay** Inspire/Dex3 en este repo |
| SDK | `00SDK/unitree_sdk2_python` vacío; install = clone oficial + `cyclonedds==0.10.2` |
| Joints dedos | No existen en el modelo 29DoF; solo hasta muñeca |

## Supuestos a confirmar (marcados en el código)

1. Topic de comando: `rt/inspire/cmd` (`MotorCmds_`, unitree_go) — docs
   Unitree / dfx_inspire_service; **no aparece en el repo del lab**.
2. Índices 0–5 = mano derecha, 6–11 = izquierda.
3. Orden por mano: `pinky, ring, middle, index, thumb_bend, thumb_rotation`.
4. `q`: **1.0 = abierto, 0.0 = cerrado** (labels open/close del servicio).
5. Interfaz default del módulo real: `enp0s31f6` (igual que el taller G1);
   el día de clase se pasa `--interfaz ...` si hace falta.
6. Hace falta el bridge serial→DDS (`inspire_g1`) en el robot.

Si algo no coincide en la prueba: editá el diccionario
`MAPEO_DEDOS_DERECHA` / `MAPEO_DEDOS_IZQUIERDA` en
`robot_real/ejecutor_pose_real.py` (está comentado a propósito).

## Firma unificada

```python
ejecutor_pose(pose)  # pose = frame o lista de frames
# frame = {
#   "brazo": {"right_shoulder_pitch": ..., ...},
#   "mano_derecha": {"pinky": 1.0, "ring": 1.0, ...},
#   "mano_izquierda": {...},
# }
```

Simulación y real comparten el mismo `senas/diccionario.py`.
