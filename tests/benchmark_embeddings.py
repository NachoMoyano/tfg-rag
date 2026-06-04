"""
benchmark_embeddings.py — Benchmark de modelos de embeddings para ChromaDB.

Compara la calidad de recuperación de distintos modelos de embeddings
contra las dos colecciones del sistema (conocimiento teórico y catálogo),
usando queries en varios idiomas. La evaluación es humana: el evaluador
marca cada contexto recuperado como relevante o no.

Uso (tres fases):

  1) Ingestar los datos con todos los modelos de embeddings:
       python tests/benchmark_embeddings.py --ingestar

  2) Ejecutar queries y evaluar manualmente los resultados:
       python tests/benchmark_embeddings.py --evaluar

  3) Generar informe y gráficos con las evaluaciones:
       python tests/benchmark_embeddings.py --informe
"""
import json
import os
import re
import time
import uuid

import chromadb
from chromadb.utils import embedding_functions

# Rutas y configuración
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARCHIVO_MD = os.path.join(BASE_DIR, "Data", "knowledge_base", "DataSharingKB.md")
ARCHIVO_EXCEL = os.path.join(BASE_DIR, "Data", "raw", "miguel_descriptions.xlsx")
RUTA_CHROMA_BENCH = os.path.join(BASE_DIR, "Data", "database", "chroma_benchmark")
RESULTADOS_PATH = os.path.join(os.path.dirname(__file__), "resultados_embeddings.json")
GRAFICOS_DIR = os.path.join(os.path.dirname(__file__), "graficos")

#
MODELOS_EMBEDDINGS = [
    {
        "id": "multi-MiniLM-L12",
        "nombre": "paraphrase-multilingual-MiniLM-L12-v2",
        "tipo": "Multilingüe",
    },
    {
        "id": "all-MiniLM-L6",
        "nombre": "all-MiniLM-L6-v2",
        "tipo": "Solo inglés",
    },
    {
        "id": "all-mpnet-base",
        "nombre": "all-mpnet-base-v2",
        "tipo": "Solo inglés (mayor calidad)",
    },
    {
        "id": "multi-distiluse",
        "nombre": "distiluse-base-multilingual-cased-v2",
        "tipo": "Multilingüe",
    },
]

#
# Cada query tiene: texto, idioma, colección destino, y descripción de qué
# contexto se consideraría relevante (para guiar al evaluador).
QUERIES = [
    # --- ESPAÑOL: knowledge base (teoría) ---
    {
        "texto": "¿Qué tipos de datos financieros existen en los marketplaces?",
        "idioma": "es",
        "coleccion": "general",
        "criterio": "Fragmentos sobre Financial Services Data",
    },
    {
        "texto": "Explica los modelos de precios para productos de datos",
        "idioma": "es",
        "coleccion": "general",
        "criterio": "Fragmentos sobre pricing schemes (subscription, one-off, volume)",
    },
    {
        "texto": "¿Cómo se entrega datos mediante S3 o APIs REST?",
        "idioma": "es",
        "coleccion": "general",
        "criterio": "Fragmentos sobre S3 buckets y/o REST API delivery",
    },
    {
        "texto": "Privacidad y anonimización de datos",
        "idioma": "es",
        "coleccion": "general",
        "criterio": "Fragmentos sobre k-anonymity, differential privacy, anonimización",
    },
    {
        "texto": "¿Qué formatos de archivos se usan para compartir datos?",
        "idioma": "es",
        "coleccion": "general",
        "criterio": "Fragmentos sobre formatos (Parquet, CSV, JSON, XML, etc.)",
    },
    # --- INGLÉS: knowledge base (teoría) ---
    {
        "texto": "What types of financial data are available in data marketplaces?",
        "idioma": "en",
        "coleccion": "general",
        "criterio": "Fragmentos sobre Financial Services Data",
    },
    {
        "texto": "Explain the pricing models for data products",
        "idioma": "en",
        "coleccion": "general",
        "criterio": "Fragmentos sobre pricing schemes (subscription, one-off, volume)",
    },
    {
        "texto": "How is data delivered through S3 or REST APIs?",
        "idioma": "en",
        "coleccion": "general",
        "criterio": "Fragmentos sobre S3 buckets y/o REST API delivery",
    },
    {
        "texto": "Data privacy and anonymization techniques",
        "idioma": "en",
        "coleccion": "general",
        "criterio": "Fragmentos sobre k-anonymity, differential privacy, anonimización",
    },
    {
        "texto": "What file formats are used for data sharing?",
        "idioma": "en",
        "coleccion": "general",
        "criterio": "Fragmentos sobre formatos (Parquet, CSV, JSON, XML, etc.)",
    },
    # --- ESPAÑOL: catálogo de productos ---
    {
        "texto": "Datos de tráfico urbano y movilidad",
        "idioma": "es",
        "coleccion": "catalogo",
        "criterio": "Productos relacionados con tráfico, transporte o movilidad",
    },
    {
        "texto": "Datasets sobre salud o medicina",
        "idioma": "es",
        "coleccion": "catalogo",
        "criterio": "Productos del ámbito sanitario o médico",
    },
    {
        "texto": "Información geográfica y mapas de Europa",
        "idioma": "es",
        "coleccion": "catalogo",
        "criterio": "Productos con datos geoespaciales o cartográficos europeos",
    },
    # --- INGLÉS: catálogo de productos ---
    {
        "texto": "Urban traffic and mobility datasets",
        "idioma": "en",
        "coleccion": "catalogo",
        "criterio": "Productos relacionados con tráfico, transporte o movilidad",
    },
    {
        "texto": "Healthcare or medical datasets",
        "idioma": "en",
        "coleccion": "catalogo",
        "criterio": "Productos del ámbito sanitario o médico",
    },
    {
        "texto": "Geographic information and maps of Europe",
        "idioma": "en",
        "coleccion": "catalogo",
        "criterio": "Productos con datos geoespaciales o cartográficos europeos",
    },
]

