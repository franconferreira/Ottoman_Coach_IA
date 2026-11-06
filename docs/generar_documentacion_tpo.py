"""Generador Automatizado de Entregables Académicos TPO UADE:
  1. Informe_TPO_Ottoman_Coach.docx (Informe Técnico en Word con gráficos embebidos)
  2. Presentacion_TPO_Ottoman_Coach.pptx (Presentación 16:9 con Notas del Orador)

Ejecución:
    python docs/generar_documentacion_tpo.py
"""

from __future__ import annotations

import json
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls
from docx.shared import Inches as DocxInches, Pt as DocxPt, RGBColor as DocxRGB

from pptx import Presentation
from pptx.dml.color import RGBColor as PptxRGB
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches as PptxInches, Pt as PptxPt

RAIZ = Path(__file__).resolve().parent.parent
GRAFICOS = RAIZ / "docs" / "graficos"
RUTA_DOCX = RAIZ / "Informe_TPO_Ottoman_Coach.docx"
RUTA_PPTX = RAIZ / "Presentacion_TPO_Ottoman_Coach.pptx"


# =====================================================================
#  1. GENERACIÓN DEL INFORME WORD (Informe_TPO_Ottoman_Coach.docx)
# =====================================================================

def _sombrear_celda(celda, hex_color: str) -> None:
    celda._tc.get_or_add_tcPr().append(
        parse_xml(f'<w:shd {nsdecls("w")} w:fill="{hex_color}"/>')
    )


def _agregar_tabla(doc: Document, encabezados: list[str], filas: list[list[str]]) -> None:
    tabla = doc.add_table(rows=1 + len(filas), cols=len(encabezados))
    tabla.style = "Table Grid"
    tabla.alignment = WD_TABLE_ALIGNMENT.CENTER

    hdr_cells = tabla.rows[0].cells
    for i, texto in enumerate(encabezados):
        hdr_cells[i].text = ""
        p = hdr_cells[i].paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(texto)
        run.bold = True
        run.font.size = DocxPt(9.5)
        run.font.color.rgb = DocxRGB(255, 255, 255)
        _sombrear_celda(hdr_cells[i], "0F172A")

    for idx_f, fila in enumerate(filas):
        row_cells = tabla.rows[idx_f + 1].cells
        bg = "F8FAFC" if idx_f % 2 == 1 else "FFFFFF"
        for i, val in enumerate(fila):
            row_cells[i].text = ""
            p = row_cells[i].paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT if i == 0 else WD_ALIGN_PARAGRAPH.CENTER
            run = p.add_run(val)
            run.font.size = DocxPt(9.0)
            run.font.color.rgb = DocxRGB(15, 23, 42)
            if i == 0:
                run.bold = True
            _sombrear_celda(row_cells[i], bg)

    doc.add_paragraph()


def _agregar_figura(doc: Document, nombre_png: str, epigrafe: str, ancho_in: float = 6.0) -> None:
    ruta = GRAFICOS / nombre_png
    if not ruta.exists():
        return
    p_img = doc.add_paragraph()
    p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_img.add_run().add_picture(str(ruta), width=DocxInches(ancho_in))

    p_cap = doc.add_paragraph()
    p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p_cap.add_run(epigrafe)
    r.italic = True
    r.font.size = DocxPt(9.0)
    r.font.color.rgb = DocxRGB(71, 85, 105)


def _titulo_seccion(doc: Document, texto: str) -> None:
    h = doc.add_heading(level=1)
    r = h.add_run(texto)
    r.font.name = "Segoe UI"
    r.font.size = DocxPt(14.5)
    r.font.color.rgb = DocxRGB(2, 132, 199)


def _subtitulo(doc: Document, texto: str) -> None:
    h = doc.add_heading(level=2)
    r = h.add_run(texto)
    r.font.name = "Segoe UI"
    r.font.size = DocxPt(11.5)
    r.font.color.rgb = DocxRGB(15, 23, 42)


def _parrafo(doc: Document, texto: str, negrita_prefijo: str = "") -> None:
    p = doc.add_paragraph()
    p.paragraph_format.space_after = DocxPt(6)
    p.paragraph_format.line_spacing = 1.15
    if negrita_prefijo:
        rb = p.add_run(negrita_prefijo)
        rb.bold = True
        rb.font.name = "Calibri"
        rb.font.size = DocxPt(10.5)
    r = p.add_run(texto)
    r.font.name = "Calibri"
    r.font.size = DocxPt(10.5)


