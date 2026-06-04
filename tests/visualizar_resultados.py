"""
visualizar_resultados.py

Busca todos los archivos resultados_*.json e informe_calidad_*.json,
y genera graficos comparativos entre modelos.

Uso:
  python tests/visualizar_resultados.py
"""
import glob
import json
import os
import matplotlib.pyplot as plt
import numpy as np

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GRAFICOS_DIR = os.path.join(os.path.dirname(__file__), "graficos")

# Mapeamos cada pregunta a su categoria
CATEGORIAS_POR_ID = {
    1: "GENERAL", 2: "GENERAL", 3: "GENERAL",
    4: "CATALOGO_BUSQUEDA", 5: "CATALOGO_BUSQUEDA", 6: "CATALOGO_BUSQUEDA",
    7: "CATALOGO_DETALLE", 8: "CATALOGO_DETALLE", 9: "CATALOGO_DETALLE",
}

NOMBRES_CATEGORIAS = {
    "GENERAL": "General (Teoría)",
    "CATALOGO_BUSQUEDA": "Catálogo (Búsqueda)",
    "CATALOGO_DETALLE": "Catálogo (Detalle)",
}

ORDEN_CATS = ["GENERAL", "CATALOGO_BUSQUEDA", "CATALOGO_DETALLE"]


def detectar_modelos():
    """Busca todos los pares de archivos resultados_X.json + informe_calidad_X.json"""
    patron = os.path.join(BASE_DIR, "resultados_*.json")
    archivos = glob.glob(patron)

    modelos = []
    for ruta_rend in archivos:
        nombre_archivo = os.path.basename(ruta_rend)
        # Extraemos el nombre del modelo: resultados_llama3.json -> llama3
        nombre_modelo = nombre_archivo.replace("resultados_", "").replace(".json", "")

        ruta_calidad = os.path.join(BASE_DIR, f"informe_calidad_{nombre_modelo}.json")
        if os.path.exists(ruta_calidad):
            modelos.append({
                "nombre": nombre_modelo,
                "ruta_rendimiento": ruta_rend,
                "ruta_calidad": ruta_calidad,
            })
        else:
            print(f"Aviso: no se encontro informe_calidad_{nombre_modelo}.json, se omite {nombre_modelo}")

    return modelos


def cargar_datos_modelo(modelo_info):
    """Carga y junta los datos de rendimiento y calidad de un modelo."""
    with open(modelo_info["ruta_rendimiento"], "r", encoding="utf-8") as f:
        rendimiento = json.load(f)
    with open(modelo_info["ruta_calidad"], "r", encoding="utf-8") as f:
        calidad = json.load(f)

    calidad_por_id = {c["id"]: c for c in calidad}

    datos = []
    for r in rendimiento:
        if r.get("estado") != "OK":
            continue
        c = calidad_por_id.get(r["id"], {})
        datos.append({
            "id": r["id"],
            "categoria": CATEGORIAS_POR_ID.get(r["id"], "DESCONOCIDA"),
            "latencia": r["latencia"],
            "tps": r["tps"],
            "fidelidad": c.get("fidelidad", 0),
            "relevancia": c.get("relevancia", 0),
        })
    return datos


def calcular_medias_globales(datos):
    """Calcula medias globales (sin separar por categoria)."""
    if not datos:
        return {"latencia": 0, "tps": 0, "fidelidad": 0, "relevancia": 0}
    return {
        "latencia": np.mean([d["latencia"] for d in datos]),
        "tps": np.mean([d["tps"] for d in datos]),
        "fidelidad": np.mean([d["fidelidad"] for d in datos]) * 100,
        "relevancia": np.mean([d["relevancia"] for d in datos]) * 100,
    }


