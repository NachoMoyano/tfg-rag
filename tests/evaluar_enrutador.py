"""
evaluar_enrutador.py — Benchmark multi-modelo del enrutador semántico.

Uso (dos fases):
  1) Cargar un modelo en LM Studio y ejecutar:
       python tests/evaluar_enrutador.py --modelo "qwen2.5-3b"
     Repetir con cada modelo. Los resultados se acumulan en resultados_enrutador.json.

  2) Cuando hayas probado todos los modelos, generar los gráficos:
       python tests/evaluar_enrutador.py --graficos
     Genera matrices de confusión y comparativa de tiempos en tests/graficos/.
"""
import argparse
import json
import os
import time

import requests

LM_STUDIO_URL = "http://localhost:1234/v1/chat/completions"
RESULTADOS_PATH = os.path.join(os.path.dirname(__file__), "resultados_enrutador.json")
GRAFICOS_DIR = os.path.join(os.path.dirname(__file__), "graficos")

CATEGORIAS = ["GENERAL", "CATALOGO_BUSQUEDA", "CATALOGO_DETALLE"]

# ── Dataset de evaluación (20 prompts + ground truth) ────────────────────────
DATASET = [
    # BÚSQUEDA / EXPLORACIÓN
    {"prompt": "Necesito un listado de productos sobre tráfico urbano.", "truth": "CATALOGO_BUSQUEDA"},
    {"prompt": "¿Qué datasets tenéis de la empresa DataRade?", "truth": "CATALOGO_BUSQUEDA"},
    {"prompt": "Busco información geográfica y mapas de Europa.", "truth": "CATALOGO_BUSQUEDA"},
    {"prompt": "Muéstrame opciones relacionadas con el clima y la lluvia.", "truth": "CATALOGO_BUSQUEDA"},
    {"prompt": "¿Hay algo en el catálogo sobre transacciones financieras?", "truth": "CATALOGO_BUSQUEDA"},
    {"prompt": "Quiero ver qué tenéis de inteligencia artificial.", "truth": "CATALOGO_BUSQUEDA"},
    {"prompt": "Fíltrame los datasets que sean de salud o medicina.", "truth": "CATALOGO_BUSQUEDA"},
    # DETALLE / ZOOM
    {"prompt": "Dame todas las características del producto EU POI Data.", "truth": "CATALOGO_DETALLE"},
    {"prompt": "Háblame más sobre la segunda opción de la tabla.", "truth": "CATALOGO_DETALLE"},
    {"prompt": "¿Quién es el proveedor exacto del Spanish Labour Market y qué incluye?", "truth": "CATALOGO_DETALLE"},
    {"prompt": "Quiero los detalles técnicos del dataset de Similarweb.", "truth": "CATALOGO_DETALLE"},
    {"prompt": "Amplía la información del último producto que mencionaste.", "truth": "CATALOGO_DETALLE"},
    {"prompt": "¿Cuál es la descripción larga del pack de datos sintéticos?", "truth": "CATALOGO_DETALLE"},
    {"prompt": "Analiza a fondo el producto número 3.", "truth": "CATALOGO_DETALLE"},
    # GENERAL / TEORÍA
    {"prompt": "Explícame el concepto de Data Mesh.", "truth": "GENERAL"},
    {"prompt": "¿Qué significa que un dataset esté anonimizado?", "truth": "GENERAL"},
    {"prompt": "Tengo una duda teórica: ¿qué es la latencia en la entrega de datos?", "truth": "GENERAL"},
    {"prompt": "Diferencias a nivel conceptual entre Data Warehouse y Data Lake.", "truth": "GENERAL"},
    {"prompt": "¿Cómo funciona el modelo de precios basado en consumo?", "truth": "GENERAL"},
    {"prompt": "Define qué es la gobernanza de datos.", "truth": "GENERAL"},
]

PROMPT_TEMPLATE = """\
Clasifica la siguiente pregunta del usuario en UNA de estas TRES categorías exactas: \
'GENERAL', 'CATALOGO_BUSQUEDA' o 'CATALOGO_DETALLE'. \
No devuelvas ningún otro texto, solo la etiqueta.

Ejemplo 1:
Pregunta: Busco datos de economía en España o mercado laboral.
Clasificación: CATALOGO_BUSQUEDA

Ejemplo 2:
Pregunta: ¿Qué diferencia hay entre usar una API REST o S3? Explícame la teoría.
Clasificación: GENERAL

Ejemplo 3:
Pregunta: Dame los detalles, características y proveedor del producto Synthetic Data Pack.
Clasificación: CATALOGO_DETALLE

Ejemplo 4:
Pregunta: ¿Tenéis algún dataset sobre el paro o pacientes de salud?
Clasificación: CATALOGO_BUSQUEDA

Ejemplo 5:
Pregunta: Quiero profundizar en la primera opción que me has dado.
Clasificación: CATALOGO_DETALLE

Ejemplo 6:
Pregunta: ¿Qué es la k-anonymity en privacidad de datos?
Clasificación: GENERAL

Pregunta: {pregunta}
Clasificación:"""