def generar_word() -> Path:
    datos_ga = json.loads((RAIZ / "mi_desarrollo" / "pesos_fusion_ga.json").read_text(encoding="utf-8"))
    datos_ml = json.loads((RAIZ / "mi_desarrollo" / "metricas_ml.json").read_text(encoding="utf-8"))
    p_opt = datos_ga["pesos_optimizados"]

    doc = Document()
    for sec in doc.sections:
        sec.top_margin = DocxInches(0.85)
        sec.bottom_margin = DocxInches(0.85)
        sec.left_margin = DocxInches(0.9)
        sec.right_margin = DocxInches(0.9)

    # --- PORTADA INSTITUCIONAL ---
    for _ in range(2):
        doc.add_paragraph()

    p_uni = doc.add_paragraph()
    p_uni.alignment = WD_ALIGN_PARAGRAPH.CENTER
    ru = p_uni.add_run("UNIVERSIDAD ARGENTINA DE LA EMPRESA (UADE)\nFacultad de Ingeniería y Ciencias Exactas")
    ru.bold = True
    ru.font.size = DocxPt(13)
    ru.font.color.rgb = DocxRGB(15, 23, 42)

    p_mat = doc.add_paragraph()
    p_mat.alignment = WD_ALIGN_PARAGRAPH.CENTER
    rm = p_mat.add_run("Materia: Inteligencia Artificial (3.4.096) — Segundo Cuatrimestre 2026\nDocente: Prof. Santiago Gabriel Martin")
    rm.font.size = DocxPt(11)
    rm.font.color.rgb = DocxRGB(71, 85, 105)

    doc.add_paragraph()
    p_tit = doc.add_paragraph()
    p_tit.alignment = WD_ALIGN_PARAGRAPH.CENTER
    rt = p_tit.add_run(
        "OTTOMAN COACH IA\n"
        "Agente Inteligente Multimodal de Regulación Emocional,\n"
        "Optimización Genética, Redes Neuronales y Control Seguro\n"
        "sobre el Robot Humanoide Unitree G1"
    )
    rt.bold = True
    rt.font.size = DocxPt(18)
    rt.font.color.rgb = DocxRGB(2, 132, 199)

    doc.add_paragraph()
    _agregar_figura(
        doc,
        "dashboard_preview.png",
        "Vista general del Modo Dashboard de Exposición (Rostro 60 FPS + Visión FACS + Plano Valencia-Arousal).",
        ancho_in=5.8,
    )

    p_aut = doc.add_paragraph()
    p_aut.alignment = WD_ALIGN_PARAGRAPH.CENTER
    ra = p_aut.add_run("\nTrabajo Práctico Obligatorio (TP07 / TPO Final)\nAlumno: Franco  •  Noviembre de 2026")
    ra.bold = True
    ra.font.size = DocxPt(11.5)
    ra.font.color.rgb = DocxRGB(15, 23, 42)

    doc.add_page_break()

    # --- SECCIÓN 1: RESUMEN EJECUTIVO ---
    _titulo_seccion(doc, "1. Resumen Ejecutivo y Fundamentación en HRI")
    _parrafo(
        doc,
        "El presente Trabajo Práctico Obligatorio desarrolla 'Ottoman Coach IA', un Agente Inteligente Híbrido "
        "diseñado para gobernar al robot humanoide Unitree G1 adquirido por UADE (simulador físico MuJoCo de 29 grados "
        "de libertad corporales más 12 articulaciones en manos Inspire RH56). A diferencia de un controlador puramente "
        "reactivo limitado a desplazarse en el espacio, Ottoman actúa como un Coach de Co-Regulación Emocional capaz "
        "de percibir simultáneamente el rostro de la persona por visión artificial (OpenCV FACS), la prosodia acústica "
        "de su voz (frecuencia fundamental F0 en Hz, intensidad en dBFS y velocidad en palabras por minuto) y el léxico "
        "rioplatense para adaptar en tiempo real su propio tono de voz, cadencia, pausas, postura corporal, distancia "
        "interpersonal (proxémica) y expresión facial animada.",
    )
    _parrafo(
        doc,
        "El proyecto integra de forma cohesiva los ejes troncales de la asignatura: Agentes Racionales PEAS (Russell & "
        "Norvig), Razonamiento Basado en Casos (CBR), Algoritmos Genéticos de codificación real para optimizar la fusión "
        "sensorial, Aprendizaje Supervisado y Redes Neuronales Multicapa (MLPClassifier) sobre un corpus propio de 560 "
        "ejemplos únicos, Visión por Computadora, Procesamiento de Señales de Voz y Seguridad Ética Human-Centered AI "
        "(human-ai.org).",
    )

    # --- SECCIÓN 2: ESPECIFICACIÓN PEAS Y ENTORNO ---
    _titulo_seccion(doc, "2. Especificación Formal del Agente (PEAS y 7 Dimensiones)")
    _parrafo(
        doc,
        "Siguiendo la taxonomía de Russell & Norvig, Ottoman se modela como un Agente Híbrido Basado en Modelos, "
        "Metas y Utilidad con Componente de Aprendizaje:",
    )
    _agregar_tabla(
        doc,
        ["Componente PEAS", "Especificación Técnica en Ottoman Coach IA"],
        [
            ["Performance\n(Rendimiento)", "1) Seguridad física y ética estricta (100% bloqueo de órdenes peligrosas o crisis).\n2) Exactitud >= 70% en benchmark oficial TP07 (alcanzado: 100.0% — 25/25).\n3) Co-regulación afectiva efectiva (reducción de arousal disfuncional y alianza empática)."],
            ["Environment\n(Entorno)", "Interacción Humano-Robot (HRI) en laboratorio/aula universitaria con usuarios emocionales, ruido acústico ambiente y variaciones lumínicas."],
            ["Actuators\n(Actuadores)", "Locomoción bípeda (proxémica +-0.25 m), 29 DoF torso/brazos + 12 DoF dedos con interpolación cosenoidal, Voz TTS adaptativa (WPM, dB, Hz, pausas) y Dashboard/Rostro Digital a 40 FPS."],
            ["Sensors\n(Sensores)", "Cámara RGB (OpenCV Haar + gradientes Sobel FACS), Micrófono PCM 16 kHz (DSP autocorrelación F0 Hz, RMS dBFS, VAD WPM), Texto/STT rioplatense y Telemetría G1 (batería, rumbo)."],
        ],
    )
    _parrafo(
        doc,
        "Clasificación de las 7 dimensiones del entorno: (1) Parcialmente Observable, pues el estado emocional interno "
        "no se mide de forma directa y puede existir enmascaramiento afectivo; (2) Multiagente Cooperativo (humano + "
        "coach); (3) Estocástico; (4) Secuencial, dado que la memoria episódica de 5 turnos condiciona las respuestas "
        "posteriores; (5) Dinámico; (6) Continuo (Hz, dB, m/s, radianes); y (7) Parcialmente Conocido.",
    )

    # --- SECCIÓN 3: PIPELINE DE 4 ETAPAS ---
    _titulo_seccion(doc, "3. Arquitectura Desacoplada de 4 Etapas y Percepción Multimodal")
    _parrafo(
        doc,
        "El software respeta estrictamente la separación en cuatro módulos independientes exigida por la cátedra: "
        "(1) ClasificadorIntencion (reglas morfológicas de prioridad para paradas de emergencia + Fusión Afectiva + "
        "Red Neuronal MLPClassifier), (2) ExtractorParametros (magnitudes físicas o PlanRegulacionEmocional CBR/LLM), "
        "(3) ValidadorSeguridad (barrera ineludible física y ética) y (4) Ejecutor (partición temporal de tramos, "
        "coreografía articular MuJoCo, voz sincronizada y actualización del Dashboard).",
    )
    _parrafo(
        doc,
        "Canales biométricos implementados en percepcion_multimodal.py:",
        negrita_prefijo="Sensado Multimodal: ",
    )
    _parrafo(
        doc,
        "• Visión Facial (AnalizadorFacial): Detecta apertura ocular (AU1/5), tensión interciliar en glabela mediante "
        "operador Sobel horizontal (AU4, ceño fruncido), curvatura geométrica labial (AU12/15) e inclinación cefálica.\n"
        "• DSP Acústico Vocal (AnalizadorAcusticoVoz): Calcula sobre ventanas Hanning de 30 ms la frecuencia fundamental "
        "F0 (75-400 Hz) por autocorrelación, energía RMS activa en dBFS, ataque glotal y palabras por minuto con VAD.\n"
        "• Modelo Circumplejo de Russell (1980): Proyecta los tres canales en el plano continuo Valencia [-1,+1] x "
        "Arousal [-1,+1] y detecta Incongruencia Emocional cuando las palabras son neutras ('estoy bien, no pasa nada') "
        "pero el rostro y la voz evidencian angustia o tristeza.",
    )

    # --- SECCIÓN 4: ALGORITMO GENÉTICO ---
    _titulo_seccion(doc, "4. Optimización Evolutiva mediante Algoritmos Genéticos")
    _parrafo(
        doc,
        "Para evitar calibrar a mano los pesos y umbrales del FusionadorMultimodal frente a sensores ruidosos y casos de "
        "enmascaramiento emocional, se implementó algoritmo_genetico.py aplicando los conceptos de las Clases 4 y 5: "
        "cada Individuo (Cromosoma) es un vector real de 11 genes (w3_lexico, w3_voz, w3_cara, w2v_lexico, w2c_lexico, "
        "inc_lexico, inc_voz, inc_cara y 3 umbrales biométricos). Se evolucionó una población de N=60 individuos durante "
        "G=50 generaciones sobre un benchmark de 180 escenarios multimodales (54 con enmascaramiento afectivo), usando "
        "Selección por Torneo (k=3), Cruza BLX-alpha (Pc=0.85), Mutación Gaussiana decreciente (Pm=0.22) y Elitismo (top 3).",
    )
    _agregar_tabla(
        doc,
        ["Configuración Evaluada", "Fitness Global", "Accuracy", "F1-Macro", "Recall Incongruencia", "RMSE (V-A)"],
        [
            ["Baseline Léxico (Sin Calibrar)", "52.02%", "59.4%", "65.5%", "0.0%", "0.362"],
            ["Heurística Manual Inicial", "85.79%", "87.8%", "87.3%", "83.3%", "0.250"],
            ["Cromosoma Evolucionado (AG)", "92.28%", "94.4%", "94.1%", "90.7%", "0.191"],
        ],
    )
    _parrafo(
        doc,
        f"Hallazgo científico notable: en condiciones congruentes el AG descubrió una tríada equilibrada "
        f"(léxico={p_opt['w3_lexico']:.2f}, voz={p_opt['w3_voz']:.2f}, cara={p_opt['w3_cara']:.2f}), mientras que bajo "
        f"enmascaramiento afectivo redujo autónomamente el peso verbal engañoso a apenas {p_opt['inc_lexico']*100:.1f}% "
        f"y asignó {(p_opt['inc_voz']+p_opt['inc_cara'])*100:.1f}% a la evidencia biométrica no verbal (rostro + voz), "
        f"convergiendo empíricamente con la teoría de Computación Afectiva de Rosalind Picard.",
    )
    _agregar_figura(
        doc,
        "ga_evolucion_fitness.png",
        "Figura 1: Evolución del Fitness máximo y promedio (+-1 sigma) a lo largo de 50 generaciones frente a los baselines.",
        ancho_in=5.9,
    )
    _agregar_figura(
        doc,
        "ga_pesos_optimizados.png",
        "Figura 2: Comparación de alelos entre el baseline no calibrado y el cromosoma óptimo hallado por el AG.",
        ancho_in=5.7,
    )
    _agregar_figura(
        doc,
        "matriz_confusion_multimodal.png",
        "Figura 3: Matriz de confusión del FusionadorMultimodal optimizado sobre los 180 escenarios con ruido sensorial.",
        ancho_in=4.7,
    )

    # --- SECCIÓN 5: APRENDIZAJE SUPERVISADO Y RED NEURONAL MLP ---
    _titulo_seccion(doc, "5. Aprendizaje Supervisado y Red Neuronal Multicapa (560 Ejemplos)")
    _parrafo(
        doc,
        "Se construyó en dataset.csv un corpus curado, libre de duplicados y perfectamente balanceado de 560 ejemplos "
        "en español rioplatense (80 ejemplos por cada una de las 7 intenciones: MOVER, GIRAR, DETENERSE, SALUDO, "
        "CONSULTAR_ESTADO, COACH_EMOCIONAL y DESCONOCIDO). En entrenar.py se compararon cuatro arquitecturas supervisadas "
        "incluyendo un Perceptrón Multicapa (MLPClassifier) con representación TF-IDF híbrida (n-gramas de caracteres 3-5 "
        "y palabras 1-2), dos capas ocultas densas (128 -> 64 neuronas con activación ReLU), regularización L2 (alpha=1e-3) "
        "y optimizador estocástico Adam.",
    )
    ho = datos_ml["holdout_25pct"]
    cv_mlp = datos_ml["cv_5fold_mlp"]
    _agregar_tabla(
        doc,
        ["Modelo Supervisado (entrenar.py)", "Accuracy", "Precision", "Recall", "F1-Macro"],
        [
            ["Árbol de Decisión (TF-IDF palabras)", f"{ho['Árbol de Decisión']['accuracy']*100:.1f}%", f"{ho['Árbol de Decisión']['precision']*100:.1f}%", f"{ho['Árbol de Decisión']['recall']*100:.1f}%", f"{ho['Árbol de Decisión']['f1']*100:.1f}%"],
            ["Multinomial Naive Bayes (char 3-5)", f"{ho['Naive Bayes (char+word)']['accuracy']*100:.1f}%", f"{ho['Naive Bayes (char+word)']['precision']*100:.1f}%", f"{ho['Naive Bayes (char+word)']['recall']*100:.1f}%", f"{ho['Naive Bayes (char+word)']['f1']*100:.1f}%"],
            ["Regresión Logística (TF-IDF Híbrido)", f"{ho['Regresión Logística (TF-IDF)']['accuracy']*100:.1f}%", f"{ho['Regresión Logística (TF-IDF)']['precision']*100:.1f}%", f"{ho['Regresión Logística (TF-IDF)']['recall']*100:.1f}%", f"{ho['Regresión Logística (TF-IDF)']['f1']*100:.1f}%"],
            ["Red Neuronal MLP (128-64 ReLU) [Hold-Out]", f"{ho['Red Neuronal MLP (128-64 ReLU)']['accuracy']*100:.1f}%", f"{ho['Red Neuronal MLP (128-64 ReLU)']['precision']*100:.1f}%", f"{ho['Red Neuronal MLP (128-64 ReLU)']['recall']*100:.1f}%", f"{ho['Red Neuronal MLP (128-64 ReLU)']['f1']*100:.1f}%"],
            ["Red Neuronal MLP (128-64 ReLU) [5-Fold CV]", f"{cv_mlp['accuracy']*100:.2f}%", f"{cv_mlp['precision']*100:.2f}%", f"{cv_mlp['recall']*100:.2f}%", f"{cv_mlp['f1_macro']*100:.2f}%"],
        ],
    )
    _agregar_figura(
        doc,
        "comparacion_modelos_ml.png",
        "Figura 4: Desempeño comparativo de las cuatro familias de algoritmos sobre la partición de test estratificada.",
        ancho_in=5.8,
    )
    _agregar_figura(
        doc,
        "matriz_confusion_mlp.png",
        "Figura 5: Matriz de confusión 7x7 obtenida mediante Validación Cruzada Estratificada 5-Fold (560 ejemplos) con MLP.",
        ancho_in=4.8,
    )
    _agregar_figura(
        doc,
        "curva_loss_mlp.png",
        f"Figura 6: Convergencia de la pérdida Cross-Entropy durante backpropagation ({cv_mlp['epocas_convergencia']} épocas, loss final={cv_mlp['loss_final']}).",
        ancho_in=5.5,
    )

    # --- SECCIÓN 6: ACTUACIÓN ADAPTATIVA Y DASHBOARD ---
    _titulo_seccion(doc, "6. Co-Regulación Prosódica, Kinésica G1 y Modo Dashboard")
    _parrafo(
        doc,
        "Siguiendo el principio terapéutico de Pacing & Leading, Ottoman no imita estados disfuncionales sino que "
        "co-regula a la persona coordinando voz, cuerpo y rostro:",
    )
    _agregar_tabla(
        doc,
        ["Estado Detectado", "Voz Adaptativa (TTS)", "Kinésica Unitree G1 y Proxémica", "Visor Animado"],
        [
            ["ANSIEDAD / ESTRÉS", "118-122 ppm (-22%), -4.3 dB, pausas largas 0.90s", "Guía respiratoria simétrica de brazos (0 m)", "Azul sereno + Halo inhalar/exhalar 8s"],
            ["TRISTEZA / DESÁNIMO", "122 ppm (-18%), -2.5 dB, timbre cálido contenedor", "Acercamiento empático +0.25m, torso inclinado +0.16 rad, mano al pecho", "Ámbar cálido + Cejas compasivas"],
            ["ENOJO / FRUSTRACIÓN", "130 ppm (-12%), -3.5 dB, tono grave ecuánime", "Desescalada proxémica -0.25m (paso atrás), palmas abiertas visibles", "Verde equilibrio no reactivo"],
            ["DUDA / INSEGURIDAD", "138 ppm (-5%), 0.0 dB, articulación clara socrática", "Gesto de enumeración estructurada con manos alternadas", "Turquesa + Ceja reflexiva"],
            ["MOTIVACIÓN / ALEGRÍA", "168 ppm (+14%), +2.5 dB, entonación brillante", "Postura erguida expansiva de celebración con brazos elevados", "Dorado + Ojos arqueados felices"],
            ["CRISIS / RIESGO ÉTICO", "115 ppm, -3.0 dB, serenidad de contención", "BLOQUEO FÍSICO TOTAL (StopMove inmediato) + Derivación Línea 135", "Índigo + Protocolo ético activo"],
        ],
    )
    _agregar_figura(
        doc,
        "ottoman_faces_preview.png",
        "Figura 7: Los 6 presets expresivos vectoriales diseñados para humanizar el visor frontal del Unitree G1.",
        ancho_in=5.8,
    )

    # --- SECCIÓN 7: SEGURIDAD, EVALUACIÓN Y ANÁLISIS CRÍTICO ---
    _titulo_seccion(doc, "7. Validador Independiente, Resultados TP07 y Análisis Crítico")
    _parrafo(
        doc,
        "En robótica humanoide física (35-45 kg), el clasificador probabilístico jamás puede ser la única barrera de "
        "seguridad. ValidadorSeguridad se ejecuta siempre antes del Ejecutor en doble capa: (1) Capa Física, que bloquea "
        "verbos riesgosos ('salta', 'empuja', 'corre', 'rompe'), exige batería >= 25%, limita distancias a <= 5 m, "
        "velocidades a <= 0.5 m/s, giros a <= 180° y audita que cada radián postural respete los topes XML del G1; y "
        "(2) Capa Ética (human-ai.org), que ante señales de autolesión detiene motores y deriva a asistencia profesional.",
    )
    _parrafo(
        doc,
        "Resultados de verificación integral automatizada:\n"
        "• Evaluación Oficial TP07 (mi_tp07.py --sin-robot --ml): 25 / 25 casos correctos = 100.0% Accuracy y 3 / 3 "
        "órdenes peligrosas bloqueadas.\n"
        "• Suite Multimodal Completa (evaluar_coach.py): 15 / 15 pruebas integrales superadas (OpenCV, DSP PCM 16 kHz, "
        "incongruencia afectiva, proxémica, límites articulares, memoria episódica, Dashboard, MLP y Algoritmo Genético).",
        negrita_prefijo="Verificación Cuantitativa: ",
    )
    _subtitulo(doc, "Limitaciones Identificadas y Trabajo Futuro")
    _parrafo(
        doc,
        "1) Sarcasmo escrito sin sensores biométricos: en modo solo-teclado, frases irónicas ('¡Qué genial, desaprobé!') "
        "presentan polaridad léxica mixta; con cámara/micrófono activos el FusionadorMultimodal lo resuelve por tono y "
        "rostro, proponiéndose a futuro fine-tuning sobre modelos Transformer en español (BETO).\n"
        "2) Sensibilidad lumínica en cascadas Haar: mitigada con ecualización de histograma, escalable a mallas faciales 3D.\n"
        "3) Comandos multi-intención secuenciales: segmentación futura de conectores temporales en colas FIFO validadas.",
    )

    # --- SECCIÓN 8: REFERENCIAS ---
    _titulo_seccion(doc, "8. Referencias Bibliográficas")
    refs = [
        "Russell, S., & Norvig, P. (2021). Artificial Intelligence: A Modern Approach (4th ed.). Pearson.",
        "Picard, R. W. (1997). Affective Computing. MIT Press.",
        "Russell, J. A. (1980). A circumplex model of affect. Journal of Personality and Social Psychology, 39(6), 1161-1178.",
        "Ekman, P., & Friesen, W. V. (1978). Facial Action Coding System (FACS). Consulting Psychologists Press.",
        "Hall, E. T. (1966). The Hidden Dimension (Proxemics in Human Interaction). Doubleday.",
        "Breazeal, C. (2003). Emotion and sociable humanoid robots. International Journal of Human-Computer Studies, 59(1-2).",
        "Stanford Institute for Human-Centered Artificial Intelligence (HAI). Principios éticos HRI — https://human-ai.org/",
    ]
    for ref in refs:
        _parrafo(doc, f"• {ref}")

    doc.save(str(RUTA_DOCX))
    return RUTA_DOCX