N_RESULTS_GENERAL = 3
N_RESULTS_CATALOGO = 5

#

MAX_CHARS_CHUNK = 800
SOLAPAMIENTO = 150
MIN_CHARS_CHUNK = 100


def limpiar_markdown(texto):
    texto = re.sub(r'#{1,6}\s*', '', texto)
    texto = re.sub(r'\*{1,2}(.+?)\*{1,2}', r'\1', texto)
    texto = re.sub(r'\[(.+?)\]\(.+?\)', r'\1', texto)
    texto = re.sub(r'`{1,3}.*?`{1,3}', '', texto, flags=re.DOTALL)
    texto = re.sub(r'[-*_]{3,}', '', texto)
    texto = re.sub(r'>\s?', '', texto)
    texto = re.sub(r'\n{3,}', '\n\n', texto)
    return texto.strip()


def limpiar_texto_prod(texto):
    if not texto or texto == 'nan':
        return ''
    texto = re.sub(r'#{1,6}\s*', '', texto)
    texto = re.sub(r'\*{1,2}(.+?)\*{1,2}', r'\1', texto)
    texto = re.sub(r'\[(.+?)\]\(.+?\)', r'\1', texto)
    texto = re.sub(r'\n{3,}', '\n\n', texto)
    texto = re.sub(r'\s{2,}', ' ', texto)
    return texto.strip()


def chunkear_con_solapamiento(texto, max_chars=MAX_CHARS_CHUNK, solapamiento=SOLAPAMIENTO):
    chunks = []
    inicio = 0
    while inicio < len(texto):
        fin = inicio + max_chars
        chunk = texto[inicio:fin]
        if fin < len(texto):
            ultimo_corte = max(chunk.rfind('. '), chunk.rfind('\n'))
            if ultimo_corte > max_chars // 2:
                fin = inicio + ultimo_corte + 1
                chunk = texto[inicio:fin]
        chunk_limpio = chunk.strip()
        if chunk_limpio:
            chunks.append(chunk_limpio)
        inicio = fin - solapamiento
    return chunks


#
# FASE 1: INGESTA
#

def _preparar_docs_general():
    """Lee la knowledge base y devuelve (documentos, metadatos, ids)."""
    with open(ARCHIVO_MD, 'r', encoding='utf-8') as f:
        texto_completo = f.read()

    secciones = texto_completo.split("\n## ")
    documentos, metadatos, ids = [], [], []

    for i, seccion in enumerate(secciones):
        seccion = seccion.strip()
        if not seccion:
            continue
        if i > 0 and not seccion.startswith("#"):
            seccion = "## " + seccion

        sub_chunks = [seccion] if len(seccion) <= MAX_CHARS_CHUNK else chunkear_con_solapamiento(seccion)

        for j, chunk in enumerate(sub_chunks):
            if len(chunk) < MIN_CHARS_CHUNK:
                continue
            documentos.append(limpiar_markdown(chunk))
            metadatos.append({"tipo": "teoria", "seccion_idx": i, "sub_chunk_idx": j})
            ids.append(f"teoria_{uuid.uuid4().hex[:8]}")

    return documentos, metadatos, ids


