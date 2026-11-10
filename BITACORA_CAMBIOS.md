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

### [2026-11-10] - Expresividad Corporal 3D Completa y Gesticulación Co-Verbal (G1)
- **Archivos tocados:**
  - `mi_desarrollo/coach_emocional.py`: Eliminadas poses heredadas con codos invertidos; postura canónica relajada (`shoulder_pitch: 0.42`, `elbow: 0.28`); nuevo método continuo `CoreografoPosturalG1.generar_postura_continua(valencia, arousal, ...)`.
  - `mi_desarrollo/rostro_ottoman.py`: `SimuladorEmbebidoG1` modula a 35 FPS en hilo principal el movimiento corporal completo según $(V, A)$; incorpora *Idle Breathing* diafragmático en reposo (0.25 Hz), *Co-speech Beat Gestures* rítmicos al hablar (Lecoq Center-out + McNeill) y sincronización con `actualizar_estado` y `set_hablando`.
  - `mi_desarrollo/demo_posturas_3d.py`: Demo interactiva standalone actualizada con sliders continuos de Valencia y Arousal, selector de cadencia gestual y telemetría en vivo (`PROBAR_POSTURA_3D.bat`).
  - `mi_desarrollo/evaluar_coach.py`: Agregada verificación exhaustiva de límites articulares sobre malla continua de 1.620 combinaciones $(V, A, t)$.
- **Estado de tests:** 25/25 en TP07 (100%) y 16/16 en multimodal (100%). Commit: `a71587c` en `franco/ottoman-coach`.
