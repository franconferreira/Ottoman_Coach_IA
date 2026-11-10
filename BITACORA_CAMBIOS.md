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
