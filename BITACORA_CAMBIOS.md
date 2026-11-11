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

### [2026-11-10] - Personalidad Jovial/Limpia, Coaching Proactivo, Memoria de Nombre y Filtro Antirrechazos
- **Archivos tocados:**
  - `mi_desarrollo/coach_emocional.py`:
    - Renovación total de plantillas CBR en las 6 emociones (`PERFILES_BASE`): rediseño casual, jovial y cálido con voseo rioplatense natural, erradicando formalismos acartonados y jerga pesada caricaturesca (*"fiera"*, *"la pucha"*, *"patatús"*, *"rosca mental"*).
    - Nueva arquitectura de coaching proactivo de 3 pasos: [Espejo Biométrico/Observación] $\rightarrow$ [Interrupción/Desafío positivo] $\rightarrow$ [Micro-compromiso accionable].
    - Implementación de memoria de identidad y nombre de usuario (`self.nombre_usuario`): captura presentaciones (*"me llamo X"*, *"mi nombre es X"*) y responde a preguntas de identidad (*"¿cómo me llamo?"*). Erradicación total del bug donde el robot asumía que el usuario se llamaba Ottoman.
    - Nuevo filtro detector de rechazos `_es_rechazo_invalido_llm`: neutraliza las negativas absurdas de modelos locales (*"no puedo ayudarte con eso"*, *"situaciones de libre voluntad"*), descartando la alucinación del LLM y activando de inmediato el fallback a plantillas CBR de coaching de alta calidad.
    - Blindaje del System Prompt para LLMs locales y en la nube: directivas explícitas de rol, prohibición de negarse ante el enojo y preservación estricta de identidades.
  - `mi_desarrollo/mi_tp07.py`:
    - Ampliación de `PATRON_CONVERSACIONAL` con expresiones de presentación y charla (*"hablame de vos"*, *"contame de vos"*, *"sobre vos"*, *"me llamo"*, *"cómo me llamo"*).
    - Priorización conversacional en `ClasificadorIntencion`: frases de diálogo verbal como *"Hola, hablame de vos"* ahora se enrutan correctamente a `COACH_EMOCIONAL` en vez de disparar el gesto motor físico `SALUDO` (`✅ saludo`).
- **Estado de tests:** 16/16 pruebas multimodales superadas (`evaluar_coach.py`), 25/25 pruebas oficiales aprobadas al 100% (`mi_tp07.py --sin-robot --evaluar`) y 6/6 tests de diálogo y memoria aprobados (`verificar_dialogo_coach.py`).

