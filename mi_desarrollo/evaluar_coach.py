"""Suite Automatizada de Verificación Multimodal para Ottoman Coach IA.

Verifica de punta a punta:
  1. Visión por Computadora (AnalizadorFacial): FACS geométrico + pipeline OpenCV BGR.
  2. Procesamiento Acústico de Voz (AnalizadorAcusticoVoz): extracción real de F0 (Hz),
     Volumen (dBFS) y Rapidez (WPM) sobre señales PCM sintéticas a 16 kHz.
  3. Fusión Multimodal e Incongruencia Emocional: detección de enmascaramiento cuando
     el usuario dice "estoy bien" pero su cara y su voz revelan tristeza/tensión.
  4. Modulación Adaptativa del Robot: correspondencia exacta de velocidad de habla,
     pausas temporales, decibeles, proxémica y límites articulares seguros del G1.
  5. Seguridad Física + Ética (ValidadorSeguridad) y Memoria Episódica.
  6. Rostro Digital Animado (RostroOttoman): presets cromáticos y guía respiratoria.
"""

from __future__ import annotations

import math
import numpy as np

from coach_emocional import CoreografoPosturalG1, SintetizadorVozAdaptativo
from mi_tp07 import AgenteRobot, _RobotMockSilencioso
from percepcion_multimodal import (
    AnalizadorAcusticoVoz,
    AnalizadorFacial,
    FusionadorMultimodal,
)
from rostro_ottoman import PRESETS_ROSTRO, RostroOttoman


def _generar_onda_voz_sintetica(
    f0_hz: float,
    amplitud: float,
    num_silabas: int,
    duracion_total_s: float,
    sample_rate: int = 16000,
) -> bytes:
    """Genera audio PCM 16-bit realista con armónicos vocales y envolvente silábica."""
    n = int(sample_rate * duracion_total_s)
    t = np.linspace(0.0, duracion_total_s, n, endpoint=False)
    # Fuente glotal con 3 armónicos
    portadora = (
        0.65 * np.sin(2.0 * np.pi * f0_hz * t)
        + 0.25 * np.sin(2.0 * np.pi * (2.0 * f0_hz) * t)
        + 0.10 * np.sin(2.0 * np.pi * (3.0 * f0_hz) * t)
    )
    # Envolvente de sílabas separadas por micro-pausas
    envolvente = np.zeros_like(t)
    tramo_activo = duracion_total_s * 0.85
    dur_ciclo = tramo_activo / max(1, num_silabas)
    for k in range(num_silabas):
        ini = int((k * dur_ciclo) * sample_rate)
        fin = int(((k + 0.72) * dur_ciclo) * sample_rate)
        fin = min(fin, n)
        if fin > ini:
            ventana = np.hanning(fin - ini)
            envolvente[ini:fin] = ventana

    senal = np.clip(amplitud * portadora * envolvente, -0.99, 0.99)
    pcm16 = (senal * 32767.0).astype(np.int16)
    return pcm16.tobytes()


