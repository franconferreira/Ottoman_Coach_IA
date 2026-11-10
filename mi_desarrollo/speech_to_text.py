"""Entrada de voz multimodal en español rioplatense (Transcripción + Prosodia DSP).

Además de convertir el habla a texto (STT), captura la onda PCM cruda del
micrófono para medir Tonalidad (F0 Hz), Rapidez (WPM), Volumen (dB) y Pausas
mediante AnalizadorAcusticoVoz.
"""

from __future__ import annotations

from percepcion_multimodal import AnalizadorAcusticoVoz, MetricasAcusticasVoz


class ReconocedorVozMultimodal:
    """Captura audio del micrófono y devuelve (texto, MetricasAcusticasVoz)."""

    def __init__(self, idioma: str = "es-AR", pausa_silencio: float = 2.0):
        try:
            import speech_recognition as sr
        except ImportError as exc:
            raise RuntimeError(
                "Falta SpeechRecognition. Ejecutá: pip install SpeechRecognition PyAudio"
            ) from exc

        self._sr = sr
        self._reconocedor = sr.Recognizer()
        self._reconocedor.pause_threshold = pausa_silencio
        self._reconocedor.non_speaking_duration = 0.8
        self._analizador_acustico = AnalizadorAcusticoVoz()
        self.idioma = idioma
        self.microfono_disponible = False
        self._microfono = None
        try:
            self._microfono = sr.Microphone()
            self.microfono_disponible = True
        except (AttributeError, OSError, Exception) as exc:
            print(f"  [MIC] Advertencia: No se detectó micrófono físico disponible ({exc}). El chat escrito permanece activo.")
            self.microfono_disponible = False

    def calibrar(self, duracion: float = 1.0) -> bool:
        if not self.microfono_disponible or self._microfono is None:
            try:
                self._microfono = self._sr.Microphone()
                self.microfono_disponible = True
            except Exception:
                self.microfono_disponible = False
                return False
        try:
            print("  [MIC] Calibrando umbral de ruido ambiente...")
            with self._microfono as fuente:
                self._reconocedor.adjust_for_ambient_noise(fuente, duration=duracion)
            print("  [MIC] Micrófono calibrado y listo.")
            return True
        except Exception as exc:
            print(f"  [MIC] No se pudo calibrar micrófono: {exc}")
            self.microfono_disponible = False
            return False

    def escuchar_multimodal(self) -> tuple[str, MetricasAcusticasVoz]:
        """Escucha una intervención y retorna el texto junto con su análisis acústico."""
        if not self.microfono_disponible or self._microfono is None:
            return "", MetricasAcusticasVoz(audio_analizado=False)
        print("\n  Hablá ahora con Ottoman (o decí 'salir' para terminar)...")
        try:
            with self._microfono as fuente:
                audio = self._reconocedor.listen(fuente, timeout=8, phrase_time_limit=40)
        except self._sr.WaitTimeoutError:
            print("  [MIC] No se detectó voz a tiempo.")
            return "", MetricasAcusticasVoz(audio_analizado=False)

        texto = ""
        try:
            texto = self._reconocedor.recognize_google(audio, language=self.idioma).strip()
        except self._sr.UnknownValueError:
            print("  [MIC] Se detectó audio pero no se distinguieron palabras claras.")
        except self._sr.RequestError as exc:
            print(f"  [MIC] Servicio STT no disponible ({exc}); se analizará solo la prosodia vocal.")

        raw_bytes = audio.get_raw_data(convert_rate=16000, convert_width=2)
        metricas = self._analizador_acustico.analizar_pcm(
            muestras=raw_bytes,
            sample_rate=16000,
            sample_width=2,
            texto_transcrito=texto,
        )
        if texto:
            print(f"  [VOZ -> TEXTO] \"{texto}\"")
        if metricas.audio_analizado:
            print(
                f"  [VOZ -> DSP]   Tono={metricas.tono_f0_hz:.0f} Hz | "
                f"Rapidez={metricas.rapidez_wpm:.0f} ppm | "
                f"Volumen={metricas.volumen_db:.1f} dB | "
                f"Emoción Vocal={metricas.emocion_vocal}"
            )
        return texto, metricas

    def escuchar(self) -> str:
        """Compatibilidad simple: devuelve únicamente el texto reconocido."""
        texto, _ = self.escuchar_multimodal()
        return texto


# Alias compatible con plantillas previas
ReconocedorVoz = ReconocedorVozMultimodal
