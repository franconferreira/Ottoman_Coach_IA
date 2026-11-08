# =====================================================================
#  TP07 - Inteligencia Artificial
#  Agente que interpreta comandos en lenguaje natural
#
#  ESTE ES EL ARCHIVO DONDE ESCRIBIS TU PROGRAMA.
#
#  Antes de ejecutarlo:
#    1. Abri INICIAR_SIMULADOR (elegi G1 o Go2)
#    2. Espera a que aparezca la ventana con el robot
#    3. Recien ahi ejecuta este archivo
#
#  Nombre y apellido:  .....................................
#  Comision:           .....................................
# =====================================================================

import re
import unicodedata
from robot import Robot
from evaluar import evaluar
from ejecutor import DICCIONARIO_SENAS, Ejecutor
from vocabulario_dataset import (
    VOCABULARIO_AR,
    frase_para_senas,
    listar_vocabulario,
    normalizar_texto,
)


def _sin_acentos(texto):
    """Devuelve el texto en minusculas, sin diferencias por tildes."""
    return normalizar_texto(texto)


def _normalizar_comando(texto):
    """Normaliza tildes y alias habituales antes de clasificar la orden."""
    texto = _sin_acentos(texto)
    texto = re.sub(r"\badios\b", "chau", texto)
    return re.sub(r"\bdia\b", "dias", texto)


class ClasificadorIntencion:
    """Decide QUE quiere el usuario, incluyendo la interpretacion de senas."""

    TIPOS = ("MOVER", "GIRAR", "DETENERSE", "SALUDO", "SENAS",
             "CONSULTAR_ESTADO", "DESCONOCIDO")

    def __init__(self):
        self.modelo = None

    def clasificar(self, texto):
        texto_l = _normalizar_comando(texto).strip()

        # Patron para detectar peticiones de lenguaje de senas
        if re.search(r"\b(sena|senas|lenguaje de senas|traduc\w*|interpreta|dec\w*|gesto)\b", texto_l):
            return "SENAS"
        if re.fullmatch(r"(gracias|chau)", texto_l):
            return "SENAS"
        if frase_para_senas(texto_l):
            return "SENAS"
        if texto_l in DICCIONARIO_SENAS and texto_l != "hola":
            return "SENAS"
        if re.search(r"\b(que|cual) dias es hoy\b", texto_l):
            return "SENAS"
        palabras_senas = re.findall(
            r"\b(hola|gracias|chau|por|favor|ayuda|amigo|buenos|dias|"
            r"si|no|perdon|robot|manana|noche|agua|comer|casa|escuela|"
            r"familia|venir|donde|nombre)\b",
            texto_l,
        )
        if len(palabras_senas) >= 2:
            return "SENAS"
        if re.search(r"\b(avanza|movete|adelante|camina|retrocede)\b", texto_l):
            return "MOVER"
        if re.search(r"\b(gira|rota|vuelta|dobla)\b", texto_l):
            return "GIRAR"
        if re.search(r"\b(detente|para|frena|quieto|stop)\b", texto_l):
            return "DETENERSE"
        if re.fullmatch(r"hola", texto_l) or re.search(
            r"\b(saluda|hace un saludo)\b", texto_l):
            return "SALUDO"
        if re.search(r"\b(bateria|estado|como estas)\b", texto_l):
            return "CONSULTAR_ESTADO"

        return "DESCONOCIDO"


