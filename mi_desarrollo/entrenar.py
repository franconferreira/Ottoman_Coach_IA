# =====================================================================
#  Entrenamiento y Comparación de Clasificadores ML y Redes Neuronales
#  NIVEL 2 + EXTENSIÓN DEEP LEARNING (Clase 9/10 IA — TPO UADE)
#
#  Entrena y compara cuatro familias de algoritmos vistas en la materia
#  sobre el dataset balanceado de 560 ejemplos en español rioplatense:
#    1. Multinomial Naive Bayes (n-gramas de caracteres)
#    2. Árbol de Decisión (DecisionTreeClassifier)
#    3. Regresión Logística Lineal (TF-IDF Híbrido char + word)
#    4. Red Neuronal Multicapa — Perceptrón Multicapa (MLPClassifier
#       arquitectura densa 128 -> 64 -> 7 con activación ReLU + Adam)
#
#  Además exporta gráficos de alta resolución en docs/graficos/:
#    - comparacion_modelos_ml.png
#    - matriz_confusion_mlp.png
#    - curva_loss_mlp.png
#
#  Corrida rápida:
#      python mi_desarrollo/entrenar.py
# =====================================================================

from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

import numpy as np

DIR_ACTUAL = Path(__file__).resolve().parent
DATASET = DIR_ACTUAL / "dataset.csv"
DIR_GRAFICOS = DIR_ACTUAL.parent / "docs" / "graficos"
RUTA_METRICAS_JSON = DIR_ACTUAL / "metricas_ml.json"

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
    """Construye los cuatro pipelines supervisados incluyendo Red Neuronal MLP."""
    from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.naive_bayes import MultinomialNB
    from sklearn.neural_network import MLPClassifier
    from sklearn.pipeline import FeatureUnion, make_pipeline
    from sklearn.tree import DecisionTreeClassifier

    features_hibridas_lr = FeatureUnion([
        ("chars", TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), max_features=2500)),
        ("words", TfidfVectorizer(analyzer="word", ngram_range=(1, 2), max_features=1800)),
    ])

    features_hibridas_mlp = FeatureUnion([
        ("chars", TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), max_features=2200)),
        ("words", TfidfVectorizer(analyzer="word", ngram_range=(1, 2), max_features=1600)),
    ])

    return {
        "Naive Bayes (char+word)": make_pipeline(
            CountVectorizer(analyzer="char_wb", ngram_range=(3, 5), max_features=3000),
            MultinomialNB(alpha=0.3),
        ),
        "Árbol de Decisión": make_pipeline(
            TfidfVectorizer(analyzer="word", ngram_range=(1, 2), max_features=2000),
            DecisionTreeClassifier(max_depth=30, random_state=42),
        ),
        "Regresión Logística (TF-IDF)": make_pipeline(
            features_hibridas_lr,
            LogisticRegression(max_iter=1000, C=3.0, random_state=42),
        ),
        "Red Neuronal MLP (128-64 ReLU)": make_pipeline(
            features_hibridas_mlp,
            MLPClassifier(
                hidden_layer_sizes=(128, 64),
                activation="relu",
                solver="adam",
                alpha=1e-3,
                batch_size=32,
                learning_rate_init=1.5e-3,
                max_iter=180,
                random_state=42,
            ),
        ),
    }


def entrenar(textos: list[str], etiquetas: list[str]):
    """Entrena el modelo neuronal MLP seleccionado sobre el corpus completo."""
    modelos = construir_modelos()
    mejor = modelos["Red Neuronal MLP (128-64 ReLU)"]
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


