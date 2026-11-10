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

### [2026-11-10] - Síntesis de Voz Neuronal Humana (Edge-TTS Tomás), Nueva Base Ágil y Acentuación Rioplatense
- **Archivos tocados:**
  - `mi_desarrollo/coach_emocional.py`:
    - Migración del motor de audio primario en `SintetizadorVozAdaptativo.hablar_sincronizado`: reemplazado el sintetizador robótico SAPI5 (`pyttsx3`) por voz neuronal de Deep Learning argentina `es-AR-TomasNeural` (`edge-tts`) con conversión transparente PCM vía `ffmpeg`.
    - Conservado `pyttsx3` como fallback offline automático ante cortes de conexión o fallas de red en presentaciones.
    - Implementada la **nueva base acústica ágil y despierta** (`+8%` velocidad, `+3 Hz` tono fundamental, piso mínimo en `+3%`), erradicando el arrastre de vocales y la monotonía.
    - Nueva función `enriquecer_texto_prosodico`: inyección de comas de apoyo rítmico, signos dobles en aperturas y cierres coloquiales (`¡Mirá!,`, `¡¿dale?!`) y garantía de tildes ortográficas en verbos del voseo (*tenés*, *estás*, *mirá*, *respirá*, *hacé*), logrando la acentuación tónica viva validada en la Prueba 3.
    - Síntesis por bloques dinámicos: segmentación automática de respuestas bimodales (bloque 1 contención suave $\rightarrow$ silencio respiratorio de $420\text{ ms}$ $\rightarrow$ bloque 2 acción y empuje resolutivo pleno).
    - Nueva función estática `SintetizadorVozAdaptativo.aplicar_dsp_estudio`: mastering acústico con realce cálido de pecho ($200\text{--}450\text{ Hz}$), de-essing suave ($>6800\text{ Hz}$) y micro-reverberación de sala física ($18\text{ ms}, 31\text{ ms}, 46\text{ ms}$) para eliminar el vacío anecoico.
- **Estado de tests:** 16/16 pruebas multimodales superadas (`evaluar_coach.py`) y 25/25 pruebas oficiales aprobadas al 100% (`mi_tp07.py`). Verificación en vivo completada exitosamente.

### [2026-11-10] - Catálogo Multivariante de Emotes, Fin de Bucle 3D, STT Humano y Memoria Anti-Repetición
- **Archivos tocados:**
  - `mi_desarrollo/coach_emocional.py`:
    - Incorporación de catálogo de **2 a 3 variantes de emotes teatrales por estado emocional**: Alegría (Victoria / Apertura cálida / Complicidad aliento), Tristeza (Contención íntima / Acogida apoyo / Acompañamiento silencioso), Enojo (Barrera freno / Escucha aplomo / Canalización tierra), Ansiedad (Metrónomo respiratorio 4-4 / Grounding a tierra / Pausa sosiego), Duda (Balanza socrática / Indagación reflexiva) y Neutro (Atención izquierda / derecha / Escucha abierta).
    - Rotación dinámica sin repetición inmediata o por intensidad en `CoreografoPosturalG1.obtener_coreografia`.
    - Detección explícita de bloqueos reflexivos ("no sé qué decirte", "me quedé en blanco", "no sé") con respuesta cálida descompresiva.
    - Ampliación de plantillas de 3 a 6 por emoción con filtro activo anti-repetición en historial de chat.
  - `mi_desarrollo/rostro_ottoman.py`:
    - Fin del bucle infinito de animación: la coreografía se ejecuta una única vez a lo largo de su arco y transiciona limpiamente a `quieto` o gesticulación de habla viva (`hablando`).
    - Posturas base con palmas hacia el cuerpo (`left_wrist_roll: -1.25`, `right_wrist_roll: 1.25`) por defecto.
  - `mi_desarrollo/demo_posturas_3d.py`:
    - Transición a reposo continuo al finalizar la coreografía en vez de ciclar en loop. Cada clic sobre el botón de emoción dispara una variante distinta del catálogo.
  - `mi_desarrollo/speech_to_text.py`:
    - Calibración humana de escucha: `pause_threshold = 2.0s` (no te corta al respirar o pensar), `phrase_time_limit = 40s` (permite desahogos largos) y `non_speaking_duration = 0.8s`.
  - `mi_desarrollo/percepcion_multimodal.py`:
    - Patrones léxicos para expresiones de bloqueo y vacilación en `DUDA_INSEGURIDAD`.
- **Estado de tests:** 16/16 pruebas multimodales superadas (`evaluar_coach.py`) y 25/25 pruebas oficiales aprobadas al 100% (`mi_tp07.py`).

