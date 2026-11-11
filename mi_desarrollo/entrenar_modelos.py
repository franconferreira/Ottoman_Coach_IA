"""Script Maestro de Entrenamiento y Evaluación Rigurosa (Ottoman Coach IA).

Entrena y evalúa los 3 modelos de Machine Learning:
1. clasificador_locutor.joblib        -> Identificación Biométrica (Franco vs. Invitado)
2. clasificador_emocion_voz.joblib    -> SER Acústico (Neutro, Motivado, Cansancio, Enojo, Ansiedad)
3. clasificador_emocion_texto.joblib  -> NLP de Texto Afectivo Rioplatense

Genera matrices de confusión en PNG y reportes de métricas (Precision, Recall, F1)
listos para incluir en el informe del TPO.
"""

from __future__ import annotations

import csv
import json
import os
import sys
import numpy as np
import joblib

import matplotlib
matplotlib.use("Agg")  # Sin GUI para servidores / scripts
import matplotlib.pyplot as plt

from sklearn.ensemble import RandomForestClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.svm import SVC
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.metrics import classification_report, confusion_matrix, ConfusionMatrixDisplay

# Importar el extractor acústico propio
sys.path.insert(0, os.path.dirname(__file__))
from extractor_acustico import ExtractorAcusticoRobusto


BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATOS_AUDIO_DIR = os.path.join(BASE_DIR, "datos", "audio")
CSV_TEXTO_PATH = os.path.join(BASE_DIR, "mi_desarrollo", "dataset_emociones_texto.csv")
MODELOS_DIR = os.path.join(BASE_DIR, "mi_desarrollo", "modelos")
os.makedirs(MODELOS_DIR, exist_ok=True)


def guardar_grafico_confusion(cm: np.ndarray, labels: list[str], titulo: str, ruta_png: str):
    fig, ax = plt.subplots(figsize=(7, 6))
    disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=labels)
    disp.plot(cmap=plt.cm.Blues, ax=ax, values_format="d")
    ax.set_title(titulo, fontsize=12, fontweight="bold", pad=12)
    plt.tight_layout()
    plt.savefig(ruta_png, dpi=300)
    plt.close()
    print(f"  [GRAFICO] Matriz guardada en: {ruta_png}")