def enrutador_semantico(pregunta: str) -> str:
    payload = {
        "messages": [{"role": "user", "content": PROMPT_TEMPLATE.format(pregunta=pregunta)}],
        "temperature": 0.0,
        "max_tokens": 10,
    }
    try:
        resp = requests.post(LM_STUDIO_URL, json=payload, timeout=120)
        resp.raise_for_status()
        decision = resp.json()["choices"][0]["message"]["content"].strip().upper()
        if "GENERAL" in decision:
            return "GENERAL"
        elif "DETALLE" in decision:
            return "CATALOGO_DETALLE"
        else:
            return "CATALOGO_BUSQUEDA"
    except Exception as e:
        return f"ERROR ({e})"


# ── Fase 1: ejecutar benchmark para un modelo ────────────────────────────────

def ejecutar_benchmark(nombre_modelo: str):
    print(f"\nBenchmark del enrutador con modelo: {nombre_modelo}")
    print(f"Dataset: {len(DATASET)} prompts\n")

    resultados = []
    aciertos = 0

    for i, test in enumerate(DATASET, 1):
        print(f"  [{i}/{len(DATASET)}] ...", end="\r")
        inicio = time.time()
        prediccion = enrutador_semantico(test["prompt"])
        tiempo_ms = round((time.time() - inicio) * 1000)

        correcto = prediccion == test["truth"]
        if correcto:
            aciertos += 1

        resultados.append({
            "prompt": test["prompt"],
            "esperado": test["truth"],
            "prediccion": prediccion,
            "correcto": correcto,
            "tiempo_ms": tiempo_ms,
        })

    accuracy = aciertos / len(DATASET) * 100
    tiempos = [r["tiempo_ms"] for r in resultados]
    tiempo_medio = sum(tiempos) / len(tiempos)

    entrada_modelo = {
        "modelo": nombre_modelo,
        "accuracy": round(accuracy, 2),
        "tiempo_medio_ms": round(tiempo_medio, 1),
        "aciertos": aciertos,
        "total": len(DATASET),
        "detalle": resultados,
    }

    # Acumular en JSON
    todos = []
    if os.path.exists(RESULTADOS_PATH):
        with open(RESULTADOS_PATH, "r", encoding="utf-8") as f:
            todos = json.load(f)

    # Reemplazar si el modelo ya existe
    todos = [m for m in todos if m["modelo"] != nombre_modelo]
    todos.append(entrada_modelo)

    with open(RESULTADOS_PATH, "w", encoding="utf-8") as f:
        json.dump(todos, f, ensure_ascii=False, indent=2)

    # Informe por consola
    print(" " * 40, end="\r")
    print("-" * 70)
    print(f"MODELO: {nombre_modelo}")
    print("-" * 70)
    for r in resultados:
        icono = "OK" if r["correcto"] else "FALLO"
        marca = "  " if r["correcto"] else ">> "
        print(f"  {marca} [{icono}] {r['esperado']:20s} -> {r['prediccion']:20s} ({r['tiempo_ms']}ms)")
        if not r["correcto"]:
            print(f"         Prompt: {r['prompt']}")
    print("-" * 70)
    print(f"  Accuracy: {aciertos}/{len(DATASET)} ({accuracy:.1f}%)")
    print(f"  Tiempo medio: {tiempo_medio:.0f} ms")
    print(f"  Resultados guardados en: {RESULTADOS_PATH}")
    print("-" * 70)


# ── Fase 2: generar matrices de confusión y gráficos ─────────────────────────

