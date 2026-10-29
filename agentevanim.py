import itertools
import random
import time
import math
import matplotlib.pyplot as plt
from matplotlib import gridspec
from matplotlib.animation import FuncAnimation

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
# Visualización y animación en una sola ventana
# ------------------------
def mostrar_todo_con_animacion(M, nombres, coords, ruta_optima, dist_min, tiempo_ms):
    n = len(nombres)
    
    # Crear la figura y GridSpec
    fig = plt.figure(figsize=(14, 10))
    gs = gridspec.GridSpec(3, 2, height_ratios=[2, 2, 1], width_ratios=[1, 1.5], hspace=0.35, wspace=0.2)
    
    # ----- Panel (0,0) Matriz -----
    ax_tabla = fig.add_subplot(gs[0, 0])
    ax_tabla.axis('off')
    tabla = ax_tabla.table(cellText=M, colLabels=nombres, rowLabels=nombres, cellLoc='center', loc='center')
    tabla.auto_set_font_size(False)
    tabla.set_fontsize(9)
    tabla.scale(1.05, 1.2)
    ax_tabla.set_title("Matriz de Distancias", fontweight='bold', pad=8)
    
    # ----- Panel (0,1) Nodos -----
    ax_grafo = fig.add_subplot(gs[0, 1])
    ax_grafo.set_title("Mapa de Nodos", fontweight='bold', pad=8)
    for i in range(n):
        x_i, y_i = coords[i]
        for j in range(i+1, n):
            x_j, y_j = coords[j]
            ax_grafo.plot([x_i, x_j], [y_i, y_j], linestyle='--', linewidth=0.8, color='lightgray', zorder=1)
    for i, (x, y) in enumerate(coords):
        ax_grafo.scatter(x, y, s=220, edgecolors='black', facecolors='skyblue', zorder=4)
        ax_grafo.text(x, y + 0.6, nombres[i], ha='center', fontsize=10, fontweight='bold', zorder=5)
    ax_grafo.set_aspect('equal')
    ax_grafo.axis('off')
    
    # ----- Panel (1,0) Animación Ruta no óptima -----
    ax_no_opt = fig.add_subplot(gs[1, 0])
    ax_no_opt.set_title("Ruta No Óptima (ejemplo)", fontweight='bold', pad=8)
    for i, (x, y) in enumerate(coords):
        ax_no_opt.scatter(x, y, s=180, c='lightgray', edgecolors='black')
        ax_no_opt.text(x, y + 0.3, nombres[i], fontsize=9, ha='center')
    ax_no_opt.set_aspect('equal')
    ax_no_opt.axis('off')
    linea_no_opt, = ax_no_opt.plot([], [], 'gray', lw=2)
    
    # Crear una ruta no óptima: simplemente invertir la ruta óptima (solo para animar)
    ruta_no_opt = ruta_optima[::-1]
    
    # ----- Panel (1,1) Animación Ruta óptima -----
    ax_opt = fig.add_subplot(gs[1, 1])
    ax_opt.set_title("Ruta Óptima", fontweight='bold', pad=8)
    for i, (x, y) in enumerate(coords):
        ax_opt.scatter(x, y, s=180, c='skyblue', edgecolors='black')
        ax_opt.text(x, y + 0.3, nombres[i], fontsize=9, ha='center')
    ax_opt.set_aspect('equal')
    ax_opt.axis('off')
    linea_opt, = ax_opt.plot([], [], 'red', lw=2)
    
    # ----- Panel (2,0:2) Resultados -----
    ax_result = fig.add_subplot(gs[2, :])
    ax_result.axis('off')
    ruta_nombres = " → ".join(nombres[i] for i in ruta_optima) + f" → {nombres[ruta_optima[0]]}"
    texto_resultados = (
        f"Mejor ruta: {ruta_nombres}\n"
        f"Distancia mínima: {dist_min}\n"
        f"Tiempo de ejecución: {tiempo_ms:.3f} ms"
    )
    ax_result.text(0.5, 0.5, texto_resultados,
                   fontsize=12, fontweight='bold',
                   ha='center', va='center',
                   bbox=dict(facecolor='lightyellow', edgecolor='black', boxstyle='round,pad=1'))
    
    # ----- Funciones para animación -----
    def init():
        linea_no_opt.set_data([], [])
        linea_opt.set_data([], [])
        return linea_no_opt, linea_opt

    def update(frame):
        paso = frame + 1
        # Ruta no óptima
        xdata_no = [coords[i][0] for i in ruta_no_opt[:paso]]
        ydata_no = [coords[i][1] for i in ruta_no_opt[:paso]]
        if paso == len(ruta_no_opt):
            xdata_no.append(coords[ruta_no_opt[0]][0])
            ydata_no.append(coords[ruta_no_opt[0]][1])
        linea_no_opt.set_data(xdata_no, ydata_no)
        # Ruta óptima
        xdata_opt = [coords[i][0] for i in ruta_optima[:paso]]
        ydata_opt = [coords[i][1] for i in ruta_optima[:paso]]
        if paso == len(ruta_optima):
            xdata_opt.append(coords[ruta_optima[0]][0])
            ydata_opt.append(coords[ruta_optima[0]][1])
        linea_opt.set_data(xdata_opt, ydata_opt)
        return linea_no_opt, linea_opt

    ani = FuncAnimation(fig, update, frames=len(ruta_optima), init_func=init,
                        interval=800, blit=True, repeat=False)
    
    plt.suptitle("Problema del Agente Viajero - Fuerza Bruta", fontsize=14, fontweight='bold')
    plt.show()

# ------------------------
# Programa principal
# ------------------------
if __name__ == "__main__":
    nombres_ciudades = ["Toluca", "CDMX", "Monterrey", "Guadalajara", "Puebla", "Sonora", "Campeche"]
    N = len(nombres_ciudades)

    coordenadas = generar_coordenadas(N, seed=42)
    M = generar_matriz_distancias(coordenadas)

    ruta, dist_min, tiempo_ms = tsp_fuerza_bruta(M)

    print("Mejor ruta:", " → ".join(nombres_ciudades[i] for i in ruta), "→", nombres_ciudades[ruta[0]])
    print("Distancia mínima:", dist_min)
    print(f"Tiempo de ejecución: {tiempo_ms:.3f} ms")

    mostrar_todo_con_animacion(M, nombres_ciudades, coordenadas, ruta, dist_min, tiempo_ms)
