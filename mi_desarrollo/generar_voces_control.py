"""Generador de Muestras de Control para Locutor Invitado / Desconocido.

Para que el clasificador biométrico de locutor aprenda a distinguir con robustez
a 'Franco' frente a 'Invitado' (otras personas), este script genera clips limpios
de voces de referencia (hombres y mujeres con diferentes timbres y entonaciones)
utilizando el motor de síntesis TTS neuronal en la carpeta datos/audio/invitado/.
"""

import asyncio
import os
import shutil
import wave

FRASES_INVITADO = [
    ("es-AR-ElenaNeural", "Hola Ottoman, soy un nuevo alumno del gimnasio y vengo a probar."),
    ("es-AR-ElenaNeural", "Buenas tardes, me gustaría saber cómo funciona este sistema interactivo."),
    ("es-AR-ElenaNeural", "No estoy seguro de cómo colocar la espalda en este ejercicio."),
    ("es-AR-ElenaNeural", "Hoy me siento con bastante energía para completar la clase."),
    ("es-AR-ElenaNeural", "La verdad estoy muy cansada por el trabajo de toda la semana."),
    ("es-AR-ElenaNeural", "Qué bronca me da no poder coordinar bien los movimientos."),
    ("es-AR-ElenaNeural", "Tengo un poco de miedo de lesionarme la rodilla si bajo mucho."),
    ("es-AR-ElenaNeural", "Avisame por favor cuando pasen los dos minutos de pausa."),
    ("es-AR-ElenaNeural", "Excelente explicación, ahora entiendo la técnica correcta."),
    ("es-AR-ElenaNeural", "Muchas gracias por la ayuda, nos vemos la próxima semana."),
    # Voz de otro hombre (distinto tracto vocal y formantes a Tomás/Franco)
    ("es-UY-MateoNeural", "Hola, me presento, soy un compañero de Franco en la facultad."),
    ("es-UY-MateoNeural", "Buenas, vengo a ver la demostración del robot y la inteligencia artificial."),
    ("es-UY-MateoNeural", "Qué tal Ottoman, decime cuál es el plan de entrenamiento para hoy."),
    ("es-UY-MateoNeural", "Estoy agotado de estudiar toda la noche para el parcial de mañana."),
    ("es-UY-MateoNeural", "Me da mucha rabia equivocarme en una rutina tan sencilla."),
    ("es-UY-MateoNeural", "Siento taquicardia y mucha ansiedad por las entregas finales."),
    ("es-UY-MateoNeural", "Vamos con todo en esta serie que hoy rompemos el récord personal."),
    ("es-UY-MateoNeural", "Decime cuántas repeticiones me quedan pendientes en el circuito."),
    ("es-UY-MateoNeural", "Cómo estás, quería hacerte una consulta sobre la postura de hombros."),
    ("es-UY-MateoNeural", "Genial, pudimos completar todas las series en tiempo y forma."),
    # Tercera voz de contraste (España neutro)
    ("es-ES-AlvaroNeural", "Hola robot, soy un profesor de la cátedra evaluando el proyecto."),
    ("es-ES-AlvaroNeural", "Muéstrame cómo funciona el reconocimiento de emociones multimodales."),
    ("es-ES-AlvaroNeural", "El sistema responde de forma ágil y los gráficos son muy claros."),
    ("es-ES-AlvaroNeural", "Tengo curiosidad por ver la matriz de confusión del clasificador."),
    ("es-ES-AlvaroNeural", "Muy bien, la demostración práctica ha sido sumamente interesante."),
]


async def generar_audios_invitado():
    import edge_tts

    base_dir = os.path.join(
        os.path.dirname(__file__), "..", "datos", "audio", "invitado"
    )
    base_dir = os.path.abspath(base_dir)
    os.makedirs(base_dir, exist_ok=True)

    print(f"[*] Generando {len(FRASES_INVITADO)} muestras de control en: {base_dir}")

    for idx, (voz, frase) in enumerate(FRASES_INVITADO):
        ruta_mp3 = os.path.join(base_dir, f"temp_invitado_{idx:02d}.mp3")
        ruta_wav = os.path.join(base_dir, f"invitado_{idx:02d}.wav")

        comunicador = edge_tts.Communicate(frase, voz)
        await comunicador.save(ruta_mp3)

        # Convertir a WAV 16kHz mono usando ffmpeg
        cmd = f'ffmpeg -y -i "{ruta_mp3}" -ac 1 -ar 16000 "{ruta_wav}" -loglevel quiet'
        os.system(cmd)

        if os.path.exists(ruta_mp3):
            os.remove(ruta_mp3)

        print(f"  [+] Generado: invitado_{idx:02d}.wav ({voz})")

    print("[OK] Generación de locutores de control finalizada con éxito.")


if __name__ == "__main__":
    asyncio.run(generar_audios_invitado())