def generar_graficos():
    if not os.path.exists(RESULTADOS_PATH):
        print(f"No se encontró {RESULTADOS_PATH}. Ejecuta primero los benchmarks.")
        return

    try:
        from sklearn.metrics import confusion_matrix, ConfusionMatrixDisplay
        import matplotlib.pyplot as plt
        import numpy as np
    except ImportError:
        print("Instala las dependencias: pip install scikit-learn matplotlib")
        return

    with open(RESULTADOS_PATH, "r", encoding="utf-8") as f:
        todos = json.load(f)

    if not todos:
        print("El archivo de resultados está vacío.")
        return

    os.makedirs(GRAFICOS_DIR, exist_ok=True)
    n_modelos = len(todos)

    # ── 1. Una matriz de confusión por modelo ─────────────────────────────
    fig_cm, axes_cm = plt.subplots(1, n_modelos, figsize=(6 * n_modelos, 5))
    if n_modelos == 1:
        axes_cm = [axes_cm]

    for ax, datos_modelo in zip(axes_cm, todos):
        y_true = [r["esperado"] for r in datos_modelo["detalle"]]
        y_pred = [r["prediccion"] for r in datos_modelo["detalle"]]

        cm = confusion_matrix(y_true, y_pred, labels=CATEGORIAS)
        disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=CATEGORIAS)
        disp.plot(ax=ax, cmap="Blues", colorbar=False, values_format="d")
        ax.set_title(f"{datos_modelo['modelo']}\nAccuracy: {datos_modelo['accuracy']}%", fontsize=11)
        ax.set_xlabel("Predicción")
        ax.set_ylabel("Real")
        plt.setp(ax.get_xticklabels(), rotation=30, ha="right", fontsize=8)
        plt.setp(ax.get_yticklabels(), fontsize=8)

    fig_cm.suptitle("Matrices de Confusión — Enrutador Semántico", fontsize=14, fontweight="bold")
    fig_cm.tight_layout()
    path_cm = os.path.join(GRAFICOS_DIR, "matrices_confusion.png")
    fig_cm.savefig(path_cm, dpi=150, bbox_inches="tight")
    print(f"Matrices de confusión guardadas en: {path_cm}")

    # ── 2. Comparativa de accuracy ────────────────────────────────────────
    modelos = [d["modelo"] for d in todos]
    accuracies = [d["accuracy"] for d in todos]
    tiempos_medios = [d["tiempo_medio_ms"] for d in todos]

    fig_comp, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

    colores = plt.cm.Set2(np.linspace(0, 1, n_modelos))
    bars1 = ax1.bar(modelos, accuracies, color=colores, edgecolor="black", linewidth=0.5)
    ax1.set_ylim(0, 105)
    ax1.set_ylabel("Accuracy (%)")
    ax1.set_title("Accuracy por Modelo")
    ax1.axhline(y=100, color="green", linestyle="--", alpha=0.3, label="100%")
    for bar, acc in zip(bars1, accuracies):
        ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1,
                 f"{acc}%", ha="center", va="bottom", fontsize=10, fontweight="bold")
    plt.setp(ax1.get_xticklabels(), rotation=20, ha="right")

    bars2 = ax2.bar(modelos, tiempos_medios, color=colores, edgecolor="black", linewidth=0.5)
    ax2.set_ylabel("Tiempo medio (ms)")
    ax2.set_title("Latencia media por Modelo")
    for bar, t in zip(bars2, tiempos_medios):
        ax2.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 5,
                 f"{t:.0f} ms", ha="center", va="bottom", fontsize=10, fontweight="bold")
    plt.setp(ax2.get_xticklabels(), rotation=20, ha="right")

    fig_comp.suptitle("Comparativa de Modelos — Enrutador Semántico", fontsize=14, fontweight="bold")
    fig_comp.tight_layout()
    path_comp = os.path.join(GRAFICOS_DIR, "comparativa_modelos.png")
    fig_comp.savefig(path_comp, dpi=150, bbox_inches="tight")
    print(f"Comparativa guardada en: {path_comp}")

    # ── 3. Distribución de tiempos (boxplot) ──────────────────────────────
    fig_box, ax3 = plt.subplots(figsize=(8, 5))
    data_tiempos = []
    for d in todos:
        data_tiempos.append([r["tiempo_ms"] for r in d["detalle"]])

    bp = ax3.boxplot(data_tiempos, labels=modelos, patch_artist=True)
    for patch, color in zip(bp["boxes"], colores):
        patch.set_facecolor(color)
    ax3.set_ylabel("Tiempo (ms)")
    ax3.set_title("Distribución de Tiempos de Clasificación por Modelo",
                   fontsize=13, fontweight="bold")
    plt.setp(ax3.get_xticklabels(), rotation=20, ha="right")
    fig_box.tight_layout()
    path_box = os.path.join(GRAFICOS_DIR, "distribucion_tiempos.png")
    fig_box.savefig(path_box, dpi=150, bbox_inches="tight")
    print(f"Distribución de tiempos guardada en: {path_box}")

    # ── 4. Resumen en consola ─────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("RESUMEN COMPARATIVO")
    print("=" * 70)
    print(f"{'Modelo':<25} {'Accuracy':>10} {'Tiempo medio':>15} {'Errores':>10}")
    print("-" * 70)
    for d in todos:
        errores = d["total"] - d["aciertos"]
        print(f"{d['modelo']:<25} {d['accuracy']:>9.1f}% {d['tiempo_medio_ms']:>12.0f} ms {errores:>10}")
    print("=" * 70)

    plt.show()


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Benchmark multi-modelo del enrutador semántico")
    parser.add_argument("--modelo", type=str, help="Nombre del modelo cargado en LM Studio (ej: 'qwen2.5-3b')")
    parser.add_argument("--graficos", action="store_true", help="Generar matrices de confusión y gráficos comparativos")
    args = parser.parse_args()

    if args.graficos:
        generar_graficos()
    elif args.modelo:
        ejecutar_benchmark(args.modelo)
    else:
        parser.print_help()
