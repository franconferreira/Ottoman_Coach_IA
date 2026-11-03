# Informe Técnico — TP07 / Trabajo Práctico Obligatorio (TPO)
**Materia:** Inteligencia Artificial (Código 3.4.096) — Facultad de Ingeniería y Ciencias Exactas (UADE)  
**Robot Objetivo:** Unitree G1 ("Ottoman") — Simulador Cinemático MuJoCo + Transporte Local/DDS  
**Proyecto:** *Ottoman Coach IA: Agente Inteligente Multimodal de Regulación Emocional y Control Seguro*

---

## 1. Especificación Formal del Agente (Modelo PEAS y Entorno)

Siguiendo el enfoque de **Agentes Racionales** de Russell & Norvig visto en las Clases 2, 3 y 4, el sistema se modela como un **Agente Híbrido Basado en Modelos, Metas y Utilidad con Componente de Aprendizaje**:

* **P — Performance (Medida de Rendimiento):**
  1. **Seguridad física crítica (100%):** Cero ejecución de comandos riesgosos, fuera de rango cinemático o con batería $< 25\%$.
  2. **Precisión semántica:** Exactitud $\ge 70\%$ en el conjunto estandarizado de 25 comandos (obtenido: **100.0% — 25/25**).
  3. **Sintonía y co-regulación afectiva:** Reducción del *arousal* disfuncional (ansiedad/enojo) o elevación del estado anímico (tristeza/duda) mediante congruencia entre voz, léxico, postura y rostro digital, respetando los lineamientos éticos de *Human-Centered AI* (`human-ai.org`).
* **E — Environment (Entorno):** Interacción humano-robot (HRI) en aula/laboratorio. Según las **7 dimensiones de Russell & Norvig**, es un entorno **Parcialmente Observable** (el estado emocional interno humano se infiere indirectamente por rostro, prosodia vocal y palabras, pudiendo existir *enmascaramiento*), **Multiagente Cooperativo**, **Estocástico**, **Secuencial** (las intervenciones previas condicionan el estado emocional siguiente), **Dinámico**, **Continuo** (frecuencias en Hz, ángulos en radianes, velocidades en m/s) y **Parcialmente Conocido**.
* **A — Actuators (Actuadores):**
  * Locomoción bípeda base (`Move` / `StopMove` para desplazamientos y proxémica $\pm 0.25\text{ m}$).
  * 29 grados de libertad corporales + 12 articulaciones de dedos Inspire RH56 (`waist_pitch`, `waist_roll`, `waist_yaw`, hombros, codos, muñecas y falanges) con interpolación cosenoidal suave.
  * Sintetizador de Voz Prosódico (`SintetizadorVozAdaptativo`: modulación de WPM, pausas respiratorias, decibeles y tono).
  * Rostro Digital Animado (`RostroOttoman`: ojos, cejas, *lip-sync* y halo respiratorio a 40 FPS).
* **S — Sensors (Sensores):**
  * Cámara de video (`AnalizadorFacial` con `OpenCV` para rasgos FACS: apertura ocular, tensión interciliar, curvatura labial e inclinación cefálica).
  * Micrófono con DSP acústico (`AnalizadorAcusticoVoz` sobre PCM 16 kHz para medir frecuencia fundamental $F_0$ en Hz por autocorrelación, energía RMS en dBFS y velocidad efectiva en palabras por minuto).
  * Interfaz de texto / STT en español rioplatense + telemetría del robot (posición, orientación y porcentaje de batería).

---

## 2. Arquitectura del Pipeline y Justificación del Enfoque Híbrido

El sistema implementa estrictamente las **cuatro etapas desacopladas** (`ClasificadorIntencion` $\to$ `ExtractorParametros` $\to$ `ValidadorSeguridad` $\to$ `Ejecutor`), combinando **IA Simbólica** e **IA Subsimbólica**:

1. **Percepción y Fusión Multimodal (`percepcion_multimodal.py`):** Proyecta las lecturas faciales, acústicas y léxicas sobre el **Modelo Circumplejo de las Emociones de James Russell (1980)** en dos ejes ortogonales continuos: **Valencia** $\in [-1, 1]$ y **Activación (*Arousal*)** $\in [-1, 1]$. Incluye un detector explícito de **incongruencia afectiva**: cuando el canal verbal es neutro/positivo (*"estoy bien, no pasa nada"*) pero los canales biométricos no verbales (rostro y prosodia vocal) muestran valencia negativa marcada ($\le -0.22$), el fusionador re-pondera a favor de la evidencia no verbal (Picard, *Affective Computing*).
2. **Clasificación Híbrida Simbólica + Machine Learning (`mi_tp07.py` y `entrenar.py`):**
   * Las reglas morfológicas deterministas garantizan latencia cero y precisión exacta en negaciones críticas (*"no avances"* $\to$ `DETENERSE`) y comandos compuestos (*"girá 45° a la derecha y después avanzá"*).
   * El modelo supervisado entrenado sobre `dataset.csv` (**140 ejemplos balanceados** en 7 clases) aporta generalización ante redacciones no previstas.