# =====================================================================
# 1. ENTRENAMIENTO: CLASIFICADOR DE EMOCIONES DE TEXTO (NLP)
# =====================================================================
def entrenar_modelo_texto():
    print("\n" + "=" * 65)
    print("📝 ENTRENANDO MODELO 1: EMOCIONES EN TEXTO (NLP)")
    print("=" * 65)

    if not os.path.exists(CSV_TEXTO_PATH):
        print(f"[ERROR] No se encontró el dataset: {CSV_TEXTO_PATH}")
        return

    textos = []
    etiquetas = []
    with open(CSV_TEXTO_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for fila in reader:
            txt = fila.get("texto", "").strip()
            emo = fila.get("emocion", "").strip()
            if txt and emo:
                textos.append(txt)
                etiquetas.append(emo)

    print(f"Total de frases cargadas: {len(textos)}")

    # Vectorización TF-IDF con n-gramas
    vectorizador = TfidfVectorizer(
        lowercase=True,
        ngram_range=(1, 2),
        min_df=1,
        sublinear_tf=True
    )
    X = vectorizador.fit_transform(textos)
    y = np.array(etiquetas)

    clases = sorted(list(set(y)))

    # Evaluación con Stratified K-Fold
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    modelo = MLPClassifier(hidden_layer_sizes=(64, 32), max_iter=500, random_state=42)

    predicciones = cross_val_predict(modelo, X, y, cv=skf)
    reporte = classification_report(y, predicciones, target_names=clases, output_dict=True)
    print("\nReporte de Clasificación (Validación Cruzada 5-Fold):")
    print(classification_report(y, predicciones, target_names=clases))

    cm = confusion_matrix(y, predicciones, labels=clases)
    guardar_grafico_confusion(
        cm, clases, "Matriz de Confusión - Emociones de Texto (NLP)",
        os.path.join(MODELOS_DIR, "matriz_confusion_emocion_texto.png")
    )

    # Entrenar sobre el 100% y serializar
    modelo.fit(X, y)
    joblib.dump(modelo, os.path.join(MODELOS_DIR, "clasificador_emocion_texto.joblib"))
    joblib.dump(vectorizador, os.path.join(MODELOS_DIR, "vectorizador_texto.joblib"))
    print("  [OK] Modelo y vectorizador exportados con éxito.")
    return reporte


# =====================================================================
# 2. CARGA Y EXTRACCIÓN DE FEATURES DE AUDIOS
# =====================================================================
def cargar_dataset_audio():
    extractor = ExtractorAcusticoRobusto()
    
    # Datos de Franco por emoción
    franco_dir = os.path.join(DATOS_AUDIO_DIR, "franco")
    invitado_dir = os.path.join(DATOS_AUDIO_DIR, "invitado")

    X_locutor = []
    y_locutor = []

    X_emocion = []
    y_emocion = []

    # Audios de Franco
    if os.path.exists(franco_dir):
        for sub in os.listdir(franco_dir):
            emo_path = os.path.join(franco_dir, sub)
            if not os.path.isdir(emo_path):
                continue
            emo_nombre = sub.upper()
            archivos = [os.path.join(emo_path, f) for f in os.listdir(emo_path) if f.endswith(".wav")]
            for arch in archivos:
                try:
                    feat = extractor.extraer_desde_wav(arch)
                    # Para locutor
                    X_locutor.append(feat)
                    y_locutor.append("Franco")
                    # Para emoción
                    X_emocion.append(feat)
                    y_emocion.append(emo_nombre)
                except Exception as exc:
                    print(f"  [!] Error procesando {arch}: {exc}")

    # Audios de Invitados
    if os.path.exists(invitado_dir):
        archivos_inv = [os.path.join(invitado_dir, f) for f in os.listdir(invitado_dir) if f.endswith(".wav")]
        for arch in archivos_inv:
            try:
                feat = extractor.extraer_desde_wav(arch)
                X_locutor.append(feat)
                y_locutor.append("Invitado")
            except Exception as exc:
                print(f"  [!] Error procesando {arch}: {exc}")

    return (
        np.array(X_locutor, dtype=np.float32),
        np.array(y_locutor),
        np.array(X_emocion, dtype=np.float32),
        np.array(y_emocion)
    )


# =====================================================================
# 3. ENTRENAMIENTO: RECONOCIMIENTO DE LOCUTOR (BIOMETRÍA)
# =====================================================================
def entrenar_modelo_locutor(X: np.ndarray, y: np.ndarray):
    print("\n" + "=" * 65)
    print("👤 ENTRENANDO MODELO 2: IDENTIFICACIÓN DE LOCUTOR (BIOMETRÍA)")
    print("=" * 65)

    if len(X) < 10 or len(set(y)) < 2:
        print(f"[AVISO] Datos insuficientes para entrenar locutor (Total: {len(X)} muestras, Clases: {set(y)}).")
        print("Grabá más audios con grabar_dataset_voz.py y asegurate de tener muestras en datos/audio/invitado/.")
        return None

    clases = ["Franco", "Invitado"]
    print(f"Muestras: Franco={np.sum(y == 'Franco')} | Invitado={np.sum(y == 'Invitado')}")

    # Clasificador SVM RBF o Random Forest
    modelo = SVC(kernel="rbf", probability=True, C=2.5, random_state=42)
    skf = StratifiedKFold(n_splits=min(5, np.min(np.bincount([0 if val == 'Franco' else 1 for val in y]))), shuffle=True, random_state=42)

    predicciones = cross_val_predict(modelo, X, y, cv=skf)
    print("\nReporte de Clasificación Biométrica (Cross-Validation):")
    print(classification_report(y, predicciones, target_names=clases))

    cm = confusion_matrix(y, predicciones, labels=clases)
    guardar_grafico_confusion(
        cm, clases, "Matriz de Confusión - Identificación de Locutor",
        os.path.join(MODELOS_DIR, "matriz_confusion_locutor.png")
    )

    modelo.fit(X, y)
    joblib.dump(modelo, os.path.join(MODELOS_DIR, "clasificador_locutor.joblib"))
    print("  [OK] Modelo de Locutor exportado.")
    return classification_report(y, predicciones, target_names=clases, output_dict=True)


# =====================================================================
# 4. ENTRENAMIENTO: CLASIFICADOR DE EMOCIONES DE VOZ (SER)
# =====================================================================
def entrenar_modelo_emocion_voz(X: np.ndarray, y: np.ndarray):
    print("\n" + "=" * 65)
    print("🎙️ ENTRENANDO MODELO 3: CLASIFICADOR DE EMOCIONES DE VOZ (SER)")
    print("=" * 65)

    clases_unicas = sorted(list(set(y)))
    if len(X) < 15 or len(clases_unicas) < 2:
        print(f"[AVISO] Muestras insuficientes para emociones de voz (Total: {len(X)} muestras, Clases: {clases_unicas}).")
        print("Grabá al menos 5-10 audios por emoción ejecutando: python mi_desarrollo/grabar_dataset_voz.py")
        return None

    print(f"Muestras por emoción: { {c: int(np.sum(y == c)) for c in clases_unicas} }")

    # Comparar Random Forest y MLP
    min_clase = min([np.sum(y == c) for c in clases_unicas])
    n_splits = min(5, max(2, min_clase))
    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)

    rf = RandomForestClassifier(n_estimators=100, max_depth=12, random_state=42)
    predicciones = cross_val_predict(rf, X, y, cv=skf)

    print("\nReporte de Clasificación Acústica SER (Cross-Validation):")
    print(classification_report(y, predicciones, target_names=clases_unicas))

    cm = confusion_matrix(y, predicciones, labels=clases_unicas)
    guardar_grafico_confusion(
        cm, clases_unicas, "Matriz de Confusión - Emociones de Voz (SER)",
        os.path.join(MODELOS_DIR, "matriz_confusion_emocion_voz.png")
    )

    rf.fit(X, y)
    joblib.dump(rf, os.path.join(MODELOS_DIR, "clasificador_emocion_voz.joblib"))
    print("  [OK] Modelo SER exportado.")
    return classification_report(y, predicciones, target_names=clases_unicas, output_dict=True)