def _preparar_docs_catalogo():
    """Lee el Excel de productos y devuelve (documentos, metadatos, ids)."""
    import pandas as pd

    if not os.path.exists(ARCHIVO_EXCEL):
        print(f"  AVISO: No se encuentra {ARCHIVO_EXCEL}. Se omite el catálogo.")
        return [], [], []

    df = pd.read_excel(ARCHIVO_EXCEL)
    documentos, metadatos, ids = [], [], []

    for _, row in df.iterrows():
        proveedor = limpiar_texto_prod(str(row.get('Marketplace', '')))
        titulo = limpiar_texto_prod(str(row.get('Título', '')))
        desc_corta = limpiar_texto_prod(str(row.get('Descripción corta', '')))
        desc_larga = limpiar_texto_prod(str(row.get('Descripción larga', '')))

        if not titulo or not desc_corta:
            continue

        texto_vector = (
            f"Título: {titulo}. Proveedor: {proveedor}. "
            f"Resumen: {desc_corta}. Detalles: {desc_larga[:300]}"
        )
        documentos.append(texto_vector)
        metadatos.append({
            "proveedor": proveedor, "titulo": titulo,
            "descripcion_corta": desc_corta, "descripcion_larga": desc_larga,
        })
        ids.append(f"prod_{uuid.uuid4().hex[:8]}")

    return documentos, metadatos, ids


def fase_ingestar():
    print("--------------------------------------------------")
    print("FASE 1: INGESTA CON MÚLTIPLES MODELOS DE EMBEDDINGS")
    print("--------------------------------------------------")

    docs_gen, meta_gen, ids_gen = _preparar_docs_general()
    print(f"\n  Knowledge base: {len(docs_gen)} fragmentos")

    docs_cat, meta_cat, ids_cat = _preparar_docs_catalogo()
    print(f"  Catálogo: {len(docs_cat)} productos")

    client = chromadb.PersistentClient(path=RUTA_CHROMA_BENCH)

    for modelo in MODELOS_EMBEDDINGS:
        print(f"\n{'─' * 70}")
        print(f"  Modelo: {modelo['nombre']} ({modelo['tipo']})")
        print("--------------------------------------------------")

        ef = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=modelo["nombre"]
        )

        col_name_gen = f"bench_{modelo['id']}_general"
        col_name_cat = f"bench_{modelo['id']}_catalogo"

        # Borrar si ya existían
        for name in [col_name_gen, col_name_cat]:
            try:
                client.delete_collection(name=name)
            except Exception:
                pass

        # Ingestar knowledge base
        if docs_gen:
            col_gen = client.create_collection(name=col_name_gen, embedding_function=ef)
            print(f"    Insertando {len(docs_gen)} fragmentos en {col_name_gen}...")
            inicio = time.time()
            col_gen.add(documents=docs_gen, metadatas=meta_gen, ids=ids_gen)
            print(f"    Hecho en {time.time() - inicio:.1f}s")

        # Ingestar catálogo
        if docs_cat:
            col_cat = client.create_collection(name=col_name_cat, embedding_function=ef)
            total = len(docs_cat)
            print(f"    Insertando {total} productos en {col_name_cat}...")
            inicio = time.time()
            for i in range(0, total, 5000):
                fin = min(i + 5000, total)
                col_cat.add(
                    documents=docs_cat[i:fin],
                    metadatas=meta_cat[i:fin],
                    ids=ids_cat[i:fin],
                )
            print(f"    Hecho en {time.time() - inicio:.1f}s")

    print(f"\nIngesta completa. DB en: {RUTA_CHROMA_BENCH}")


#
# FASE 2: EVALUACIÓN HUMANA
#