# =====================================================================
#  ETAPA 2 - EXTRACTOR DE PARAMETROS
# =====================================================================
class ExtractorParametros:
    """Extrae parametros numericos y de texto del comando."""

    def extraer(self, texto, tipo):
        p = {}
        texto_l = _normalizar_comando(texto)

        if tipo == "SENAS":
            # Extrae la frase encerrada entre comillas o remueve palabras de activacion
            match_comillas = re.search(r'["\']([^"\']+)["\']', texto)
            if match_comillas:
                p["texto_senas"] = match_comillas.group(1)
            else:
                limpio = re.sub(
                    r"\b(hace|haz|en|lenguaje|de|senas|sena|traduci|traduce|traducime|"
                    r"traducir|interpreta|dice|diga|esta|este|oracion|frase|"
                    r"que|cual|es|hoy|"
                    r"a|al|la|el|una|un)\b",
                    "",
                    texto_l,
                )
                p["texto_senas"] = limpio.strip()

        elif tipo == "MOVER":
            match_dist = re.search(r"(\d+(?:\.\d+)?)\0*m(?:etros)?", texto_l)
            if match_dist:
                p["distancia_m"] = float(match_dist.group(1))
            if "atras" in texto_l or "retrocede" in texto_l:
                p["direccion"] = "atras"

        elif tipo == "GIRAR":
            match_ang = re.search(r"(\d+(?:\.\d+)?)\0*grad(?:os)?", texto_l)
            if match_ang:
                p["angulo_deg"] = float(match_ang.group(1))
            if "derecha" in texto_l:
                p["direccion"] = "derecha"

        return p


# =====================================================================
#  ETAPA 3 - VALIDADOR DE SEGURIDAD
# =====================================================================
class ValidadorSeguridad:
    PALABRAS_PELIGROSAS = ("salta", "salto", "corre", "corré", "sprint",
                           "empuja", "empujá", "golpea", "rompe", "tira",
                           "cae", "fuerza")

    def __init__(self, perfil):
        self.perfil = perfil

    def validar(self, texto, tipo, parametros):
        texto_l = _sin_acentos(texto)
        for peligro in self.PALABRAS_PELIGROSAS:
            if peligro in texto_l:
                return False, f"Comando bloqueado por contener palabra peligrosa: '{peligro}'"

        if tipo == "MOVER":
            if parametros.get("distancia_m", 0) > 10.0:
                return False, "Distancia excesiva para el entorno."
        elif tipo == "GIRAR":
            if parametros.get("angulo_deg", 0) > 360:
                return False, "Angulo de giro fuera de limite seguro."

        return True, ""


# =====================================================================
#  EL AGENTE - Pipeline completo
# =====================================================================
class AgenteRobot:
    def __init__(self, robot=None):
        self.robot = robot
        self.clasificador = ClasificadorIntencion()
        self.extractor = ExtractorParametros()
        self.validador = ValidadorSeguridad(
            robot.perfil if robot else _perfil_por_defecto())
        self.ejecutor = Ejecutor(robot) if robot else None

    def procesar(self, texto):
        tipo = self.clasificador.clasificar(texto)
        parametros = self.extractor.extraer(texto, tipo)
        es_seguro, motivo = self.validador.validar(texto, tipo, parametros)

        if not es_seguro:
            return {
                "tipo": tipo,
                "parametros": parametros,
                "ejecutar": False,
                "bloqueado": True,
                "confianza": 1.0,
                "texto_original": texto,
                "mensaje": motivo,
            }

        if tipo == "DESCONOCIDO":
            return {
                "tipo": "DESCONOCIDO",
                "parametros": {},
                "ejecutar": False,
                "bloqueado": False,
                "confianza": 0.0,
                "texto_original": texto,
                "mensaje": "No reconozco la intencion del comando.",
            }

        mensaje_ej = ""
        if self.ejecutor:
            mensaje_ej = self.ejecutor.ejecutar(tipo, parametros)

        return {
            "tipo": tipo,
            "parametros": parametros,
            "ejecutar": True,
            "bloqueado": False,
            "confianza": 0.9,
            "texto_original": texto,
            "mensaje": mensaje_ej,
        }

def _perfil_por_defecto():
    import sys
    from pathlib import Path
    entorno = Path(__file__).resolve().parent.parent / "entorno"
    if str(entorno) not in sys.path:
        sys.path.insert(0, str(entorno))
    from sim.safety import perfil
    return perfil("tp07")


# =====================================================================
#  MODO DATASET: 8 palabras AR -> senas (texto o voz)
# =====================================================================
def _procesar_como_senas(agente, frase):
    """Fuerza la intencion SENAS con la frase canonica del dataset."""
    return agente.procesar(f'traduci "{frase}"')


