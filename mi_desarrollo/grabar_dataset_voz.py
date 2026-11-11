"""Grabador Interactivo Guiado de Dataset de Voz (Ottoman Coach IA).

Este script permite al usuario grabar de forma ordenada y cómoda su dataset
de voz categorizado por emoción para entrenar tanto el Reconocedor de Locutor (Franco)
como el Clasificador de Emociones Acústicas (SER).
"""

import math
import os
import sys
import time
import wave

# Frases sugeridas por emoción para dar variedad fonética y naturalidad
FRASES_SUGERIDAS = {
    "NEUTRO": [
        "Hola Ottoman, cómo estás todo bien.",
        "Cuál es el siguiente ejercicio del circuito.",
        "Avisame cuando pasen los dos minutos de descanso.",
        "Registrá que completé las cuatro series de sentadillas.",
        "Qué músculos trabaja principalmente este movimiento.",
        "Recordame cuánto peso levanté la semana pasada.",
        "Me llamo Franco y vengo a hacer la rutina programada.",
        "Mostrame la postura correcta para la espalda.",
        "Confirmame si el rango de movimiento fue el adecuado.",
        "Bueno, nos vemos en la próxima sesión de entrenamiento.",
    ],
    "MOTIVADO": [
        "¡Dale que podemos con todo, metele que sale!",
        "¡Hoy me siento imparable, vamos por esa marca personal!",
        "¡Excelente rutina, me encantó la energía que le pusimos!",
        "¡Vamos una repetición más carajo, no aflojes ahora!",
        "¡Estoy con todas las pilas para arrancar a entrenar!",
        "¡Qué buen entrenamiento metimos hoy, tremendo!",
        "¡Me siento con muchísima fuerza, subile un poco el peso!",
        "¡Vamos que queda la última serie con toda la garra!",
        "¡Qué lindo cuando sentís que todo el esfuerzo vale la pena!",
        "¡A romperla en este ejercicio, confío plenamente en la técnica!",
    ],
    "CANSANCIO": [
        "No doy más de verdad, no me dan los brazos...",
        "Estoy fusilado, me tiemblan las piernas de la fatiga...",
        "Dormí re poco anoche y siento el cuerpo pesado...",
        "Necesito parar un toque porque me falta el aire...",
        "Estoy muerto de cansancio, fue un día larguísimo...",
        "No tengo fuerzas para levantar ni un kilo más...",
        "Podemos bajar la intensidad porque no llego al final...",
        "Estoy sin nafta, necesito descansar un ratito largo...",
        "Hoy el entrenamiento me pasó por encima...",
        "Dejemos la última serie para la próxima porque no llego...",
    ],
    "ENOJO": [
        "¡La puta madre, no me sale este ejercicio de mierda!",
        "¡Me da una bronca terrible lesionarme justo ahora!",
        "¡Qué calentura que tengo, fallé la serie por una pavada!",
        "¡No me salgas con boludeces ahora, estoy re caliente!",
        "¡Me pudrí de intentar diez veces y que no me salga!",
        "¡Qué bronca loco, siempre me trabo en la misma parte!",
        "¡No me rompas las bolas Ottoman, estoy enojado!",
        "¡Qué porquería de serie, me da muchísima rabia!",
        "¡Basta de vueltas, me pudrí de perder el tiempo!",
        "¡Estoy de un humor de mierda hoy, no me aguanto ni yo!",
    ],
    "ANSIEDAD": [
        "No sé si voy a poder rendir el examen, tengo taquicardia...",
        "Me da miedo lastimarme la rodilla si bajo más profundo...",
        "Estoy muy acelerado y siento que no puedo respirar bien...",
        "Siento un nudo en el pecho antes de tirar este peso tan alto...",
        "Tengo miedo de quedarme trabado abajo de la barra solo...",
        "Estoy muy preocupado por los dolores que estoy sintiendo...",
        "Y si lo hago mal y me rompo todo... ¿qué pasa?",
        "Siento que me tiemblan las manos y no puedo concentrarme...",
        "Tengo la sensación constante de que algo va a salir mal...",
        "Estoy hiperventilando un poco, decime qué hago Ottoman...",
    ],
}


