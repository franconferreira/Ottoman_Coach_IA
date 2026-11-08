"""Entrada de voz en espanol para el TP07.

El modulo importa SpeechRecognition/PyAudio solo cuando se crea el
reconocedor. De esa forma el modo --sin-robot sigue funcionando sin audio.
"""


class ReconocedorVoz:
    """Convierte lo dicho por el usuario en texto usando Google Speech API."""

    def __init__(self, idioma="es-AR", pausa_silencio=0.8):
        try:
            import speech_recognition as sr
        except ImportError as exc:
            raise RuntimeError(
                "Falta SpeechRecognition. Ejecuta: "
                "python -m pip install -r requirements-voz.txt"
            ) from exc

        self._sr = sr
        self._reconocedor = sr.Recognizer()
        self._reconocedor.pause_threshold = pausa_silencio
        try:
            self._microfono = sr.Microphone()
        except (AttributeError, OSError) as exc:
            raise RuntimeError(
                "No se pudo abrir el microfono. Verifica PyAudio, el "
                "microfono predeterminado y los permisos de Windows."
            ) from exc
        self.idioma = idioma

    def calibrar(self, duracion=1):
        """Ajusta el umbral al ruido ambiente durante unos segundos."""
        print("  Ajustando el microfono al ruido ambiente...")
        with self._microfono as fuente:
            self._reconocedor.adjust_for_ambient_noise(fuente, duration=duracion)
        print("  Microfono listo.")

    def escuchar(self):
        """Escucha una frase y devuelve su transcripcion, o una cadena vacia."""
        print("\n  Habla ahora (o deci 'salir' para terminar)...")
        try:
            with self._microfono as fuente:
                audio = self._reconocedor.listen(fuente, timeout=5, phrase_time_limit=12)
        except self._sr.WaitTimeoutError:
            print("  No detecte voz a tiempo.")
            return ""
        except self._sr.RequestError as exc:
            print(f"  No se pudo acceder al servicio de voz: {exc}")
            return ""

        try:
            texto = self._reconocedor.recognize_google(audio, language=self.idioma)
        except self._sr.UnknownValueError:
            print("  No pude entender lo que dijiste.")
            return ""
        except self._sr.RequestError as exc:
            print(f"  Error del servicio de reconocimiento: {exc}")
            return ""

        texto = texto.strip()
        print(f"  Texto reconocido: {texto}")
        return texto