def generar_graficos():
    modelos = detectar_modelos()
    if not modelos:
        print("No se encontraron archivos de resultados.")
        print(f"Busqué en: {BASE_DIR}/resultados_*.json")
        return

    os.makedirs(GRAFICOS_DIR, exist_ok=True)

    # Cargamos datos de cada modelo
    nombres = []
    medias_por_modelo = []
    for m in modelos:
        datos = cargar_datos_modelo(m)
        media = calcular_medias_globales(datos)
        nombres.append(m["nombre"])
        medias_por_modelo.append(media)

    print(f"Modelos encontrados: {', '.join(nombres)}")

    colores = plt.cm.Set2(np.linspace(0, 1, len(nombres)))

    # --- Grafico 1: Barras comparativas (4 metricas) ---
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    fig.suptitle("Comparativa de Modelos: Rendimiento y Calidad", fontsize=14, fontweight="bold")

    metricas = [
        ("fidelidad", "Fidelidad (%)", "%", axes[0][0]),
        ("relevancia", "Relevancia (%)", "%", axes[0][1]),
        ("latencia", "Latencia (s)", "s", axes[1][0]),
        ("tps", "TPS (tokens/s)", "", axes[1][1]),
    ]

    for clave, titulo, sufijo, ax in metricas:
        vals = [m[clave] for m in medias_por_modelo]
        bars = ax.bar(nombres, vals, color=colores, edgecolor="black", linewidth=0.5)
        for bar, v in zip(bars, vals):
            texto = f"{v:.0f}{sufijo}" if sufijo == "%" else f"{v:.1f}{sufijo}"
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + max(vals) * 0.02,
                    texto, ha="center", fontweight="bold", fontsize=10)
        ax.set_ylabel(titulo)
        ax.set_title(titulo)
        if sufijo == "%":
            ax.set_ylim(0, 115)

    fig.tight_layout()
    fig.savefig(os.path.join(GRAFICOS_DIR, "comparativa_modelos.png"), dpi=150, bbox_inches="tight")

    # --- Grafico 2: Matriz rendimiento vs calidad ---
    metricas_nombres = ["Latencia (s)", "TPS", "Fidelidad (%)", "Relevancia (%)"]
    matriz = []
    for m in medias_por_modelo:
        matriz.append([m["latencia"], m["tps"], m["fidelidad"], m["relevancia"]])
    matriz = np.array(matriz)

    # Normalizamos cada columna de 0 a 1 para el color
    norm = np.zeros_like(matriz)
    for j in range(matriz.shape[1]):
        col = matriz[:, j]
        rango = col.max() - col.min()
        if rango > 0:
            norm[:, j] = (col - col.min()) / rango
        else:
            norm[:, j] = 1.0
    # En latencia, menor es mejor
    norm[:, 0] = 1.0 - norm[:, 0]

    fig2, ax2 = plt.subplots(figsize=(9, max(3, len(nombres) * 1.2)))
    ax2.imshow(norm, cmap="RdYlGn", aspect="auto", vmin=0, vmax=1)

    ax2.set_xticks(range(len(metricas_nombres)))
    ax2.set_xticklabels(metricas_nombres, fontsize=10)
    ax2.set_yticks(range(len(nombres)))
    ax2.set_yticklabels(nombres, fontsize=11)

    for i in range(len(nombres)):
        for j in range(len(metricas_nombres)):
            fmt = ".1f" if j <= 1 else ".0f"
            val = f"{matriz[i, j]:{fmt}}"
            color_texto = "white" if norm[i, j] < 0.4 else "black"
            ax2.text(j, i, val, ha="center", va="center", fontsize=12,
                     fontweight="bold", color=color_texto)

    ax2.set_title("Matriz Rendimiento vs Calidad por Modelo\n(verde = mejor, rojo = peor)",
                  fontsize=12, fontweight="bold")
    fig2.tight_layout()
    fig2.savefig(os.path.join(GRAFICOS_DIR, "matriz_rendimiento_calidad.png"), dpi=150, bbox_inches="tight")

    # --- Resumen por consola ---
    print(f"\n{'Modelo':<20} {'Latencia':>10} {'TPS':>10} {'Fidelidad':>12} {'Relevancia':>12}")
    print("-" * 65)
    for nombre, m in zip(nombres, medias_por_modelo):
        print(f"  {nombre:<18} {m['latencia']:>8.1f}s {m['tps']:>9.1f} {m['fidelidad']:>10.0f}% {m['relevancia']:>10.0f}%")
    print("-" * 65)

    print(f"\nGraficos guardados en: {GRAFICOS_DIR}/")
    plt.show()


if __name__ == "__main__":
    generar_graficos()