def guardar_graficos_ml(
    resultados_holdout: dict[str, dict[str, float]],
    matriz_mlp: np.ndarray,
    loss_curve: list[float],
    acc_cv_mlp: float,
) -> list[Path]:
    """Genera los tres gráficos de evaluación supervisada y neuronal."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    DIR_GRAFICOS.mkdir(parents=True, exist_ok=True)
    rutas: list[Path] = []

    # 1. Comparación de los 4 modelos (Accuracy, Precision, Recall, F1)
    nombres = list(resultados_holdout.keys())
    nombres_cortos = [
        "Naive Bayes\n(Char 3-5)",
        "Árbol de\nDecisión",
        "Regresión\nLogística",
        "Red Neuronal\nMLP (128-64)",
    ]
    acc_vals = [resultados_holdout[k]["accuracy"] * 100 for k in nombres]
    prec_vals = [resultados_holdout[k]["precision"] * 100 for k in nombres]
    rec_vals = [resultados_holdout[k]["recall"] * 100 for k in nombres]
    f1_vals = [resultados_holdout[k]["f1"] * 100 for k in nombres]

    x = np.arange(len(nombres))
    w = 0.19
    fig, ax = plt.subplots(figsize=(9.6, 5.2), dpi=180)
    b_acc = ax.bar(x - 1.5 * w, acc_vals, w, label="Accuracy", color="#0284C7")
    b_pre = ax.bar(x - 0.5 * w, prec_vals, w, label="Precision (Macro)", color="#10B981")
    b_rec = ax.bar(x + 0.5 * w, rec_vals, w, label="Recall (Macro)", color="#F59E0B")
    b_f1 = ax.bar(x + 1.5 * w, f1_vals, w, label="F1-Score (Macro)", color="#6366F1")

    for rect in b_f1:
        h = rect.get_height()
        ax.annotate(
            f"{h:.1f}%",
            xy=(rect.get_x() + rect.get_width() / 2, h),
            xytext=(0, 3),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=8.5,
            fontweight="bold",
        )

    ax.set_xticks(x)
    ax.set_xticklabels(nombres_cortos, fontsize=9.8)
    ax.set_ylim(50, 105)
    ax.set_ylabel("Desempeño en Hold-Out Estratificado (%)", fontsize=10.5)
    ax.set_title(
        "Comparación de Clasificadores de Intención sobre 560 Ejemplos (TPO UADE)",
        fontsize=12,
        fontweight="bold",
        pad=12,
    )
    ax.grid(axis="y", linestyle="--", alpha=0.32)
    ax.legend(loc="lower right", frameon=True, fontsize=9)
    fig.tight_layout()
    ruta_comp = DIR_GRAFICOS / "comparacion_modelos_ml.png"
    fig.savefig(ruta_comp)
    plt.close(fig)
    rutas.append(ruta_comp)

    # 2. Matriz de Confusión 7x7 de la Red Neuronal MLP (5-Fold CV sobre 560 ejemplos)
    etiquetas_cortas = [
        "MOVER",
        "GIRAR",
        "DETENERSE",
        "SALUDO",
        "ESTADO",
        "COACH_EMO",
        "DESCONOCIDO",
    ]
    fig, ax = plt.subplots(figsize=(7.8, 6.6), dpi=180)
    im = ax.imshow(matriz_mlp, cmap="Purples")
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    ax.set_xticks(np.arange(len(etiquetas_cortas)))
    ax.set_yticks(np.arange(len(etiquetas_cortas)))
    ax.set_xticklabels(etiquetas_cortas, rotation=32, ha="right", fontsize=9.2)
    ax.set_yticklabels(etiquetas_cortas, fontsize=9.2)
    ax.set_xlabel("Intención Predicha por MLPClassifier", fontsize=10.5, fontweight="bold")
    ax.set_ylabel("Intención Real en Dataset (80 ej./clase)", fontsize=10.5, fontweight="bold")
    ax.set_title(
        f"Matriz de Confusión 5-Fold CV — Red Neuronal MLP (Accuracy: {acc_cv_mlp:.1f}%)",
        fontsize=11.5,
        fontweight="bold",
        pad=12,
    )
    umbral = matriz_mlp.max() * 0.55
    for i in range(matriz_mlp.shape[0]):
        for j in range(matriz_mlp.shape[1]):
            ax.text(
                j,
                i,
                str(matriz_mlp[i, j]),
                ha="center",
                va="center",
                color="white" if matriz_mlp[i, j] > umbral else "#1E1B4B",
                fontsize=9.5,
                fontweight="bold",
            )
    fig.tight_layout()
    ruta_cm = DIR_GRAFICOS / "matriz_confusion_mlp.png"
    fig.savefig(ruta_cm)
    plt.close(fig)
    rutas.append(ruta_cm)

    # 3. Curva de Convergencia de Pérdida (Cross-Entropy Loss) de la Red Neuronal MLP
    epocas = np.arange(1, len(loss_curve) + 1)
    fig, ax = plt.subplots(figsize=(8.6, 4.6), dpi=180)
    ax.plot(epocas, loss_curve, color="#7C3AED", linewidth=2.5, label="Cross-Entropy Loss (Adam + ReLU)")
    ax.fill_between(epocas, loss_curve, color="#7C3AED", alpha=0.12)
    ax.set_title(
        "Curva de Aprendizaje de la Red Neuronal MLP (128 → 64 → 7 Intenciones)",
        fontsize=11.8,
        fontweight="bold",
        pad=11,
    )
    ax.set_xlabel("Época de Entrenamiento (Backpropagation)", fontsize=10.5)
    ax.set_ylabel("Función de Pérdida (Log-Loss)", fontsize=10.5)
    ax.grid(True, linestyle="--", alpha=0.32)
    ax.legend(frameon=True, fontsize=9.5)
    fig.tight_layout()
    ruta_loss = DIR_GRAFICOS / "curva_loss_mlp.png"
    fig.savefig(ruta_loss)
    plt.close(fig)
    rutas.append(ruta_loss)

    return rutas


def main() -> int:
    from sklearn.metrics import (
        accuracy_score,
        confusion_matrix,
        f1_score,
        precision_score,
        recall_score,
    )
    from sklearn.model_selection import StratifiedKFold, cross_val_predict, train_test_split

    print("\n" + "=" * 78)
    print("  ENTRENAMIENTO DE CLASIFICADORES ML Y RED NEURONAL MLP (TPO UADE)")
    print("=" * 78)

    textos, etiquetas = cargar_dataset()
    cuenta = Counter(etiquetas)

    print(f"\n  Dataset cargado: {len(textos)} ejemplos únicos en {len(cuenta)} clases:")
    for t in TIPOS:
        print(f"    - {t:<20}: {cuenta[t]:>3} ejemplos")

    avisos = revisar_dataset(textos, etiquetas)
    for aviso in avisos:
        print(f"  [AVISO] {aviso}")

    x_tr, x_te, y_tr, y_te = train_test_split(
        textos, etiquetas, test_size=0.25, random_state=42, stratify=etiquetas
    )

    print(f"\n  Partición Hold-out Estratificada: {len(x_tr)} train / {len(x_te)} test")
    print("  " + "-" * 74)
    print(f"  {'Modelo Supervisado':<36} {'Acc':>8} {'Prec':>8} {'Rec':>8} {'F1':>8}")
    print("  " + "-" * 74)

    modelos = construir_modelos()
    resultados_holdout: dict[str, dict[str, float]] = {}
    loss_curve_mlp: list[float] = []

    for nombre, pipe in modelos.items():
        pipe.fit(x_tr, y_tr)
        m = metricas(pipe, x_te, y_te)
        resultados_holdout[nombre] = m
        if "MLP" in nombre:
            clf_mlp = pipe.named_steps["mlpclassifier"]
            loss_curve_mlp = [float(v) for v in clf_mlp.loss_curve_]
        print(
            f"  {nombre:<36} "
            f"{m['accuracy']*100:>7.1f}% {m['precision']*100:>7.1f}% "
            f"{m['recall']*100:>7.1f}% {m['f1']*100:>7.1f}%"
        )

    print("  " + "-" * 74)

    # Validación cruzada estratificada 5-Fold sobre los 560 ejemplos con la Red Neuronal MLP
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    mlp_pipe = construir_modelos()["Red Neuronal MLP (128-64 ReLU)"]
    preds_cv = cross_val_predict(mlp_pipe, textos, etiquetas, cv=cv)
    acc_cv = float(accuracy_score(etiquetas, preds_cv) * 100)
    prec_cv = float(precision_score(etiquetas, preds_cv, average="macro", zero_division=0) * 100)
    rec_cv = float(recall_score(etiquetas, preds_cv, average="macro", zero_division=0) * 100)
    f1_cv = float(f1_score(etiquetas, preds_cv, average="macro", zero_division=0) * 100)
    matriz_mlp = confusion_matrix(etiquetas, preds_cv, labels=list(TIPOS))

    print(f"\n  Validación Cruzada 5-Fold ({len(textos)} ejemplos — Red Neuronal MLP 128-64):")
    print(f"    Accuracy : {acc_cv:.1f}% | Precision: {prec_cv:.1f}% | Recall: {rec_cv:.1f}% | F1-Macro: {f1_cv:.1f}%")

    rutas = guardar_graficos_ml(resultados_holdout, matriz_mlp, loss_curve_mlp, acc_cv)

    resumen_json = {
        "total_ejemplos": len(textos),
        "clases": {t: int(cuenta[t]) for t in TIPOS},
        "holdout_25pct": {
            k: {mk: round(mv, 4) for mk, mv in v.items()}
            for k, v in resultados_holdout.items()
        },
        "cv_5fold_mlp": {
            "accuracy": round(acc_cv / 100.0, 4),
            "precision": round(prec_cv / 100.0, 4),
            "recall": round(rec_cv / 100.0, 4),
            "f1_macro": round(f1_cv / 100.0, 4),
            "epocas_convergencia": len(loss_curve_mlp),
            "loss_final": round(loss_curve_mlp[-1], 5) if loss_curve_mlp else 0.0,
        },
    }
    RUTA_METRICAS_JSON.write_text(json.dumps(resumen_json, indent=2, ensure_ascii=False), encoding="utf-8")

    for r in rutas:
        print(f"  [OK] Gráfico generado: docs/graficos/{r.name}")
    print("=" * 78 + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