### [2026-11-10] - Rediseño Minimalista del Rostro Ottoman (Estilo EVE / Cozmo)
- **Archivos tocados:**
  - `mi_desarrollo/rostro_ottoman.py`:
    - Eliminación total de rasgos antropomórficos artificiales: boca con ecualizador de líneas y cejas rectas.
    - Implementación de nueva morfología de robot humanoide: chasis aerodinámico blanco/gris estilo Unitree G1, orejeras laterales de sensores auditivos y visor curvado OLED en cristal negro profundo (`#050811`) con bisel metálico y reflejo especular curvo.
    - Foco exclusivo en **Ojos LED Gigantes**: se eliminó la carcasa/orejeras exteriores a pedido del usuario para dar protagonismo total a los ojos sobre una pantalla OLED curva completa de 410x356 px, duplicando las dimensiones de los ojos (~74x118 px) para máxima legibilidad, presencia e impacto visual.
    - Ojos LED puros basados en la hoja de 7 expresiones de referencia: cápsulas neutras, arcos sonrientes `^ ^` (`MOTIVACION_ALEGRIA`), corte diagonal firme `\ /` (`ENOJO_FRUSTRACION`), mirada caída empática `/ \` (`TRISTEZA_DESANIMO`), guiño asimétrico inquisitivo (`DUDA_INSEGURIDAD`) y ojos relajados de co-regulación (`ANSIEDAD_ESTRES`).
    - *Voice Pulse*: modulación acústica en tiempo real (escala y resplandor de los ojos) mientras habla el TTS neuronal en lugar de una boca humana.
    - Co-regulación respiratoria integrada: dilatación y contracción cadenciosa del visor y los ojos en ciclos de 8s (4s inhalación / 4s exhalación).
    - **Corrección de error crítico de Tkinter (`TclError: unknown option "-capstyle"`):** al pasar a `MOTIVACION_ALEGRIA`, `canvas.create_arc` fallaba porque Tkinter no soporta `capstyle` en arcos nativos, interrumpiendo el bucle gráfico y dejando el panel derecho vacío. Se reemplazó por un spline poligonal suavizado `canvas.create_line(*pts, smooth=True, capstyle="round")` y se blindó el renderizador con `try...finally` para asegurar que el tick nunca se detenga.
    - Actualizada la función `exportar_captura_dashboard_png` para generar las vistas previas de alta resolución con el nuevo diseño.
  - `docs/graficos/ottoman_faces_preview.png`: Hoja de referencia con las 7 expresiones renderizadas en alta resolución con ojos gigantes.
  - `docs/graficos/dashboard_preview.png`: Captura completa del Dashboard unificado actualizada con el visor OLED y ojos gigantes.
- **Estado de tests:** 16/16 pruebas multimodales superadas (`evaluar_coach.py`) y 25/25 pruebas oficiales aprobadas al 100% (`mi_tp07.py`).

### [2026-11-10] - Personalidad Sonora de Caricatura Definitiva: General Infantil (Megáfono de Juguete con Eco Teatral)
- **Archivos tocados:**
  - `mi_desarrollo/coach_emocional.py`:
    - Adopción definitiva de la personalidad de caricatura **"General Infantil"** (pitch agudo $+20\text{ Hz}$, cadencia ágil $+14\%$) inspirada en el arquetipo cómico de dictador diminuto / villano de juguete (estilo Plankton / Marvin el Marciano).
    - Cadena DSP `SintetizadorVozAdaptativo.aplicar_dsp_estudio` actualizada:
      1. Filtro pasa-banda de megáfono militar ajustado a chasis diminuto ($650\text{--}4350\text{ Hz}$).
      2. Saturación crujiente de cono de plástico/papel al límite (hard clipping $1.55\times$).
      3. Reverberación teatral en cascada de sala de ópera/catedral ($45\text{ ms}$, $90\text{ ms}$, $140\text{ ms}$ y $210\text{ ms}$).
    - Mapeo continuo adaptativo en `hablar_sincronizado`: estabilizado el anclaje del personaje para eliminar cambios bruscos entre emociones; el tono se modula de forma suave y cohesiva en una banda estrecha ($+18\text{ Hz}$ en calma/contención hasta $+22\text{ Hz}$ en euforia, velocidad $+12\%\text{ a }+16\%$), preservando su identidad cómica constante y la sincronización con el *Voice Pulse* del visor OLED.
- **Estado de tests:** 16/16 pruebas multimodales superadas (`evaluar_coach.py`) y 25/25 pruebas oficiales aprobadas al 100% (`mi_tp07.py`). Verificación en vivo completada exitosamente.

### [2026-11-10] - Inicio Rápido y Limpio de Ottoman (Tabla de Tests Optativa)
- **Archivos tocados:**
  - `mi_desarrollo/mi_tp07.py`:
    - Se agregó el flag de línea de comandos `--evaluar` para correr la tabla de los 25 casos de prueba oficiales de forma explícita.
    - El inicio interactivo por defecto (`INICIAR_OTTOMAN.bat` o `python mi_tp07.py --ml`) ya no imprime la tabla de los 25 casos en la terminal, arrancando inmediatamente a la experiencia limpia del agente.
  - `EJECUTAR_MI_CODIGO.bat`:
    - Mantiene el paso de `--evaluar` para preservar el comportamiento histórico de corrección académica exigido por la cátedra.
- **Estado de tests:** 16/16 pruebas multimodales superadas (`evaluar_coach.py`) y 25/25 pruebas oficiales aprobadas al 100% (`mi_tp07.py --sin-robot`).