# =====================================================================
#  2. GENERACIÓN DE LA PRESENTACIÓN PPTX CON NOTAS DEL ORADOR
# =====================================================================

BG_DARK = PptxRGB(11, 17, 32)
CARD_BG = PptxRGB(17, 24, 39)
BORDER_COL = PptxRGB(30, 41, 59)
CYAN = PptxRGB(56, 189, 248)
EMERALD = PptxRGB(52, 211, 153)
AMBER = PptxRGB(251, 191, 36)
WHITE = PptxRGB(248, 250, 252)
MUTED = PptxRGB(148, 163, 184)


def _nueva_slide(prs: Presentation, titulo: str, subtitulo: str, notas: str):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    bg = slide.background
    fill = bg.fill
    fill.solid()
    fill.fore_color.rgb = BG_DARK

    # Barra superior de acento
    barra = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, PptxInches(0), PptxInches(0), PptxInches(13.333), PptxInches(0.08))
    barra.fill.solid()
    barra.fill.fore_color.rgb = CYAN
    barra.line.fill.background()

    if titulo:
        tb = slide.shapes.add_textbox(PptxInches(0.6), PptxInches(0.28), PptxInches(12.1), PptxInches(0.95))
        tf = tb.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        r = p.add_run()
        r.text = titulo
        r.font.name = "Segoe UI"
        r.font.size = PptxPt(25)
        r.font.bold = True
        r.font.color.rgb = WHITE

        if subtitulo:
            p2 = tf.add_paragraph()
            r2 = p2.add_run()
            r2.text = subtitulo
            r2.font.name = "Segoe UI"
            r2.font.size = PptxPt(13)
            r2.font.color.rgb = CYAN

    slide.notes_slide.notes_text_frame.text = notas
    return slide


