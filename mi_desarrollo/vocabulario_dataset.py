"""Dataset chico de vocabulario espanol argentino -> LSA (senas).

Palabras cotidianas, faciles de reconocer por voz (es-AR). Las poses viven
en ejecutor.DICCIONARIO_SENAS (aprox. de brazo/muneca; sin dedos).

Confianza del borrador LSA (verificar con Senario CAS / video):
  alta: gracias, agua
  media-alta: amigo, hola, chau, si, ayuda
  media-baja: no (hay variantes)
"""

from __future__ import annotations

import re
import unicodedata

# 8 palabras: saludos, cortesia y basicas del dia a dia.
VOCABULARIO_AR: tuple[str, ...] = (
    "hola",
    "gracias",
    "chau",
    "si",
    "no",
    "ayuda",
    "agua",
    "amigo",
)

# Alias frecuentes en habla argentina / reconocimiento de voz.
ALIAS_A_CANONICA: dict[str, str] = {
    "adios": "chau",
    "adeu": "chau",
    "bye": "chau",
    "hasta": "chau",
    "buenas": "hola",
    "buenos": "hola",
    "buen": "hola",
    "saludos": "hola",
    "ok": "si",
    "dale": "si",
    "sip": "si",
    "nop": "no",
    "graciasito": "gracias",
    "holis": "hola",
}


def normalizar_texto(texto: str) -> str:
    """Normaliza mayusculas y tildes para comparar texto de voz."""
    texto = unicodedata.normalize("NFD", str(texto).casefold())
    return "".join(c for c in texto if unicodedata.category(c) != "Mn")


def sin_acentos(texto: str) -> str:
    return normalizar_texto(texto)


def palabras_del_dataset(texto: str) -> list[str]:
    """Extrae, en orden, las palabras del dataset presentes en el texto."""
    tokens = re.findall(r"[a-z]+", normalizar_texto(texto))
    encontradas: list[str] = []
    for token in tokens:
        canonica = ALIAS_A_CANONICA.get(token, token)
        if canonica in VOCABULARIO_AR:
            encontradas.append(canonica)
    return encontradas


def frase_para_senas(texto: str) -> str | None:
    """Devuelve la frase canónica a firmar, o None si no hay match."""
    palabras = palabras_del_dataset(texto)
    if not palabras:
        return None
    return " ".join(palabras)


def listar_vocabulario() -> str:
    return ", ".join(VOCABULARIO_AR)