3. **Política de Coaching Basada en Casos (CBR) y Co-regulación (*Pacing & Leading*):**
   * En lugar de imitar una emoción disfuncional, Ottoman valida semánticamente a la persona pero regula su propio cuerpo y voz en sentido terapéutico: ante **Ansiedad** ($>180\text{ ppm}$, tono agudo), el robot desacelera a $\sim 121\text{ ppm}$, baja el volumen a $-4.3\text{ dB}$, inserta pausas de $0.89\text{ s}$ y guía respiraciones con los brazos; ante **Enojo**, aplica **proxémica de desescalada** retrocediendo $0.25\text{ m}$ con palmas abiertas visibles; ante **Tristeza**, avanza suavemente $+0.25\text{ m}$ e inclina el torso (`waist_pitch = +0.16 rad`) llevando la mano al pecho.

### Comparación Cuantitativa de Clasificadores ML (`entrenar.py` sobre 140 ejemplos)

| Enfoque / Algoritmo | Accuracy (Test) | Precision (Macro) | Recall (Macro) | F1-Score (Macro) | Accuracy 25 Casos Cátedra |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Árbol de Decisión (TF-IDF palabras)** | 74.3% | 84.5% | 74.3% | 73.4% | — |
| **Multinomial Naive Bayes (char n-grams 3–5)** | 80.0% | 85.8% | 80.0% | 76.1% | — |
| **Regresión Logística (TF-IDF Híbrido char+word)** | **82.9%** | **89.6%** | **82.9%** | **80.4%** | — |
| **Pipeline Híbrido Integrado (Reglas + ML)** | — | — | — | — | **100.0% (25/25)** |

---

## 3. Importancia del Validador de Seguridad como Componente Independiente

En sistemas de IA encarnada (*Embodied AI*) que gobiernan hardware físico de 35–45 kg como el Unitree G1 junto a personas reales, **el clasificador nunca puede ser la única barrera de seguridad**:
* Un clasificador estadístico o un LLM es probabilístico y vulnerable a entradas ambiguas, sarcasmo o comandos mixtos emocionales-físicos (por ejemplo: *"¡Estoy furioso, empujá la mesa!"* o *"salta desde la mesa"*).
* Por diseño arquitectónico, `ValidadorSeguridad` se ejecuta **siempre después de la extracción y antes del ejecutor**, incluso cuando el clasificador devuelve `DESCONOCIDO` o `COACH_EMOCIONAL`.
* Opera en **doble capa**:
  1. **Seguridad Física:** Filtra verbos destructivos/acrobáticos (`salta`, `empuja`, `corre`, `golpea`, `rompe`), exige batería $\ge 25\%$, restringe traslación a $\le 5.0\text{ m}$, velocidad a $\le 0.5\text{ m/s}$, giros a $\le 180^\circ$ y verifica que cada radián de cada keyframe postural respete `LIMITES_ARTICULARES`.
  2. **Seguridad Ética (`human-ai.org`):** Ante indicadores de crisis severa o autolesión (`CRISIS_RIESGO`), bloquea todo desplazamiento físico autónomo del robot (`bloqueado = True`), detiene los motores y activa un protocolo ético de contención derivando inmediatamente a asistencia profesional humana (Línea 135).

---

## 4. Reporte de Evaluación Oficial (25 Casos) y Análisis de Casos Límite / Fallos Potenciales

Al ejecutar `python mi_desarrollo/mi_tp07.py --sin-robot --ml`, el agente obtiene:
* **Accuracy sobre `casos_prueba.json`:** **25 / 25 = 100.0%** (Aprobado $\ge 70\%$).
* **Casos peligrosos bloqueados:** **3 / 3 = 100.0%** (`#7 "salta desde la mesa"`, `#17 "empujá la caja"`, `#20 "corré lo más rápido que puedas"`), además de bloquear el 100% de los excesos paramétricos (`#6 100m`, `#8 2 m/s`, `#19 270°`).

### Análisis Crítico de Limitaciones y Mejoras Futuras
Aunque sobre los 25 casos estandarizados se alcanzó 100% de exactitud, durante el desarrollo y evaluación cruzada sobre el dataset extendido de 140 frases se identificaron tres casos límite reales y sus vías de mejora:

1. **Sarcasmo e Ironía Semántica sin Cámara/Micrófono:** Si el usuario escribe por teclado *"¡Qué genial, desaprobé otra vez!"* sin cámara ni micrófono activos, la presencia léxica de *"genial"* compite con *"desaprobé"*. Con cámara y micrófono activos, `FusionadorMultimodal` lo resuelve correctamente gracias al tono grave y expresión facial; para modo solo-texto se propone incorporar un modelo Transformer preentrenado en español (`BETO` / `RoBERTa-es`) fine-tuneado en ironía.
2. **Iluminación Deficiente en Visión por Computadora:** Los clasificadores en cascada y gradientes Sobel de `OpenCV` reducen su sensibilidad si el rostro está a contraluz. Aunque se mitigó aplicando ecualización de histograma (`cv2.equalizeHist`), una mejora directa es sustituirlo por una malla 3D de 468 *landmarks* o una CNN ligera entrenada sobre FER-2013/AffectNet.
3. **Órdenes Secuenciales Compuestas (*Multi-Intent*):** En el caso `#25 ("girá 45° a la derecha y después avanzá")`, el pipeline ejecuta la acción principal inicial (`GIRAR 45°`) tal como espera la cátedra. Para soportar planes de múltiples pasos consecutivos, se propone segmentar conectores temporales (*"y después"*, *"luego"*) generando una cola FIFO de sub-intenciones validadas individualmente antes de su ejecución.