def _agregar_card_bullets(
    slide, x: float, y: float, w: float, h: float, encabezado: str, items: list[str], color_enc=CYAN
) -> None:
    box = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, PptxInches(x), PptxInches(y), PptxInches(w), PptxInches(h))
    box.fill.solid()
    box.fill.fore_color.rgb = CARD_BG
    box.line.color.rgb = BORDER_COL
    box.line.width = PptxPt(1.2)

    tb = slide.shapes.add_textbox(PptxInches(x + 0.22), PptxInches(y + 0.16), PptxInches(w - 0.44), PptxInches(h - 0.30))
    tf = tb.text_frame
    tf.word_wrap = True

    p0 = tf.paragraphs[0]
    r0 = p0.add_run()
    r0.text = encabezado
    r0.font.name = "Segoe UI"
    r0.font.size = PptxPt(15)
    r0.font.bold = True
    r0.font.color.rgb = color_enc
    p0.space_after = PptxPt(8)

    for it in items:
        p = tf.add_paragraph()
        p.space_after = PptxPt(6)
        r = p.add_run()
        r.text = f"▸ {it}"
        r.font.name = "Segoe UI"
        r.font.size = PptxPt(12.5)
        r.font.color.rgb = WHITE


def generar_pptx() -> Path:
    prs = Presentation()
    prs.slide_width = PptxInches(13.333)
    prs.slide_height = PptxInches(7.5)

    # SLIDE 1: PORTADA
    s1 = _nueva_slide(
        prs,
        "",
        "",
        "NOTAS ORADOR (1 min): Buenas tardes profesor y compañeros. Presento 'Ottoman Coach IA', mi Trabajo Práctico "
        "Obligatorio para Inteligencia Artificial sobre el humanoide Unitree G1 de la UADE. El objetivo fue trascender "
        "los comandos básicos de locomoción para convertir a Ottoman en un Coach de Regulación Emocional Multimodal que "
        "percibe cara, voz y palabras, y adapta su tono vocal, postura corporal y rostro digital con seguridad total.",
    )
    tb1 = s1.shapes.add_textbox(PptxInches(0.7), PptxInches(1.1), PptxInches(5.8), PptxInches(5.4))
    tf1 = tb1.text_frame
    tf1.word_wrap = True
    for txt, sz, col, bld in [
        ("UADE • INTELIGENCIA ARTIFICIAL (2C 2026)", 13, CYAN, True),
        ("OTTOMAN COACH IA", 38, WHITE, True),
        ("Agente Inteligente Multimodal de Regulación Emocional, Fusión Evolutiva y Control Seguro para Unitree G1", 16, MUTED, False),
        ("\n• Percepción: Cara (OpenCV FACS) + Voz (Hz/WPM/dB) + Léxico\n• Aprendizaje: Red Neuronal MLP (560 ej.) + Algoritmo Genético\n• Actuación: Voz Prosódica + Postura 29 DoF + Dashboard 60 FPS\n• Seguridad: Física Cinemática + Ética (human-ai.org)", 13.5, EMERALD, False),
        ("\nAlumno: Franco  |  Prof. Santiago Gabriel Martin", 13, AMBER, True),
    ]:
        p = tf1.add_paragraph() if tf1.paragraphs[0].text else tf1.paragraphs[0]
        p.space_after = PptxPt(10)
        r = p.add_run()
        r.text = txt
        r.font.name = "Segoe UI"
        r.font.size = PptxPt(sz)
        r.font.bold = bld
        r.font.color.rgb = col
    if (GRAFICOS / "dashboard_preview.png").exists():
        s1.shapes.add_picture(str(GRAFICOS / "dashboard_preview.png"), PptxInches(6.6), PptxInches(1.25), width=PptxInches(6.2))

    # SLIDE 2: PROBLEMA Y MODELO PEAS
    s2 = _nueva_slide(
        prs,
        "1. Especificación Formal del Agente (PEAS y Entorno)",
        "Agente Híbrido Basado en Modelos, Metas, Utilidad y Aprendizaje (Russell & Norvig)",
        "NOTAS ORADOR (1.5 min): Siguiendo las clases 2 y 3 de la materia, definimos formalmente a Ottoman mediante PEAS. "
        "Destacar ante el tribunal por qué el entorno es Parcialmente Observable: una persona puede decir 'estoy bien' "
        "mientras su rostro y su voz delatan angustia; además es Secuencial (memoria de 5 turnos), Estocástico y Continuo.",
    )
    _agregar_card_bullets(
        s2, 0.6, 1.45, 6.0, 5.4,
        "Definición PEAS del Humanoide G1",
        [
            "Performance: 100% seguridad física/ética, exactitud en comandos (25/25 = 100%) y co-regulación afectiva.",
            "Environment: Aula/laboratorio HRI con usuarios emocionales, ruido acústico e iluminación variable.",
            "Actuators: Base bípeda (+-0.25m), 29 DoF torso/brazos + 12 dedos Inspire, Voz TTS prosódica y Visor 60 FPS.",
            "Sensors: Cámara OpenCV FACS, Micrófono PCM 16kHz (F0 Hz, dB, WPM), Texto rioplatense y Telemetría.",
        ],
        CYAN,
    )
    _agregar_card_bullets(
        s2, 6.85, 1.45, 5.9, 5.4,
        "Las 7 Dimensiones del Entorno",
        [
            "Parcialmente Observable: emoción interna inferida indirectamente; posible enmascaramiento.",
            "Multiagente Cooperativo: alianza humano + robot coach.",
            "Estocástico y Dinámico: señales biométricas ruidosas en tiempo real.",
            "Secuencial: memoria episódica de las últimas 5 acciones y estados afectivos.",
            "Continuo: frecuencias en Hz, decibeles, m/s y radianes articulares.",
        ],
        EMERALD,
    )

    # SLIDE 3: ARQUITECTURA DE 4 ETAPAS
    s3 = _nueva_slide(
        prs,
        "2. Arquitectura Desacoplada Híbrida (Simbólica + Subsimbólica)",
        "Cuatro etapas independientes con barrera ineludible de seguridad antes del hardware",
        "NOTAS ORADOR (1.5 min): Explicar por qué combinamos IA Simbólica e IA Subsimbólica: las reglas deterministas "
        "aseguran prioridad instantánea ante un '¡frená!' o 'no avances', mientras que la Red Neuronal MLP y el "
        "Fusionador optimizado por Algoritmos Genéticos aportan generalización semántica y sensibilidad biométrica.",
    )
    etapas = [
        ("1. ClasificadorIntencion", ["Prioridad a paradas/negaciones", "Fusión Afectiva Multimodal", "Red Neuronal MLP (560 ej.)", "8 intenciones soportadas"], CYAN),
        ("2. ExtractorParametros", ["Magnitudes (m, grados, m/s)", "Memoria Episódica (5 turnos)", "Motor CBR + Fallback Gemini", "Plan prosódico y postural"], EMERALD),
        ("3. ValidadorSeguridad", ["¡NUNCA SE SALTEA!", "Filtro verbos peligrosos", "Topes m, m/s, °, batería>=25%", "Ética human-ai.org (Línea 135)"], AMBER),
        ("4. Ejecutor Multimodal", ["Partición segura en tramos", "Proxémica +-0.25m en G1", "Interpolación cosenoidal DoF", "Lip-Sync TTS + Dashboard"], CYAN),
    ]
    for idx, (tit, buls, col) in enumerate(etapas):
        _agregar_card_bullets(s3, 0.55 + idx * 3.12, 1.65, 2.95, 5.0, tit, buls, col)

    # SLIDE 4: PERCEPCIÓN MULTIMODAL E INCONGRUENCIA
    s4 = _nueva_slide(
        prs,
        "3. Percepción Multimodal y Detección de Enmascaramiento",
        "Visión Facial FACS + DSP Acústico Vocal + Léxico proyectados en el Plano de Russell (1980)",
        "NOTAS ORADOR (1.5 min): Acá mostramos cómo cumplimos el objetivo central: Ottoman no solo lee texto. Con OpenCV "
        "mide apertura de ojos, ceño fruncido (gradiente Sobel en glabela) y curvatura de boca. Con NumPy analiza la onda "
        "de voz extrayendo frecuencia fundamental F0 por autocorrelación, volumen RMS en dBFS y palabras por minuto. "
        "Si alguien dice 'Tranqui, estoy bien' con cara triste y voz apagada a 95 ppm, detecta Incongruencia Afectiva.",
    )
    _agregar_card_bullets(
        s4, 0.6, 1.5, 3.9, 5.2,
        "Canal 1: Visión Facial (OpenCV)",
        [
            "Ecualización de histograma + Cascadas.",
            "AU1/5: Apertura ocular (alerta/tristeza).",
            "AU4: Tensión interciliar vía Sobel X.",
            "AU12/15: Curvatura geométrica labial.",
            "Agitación motora e inclinación cefálica.",
        ],
        CYAN,
    )
    _agregar_card_bullets(
        s4, 4.7, 1.5, 3.9, 5.2,
        "Canal 2: DSP Acústico (16 kHz)",
        [
            "Ventaneo Hanning 30 ms / hop 15 ms.",
            "Tono F0 (75-400 Hz) por autocorrelación.",
            "Intensidad activa RMS en dBFS.",
            "Rapidez efectiva (WPM) con VAD.",
            "Ratio de pausas y ataque energético.",
        ],
        EMERALD,
    )
    _agregar_card_bullets(
        s4, 8.8, 1.5, 3.9, 5.2,
        "Canal 3 + Fusión Russell",
        [
            "Léxico afectivo rioplatense + signos.",
            "Proyección continua Valencia x Arousal.",
            "Detector de Enmascaramiento ('Estoy bien' + biometría negativa).",
            "Pesos evolutivos optimizados por AG.",
        ],
        AMBER,
    )

    # SLIDE 5: ALGORITMO GENÉTICO - EVOLUCIÓN
    s5 = _nueva_slide(
        prs,
        "4. Algoritmos Genéticos: Optimización del Fusionador Multimodal",
        "Cromosoma real de 11 genes evolucionado durante 50 generaciones (N=60, Torneo k=3, BLX-α)",
        "NOTAS ORADOR (1.5 min): Vinculando directamente con las clases 4 y 5, implementamos un Algoritmo Genético para "
        "encontrar los pesos óptimos de fusión y los umbrales de incongruencia sobre 180 casos con ruido sensorial. "
        "El fitness pasó de 52.0% en el baseline sin calibrar y 85.8% manual hasta 92.28%, alcanzando 94.4% de Accuracy.",
    )
    _agregar_card_bullets(
        s5, 0.6, 1.5, 5.1, 5.3,
        "Diseño Evolutivo (algoritmo_genetico.py)",
        [
            "Genotipo: 11 genes reales (pesos 3/2 canales, pesos enmascaramiento y 3 umbrales).",
            "Fitness: 0.62·F1 + 0.23·Recall_Incong + 0.15·(1 - RMSE/1.5) - Penalización FP.",
            "Operadores: Torneo (k=3), Cruza BLX-α (Pc=0.85), Mutación Gaussiana (Pm=0.22), Elitismo=3.",
            "Salto cuantitativo: Fitness 52.0% -> 85.8% -> 92.28% (Accuracy 94.4%, Recall Incong 90.7%).",
        ],
        CYAN,
    )
    if (GRAFICOS / "ga_evolucion_fitness.png").exists():
        s5.shapes.add_picture(str(GRAFICOS / "ga_evolucion_fitness.png"), PptxInches(5.9), PptxInches(1.55), width=PptxInches(6.9))

    # SLIDE 6: ALGORITMO GENÉTICO - HALLAZGO Y MATRIZ
    s6 = _nueva_slide(
        prs,
        "5. Hallazgo Evolutivo y Matriz de Confusión Multimodal",
        "El AG descubrió autónomamente suprimir el texto engañoso (1.4%) durante el enmascaramiento",
        "NOTAS ORADOR (1 min): Miren el gráfico izquierdo: cuando no hay contradicción, el AG reparte el peso de forma "
        "equilibrada (~36% léxico, 28% voz, 37% cara). Pero cuando detecta enmascaramiento, baja el peso de las palabras "
        "al 1.4% y le da el 98.6% al cuerpo y la voz, replicando computacionalmente la literatura de Picard y Mehrabian.",
    )
    if (GRAFICOS / "ga_pesos_optimizados.png").exists():
        s6.shapes.add_picture(str(GRAFICOS / "ga_pesos_optimizados.png"), PptxInches(0.6), PptxInches(1.6), width=PptxInches(6.6))
    if (GRAFICOS / "matriz_confusion_multimodal.png").exists():
        s6.shapes.add_picture(str(GRAFICOS / "matriz_confusion_multimodal.png"), PptxInches(7.45), PptxInches(1.45), width=PptxInches(5.3))

    # SLIDE 7: DATASET 560 Y COMPARATIVA ML + MLP
    s7 = _nueva_slide(
        prs,
        "6. Aprendizaje Supervisado y Red Neuronal sobre 560 Ejemplos",
        "Corpus balanceado en español rioplatense (80 ej./clase x 7 clases) en entrenar.py",
        "NOTAS ORADOR (1.5 min): Ampliamos dataset.csv a 560 ejemplos únicos sin repetidos. Comparamos cuatro familias "
        "vistas en la cursada: Árbol de Decisión (80.0%), Naive Bayes (95.0%), Regresión Logística (97.1%) y una Red "
        "Neuronal Multicapa MLP (128->64 ReLU con Adam) que logra 96.4% en Hold-out y 96.25% en Validación Cruzada 5-Fold.",
    )
    _agregar_card_bullets(
        s7, 0.6, 1.5, 5.0, 5.3,
        "Corpus y Modelos Evaluados",
        [
            "560 oraciones únicas (80 por c/u de las 7 clases: MOVER, GIRAR, DETENERSE, SALUDO, ESTADO, COACH, DESCONOCIDO).",
            "Features híbridas: TF-IDF char_wb (3-5) + word (1-2) tolerantes a tildes y voseo.",
            "Red Neuronal MLP: capas ocultas 128 -> 64 (ReLU), Adam, L2 α=1e-3.",
            "5-Fold Stratified CV (MLP): 96.25% Accuracy | 96.18% F1-Macro.",
        ],
        EMERALD,
    )
    if (GRAFICOS / "comparacion_modelos_ml.png").exists():
        s7.shapes.add_picture(str(GRAFICOS / "comparacion_modelos_ml.png"), PptxInches(5.85), PptxInches(1.55), width=PptxInches(6.95))

    # SLIDE 8: MATRIZ DE CONFUSIÓN Y LOSS DE LA RED NEURONAL
    s8 = _nueva_slide(
        prs,
        "7. Convergencia y Matriz 5-Fold de la Red Neuronal MLP",
        "Entrenamiento por Backpropagation (loss final = 0.00658) y alta separabilidad entre las 7 clases",
        "NOTAS ORADOR (1 min): A la izquierda vemos la matriz de confusión sobre los 560 ejemplos completos en validación "
        "cruzada de 5 pliegues (cada fila suma exactamente 80). A la derecha, la caída limpia y monótona de la función "
        "de pérdida Cross-Entropy durante las 50 épocas de backpropagation con Adam.",
    )
    if (GRAFICOS / "matriz_confusion_mlp.png").exists():
        s8.shapes.add_picture(str(GRAFICOS / "matriz_confusion_mlp.png"), PptxInches(0.75), PptxInches(1.45), width=PptxInches(5.4))
    if (GRAFICOS / "curva_loss_mlp.png").exists():
        s8.shapes.add_picture(str(GRAFICOS / "curva_loss_mlp.png"), PptxInches(6.45), PptxInches(1.75), width=PptxInches(6.3))

    # SLIDE 9: MATRIZ DE ACTUACIÓN ADAPTATIVA
    s9 = _nueva_slide(
        prs,
        "8. Co-Regulación: Modulación de Voz, Postura G1 y Proxémica",
        "Estrategia terapéutica Pacing & Leading sobre los 29+12 DoF de Ottoman",
        "NOTAS ORADOR (1.5 min): ¿Cómo actúa Ottoman cuando detecta una emoción? No la imita: la co-regula. Si el alumno "
        "habla a 200 ppm con ansiedad, Ottoman baja su voz a 120 ppm, reduce -4.3 dB, alarga pausas a 0.9s y guía una "
        "respiración lenta con sus brazos. En tristeza se acerca +0.25m e inclina el torso; en enojo da un paso atrás "
        "(-0.25m) con palmas visibles aplicando la teoría proxémica de Edward T. Hall.",
    )
    _agregar_card_bullets(
        s9, 0.6, 1.5, 6.1, 5.3,
        "Adaptación Vocal y Kinésica por Estado",
        [
            "Ansiedad / Estrés: Voz 118 ppm (-22%), -4.3 dB, pausa 0.9s + Brazos respiratorios.",
            "Tristeza / Desánimo: Acercamiento empático (+0.25 m), torso +0.16 rad, mano al pecho.",
            "Enojo / Frustración: Paso atrás de desescalada (-0.25 m), palmas abiertas calmas.",
            "Duda / Inseguridad: Andamiaje Socrático CBR + gesto estructurado de opciones.",
            "Motivación / Alegría: Voz 168 ppm (+14%), +2.5 dB + celebración expansiva G1.",
        ],
        CYAN,
    )
    if (GRAFICOS / "ottoman_faces_preview.png").exists():
        s9.shapes.add_picture(str(GRAFICOS / "ottoman_faces_preview.png"), PptxInches(6.95), PptxInches(1.75), width=PptxInches(5.85))

    # SLIDE 10: DASHBOARD DE EXPOSICIÓN EN VIVO
    s10 = _nueva_slide(
        prs,
        "9. Modo Dashboard de Exposición en Tiempo Real (--dashboard)",
        "Interfaz unificada 1240x700 a 40 FPS: Rostro Animado + Cámara OpenCV FACS + Plano Russell V-A",
        "NOTAS ORADOR (1 min): Como el Unitree G1 real tiene un visor oscuro sin rasgos, creamos un Modo Dashboard para "
        "la exposición que muestra en simultáneo: a la izquierda el rostro expresivo con Lip-Sync y halo respiratorio; "
        "arriba a la derecha la cámara en vivo midiendo las unidades faciales AU; y abajo a la derecha la trayectoria "
        "en tiempo real de la persona sobre el plano cartesiano Valencia-Arousal.",
    )
    if (GRAFICOS / "dashboard_preview.png").exists():
        s10.shapes.add_picture(str(GRAFICOS / "dashboard_preview.png"), PptxInches(0.8), PptxInches(1.4), width=PptxInches(7.7))
    _agregar_card_bullets(
        s10, 8.75, 1.45, 4.0, 5.2,
        "3 Paneles Sincronizados",
        [
            "Visor G1: interpolación suave de cejas/pupilas, Lip-Sync y alerta de incongruencia.",
            "Panel FACS: video OpenCV en vivo + barras AU1/4/12/25.",
            "Plano Russell: cuadrantes afectivos y estela histórica de los últimos 8 turnos.",
        ],
        AMBER,
    )

    # SLIDE 11: SEGURIDAD FÍSICA Y ÉTICA
    s11 = _nueva_slide(
        prs,
        "10. Seguridad Independiente: Física Cinemática + Ética HRI",
        "Alineado con la consigna oficial TP07 y los principios de Human-Centered AI (human-ai.org)",
        "NOTAS ORADOR (1 min): Recalcar esta pregunta clave de defensa oral: el ValidadorSeguridad es independiente del "
        "clasificador porque un modelo estadístico puede equivocarse o recibir una orden emocional peligrosa como 'Estoy "
        "furioso, empujá la mesa'. Además sumamos seguridad ética: ante frases de autolesión, bloquea motores y deriva "
        "inmediatamente a la Línea 135 sin fingir ser psicólogo clínico.",
    )
    _agregar_card_bullets(
        s11, 0.6, 1.55, 5.95, 5.1,
        "Capa 1: Seguridad Física y Articular G1",
        [
            "Se ejecuta SIEMPRE, incluso si la intención dio DESCONOCIDO.",
            "Bloquea verbos peligrosos: saltar, empujar, correr, golpear, romper.",
            "Topes estrictos: dist <= 5.0 m, vel <= 0.5 m/s, giro <= 180°, batería >= 25%.",
            "Verifica radianes de cada keyframe contra g1_29dof.xml.",
        ],
        CYAN,
    )
    _agregar_card_bullets(
        s11, 6.8, 1.55, 5.95, 5.1,
        "Capa 2: Seguridad Ética (human-ai.org)",
        [
            "Transparencia: Ottoman nunca suplanta a un profesional de salud mental.",
            "Detección instantánea de CRISIS_RIESGO (riesgo vital / autolesión).",
            "Frenado inmediato del robot (bloqueado=True, StopMove).",
            "Mensaje sereno de contención y derivación directa a asistencia humana (135).",
        ],
        AMBER,
    )

    # SLIDE 12: RESULTADOS FINALES Y DEMO
    s12 = _nueva_slide(
        prs,
        "11. Verificación Cuantitativa Integral y Conclusiones",
        "100% de aprobación en todas las suites oficiales, neuronales, evolutivas y multimodales",
        "NOTAS ORADOR (1.5 min): Para cerrar, todos los módulos están verificados al 100%: 25/25 en los casos oficiales "
        "de la cátedra, 3/3 peligrosos bloqueados, 96.25% en la Red Neuronal sobre 560 ejemplos, 94.4% en fusión "
        "multimodal evolucionada por Algoritmos Genéticos y 15/15 tests de integración. ¡Ahora pasemos a la demo en vivo "
        "con el simulador MuJoCo y el Dashboard abierto! Muchas gracias.",
    )
    _agregar_card_bullets(
        s12, 0.6, 1.55, 6.0, 5.1,
        "Resumen de Métricas Alcanzadas",
        [
            "Benchmark Oficial Cátedra TP07: 25 / 25 = 100.0% Accuracy.",
            "Órdenes Peligrosas Bloqueadas: 3 / 3 = 100.0% (+ excesos m, m/s, °).",
            "Red Neuronal MLP (560 ej.): 96.25% Accuracy (5-Fold CV).",
            "Algoritmo Genético Multimodal: 92.28% Fitness | 94.4% Accuracy.",
            "Suite Multimodal (evaluar_coach.py): 15 / 15 pruebas OK.",
        ],
        EMERALD,
    )
    _agregar_card_bullets(
        s12, 6.85, 1.55, 5.9, 5.1,
        "Conclusiones y Líneas Futuras",
        [
            "Se demostró cómo integrar Agentes PEAS, CBR, Algoritmos Genéticos, Redes Neuronales, Visión y Voz en un humanoide real.",
            "La co-regulación multimodal humaniza la robótica manteniendo seguridad determinista.",
            "Futuro: Transformers para sarcasmo en texto puro y malla facial 3D de 468 puntos.",
        ],
        CYAN,
    )

    prs.save(str(RUTA_PPTX))
    return RUTA_PPTX


def main() -> int:
    docx_path = generar_word()
    pptx_path = generar_pptx()
    print(f"[OK] Informe Word generado     : {docx_path} ({docx_path.stat().st_size // 1024} KB)")
    print(f"[OK] Presentación PPTX generada: {pptx_path} ({pptx_path.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