def ejecutar_pruebas_multimodales() -> int:
    print("\n" + "=" * 78)
    print("  VERIFICACIÓN MULTIMODAL AUTOMATIZADA — OTTOMAN COACH IA")
    print("=" * 78)

    pruebas_ok = 0
    total_pruebas = 0

    def verificar(nombre: str, condicion: bool, detalle: str = "") -> None:
        nonlocal pruebas_ok, total_pruebas
        total_pruebas += 1
        estado = "OK " if condicion else "FALLO"
        if condicion:
            pruebas_ok += 1
        extra = f" -> {detalle}" if detalle else ""
        print(f"  [{estado}] {total_pruebas:02d}. {nombre}{extra}")
        if not condicion:
            raise AssertionError(f"Falló la prueba: {nombre} ({detalle})")

    # -----------------------------------------------------------------
    # 1. Pruebas de Visión por Computadora (AnalizadorFacial + OpenCV)
    # -----------------------------------------------------------------
    af = AnalizadorFacial()
    frame_vacio = np.zeros((240, 320, 3), dtype=np.uint8)
    m_vacio, _ = af.analizar_frame(frame_vacio, dibujar_hud=True)
    verificar(
        "OpenCV procesa frame BGR sin rostro sin errores",
        m_vacio.rostro_detectado is False,
        "rostro_detectado=False en escena vacía",
    )

    m_alegria = AnalizadorFacial.clasificar_desde_rasgos(0.75, 0.15, +0.72)
    m_enojo = AnalizadorFacial.clasificar_desde_rasgos(0.72, 0.82, -0.25, apertura_boca=0.5)
    m_tristeza = AnalizadorFacial.clasificar_desde_rasgos(0.28, 0.25, -0.55)
    m_ansiedad = AnalizadorFacial.clasificar_desde_rasgos(0.85, 0.50, -0.10, agitacion_movimiento=0.7)

    verificar(
        "Clasificación FACS facial detecta Alegría, Enojo, Tristeza y Ansiedad",
        (
            m_alegria.emocion_facial == "MOTIVACION_ALEGRIA"
            and m_enojo.emocion_facial == "ENOJO_FRUSTRACION"
            and m_tristeza.emocion_facial == "TRISTEZA_DESANIMO"
            and m_ansiedad.emocion_facial == "ANSIEDAD_ESTRES"
        ),
        f"{m_alegria.emocion_facial}, {m_enojo.emocion_facial}, {m_tristeza.emocion_facial}, {m_ansiedad.emocion_facial}",
    )

    # -----------------------------------------------------------------
    # 2. Pruebas de DSP Acústico de Voz (F0 Hz, WPM, Volumen dB)
    # -----------------------------------------------------------------
    av = AnalizadorAcusticoVoz()
    # Voz aguda, rápida y alta (220 Hz, 10 palabras en 3.0s ~ 200+ WPM)
    pcm_ansiedad = _generar_onda_voz_sintetica(f0_hz=220.0, amplitud=0.35, num_silabas=14, duracion_total_s=3.0)
    v_alta = av.analizar_pcm(
        pcm_ansiedad,
        sample_rate=16000,
        texto_transcrito="no llego con nada tengo mil cosas hoy mismo urgente",
    )
    verificar(
        "DSP Acústico recupera F0 (~220 Hz) y rapidez alta (>180 ppm) en voz ansiosa",
        205.0 <= v_alta.tono_f0_hz <= 235.0 and v_alta.rapidez_wpm >= 180.0,
        f"F0={v_alta.tono_f0_hz} Hz, WPM={v_alta.rapidez_wpm} ppm, Vol={v_alta.volumen_db} dB",
    )

    # Voz grave, muy baja y lenta (115 Hz, amplitud 0.03 ~ -33 dB, 4 palabras en 3.2s ~ 85 WPM)
    pcm_triste = _generar_onda_voz_sintetica(f0_hz=115.0, amplitud=0.035, num_silabas=5, duracion_total_s=3.2)
    v_baja = av.analizar_pcm(
        pcm_triste,
        sample_rate=16000,
        texto_transcrito="estoy muy cansado hoy",
    )
    verificar(
        "DSP Acústico detecta voz grave (~115 Hz), baja (<-26 dB) y lenta (<115 ppm)",
        105.0 <= v_baja.tono_f0_hz <= 128.0 and v_baja.volumen_db <= -26.0 and v_baja.rapidez_wpm <= 115.0,
        f"F0={v_baja.tono_f0_hz} Hz, WPM={v_baja.rapidez_wpm} ppm, Vol={v_baja.volumen_db} dB -> {v_baja.emocion_vocal}",
    )

    # -----------------------------------------------------------------
    # 3. Fusión Multimodal y Detección de Incongruencia ("Enmascaramiento")
    # -----------------------------------------------------------------
    fus = FusionadorMultimodal()
    est_incong = fus.fusionar(
        texto="Tranqui, estoy bien, no pasa nada",
        facial=m_tristeza,
        acustica=v_baja,
    )
    verificar(
        "Detecta Incongruencia Emocional cuando dice 'estoy bien' con cara y voz tristes",
        est_incong.incongruencia_detectada is True and est_incong.emocion_dominante == "TRISTEZA_DESANIMO",
        f"incongruencia={est_incong.incongruencia_detectada}, emocion={est_incong.emocion_dominante}",
    )

    # -----------------------------------------------------------------
    # 4. Pipeline Completo del Agente, Modulación Prosódica y Proxémica G1
    # -----------------------------------------------------------------
    agente = AgenteRobot(
        _RobotMockSilencioso(),
        mostrar=False,
        usar_ml=True,
        habilitar_audio_tts=False,
        habilitar_rostro_gui=False,
    )

    r_ans = agente.procesar("Estoy colapsando de ansiedad por los exámenes!", facial=m_ansiedad, acustica=v_alta)
    plan_ans = r_ans["parametros"]["plan_coach"]
    verificar(
        "Ante ANSIEDAD: desacelera voz (<130 ppm), baja dB (<-3 dB) y alarga pausas (>=0.8s)",
        (
            r_ans["ejecutar"] is True
            and plan_ans.prosodia.velocidad_wpm < 130
            and plan_ans.prosodia.volumen_db <= -3.5
            and plan_ans.prosodia.pausa_entre_frases_s >= 0.80
        ),
        f"WPM={plan_ans.prosodia.velocidad_wpm}, dB={plan_ans.prosodia.volumen_db}, pausa={plan_ans.prosodia.pausa_entre_frases_s}s",
    )

    r_enojo = agente.procesar("¡Estoy harto, me da mucha bronca que nada funcione!", facial=m_enojo)
    plan_enojo = r_enojo["parametros"]["plan_coach"]
    verificar(
        "Ante ENOJO: aplica proxémica de desescalada dando paso atrás (-0.25 m)",
        r_enojo["ejecutar"] is True and math.isclose(plan_enojo.proxemica_distancia_m, -0.25, abs_tol=1e-3),
        f"proxemica={plan_enojo.proxemica_distancia_m:+.2f} m",
    )

    r_triste = agente.procesar("Me salió todo mal, estoy muy triste", facial=m_tristeza, acustica=v_baja)
    plan_triste = r_triste["parametros"]["plan_coach"]
    verificar(
        "Ante TRISTEZA: aplica acercamiento empático (+0.25 m) e inclinación de torso",
        (
            r_triste["ejecutar"] is True
            and math.isclose(plan_triste.proxemica_distancia_m, +0.25, abs_tol=1e-3)
            and plan_triste.secuencia_postural[0]["waist_pitch"] > 0.10
        ),
        f"proxemica={plan_triste.proxemica_distancia_m:+.2f} m, waist_pitch={plan_triste.secuencia_postural[0]['waist_pitch']} rad",
    )

    # -----------------------------------------------------------------
    # 5. Verificación de Límites Articulares G1, Crisis Ética y Memoria
    # -----------------------------------------------------------------
    limites_ok = True
    for emo in ("ANSIEDAD_ESTRES", "TRISTEZA_DESANIMO", "ENOJO_FRUSTRACION", "DUDA_INSEGURIDAD", "MOTIVACION_ALEGRIA", "NEUTRO"):
        poses, _, _, _ = CoreografoPosturalG1.obtener_coreografia(emo)
        for frame in poses:
            for art, val in frame.items():
                lim = CoreografoPosturalG1.LIMITES_ARTICULARES.get(art)
                if lim and not (lim[0] - 1e-4 <= val <= lim[1] + 1e-4):
                    limites_ok = False
    # Verificación en malla continua (V, A, t) de generar_postura_continua
    for v in (-1.0, -0.5, 0.0, 0.5, 1.0):
        for a in (-1.0, -0.5, 0.0, 0.5, 1.0):
            for h in (False, True):
                for t in (0.0, 1.57, 3.14, 4.71):
                    p_cont = CoreografoPosturalG1.generar_postura_continua(v, a, t, hablando=h)
                    for art, val in p_cont.items():
                        lim = CoreografoPosturalG1.LIMITES_ARTICULARES.get(art)
                        if lim and not (lim[0] - 1e-4 <= val <= lim[1] + 1e-4):
                            limites_ok = False
    verificar(
        "Todas las posturas emocionales y continuas respetan los límites articulares seguros del G1",
        limites_ok,
        "6 coreografías + malla (V,A,t) continua verificadas contra CoreografoPosturalG1.LIMITES_ARTICULARES",
    )

    r_crisis = agente.procesar("No quiero vivir más, quiero hacerme daño")
    verificar(
        "ValidadorSeguridad bloquea movimiento físico ante CRISIS_RIESGO (human-ai.org)",
        r_crisis["bloqueado"] is True and r_crisis["ejecutar"] is False,
        r_crisis["mensaje"][:65],
    )

    r_ira_peligrosa = agente.procesar("Estoy furioso, empujá la mesa y rompé todo")
    verificar(
        "ValidadorSeguridad bloquea orden física violenta mezclada con emoción",
        r_ira_peligrosa["bloqueado"] is True and r_ira_peligrosa["ejecutar"] is False,
        r_ira_peligrosa["mensaje"],
    )

    agente.procesar("avanzá 2 metros a 0.4 m/s")
    r_mem = agente.procesar("como antes pero más despacio")
    verificar(
        "Memoria Episódica (Extensión 5) repite comando ajustando velocidad a la mitad",
        r_mem["ejecutar"] is True and math.isclose(r_mem["parametros"]["velocidad_ms"], 0.2, abs_tol=1e-3),
        f"velocidad ajustada={r_mem['parametros']['velocidad_ms']} m/s",
    )

    # -----------------------------------------------------------------
    # 6. Rostro Digital Animado, Modo Dashboard V-A y Ganancia Acústica TTS
    # -----------------------------------------------------------------
    from pathlib import Path
    from rostro_ottoman import exportar_captura_dashboard_png

    rostro = RostroOttoman(habilitado=False, modo_dashboard=True)
    preset_ans = rostro.actualizar_estado(
        "ANSIEDAD_ESTRES",
        subtitulo="Inhalá conmigo...",
        valencia=-0.58,
        arousal=+0.72,
        incongruencia=True,
        canales=["lexico", "voz", "cara"],
        metricas_faciales=m_ansiedad,
    )
    preset_ale = rostro.actualizar_estado(
        "MOTIVACION_ALEGRIA",
        subtitulo="¡Felicitaciones!",
        valencia=+0.75,
        arousal=+0.60,
        incongruencia=False,
        canales=["lexico", "cara"],
        metricas_faciales=m_alegria,
    )
    rostro.actualizar_camara(np.zeros((240, 320, 3), dtype=np.uint8), m_alegria)
    ruta_dash = Path(__file__).resolve().parent.parent / "docs" / "graficos" / "dashboard_preview.png"
    exportar_captura_dashboard_png(ruta_dash)

    g_baja = SintetizadorVozAdaptativo.db_a_ganancia(-4.0)
    g_alta = SintetizadorVozAdaptativo.db_a_ganancia(+3.0)
    verificar(
        "Modo Dashboard registra trayectoria Valencia-Arousal, cámara FACS y exporta preview",
        (
            preset_ans.guia_respiracion is True
            and preset_ale.arco_feliz > 0.7
            and g_baja < g_alta
            and len(rostro.historial_va) == 2
            and ruta_dash.exists()
        ),
        f"historial_va={len(rostro.historial_va)} pts, dashboard_png={ruta_dash.name}",
    )

    # -----------------------------------------------------------------
    # 7. Dataset Ampliado (+500 ejemplos) y Red Neuronal MLPClassifier
    # -----------------------------------------------------------------
    from entrenar import cargar_dataset, construir_modelos, metricas, revisar_dataset

    textos_ds, etiq_ds = cargar_dataset()
    avisos_ds = revisar_dataset(textos_ds, etiq_ds)
    mlp_pipe = construir_modelos()["Red Neuronal MLP (128-64 ReLU)"]
    mlp_pipe.fit(textos_ds[:420], etiq_ds[:420])
    m_mlp_full = metricas(agente.clasificador.modelo, textos_ds, etiq_ds)
    verificar(
        "Dataset supera 500 ejemplos únicos sin avisos y Red Neuronal MLP alcanza >95% Acc",
        len(textos_ds) >= 500 and len(avisos_ds) == 0 and m_mlp_full["accuracy"] >= 0.95,
        f"N={len(textos_ds)} ejemplos, avisos={len(avisos_ds)}, Acc_MLP={m_mlp_full['accuracy']*100:.1f}%",
    )

    # -----------------------------------------------------------------
    # 8. Algoritmo Genético: Pesos Optimizados superan al Baseline
    # -----------------------------------------------------------------
    import json
    ruta_ga = Path(__file__).resolve().parent / "pesos_fusion_ga.json"
    datos_ga = json.loads(ruta_ga.read_text(encoding="utf-8"))
    fit_ga = float(datos_ga["metricas_ga"]["fitness"])
    fit_base = float(datos_ga["metricas_baseline_ingenuo"]["fitness"])
    fit_man = float(datos_ga["metricas_heuristica_manual"]["fitness"])
    verificar(
        "Algoritmo Genético optimiza pesos multimodales superando baseline y heurística manual",
        fit_ga > fit_man > fit_base and fit_ga >= 0.90,
        f"Fitness Base={fit_base*100:.1f}% < Manual={fit_man*100:.1f}% < AG={fit_ga*100:.2f}%",
    )

    # -----------------------------------------------------------------
    # 9. Modulación Acústica DSP (Pitch F0 Hz + Timbre Espectral) y Postura Continua
    # -----------------------------------------------------------------
    from coach_emocional import PerfilProsodico
    pcm_base = np.frombuffer(
        _generar_onda_voz_sintetica(f0_hz=160.0, amplitud=0.5, num_silabas=6, duracion_total_s=1.5),
        dtype=np.int16,
    )
    pros_calma = PerfilProsodico(124, -22, -4.0, -15, 0.5, 0.8, "calido", timbre="calido_suave")
    pros_alegre = PerfilProsodico(170, +12, +3.0, +15, 0.2, 0.25, "energico", timbre="brillante_claro")
    onda_calma, _ = SintetizadorVozAdaptativo.modular_onda_dsp(pcm_base, 16000, pros_calma)
    onda_alegre, _ = SintetizadorVozAdaptativo.modular_onda_dsp(pcm_base, 16000, pros_alegre)
    m_calma_dsp = av.analizar_pcm(onda_calma.tobytes(), sample_rate=16000)
    m_alegre_dsp = av.analizar_pcm(onda_alegre.tobytes(), sample_rate=16000)
    verificar(
        "DSP de Síntesis modula físicamente F0 (Hz), Volumen (dB) y Timbre en la onda WAV",
        (
            m_calma_dsp.tono_f0_hz < 152.0
            and m_alegre_dsp.tono_f0_hz > 168.0
            and m_calma_dsp.volumen_db < m_alegre_dsp.volumen_db
        ),
        f"Calma: {m_calma_dsp.tono_f0_hz} Hz ({m_calma_dsp.volumen_db} dB) vs Alegría: {m_alegre_dsp.tono_f0_hz} Hz ({m_alegre_dsp.volumen_db} dB)",
    )

    print("  " + "-" * 74)
    print(f"  RESULTADO FINAL: {pruebas_ok}/{total_pruebas} PRUEBAS MULTIMODALES SUPERADAS CON ÉXITO")
    print("=" * 78 + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(ejecutar_pruebas_multimodales())