def fase_evaluar():
    print("--------------------------------------------------")
    print("FASE 2: EVALUACIÓN HUMANA DE RESULTADOS")
    print("--------------------------------------------------")
    print("\nPara cada query y modelo se muestran los contextos recuperados.")
    print("Marca con 's' (relevante) o 'n' (no relevante). Enter = 's'.\n")

    client = chromadb.PersistentClient(path=RUTA_CHROMA_BENCH)

    # Cargar evaluaciones previas (para poder reanudar)
    evaluaciones = []
    if os.path.exists(RESULTADOS_PATH):
        with open(RESULTADOS_PATH, "r", encoding="utf-8") as f:
            evaluaciones = json.load(f)

    queries_ya_hechas = {
        (e["modelo_id"], e["query_texto"]) for e in evaluaciones
    }

    for modelo in MODELOS_EMBEDDINGS:
        ef = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=modelo["nombre"]
        )

        for q in QUERIES:
            if (modelo["id"], q["texto"]) in queries_ya_hechas:
                continue

            col_name = (
                f"bench_{modelo['id']}_general"
                if q["coleccion"] == "general"
                else f"bench_{modelo['id']}_catalogo"
            )

            try:
                col = client.get_collection(name=col_name, embedding_function=ef)
            except Exception:
                print(f"\n  AVISO: colección {col_name} no encontrada, omitiendo.")
                continue

            n_results = N_RESULTS_GENERAL if q["coleccion"] == "general" else N_RESULTS_CATALOGO
            inicio = time.time()
            results = col.query(query_texts=[q["texto"]], n_results=n_results)
            tiempo_ms = round((time.time() - inicio) * 1000)

            print(f"\n{'═' * 70}")
            print(f"  Modelo:    {modelo['nombre']} ({modelo['tipo']})")
            print(f"  Query:     {q['texto']}")
            print(f"  Idioma:    {q['idioma'].upper()}")
            print(f"  Colección: {q['coleccion']}")
            print(f"  Criterio:  {q['criterio']}")
            print(f"  Tiempo:    {tiempo_ms} ms")
            print("--------------------------------------------------")

            docs = results["documents"][0] if results["documents"] else []
            metas = results["metadatas"][0] if results["metadatas"] else []
            dists = results["distances"][0] if results["distances"] else []

            juicios = []
            for i, (doc, meta, dist) in enumerate(zip(docs, metas, dists)):
                print(f"\n  ── Resultado {i + 1}/{len(docs)} (distancia: {dist:.4f}) ──")

                if q["coleccion"] == "catalogo":
                    print(f"  Título:    {meta.get('titulo', 'N/A')}")
                    print(f"  Proveedor: {meta.get('proveedor', 'N/A')}")
                    print(f"  Desc:      {meta.get('descripcion_corta', 'N/A')}")
                else:
                    preview = doc[:300] + "..." if len(doc) > 300 else doc
                    print(f"  Texto:     {preview}")

                while True:
                    respuesta = input("  ¿Relevante? [S/n]: ").strip().lower()
                    if respuesta in ("", "s", "n"):
                        break
                    print("  Introduce 's', 'n' o Enter (= sí)")

                juicios.append({
                    "posicion": i + 1,
                    "relevante": respuesta != "n",
                    "distancia": round(dist, 4),
                    "preview": doc[:200],
                    "meta": {k: str(v)[:100] for k, v in meta.items()},
                })

            n_relevantes = sum(1 for j in juicios if j["relevante"])

            evaluaciones.append({
                "modelo_id": modelo["id"],
                "modelo_nombre": modelo["nombre"],
                "modelo_tipo": modelo["tipo"],
                "query_texto": q["texto"],
                "query_idioma": q["idioma"],
                "query_coleccion": q["coleccion"],
                "query_criterio": q["criterio"],
                "tiempo_ms": tiempo_ms,
                "n_recuperados": len(docs),
                "n_relevantes": n_relevantes,
                "precision": round(n_relevantes / len(docs), 2) if docs else 0,
                "resultados": juicios,
            })

            # Guardar después de cada query (para poder reanudar)
            with open(RESULTADOS_PATH, "w", encoding="utf-8") as f:
                json.dump(evaluaciones, f, ensure_ascii=False, indent=2)

            print(f"\n  >> Relevantes: {n_relevantes}/{len(docs)} "
                  f"(Precision@{len(docs)}: {n_relevantes / len(docs) * 100:.0f}%)")

    total_pendientes = (
        len(MODELOS_EMBEDDINGS) * len(QUERIES)
        - len(queries_ya_hechas)
        - sum(1 for e in evaluaciones if (e["modelo_id"], e["query_texto"]) not in queries_ya_hechas)
    )
    if total_pendientes <= 0:
        print(f"\nEvaluación completa. Resultados en: {RESULTADOS_PATH}")
    else:
        print(f"\nProgreso guardado. Quedan {total_pendientes} combinaciones.")
    print("Ejecuta --informe para generar los gráficos.")


