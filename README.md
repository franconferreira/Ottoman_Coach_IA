# 🤖 Ottoman Coach IA — Agente de Regulación Emocional Multimodal para Unitree G1

Proyecto integrador para la asignatura **Inteligencia Artificial (UADE)** sobre el robot humanoide bípedo **Ottoman (Unitree G1)**.

Transforma a Ottoman en un **Coach Emocional Encarnado (*Embodied Affective Coach*)** capaz de analizar en tiempo real la **cara**, la **acústica de la voz** y el **léxico** de la persona con la que interactúa, adaptando sincronizadamente:
1. **Su Voz (TTS Prosódico):** Velocidad en palabras por minuto (WPM), temporalización de pausas respiratorias, volumen en decibeles (dB) y tono fundamental (Hz).
2. **Su Léxico y Estrategia Psicolingüística:** *Grounding* en ansiedad, validación empática en tristeza, desescalada no confrontativa en enojo, andamiaje socrático en duda y refuerzo en motivación (con motor **CBR local offline** + soporte opcional de **Gemini API**).
3. **Su Lenguaje Corporal y Proxémica en el G1 (MuJoCo 3D / Robot Real):** Inclinación empática del torso (`waist_pitch`, `waist_roll`, `waist_yaw`), apertura y ritmo respiratorio de brazos, gestos con los **12 motores de dedos Inspire RH56** y ajuste espacial seguro (`+0.25 m` acercamiento empático / `-0.25 m` espacio personal de desescalada).
4. **Su Rostro Digital Animado (`rostro_ottoman.py`):** Ventana gráfica vectorial en tiempo real con ojos expresivos, cejas articuladas, parpadeo orgánico, sincronización labial (*lip-sync*) y halo visual de respiración guiada para humanizar la interacción.

Cumple además el **100% de la consigna oficial del TP07** (`25/25 = 100.0% Accuracy` y `3/3 Peligrosos Bloqueados` en `evaluar.py`).

---

## 🚀 Inicio Rápido

### 1. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 2. Abrir el Simulador 3D MuJoCo (Unitree G1)
En Windows, hacé doble clic en **`INICIAR_SIMULADOR.bat`** (elegí `1 = G1`) o ejecutá en una terminal:
```bash
cd entorno
python -m sim --robot g1 --materia tp07
```

### 3. Ejecutar Ottoman Coach IA
En una segunda terminal (o haciendo doble clic en **`EJECUTAR_COACH_COMPLETO.bat`**):

```bash
# Modo interactivo completo (Teclado + Rostro Animado + Voz TTS + Simulador G1 + ML)
python mi_desarrollo/mi_tp07.py --ml

# Modo Multimodal en Vivo con Cámara Facial (OpenCV) + Micrófono (DSP Voz)
python mi_desarrollo/mi_tp07.py --ml --camara --voz

# Demostración automática guiada de los 6 escenarios emocionales e incongruencia
python mi_desarrollo/mi_tp07.py --ml --demo-coach
```

---

## 🧪 Verificación y Pruebas Automatizadas

```bash
# 1. Evaluación oficial de cátedra (25 casos de casos_prueba.json)
python mi_desarrollo/mi_tp07.py --sin-robot --ml

# 2. Entrenamiento y comparación de clasificadores Machine Learning (140 ejemplos)
python mi_desarrollo/entrenar.py

# 3. Suite de 13 pruebas multimodales (OpenCV + DSP Voz Hz/WPM/dB + Incongruencia + Seguridad G1)
python mi_desarrollo/evaluar_coach.py
```

---

## 📂 Estructura del Proyecto

* `mi_desarrollo/mi_tp07.py`: Pipeline modular de 4 etapas (`ClasificadorIntencion`, `ExtractorParametros`, `ValidadorSeguridad`, `Ejecutor`) + `AgenteRobot` con memoria episódica de 5 turnos.
* `mi_desarrollo/percepcion_multimodal.py`:
  * `AnalizadorFacial`: Detección de rostro y unidades de acción facial (FACS) mediante `OpenCV`.
  * `AnalizadorAcusticoVoz`: Extracción DSP con `NumPy` de Tonalidad ($F_0$ Hz por autocorrelación), Intensidad ($\text{dBFS}$) y Rapidez ($\text{WPM}$).
  * `FusionadorMultimodal`: Integración en el Modelo Circumplejo de Russell (Valencia $\times$ Arousal) y detector de **incongruencia emocional** (enmascaramiento).
* `mi_desarrollo/coach_emocional.py`: Motor CBR/LLM de regulación afectiva, `CoreografoPosturalG1` y `SintetizadorVozAdaptativo`.
* `mi_desarrollo/rostro_ottoman.py`: Interfaz gráfica animada del rostro de Ottoman con *lip-sync* y telemetría biométrica en vivo.
* `INFORME_TECNICO_TPO.md`: Informe técnico académico, marco teórico (`txyz.ai`, `human-ai.org`, Russell & Norvig), métricas ML y análisis de fallos.