### [2026-11-10] - Coreografía Facial Dinámica, Micro-expresiones Vivas y Glifos Heroicos (!) y (?)
- **Archivos tocados:**
  - `mi_desarrollo/rostro_ottoman.py`:
    - Eliminación de la línea curva especular de cristal: pantalla OLED 100% limpia y pura en negro profundo (`#050811`).
    - `ojo_circular_asombro` ampliado con radio aumentado a ~68% de escala para un asombro más expresivo.
    - `suave_calma` renovado con líneas zen que tienen la parte elevada al medio (`/ \`) en ambos ojos (párpados relajados de meditación).
    - Eliminación de `asimetrico_duda` unificando el estado de análisis e introspección en `entrecerrado_enfoque`.
    - Incorporación de renderizado nativo de Glifos Heroicos `!` y `?` (sin paréntesis) como un único símbolo gigante centrado en el medio del visor OLED (~135 pt) con reactividad y pulso de voz.
    - Motor de interpolación temporal y micro-expresiones dinámicas (`disparar_micro_expresion` / `disparar_glifo`) con desvanecimiento orgánico a la pose base.
    - Sistema *Idle Life* con micro-sacadas oculares estocásticas de atención foveal (cada 1.8-3.8s) y doble pestañeo humanoide.
  - `mi_desarrollo/coach_emocional.py`:
    - Implementación de `PlanificadorCoreografiaFacial` y `EventoMicroExpresion`: parser sintáctico-prosódico que segmenta el discurso de Ottoman por signos de puntuación (`¡!`, `¿?`, `,`, `.`), velocidad WPM y marcadores discursivos, generando una línea de tiempo sincronizada.
    - Despachador asíncrono en `SintetizadorVozAdaptativo.hablar_sincronizado`: sincroniza la emisión acústica neuronal/DSP con las transiciones gestuales de los ojos en tiempo real.
  - `mi_desarrollo/ejecutor.py` y `mi_desarrollo/mi_tp07.py`:
    - Vinculación reactiva del glifo `?` ante instrucciones fuera de dominio (`DESCONOCIDO`).
    - Vinculación reactiva del glifo `!` ante bloqueos de seguridad y paradas de emergencia (`DETENERSE`).
  - `docs/graficos/ottoman_faces_preview.png`:
    - Nueva lámina técnica 3x4 con las 12 expresiones, glifos heroicos y pestañeo electrónico.
- **Estado de tests:** 16/16 pruebas multimodales superadas (`evaluar_coach.py`) y 25/25 pruebas oficiales aprobadas al 100% (`mi_tp07.py --sin-robot --evaluar`).

### [2026-11-10] - Simulación 3D Viva en Reposo y Desambiguación de Charla en 1ª Persona ("Salir a caminar")
- **Archivos tocados:**
  - `mi_desarrollo/rostro_ottoman.py`:
    - Erradicación de la congelación visual en reposo (`quieto`):
      - Respiración diafragmática y torácica amplificada a valores plenamente visibles (amplitud de torso a $0.038\text{ rad} \approx 2.2^\circ$, hombros $0.028\text{ rad}$, codos $0.022\text{ rad}$ y muñecas $0.040\text{ rad}$).
      - Balanceo postural pendular orgánico (*postural sway* de período lento $\sim 6.5\text{s}$) en pelvis: inclinación lateral `waist_roll` ($\pm 0.022\text{ rad}$) y rotación `waist_yaw` ($\pm 0.014\text{ rad}$).
      - *Contrapposto* dinámico con transferencia de peso en piernas: alternancia fluida de flexión de rodillas ($0.278 \leftrightarrow 0.362\text{ rad}$) y caderas, manteniendo los pies firmes y el centro de masa compensado en altura (`knee_avg`).
      - Manos Inspire RH56 con micro-movimientos cadenciosos de relajación en falanges ($0.05 \leftrightarrow 0.15$) al ritmo del aire.
  - `mi_desarrollo/coach_emocional.py`:
    - Sincronización de `CoreografoPosturalG1.generar_postura_continua` con las mismas dinámicas de respiración y sway postural vivo.
    - Nuevo manejador conversacional en `_responder_conversacion_basica` para actividades de esparcimiento, caminata y bienestar ("salir a caminar", "caminar un rato", "dar una vuelta", "despejarme"), respondiendo con aliento motivacional en lugar de silencio o comandos mecánicos.
  - `mi_desarrollo/mi_tp07.py`:
    - Incorporación de `PATRON_DESAMBIGUACION_CHARLA` en `ClasificadorIntencion`: intercepta y enruta a `COACH_EMOCIONAL` expresiones en primera persona ("me gustaría...", "quiero...", "estaba pensando en..."), planes personales ("salir a caminar", "ir a caminar", "caminar un rato", "dar una vuelta") y metáforas reflexivas ("avanzar en mi...", "dar vueltas con...").
    - `PATRON_MOVER` ajustado para exigir contexto directivo/imperativo para infinitivos (`caminá hacia adelante`, `caminar 2 metros`), evitando que palabras sueltas como "caminar" en medio de una charla activen los motores del robot.
- **Estado de tests:** 16/16 pruebas multimodales superadas (`evaluar_coach.py`) y 25/25 pruebas oficiales aprobadas al 100% (`mi_tp07.py --sin-robot`). Verificación de desambiguación completada exitosamente.

### [2026-11-10] - Erradicación Definitiva de Vocativo "Ottoman" y Enrutamiento de Apertura "Hablame"
- **Archivos tocados:**
  - `mi_desarrollo/coach_emocional.py`:
    - Ampliado `_responder_conversacion_basica` para capturar aperturas directas de charla como `"Hablame"`, `"Hablame un poco"`, `"Charlame"` y `"Contame algo"`, respondiendo con la presentación oficial y cálida de Ottoman de forma inmediata sin caer a alucinaciones de LLM.
    - Saneamiento estricto post-generación de LLM en `_consultar_llm_local_gguf`: erradicación de vocativos donde el modelo añade `", Ottoman"` o `"Ottoman,"` al final de sus oraciones.
    - Nuevo filtro estricto en `_es_rechazo_invalido_llm`: cualquier respuesta que aún contenga la palabra *"Ottoman"* sin ser una autopresentación en primera persona (*"Soy Ottoman"*, *"Me llamo Ottoman"*) es automáticamente rechazada y sustituida por las plantillas CBR joviales de alta calidad.
    - Reescritura del system prompt para no cebar el token "Ottoman" como nombre del interlocutor humano.
- **Estado de tests:** 16/16 pruebas multimodales superadas (`evaluar_coach.py`), 25/25 pruebas oficiales aprobadas al 100% (`mi_tp07.py --sin-robot --evaluar`) y 7/7 tests de diálogo, identidad y apertura aprobados (`verificar_dialogo_coach.py`).

### [2026-11-10] - Identidad LED Unificada (Azul Signature Permanente), Fidelidad Geométrica 1:1 en GUI y Barra de Chips de Expresión
- **Archivos tocados:**
  - `mi_desarrollo/rostro_ottoman.py`:
    - **Color LED unificado permanente:** Se fijó `color_rgb=(56, 189, 248)` (`#38BDF8`, el azul cian original de Ottoman) para la totalidad de los presets en `PRESETS_ROSTRO`, eliminando los cambios de tinte cromático y preservando la expresividad puramente morfológica (estilo EVE / Astro Bot).
    - **Ampliación de presets faciales directos:** Se añadieron a `PRESETS_ROSTRO` las claves `"ASOMBRO"` (ojos circulares gigantes), `"EUREKA"` (estrellas de 4 puntas), `"ALERTA"` (glifo heroico central `!`), `"PREGUNTA"` (glifo heroico central `?`), `"ENFOQUE"` (ojos entrecerrados analíticos) y `"CALMA"` (líneas serenas elevadas al medio `/ \`).
    - **Geometría 1:1 en Tkinter Canvas:**
      - `capsula`: dibujado con `create_line(..., width=2*rx, capstyle="round")`, logrando la forma de cápsula/píldora con laterales perfectamente rectos y tapas semicirculares idéntica al vector, en lugar del óvalo deformado de `create_oval`.
      - `chispa_estrella`: removido `smooth=True` para preservar los vértices afilados y diamantinos de la estrella de 4 puntas.
      - `diagonal_enojo` y `caido_triste`: removido `smooth=True` para mantener cortes angulares limpios sin deformación en manchas redondeadas.
      - `ojo_circular_asombro`: radio escalado y acotado para un impacto visual máximo sin solapamiento entre ojos.
      - `suave_calma`: geometría zen `/ \` con el centro elevado y los extremos exteriores descendentes.
      - `entrecerrado_enfoque`: renderizado como ranura/cápsula horizontal pura.
    - **Barra interactiva de chips de expresión (`frame_caras`):** agregada barra con 10 botones rápidos (`[😐 Neutro]`, `[😊 Sonrisa]`, `[✨ Eureka]`, `[😮 Asombro]`, `[❗ Alerta]`, `[❓ Pregunta]`, `[🧘 Calma]`, `[🔍 Enfoque]`, `[😠 Firme]`, `[🥺 Empatía]`) para probar e intercambiar cualquier rostro al instante en el visor OLED durante la ejecución.
  - `docs/graficos/ottoman_faces_preview.png`:
    - Lámina técnica regenerada con las 11 expresiones y glifos heroicos unificados al 100% en el azul signature `#38BDF8`.
  - `docs/graficos/dashboard_preview.png`:
    - Captura completa del Dashboard actualizada con el visor y ojos en azul `#38BDF8`.
- **Estado de tests:** 16/16 pruebas multimodales superadas (`evaluar_coach.py`) y 25/25 pruebas oficiales aprobadas al 100% (`mi_tp07.py --ml --sin-robot --evaluar`).

### [2026-11-10] - Avance Fase 1 y 2: Pipeline de ML Multimodal (Extractor Acústico, NLP y Dataset de Control)
- **Archivos creados:**
  - `mi_desarrollo/extractor_acustico.py`: Extractor matemático de 34 features acústicos (Pitch F0 por autocorrelación, RMS, ataque de energía, pausas, WPM, ZCR, centroide espectral y 13 MFCCs + deltas) con `scipy` y `numpy`.
  - `mi_desarrollo/dataset_emociones_texto.csv`: Dataset curado de 150 frases rioplatenses deportivas y afectivas (Enojo, Cansancio, Motivado, Ansiedad, Neutro).
  - `mi_desarrollo/generar_voces_control.py`: Generador de 25 muestras de control de locutores de contraste (`invitado_*.wav` hombres y mujeres en `datos/audio/invitado/`) para biometría de locutor.
  - `mi_desarrollo/grabar_dataset_voz.py`: Grabador interactivo guiado por terminal con frases sugeridas y cuenta regresiva para la captura de audios del usuario en `datos/audio/franco/`.
  - `mi_desarrollo/entrenar_modelos.py`: Pipeline maestro con 5-fold Stratified Cross-Validation, matrices de confusión en PNG y exportación a `.joblib`.
### [2026-11-11] - Integración Plena de los 3 Modelos de Machine Learning (SER, Locutor y NLP)
- **Dataset Acústico Completo:**
  - Grabadas 100 muestras reales del usuario (20 para cada una de las 5 emociones: Neutro, Motivado, Cansancio, Enojo, Ansiedad).
  - Aplicada normalización de pico de ganancia al 85% (-1.4 dBFS) preservando armónicos y dinámica natural sin ruido.
  - Generadas 25 muestras de control de locutores externos masculinos y femeninos en `datos/audio/invitado/`.
- **Modelos Entrenados y Evaluados (Stratified Cross-Validation):**
  - `clasificador_locutor.joblib` (SVM RBF): Reconocimiento biométrico Franco vs. Invitado (**100% Accuracy / F1=1.0**).
  - `clasificador_emocion_voz.joblib` (Random Forest): Reconocimiento de emoción acústica pura (**77% F1-score multiclase** en validación cruzada).
  - `clasificador_emocion_texto.joblib` (MLP Classifier) + `vectorizador_texto.joblib`: NLP emocional (>90% confianza en frases rioplatenses).
  - Matrices de confusión guardadas en `mi_desarrollo/modelos/*.png` y métricas en `metricas_clasificadores.json`.
- **Integración Multimodal:**
  - `mi_desarrollo/percepcion_multimodal.py`: Conectada la inferencia de los 3 modelos con vector de 34 features en `AnalizadorAcusticoVoz.analizar_pcm` y `AnalizadorLexicoAfectivo.analizar`.
  - `mi_desarrollo/speech_to_text.py`: Feedback en consola mostrando el locutor detectado y porcentaje de certeza biométrica.
- **Estado de tests:** 16/16 pruebas multimodales superadas (`evaluar_coach.py`) y 25/25 pruebas oficiales aprobadas al 100% (`mi_tp07.py --ml --sin-robot --evaluar`).

### [2026-11-11] - Rotación de Caído Triste con Lados Centrales Paralelos (Giro Inverso)
- **Archivos tocados:**
  - `mi_desarrollo/rostro_ottoman.py`:
    - En la morfología `caido_triste` (usada en `TRISTEZA_DESANIMO` y el chip rápido `[🥺 Empatía]`), se rotaron los ojos en dirección contraria al giro de 90° previo hasta que los lados de los trapezoides ubicados en el centro queden **completamente verticales y paralelos entre sí**:
      - Ángulo de corte calculado: $\theta = \arctan(d_{\text{caida}} / r_x)$.
      - Ojo izquierdo: rotado por $\alpha = 90^\circ - \theta$ (en sentido horario, equivalente a retroceder $\theta$ en sentido antihorario desde la posición previa de 90°).
      - Ojo derecho: rotado por $-\alpha = -(90^\circ - \theta)$ (en sentido antihorario, equivalente a retroceder $\theta$ en sentido horario).
      - Como resultado, las coordenadas $X$ de los dos vértices que forman el lado interior de cada trapezoide coinciden exactamente ($\Delta X = 0$), garantizando paralelismo absoluto y simetría especular.
  - `docs/graficos/ottoman_faces_preview.png` y `docs/graficos/dashboard_preview.png`:
    - Regeneradas las láminas técnicas oficiales reflejando los lados centrales perfectamente paralelos.
- **Estado de tests:** 16/16 pruebas multimodales superadas (`evaluar_coach.py`) y 25/25 pruebas oficiales aprobadas al 100% (`mi_tp07.py --ml --sin-robot --evaluar`).

### [2026-11-11] - Erradicación de Charla Técnica y Métricas Acústicas en Diálogo Humano (Cero Decibeles / Hz)
- **Archivos tocados:**
  - `mi_desarrollo/percepcion_multimodal.py`:
    - Eliminado el formateo numérico de laboratorio en `detalle_incongruencia` (`voz ({acu.rapidez_wpm:.0f} ppm, {acu.volumen_db:.1f} dB, {acu.tono_f0_hz:.0f} Hz)`).
    - Reemplazado por observaciones cualitativas, empáticas y humanas (`señales_humanas`): *"el tono de voz bastante apagado"*, *"la mirada un poco decaída"*, *"la voz algo acelerada"*, *"cierta tensión en el rostro"*.
    - El prefijo ante incongruencia ahora es cálido y natural: *"Me decís que estás bien, pero te noto la mirada un poco decaída y el tono de voz bastante apagado. No hace falta disimular conmigo."*
  - `mi_desarrollo/coach_emocional.py`:
    - `_construir_contexto_sensorial`: transformado para inyectar descripciones perceptivas cualitativas al LLM en lugar de valores numéricos de telemetría (se eliminaron los números en bruto de Hz, dB y ppm).
    - Prohibición estricta en el System Prompt de LLMs locales y de nube: directiva explícita prohibiendo terminología técnica de laboratorio (decibeles, hercios, Hz, biometría, sensores, frecuencias) y exigiendo hablar como un amigo o tutor empático.
    - Filtro detector `_es_rechazo_invalido_llm`: incorporado patrón de rechazo ante filtración de términos de laboratorio (`decibel`, `hercio`, `\bhz\b`, `f0`, `ppm`, `wpm`, `facs`, `sensores detectan`), descartando cualquier alucinación técnica para recurrir inmediatamente a las plantillas CBR cálidas y joviales.
    - `_responder_conversacion_basica`: eliminado *"sensores activos"* de la respuesta social cotidiana, reemplazado por *"Con toda la energía para darte una mano"*.
- **Estado de tests:** 16/16 pruebas multimodales superadas (`evaluar_coach.py`), 25/25 pruebas oficiales aprobadas al 100% (`mi_tp07.py --sin-robot --evaluar`) y 7/7 tests de diálogo, incongruencia y vocabulario aprobados (`verificar_dialogo_coach.py`).

### [2026-11-11] - Erradicación de Cara Ficticia y Modo Offline Fiel en Panel FACS (Cero Datos Simulados)
- **Archivos tocados:**
  - `mi_desarrollo/rostro_ottoman.py`:
    - Eliminado por completo el dibujo vectorial de rostro artificial (óvalos de ojos, cejas y boca) que se renderizaba en el panel superior derecho cuando no había webcam.
    - Implementado estado **CÁMARA OFFLINE**: chasis técnico de cámara con barra diagonal roja indicando falta de señal de video USB y mensaje instructivo.
    - Cuando la cámara está activa pero no ve a nadie, muestra el video real con el badge `BUSCANDO ROSTRO EN ESCENA...`.
    - **Barras FACS en reposo/offline**: si no hay un rostro real detectado por OpenCV en el video, las barras `AU1/5 Ojos`, `AU4 Cejas`, `AU12 Sonrisa` y `AU25 Boca` muestran el sufijo `[--]`, fondo oscuro inactivo y 0% de llenado (sin barras de color inventadas).
  - `mi_desarrollo/ejecutor.py`:
    - Erradicada la proyección matemática sintética en `_metricas_faciales_para_dashboard`: si no hay rostro real frente a la cámara, devuelve métricas inactivas en 0.0 y emoción `INACTIVO`, garantizando que ninguna interacción de texto invente unidades de acción facial.
- **Estado de tests:** 16/16 pruebas multimodales superadas (`evaluar_coach.py`) y 25/25 pruebas oficiales aprobadas al 100% (`mi_tp07.py --sin-robot --evaluar`).









