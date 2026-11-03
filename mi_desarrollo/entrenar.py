# =====================================================================
#  Entrenamiento y Comparación de Clasificadores ML — NIVEL 2 (Extensión)
#
#  Entrena y compara tres familias de algoritmos vistas en la materia:
#    1. Multinomial Naive Bayes (n-gramas de caracteres + palabras)
#    2. Árbol de Decisión (DecisionTreeClassifier)
#    3. Máquina de Soporte Vectorial Lineal / Regresión Logística
#
#  Corrida rápida:
#      python entrenar.py
# =====================================================================

from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path

DATASET = Path(__file__).resolve().parent / "dataset.csv"

TIPOS = (
    "MOVER",
    "GIRAR",
    "DETENERSE",
    "SALUDO",
    "CONSULTAR_ESTADO",
    "COACH_EMOCIONAL",
    "DESCONOCIDO",
)


def cargar_dataset(ruta: Path = DATASET) -> tuple[list[str], list[str]]:
    if not ruta.exists():
        raise FileNotFoundError(f"No encuentro {ruta}.")

    textos, etiquetas = [], []
    with open(ruta, encoding="utf-8", newline="") as f:
        lector = csv.reader(f)
        for n, fila in enumerate(lector, 1):
            if not fila or fila[0].strip().startswith("#"):
                continue
            if n == 1 and fila[0].strip().lower() == "texto":
                continue
            if len(fila) < 2:
                raise ValueError(f"{ruta.name}:{n}: falta la intención -> {fila!r}")
            texto = fila[0].strip()
            etiqueta = fila[1].strip().upper()
            if etiqueta not in TIPOS:
                raise ValueError(f"{ruta.name}:{n}: '{etiqueta}' no está en {TIPOS}")
            textos.append(texto)
            etiquetas.append(etiqueta)

    if not textos:
        raise ValueError(f"{ruta.name} no tiene ejemplos.")
    return textos, etiquetas


def revisar_dataset(textos: list[str], etiquetas: list[str]) -> list[str]:
    avisos = []
    cuenta = Counter(etiquetas)
    if len(textos) < 80:
        avisos.append(f"Solo {len(textos)} ejemplos (se recomiendan >= 80).")
    faltan = [t for t in TIPOS if cuenta[t] == 0]
    if faltan:
        avisos.append(f"Faltan clases en el dataset: {', '.join(faltan)}.")
    repetidos = [t for t, c in Counter(x.lower().strip() for x in textos).items() if c > 1]
    if repetidos:
        avisos.append(f"Hay {len(repetidos)} ejemplo(s) repetido(s).")
    return avisos


def construir_modelos() -> dict:
    """Construye los tres pipelines supervisados para evaluación comparativa."""
    from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.naive_bayes import MultinomialNB
    from sklearn.pipeline import FeatureUnion, make_pipeline
    from sklearn.tree import DecisionTreeClassifier

    features_hibridas = FeatureUnion([
        ("chars", TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5))),
        ("words", TfidfVectorizer(analyzer="word", ngram_range=(1, 2))),
    ])

    return {
        "Naive Bayes (char+word)": make_pipeline(
            CountVectorizer(analyzer="char_wb", ngram_range=(3, 5)),
            MultinomialNB(alpha=0.3),
        ),
        "Árbol de Decisión": make_pipeline(
            TfidfVectorizer(analyzer="word", ngram_range=(1, 2)),
            DecisionTreeClassifier(max_depth=22, random_state=42),
        ),
        "Regresión Logística (TF-IDF Híbrido)": make_pipeline(
            features_hibridas,
            LogisticRegression(max_iter=1000, C=3.0, random_state=42),
        ),
    }


def entrenar(textos: list[str], etiquetas: list[str]):
    """Entrena el mejor modelo generalista (TF-IDF Híbrido + Regresión Logística)."""
    modelos = construir_modelos()
    mejor = modelos["Regresión Logística (TF-IDF Híbrido)"]
    mejor.fit(textos, etiquetas)
    return mejor


def entrenar_desde_csv(ruta: Path = DATASET):
    textos, etiquetas = cargar_dataset(ruta)
    return entrenar(textos, etiquetas)


def metricas(modelo, textos: list[str], etiquetas: list[str]) -> dict[str, float]:
    from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score

    pred = modelo.predict(textos)
    return {
        "accuracy": float(accuracy_score(etiquetas, pred)),
        "precision": float(precision_score(etiquetas, pred, average="macro", zero_division=0)),
        "recall": float(recall_score(etiquetas, pred, average="macro", zero_division=0)),
        "f1": float(f1_score(etiquetas, pred, average="macro", zero_division=0)),
    }


def main() -> int:
    from sklearn.model_selection import StratifiedKFold, cross_val_predict, train_test_split
    from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score

    print("\n" + "=" * 76)
    print("  ENTRENAMIENTO Y COMPARACIÓN DE CLASIFICADORES ML (NIVEL 2 — TPO UADE)")
    print("=" * 76)

    textos, etiquetas = cargar_dataset()
    cuenta = Counter(etiquetas)

    print(f"\n  Dataset cargado: {len(textos)} ejemplos balanceados en {len(cuenta)} intenciones:")
    for t in TIPOS:
        print(f"    - {t:<20}: {cuenta[t]:>3} ejemplos")

    for aviso in revisar_dataset(textos, etiquetas):
        print(f"  [AVISO] {aviso}")

    x_tr, x_te, y_tr, y_te = train_test_split(
        textos, etiquetas, test_size=0.25, random_state=42, stratify=etiquetas
    )

    print(f"\n  Partición Hold-out Estratificada: {len(x_tr)} train / {len(x_te)} test")
    print("  " + "-" * 72)
    print(f"  {'Modelo Supervisado':<38} {'Acc':>7} {'Prec':>7} {'Rec':>7} {'F1':>7}")
    print("  " + "-" * 72)

    modelos = construir_modelos()
    for nombre, pipe in modelos.items():
        pipe.fit(x_tr, y_tr)
        m = metricas(pipe, x_te, y_te)
        print(
            f"  {nombre:<38} "
            f"{m['accuracy']*100:>6.1f}% {m['precision']*100:>6.1f}% "
            f"{m['recall']*100:>6.1f}% {m['f1']*100:>6.1f}%"
        )

    print("  " + "-" * 72)

    # Validación cruzada estratificada de 5 pliegues sobre los 140 ejemplos
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    mejor_pipe = construir_modelos()["Regresión Logística (TF-IDF Híbrido)"]
    preds_cv = cross_val_predict(mejor_pipe, textos, etiquetas, cv=cv)
    acc_cv = accuracy_score(etiquetas, preds_cv) * 100
    prec_cv = precision_score(etiquetas, preds_cv, average="macro", zero_division=0) * 100
    rec_cv = recall_score(etiquetas, preds_cv, average="macro", zero_division=0) * 100
    f1_cv = f1_score(etiquetas, preds_cv, average="macro", zero_division=0) * 100

    print("\n  Validación Cruzada 5-Fold (140 ejemplos completos — Modelo Seleccionado):")
    print(f"    Accuracy : {acc_cv:.1f}% | Precision: {prec_cv:.1f}% | Recall: {rec_cv:.1f}% | F1-Macro: {f1_cv:.1f}%")
    print("=" * 76 + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