def grabar_audio_pcm(duracion_seg: float = 3.5, sample_rate: int = 16000) -> bytes:
    """Captura audio del micrófono usando PyAudio con cuenta regresiva."""
    try:
        import pyaudio
    except ImportError:
        print("[ERROR] Falta pyaudio. Instalalo con: pip install pyaudio")
        sys.exit(1)

    p = pyaudio.PyAudio()
    chunk = 1024
    formato = pyaudio.paInt16
    canales = 1

    try:
        stream = p.open(
            format=formato,
            channels=canales,
            rate=sample_rate,
            input=True,
            frames_per_buffer=chunk,
        )
    except Exception as exc:
        print(f"[ERROR] No se pudo abrir el micrófono: {exc}")
        p.terminate()
        return b""

    frames = []
    total_chunks = int(sample_rate / chunk * duracion_seg)

    print("    🔴 GRABANDO AHORA... (hablá con la emoción indicada) ", end="", flush=True)
    for i in range(total_chunks):
        data = stream.read(chunk, exception_on_overflow=False)
        frames.append(data)
        if i % (total_chunks // 6) == 0:
            print("▪", end="", flush=True)

    print(" ✔️ [Fin]")
    stream.stop_stream()
    stream.close()
    p.terminate()

    return b"".join(frames)


def guardar_wav(ruta: str, pcm_bytes: bytes, sample_rate: int = 16000):
    with wave.open(ruta, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_bytes)


def menu_grabador():
    base_dir = os.path.join(
        os.path.dirname(__file__), "..", "datos", "audio", "franco"
    )
    base_dir = os.path.abspath(base_dir)

    print("=" * 70)
    print("🎙️  GRABADOR DE DATASET ACÚSTICO GUIADO - OTTOMAN COACH")
    print("=" * 70)
    print(f"Directorio de guardado: {base_dir}\n")

    emociones = ["NEUTRO", "MOTIVADO", "CANSANCIO", "ENOJO", "ANSIEDAD"]

    while True:
        print("\nSeleccioná la emoción que querés grabar:")
        for idx, emo in enumerate(emociones, 1):
            carpeta_emo = os.path.join(base_dir, emo.lower())
            os.makedirs(carpeta_emo, exist_ok=True)
            archivos_existentes = len([f for f in os.listdir(carpeta_emo) if f.endswith(".wav")])
            print(f"  {idx}. {emo:<12} (Grabadas actualmente: {archivos_existentes} muestras)")
        print("  6. Salir")

        opcion = input("\nElegí una opción (1-6): ").strip()
        if opcion == "6":
            print("Saliendo del grabador. ¡Buen trabajo!")
            break
        if not opcion.isdigit() or int(opcion) not in range(1, 6):
            print("Opción inválida. Intentá de nuevo.")
            continue

        emo_sel = emociones[int(opcion) - 1]
        carpeta_emo = os.path.join(base_dir, emo_sel.lower())
        frases = FRASES_SUGERIDAS.get(emo_sel, [])

        print(f"\n--- Sesión de grabación: {emo_sel} ---")
        print("Consejo: actúala con naturalidad e intensidad para que el modelo aprenda.")
        print("Presioná [ENTER] para comenzar la cuenta regresiva, o escribí 'b' para volver.")

        idx_frase = 0
        while True:
            frase_actual = frases[idx_frase % len(frases)]
            print(f"\nFrase sugerida #{idx_frase + 1}:")
            print(f"  👉 \"{frase_actual}\"")
            cmd = input("Presioná [ENTER] para grabar (o 'b' volver, 's' saltear frase): ").strip()
            if cmd.lower() == "b":
                break
            if cmd.lower() == "s":
                idx_frase += 1
                continue

            # Cuenta regresiva
            for s in [3, 2, 1]:
                print(f"  Preparate... {s}", end="\r", flush=True)
                time.sleep(0.7)

            pcm_data = grabar_audio_pcm(duracion_seg=3.5)
            if not pcm_data:
                print("Error capturando audio. Revisá tu micrófono.")
                break

            # Nombre de archivo incremental
            num_actual = len([f for f in os.listdir(carpeta_emo) if f.endswith(".wav")]) + 1
            nombre_wav = f"franco_{emo_sel.lower()}_{num_actual:03d}.wav"
            ruta_wav = os.path.join(carpeta_emo, nombre_wav)
            guardar_wav(ruta_wav, pcm_data)
            print(f"  💾 Guardado: {nombre_wav}")

            idx_frase += 1


if __name__ == "__main__":
    menu_grabador()
