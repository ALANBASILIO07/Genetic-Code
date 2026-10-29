import itertools
import random
import time
import math
import matplotlib.pyplot as plt
from matplotlib import gridspec

# ------------------------
# Funciones de apoyo
# ------------------------
def generar_coordenadas(n, xmin=0, xmax=20, ymin=0, ymax=20, seed=None):
    if seed is not None:
        random.seed(seed)
    return [(random.uniform(xmin, xmax), random.uniform(ymin, ymax)) for _ in range(n)]

def distancia_euclidiana(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])

def generar_matriz_distancias(coords, redondeo=True):
    n = len(coords)
    M = [[0]*n for _ in range(n)]
    for i in range(n):
        for j in range(i+1, n):
            d = distancia_euclidiana(coords[i], coords[j])
            if redondeo:
                d = int(round(d))
            M[i][j] = M[j][i] = d
    return M

def calcular_distancia(ruta, M):
    dist = 0
    for i in range(len(ruta) - 1):
        dist += M[ruta[i]][ruta[i+1]]
    dist += M[ruta[-1]][ruta[0]]
    return dist

def tsp_fuerza_bruta(M):
    n = len(M)
    indices = list(range(n))
    mejor_ruta = None
    mejor_dist = float("inf")

    t0 = time.perf_counter()
    for perm in itertools.permutations(indices[1:]):
        ruta = (0,) + perm
        d = calcular_distancia(ruta, M)
        if d < mejor_dist:
            mejor_dist = d
            mejor_ruta = ruta
    t1 = time.perf_counter()

    tiempo_ms = (t1 - t0) * 1000.0
    return list(mejor_ruta), mejor_dist, tiempo_ms

# ------------------------
# Visualización ordenada
# ------------------------
def mostrar_resultados_en_layout(M, nombres, coords, ruta, dist_min, tiempo_ms):
    n = len(nombres)

    fig = plt.figure(figsize=(12, 7))
    gs = gridspec.GridSpec(2, 2, height_ratios=[3, 1], width_ratios=[1, 1.4], hspace=0.3, wspace=0.15)

    # ----- Panel (0,0): Matriz -----
    ax_tabla = fig.add_subplot(gs[0, 0])
    ax_tabla.axis('off')
    tabla = ax_tabla.table(
        cellText=M,
        colLabels=nombres,
        rowLabels=nombres,
        cellLoc='center',
        loc='center'
    )
    tabla.auto_set_font_size(False)
    tabla.set_fontsize(9)
    tabla.scale(1.05, 1.2)
    ax_tabla.set_title("Matriz de Distancias", fontweight='bold', pad=8)

    # ----- Panel (0,1): Grafo -----
    ax_grafo = fig.add_subplot(gs[0, 1])
    ax_grafo.set_title("Mapa de Nodos y Ruta Óptima", fontweight='bold', pad=8)

    # Conexiones en gris
    for i in range(n):
        x_i, y_i = coords[i]
        for j in range(i+1, n):
            x_j, y_j = coords[j]
            ax_grafo.plot([x_i, x_j], [y_i, y_j], linestyle='--', linewidth=0.8, color='lightgray', zorder=1)

    # Ruta óptima en rojo
    for k in range(len(ruta)):
        a = ruta[k]
        b = ruta[(k+1) % n]
        ax_grafo.plot([coords[a][0], coords[b][0]],
                      [coords[a][1], coords[b][1]],
                      linewidth=2.8, color='red', zorder=3)

    # Nodos
    for i, (x, y) in enumerate(coords):
        ax_grafo.scatter(x, y, s=220, edgecolors='black', facecolors='skyblue', zorder=4)
        ax_grafo.text(x, y + 0.6, nombres[i], ha='center', fontsize=10, fontweight='bold', zorder=5)

    # Orden de visita
    for paso, idx in enumerate(ruta):
        x, y = coords[idx]
        ax_grafo.text(x, y - 0.8, f"{paso+1}", ha='center', fontsize=9, color='darkred', zorder=6)

    ax_grafo.set_aspect('equal')
    ax_grafo.axis('off')

    # ----- Panel (1,0) y (1,1): Resultados -----
    ax_result = fig.add_subplot(gs[1, :])
    ax_result.axis('off')
    ruta_nombres = " → ".join(nombres[i] for i in ruta) + f" → {nombres[ruta[0]]}"

    texto_resultados = (
        f"Mejor ruta: {ruta_nombres}\n"
        f"Distancia mínima: {dist_min}\n"
        f"Tiempo de ejecución: {tiempo_ms:.3f} ms"
    )
    ax_result.text(0.5, 0.5, texto_resultados,
                   fontsize=12, fontweight='bold',
                   ha='center', va='center',
                   bbox=dict(facecolor='lightyellow', edgecolor='black', boxstyle='round,pad=1'))

    plt.suptitle("Problema del Agente Viajero (Fuerza Bruta)", fontsize=14, fontweight='bold')
    plt.show()

# ------------------------
# Programa principal
# ------------------------
if __name__ == "__main__":
    nombres_ciudades = ["Toluca", "CDMX", "Monterrey", "Guadalajara", "Puebla", "Sonora", "Chihuahua", "Guanajuato", "Campeche"]
    N = len(nombres_ciudades)

    coordenadas = generar_coordenadas(N, seed=42)
    M = generar_matriz_distancias(coordenadas)

    ruta, dist_min, tiempo_ms = tsp_fuerza_bruta(M)

    print("Mejor ruta:", " → ".join(nombres_ciudades[i] for i in ruta), "→", nombres_ciudades[ruta[0]])
    print("Distancia mínima:", dist_min)
    print(f"Tiempo de ejecución: {tiempo_ms:.3f} ms")

    mostrar_resultados_en_layout(M, nombres_ciudades, coordenadas, ruta, dist_min, tiempo_ms)