#
# FASE 3: INFORME Y GRÁFICOS
#

def fase_informe():
    if not os.path.exists(RESULTADOS_PATH):
        print(f"No se encontró {RESULTADOS_PATH}. Ejecuta primero --evaluar.")
        return

    try:
        import matplotlib.pyplot as plt
        import numpy as np
    except ImportError:
        print("Instala las dependencias: pip install matplotlib numpy")
        return

    with open(RESULTADOS_PATH, "r", encoding="utf-8") as f:
        evaluaciones = json.load(f)

    if not evaluaciones:
        print("Sin evaluaciones.")
        return

    os.makedirs(GRAFICOS_DIR, exist_ok=True)

    #
    modelos_ids = list(dict.fromkeys(e["modelo_id"] for e in evaluaciones))
    modelos_nombres = {e["modelo_id"]: e["modelo_nombre"] for e in evaluaciones}
    idiomas = sorted(set(e["query_idioma"] for e in evaluaciones))
    colecciones = sorted(set(e["query_coleccion"] for e in evaluaciones))

    def media_precision(filtro):
        vals = [e["precision"] for e in evaluaciones if filtro(e)]
        return sum(vals) / len(vals) * 100 if vals else 0

    def media_tiempo(filtro):
        vals = [e["tiempo_ms"] for e in evaluaciones if filtro(e)]
        return sum(vals) / len(vals) if vals else 0

    #
    fig1, ax1 = plt.subplots(figsize=(10, 5))
    prec_global = [media_precision(lambda e, m=m: e["modelo_id"] == m) for m in modelos_ids]
    labels = [f"{modelos_nombres[m]}" for m in modelos_ids]
    colores = plt.cm.Set2(np.linspace(0, 1, len(modelos_ids)))

    bars = ax1.bar(labels, prec_global, color=colores, edgecolor="black", linewidth=0.5)
    for bar, p in zip(bars, prec_global):
        ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1,
                 f"{p:.0f}%", ha="center", va="bottom", fontweight="bold")
    ax1.set_ylim(0, 110)
    ax1.set_ylabel("Precision media (%)")
    ax1.set_title("Precision Global por Modelo de Embeddings", fontweight="bold")
    plt.setp(ax1.get_xticklabels(), rotation=15, ha="right", fontsize=9)
    fig1.tight_layout()
    fig1.savefig(os.path.join(GRAFICOS_DIR, "emb_precision_global.png"), dpi=150, bbox_inches="tight")

    #
    fig2, ax2 = plt.subplots(figsize=(10, 5))
    x = np.arange(len(modelos_ids))
    ancho = 0.8 / len(idiomas)
    colores_idioma = {"es": "#e94560", "en": "#0f3460"}

    for k, idioma in enumerate(idiomas):
        precs = [media_precision(lambda e, m=m, i=idioma: e["modelo_id"] == m and e["query_idioma"] == i)
                 for m in modelos_ids]
        offset = (k - len(idiomas) / 2 + 0.5) * ancho
        bars = ax2.bar(x + offset, precs, ancho, label=idioma.upper(),
                       color=colores_idioma.get(idioma, f"C{k}"), edgecolor="black", linewidth=0.5)
        for bar, p in zip(bars, precs):
            if p > 0:
                ax2.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1,
                         f"{p:.0f}%", ha="center", va="bottom", fontsize=8)

    ax2.set_xticks(x)
    ax2.set_xticklabels([modelos_nombres[m] for m in modelos_ids], rotation=15, ha="right", fontsize=9)
    ax2.set_ylim(0, 110)
    ax2.set_ylabel("Precision media (%)")
    ax2.set_title("Precision por Modelo e Idioma", fontweight="bold")
    ax2.legend()
    fig2.tight_layout()
    fig2.savefig(os.path.join(GRAFICOS_DIR, "emb_precision_idioma.png"), dpi=150, bbox_inches="tight")

    #
    fig3, ax3 = plt.subplots(figsize=(10, 5))
    colores_col = {"general": "#533483", "catalogo": "#1b4332"}

    for k, col in enumerate(colecciones):
        precs = [media_precision(lambda e, m=m, c=col: e["modelo_id"] == m and e["query_coleccion"] == c)
                 for m in modelos_ids]
        offset = (k - len(colecciones) / 2 + 0.5) * ancho
        bars = ax3.bar(x + offset, precs, ancho, label=col.capitalize(),
                       color=colores_col.get(col, f"C{k}"), edgecolor="black", linewidth=0.5)
        for bar, p in zip(bars, precs):
            if p > 0:
                ax3.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1,
                         f"{p:.0f}%", ha="center", va="bottom", fontsize=8)

    ax3.set_xticks(x)
    ax3.set_xticklabels([modelos_nombres[m] for m in modelos_ids], rotation=15, ha="right", fontsize=9)
    ax3.set_ylim(0, 110)
    ax3.set_ylabel("Precision media (%)")
    ax3.set_title("Precision por Modelo y Colección", fontweight="bold")
    ax3.legend()
    fig3.tight_layout()
    fig3.savefig(os.path.join(GRAFICOS_DIR, "emb_precision_coleccion.png"), dpi=150, bbox_inches="tight")

    #
    fig4, ax4 = plt.subplots(figsize=(10, 5))
    tiempos = [media_tiempo(lambda e, m=m: e["modelo_id"] == m) for m in modelos_ids]

    bars = ax4.bar(labels, tiempos, color=colores, edgecolor="black", linewidth=0.5)
    for bar, t in zip(bars, tiempos):
        ax4.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1,
                 f"{t:.0f} ms", ha="center", va="bottom", fontweight="bold")
    ax4.set_ylabel("Tiempo medio de query (ms)")
    ax4.set_title("Latencia de Búsqueda por Modelo de Embeddings", fontweight="bold")
    plt.setp(ax4.get_xticklabels(), rotation=15, ha="right", fontsize=9)
    fig4.tight_layout()
    fig4.savefig(os.path.join(GRAFICOS_DIR, "emb_tiempos.png"), dpi=150, bbox_inches="tight")

    #
    print("\n" + "=" * 90)
    print("INFORME DE EVALUACIÓN DE MODELOS DE EMBEDDINGS")
    print("--------------------------------------------------")

    print(f"\n{'Modelo':<40} {'Idioma':>7} {'Col.':>10} {'Prec.':>8} {'Tiempo':>10}")
    print("-" * 90)

    for modelo_id in modelos_ids:
        for idioma in idiomas:
            for col in colecciones:
                p = media_precision(
                    lambda e, m=modelo_id, i=idioma, c=col:
                        e["modelo_id"] == m and e["query_idioma"] == i and e["query_coleccion"] == c
                )
                t = media_tiempo(
                    lambda e, m=modelo_id, i=idioma, c=col:
                        e["modelo_id"] == m and e["query_idioma"] == i and e["query_coleccion"] == c
                )
                n = sum(1 for e in evaluaciones
                        if e["modelo_id"] == modelo_id and e["query_idioma"] == idioma
                        and e["query_coleccion"] == col)
                if n > 0:
                    print(f"  {modelos_nombres[modelo_id]:<38} {idioma.upper():>7} {col:>10} "
                          f"{p:>7.0f}% {t:>8.0f} ms")
        print()

    # Resumen global
    print("--------------------------------------------------")
    print(f"{'RESUMEN GLOBAL':<40} {'Precision':>10} {'Tiempo':>10} {'Queries':>10}")
    print("-" * 90)
    for modelo_id in modelos_ids:
        p = media_precision(lambda e, m=modelo_id: e["modelo_id"] == m)
        t = media_tiempo(lambda e, m=modelo_id: e["modelo_id"] == m)
        n = sum(1 for e in evaluaciones if e["modelo_id"] == modelo_id)
        print(f"  {modelos_nombres[modelo_id]:<38} {p:>9.0f}% {t:>8.0f} ms {n:>10}")
    print("--------------------------------------------------")

    print(f"\nGráficos guardados en: {GRAFICOS_DIR}/")
    plt.show()


#

if __name__ == "__main__":
    # Descomenta la fase que quieras ejecutar:
    
    # 1. Meter los datos en la BD vectorial con todos los modelos
    # fase_ingestar()
    
    # 2. Hacer las consultas y evaluarlas a mano
    # fase_evaluar()
    
    # 3. Generar los graficos de resultados
    # fase_informe()
    
    print("Abre el script y descomenta la fase que quieras ejecutar (ingestar, evaluar o informe).")