def main():
    print("\n🚀 INICIANDO PIPELINE DE ENTRENAMIENTO DE IA ROBUSTO")
    reportes = {}

    # 1. Texto (funciona de inmediato con el CSV curado)
    rep_txt = entrenar_modelo_texto()
    if rep_txt:
        reportes["texto"] = rep_txt

    # 2. Cargar audios
    X_loc, y_loc, X_emo, y_emo = cargar_dataset_audio()

    # 3. Locutor
    if len(X_loc) > 0:
        rep_loc = entrenar_modelo_locutor(X_loc, y_loc)
        if rep_loc:
            reportes["locutor"] = rep_loc

    # 4. Emoción voz
    if len(X_emo) > 0:
        rep_emo = entrenar_modelo_emocion_voz(X_emo, y_emo)
        if rep_emo:
            reportes["emocion_voz"] = rep_emo

    with open(os.path.join(MODELOS_DIR, "metricas_clasificadores.json"), "w", encoding="utf-8") as f:
        json.dump(reportes, f, indent=2, ensure_ascii=False)
    print(f"\n📊 Métricas consolidadas guardadas en: {os.path.join(MODELOS_DIR, 'metricas_clasificadores.json')}")
    print("\n✨ Proceso de entrenamiento completado.")


if __name__ == "__main__":
    main()
