# 📝 Bitácora de Cambios del Proyecto (Ottoman Coach IA)

Este archivo sirve como cuaderno de notas compartido entre los distintos chats de desarrollo para mantenernos sincronizados y no pisar cambios.

---

## 📌 Regla simple:
1. **Antes de modificar código:** Pegale una leída rápida a los últimos cambios de este archivo para saber qué cosas nuevas hay en el proyecto.
2. **Al terminar un cambio o agregar una función:** Dejá un mensaje breve acá abajo (fecha, qué archivo tocaste y qué agregaste/cambiaste).

---

## 🕒 Historial de Cambios:

### [2026-11-10] - Sincronización Inicial
- Creación de esta bitácora compartida.
- Próximamente: Entrenamiento de modelos ligeros para emoción de voz, texto y reconocimiento de usuario.

### [2026-11-10] - Implementación Motor Animatrónico Teatral (Disney Style)
- **Archivos tocados:**
  - `mi_desarrollo/coach_emocional.py`: Nueva clase `RepertorioAnimatronicoG1` con 4 roles teatrales (Festejo, Contención, Pacificador, Sosiego) y coreografías de gran escala ($30^\circ\text{–}60^\circ$).
  - `mi_desarrollo/rostro_ottoman.py`: Implementado `SimuladorEmbebidoG1.fijar_coreografia` y `accion == "animacion"` para Show Action Sequencing (transiciones fluidas de poses).
  - `mi_desarrollo/demo_posturas_3d.py`: Añadidos botones de roles al visor para prueba interactiva en tiempo real.
- **Estado de tests:** 16/16 pruebas multimodales superadas (`evaluar_coach.py`) y 25/25 pruebas oficiales aprobadas al 100% (`mi_tp07.py`). Commit: `dca7145`.
- **Detalle de roles implementados:**
  - `MOTIVACION_ALEGRIA`: Compañero de festejo (apertura triunfal, señalamiento cómplice y brazos en V).
  - `TRISTEZA_DESANIMO`: Contenedor cálido (inclinación de torso +0.20 rad, mano al corazón, abrazo de contención, proxémica +0.25 m).
  - `ENOJO_FRUSTRACION`: Pacificador / Desescalada (paso atrás -0.25 m, palmas abiertas de frenado, postura estable de desescalada).
  - `ANSIEDAD_ESTRES`: Guía de respiración diafragmática (metrónomo corporal de inhalación/exhalación, brazos cadenciosos).
  - `DUDA_INSEGURIDAD` & `NEUTRO`: Poses de atención receptiva y calidez.

### [2026-11-10] - Movilidad Corporal Integral: Manos 6-DoF, Caderas, Piernas y Desarticulación Meme 6-7
- **Archivos tocados:**
  - `mi_desarrollo/coach_emocional.py`:
    - Arquetipos de manos diestras Inspire RH56 (6 DoF por mano): cascada anatómica relajada, mano al corazón empática, barrera de frenado pacificador, puño triunfal, señalamiento cómplice y apertura declamatoria.
    - Erradicación total de la postura meme "6-7" mediante arcos amplios 3D, rotación de muñecas (`pitch`, `roll`, `yaw`) y caída natural lateral de brazos.
    - Movilidad pélvica (*contrapposto*): basculación lateral (`waist_roll`) y torsión (`waist_yaw`), coordinados con caderas (`hip_roll`, `hip_pitch`).
    - Piernas vivas: microflexión basal de rodillas (`knee = 0.12 rad`) y tobillos (`ankle_pitch = -0.06 rad`), más posturas bipedales diferenciadas por rol (base enraizada en enojo, elevación/descenso rítmico respiratorio en calma).
    - Ampliación de `LIMITES_ARTICULARES` con los rangos físicos seguros de caderas, rodillas, tobillos y falanges de manos.
  - `mi_desarrollo/demo_posturas_3d.py`: Removido el bloqueo hardcodeado de piernas a 0.0 en el loop principal, permitiendo interpolación y movimiento libre del tren inferior. Activado auto-play de coreografía al iniciar y mapeados todos los botones de presets para disparar las coreografías teatrales. Añadido selector de cámara (Cuerpo Entero y Primer Plano de Manos/Torso).
  - `mi_desarrollo/rostro_ottoman.py`: Removido el forzado a 0.0 de piernas en modo `quieto`; conectada la cascada anatómica de dedos y microflexión de rodillas. Acelerada la interpolación lerp a 8.5 para transiciones vivas.
- **Estado de tests:** 16/16 pruebas multimodales superadas (`evaluar_coach.py`) y 25/25 pruebas oficiales aprobadas al 100% (`mi_tp07.py`). Commit: `e225e30`.

### [2026-11-10] - Cinemática Natural y Gravedad: Rodillas Flexionadas, Compensación de Centro de Masa y Palmas Neutras
- **Archivos tocados:**
  - `mi_desarrollo/coach_emocional.py`:
    - Eliminación de palmas hacia arriba como postura por defecto: rotación medial de muñeca (`left_wrist_roll: -1.25`, `right_wrist_roll: 1.25`) en reposo neutro y poses base para que las palmas miren naturalmente hacia los muslos y el cuerpo (desaparece el zombie/meme).
    - Flexión visible de rodillas ($0.32\text{–}0.52\text{ rad}$, $18^\circ\text{–}30^\circ$) con pitch compensatorio de cadera ($-0.16\text{ a }-0.26\text{ rad}$) y tobillos ($-0.16\text{ a }-0.26\text{ rad}$), otorgando postura atlética y dinámica.
    - Corrección física de inclinación en tristeza: se atenuó `waist_pitch` a $0.15\text{ rad}$ coordinado con cadera retrasada (`left_hip_pitch: -0.20`) y rodillas flexionadas, respetando el límite seguro del test (>0.10 rad) sin quebrar la gravedad.
  - `mi_desarrollo/demo_posturas_3d.py` y `mi_desarrollo/rostro_ottoman.py`:
    - Cinemática inversa simplificada de pelvis: cálculo dinámico de altura Z ($Z = 0.793 - 0.045 \times \text{knee}^2$) para que los pies queden siempre firmes sobre el piso al flexionar rodillas sin flotación.
    - Compensación de Centro de Masas (CoM) en el eje X: retroceso dinámico de pelvis ($X = -0.16 \times \text{waist\_pitch}$) cuando el torso se inclina hacia adelante, evitando la inclinación sobrenatural tipo voladizo.
    - Modos de cámara optimizados: añadido botón de primer plano `[ 🔍 Primer Plano (Manos/Torso) ]` y auto-arranque en `MOTIVACION_ALEGRIA`.
- **Estado de tests:** 16/16 pruebas multimodales superadas (`evaluar_coach.py`) y 25/25 pruebas oficiales aprobadas al 100% (`mi_tp07.py`).