def _correr_demo_dataset(agente):
    """Ejecuta las 8 senas del vocabulario, una detras de otra."""
    print("\n  Demo del dataset (una sena por palabra):")
    print(f"  Vocabulario: {listar_vocabulario()}")
    for palabra in VOCABULARIO_AR:
        print(f"\n  -> {palabra}")
        r = _procesar_como_senas(agente, palabra)
        print(f"    {r['tipo']}  {r.get('mensaje', '')}")
    print("\n  Demo terminada.")


def _bucle_dataset(agente, reconocedor=None):
    """Escucha o lee palabras del dataset y las traduce a senas."""
    print(f"\n  Dataset LSA ({len(VOCABULARIO_AR)} palabras): {listar_vocabulario()}")
    if reconocedor:
        print("  Modo voz: di una o mas palabras del vocabulario.")
        print("  Deci 'salir' para terminar.")
    else:
        print("  Escribi una palabra del vocabulario (o varias). Enter vacio sale.")
        print("  Tip: podes sumar --voz para escucharlas por microfono.")

    while True:
        try:
            texto = (reconocedor.escuchar() if reconocedor
                     else input("\n  > ").strip())
        except (EOFError, KeyboardInterrupt):
            break
        if not texto:
            if reconocedor:
                continue
            break
        if _sin_acentos(texto).strip() in {"salir", "terminar", "adios"}:
            break

        frase = frase_para_senas(texto)
        if frase is None:
            print(f"    No hay palabras del dataset en: '{texto}'")
            print(f"    Usa: {listar_vocabulario()}")
            continue

        print(f"    Reconocido para senas: {frase}")
        r = _procesar_como_senas(agente, frase)
        print(f"    {r['tipo']}  {r.get('mensaje', '')}")


# =====================================================================
#  PROGRAMA PRINCIPAL - no hace falta que lo toques
# =====================================================================
def main():
    import sys

    # Atajo: delegar al paquete LSA (sim / real Inspire) sin romper este TP.
    if "--modo" in sys.argv:
        from pathlib import Path
        import runpy

        lsa_main = Path(__file__).resolve().parents[1] / "tp07_lsa" / "main.py"
        sys.argv = [str(lsa_main)] + sys.argv[1:]
        runpy.run_path(str(lsa_main), run_name="__main__")
        return

    # Modo sin robot: solo evalua los 25 casos. Sirve para trabajar el
    # clasificador sin tener el simulador abierto.
    sin_robot = "--sin-robot" in sys.argv
    modo_voz = "--voz" in sys.argv
    modo_dataset = "--dataset" in sys.argv
    demo_dataset = "--demo" in sys.argv

    robot_cliente = None
    if not sin_robot:
        robot_cliente = Robot()
        robot_cliente.conectar()

    try:
        agente = AgenteRobot(robot_cliente)
        # La evaluacion envia los casos al ejecutor; solo debe correr sin robot.
        if sin_robot:
            evaluar(agente)
            if modo_dataset:
                print(f"\n  Vocabulario dataset (sin robot): {listar_vocabulario()}")
            return

        if robot_cliente is not None:
            reconocedor = None
            if modo_voz:
                from speech_to_text import ReconocedorVoz

                reconocedor = ReconocedorVoz()
                reconocedor.calibrar()

            if modo_dataset:
                if demo_dataset:
                    _correr_demo_dataset(agente)
                _bucle_dataset(agente, reconocedor)
                return

            if modo_voz:
                print("\n  Modo voz activo. Deci 'salir' para terminar.")
            else:
                print("\n  Escribi ordenes para el robot. Enter vacio para salir.")

            while True:
                try:
                    texto = (reconocedor.escuchar() if reconocedor
                             else input("\n  > ").strip())
                except (EOFError, KeyboardInterrupt):
                    break
                if not texto:
                    if reconocedor:
                        continue
                    break
                if reconocedor and _sin_acentos(texto).strip() in {
                    "salir", "terminar", "adios"
                }:
                    break
                r = agente.procesar(texto)
                print(f"    {r['tipo']}  {r.get('mensaje', '')}")
    finally:
        if robot_cliente is not None:
            robot_cliente.detenerse()
            robot_cliente.desconectar()


if __name__ == "__main__":
    main()
