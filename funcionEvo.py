import numpy as np
from concurrent.futures import ThreadPoolExecutor

# Parámetros configurables
inicio = -10
fin = 10
num_decimales = 10  # ← Cambia este valor para ajustar la precisión
max_muestras = 10  # ← Límite para evitar errores de memoria

# Generar lista de pasos según número de decimales
precisiones = [10**-i for i in range(0, num_decimales + 1)]

# Función matemática
def f(x):
    return (2 * x**2) + (11 * x / 3)

# Función para procesar cada precisión
def calcular_precision(paso):
    try:
        cantidad = int((fin - inicio) / paso) + 1
        if cantidad > max_muestras:
            return f"⚠️ Precisión {paso} omitida (demasiados puntos: {cantidad})"
        
        x_vals = np.arange(inicio, fin + paso, paso, dtype=np.float64)
        y_vals = f(x_vals)
        
        salida = [f"Precisión: {paso:.{num_decimales}f}"]
        for i in range(0, len(x_vals), max(1, len(x_vals)//10)):
            x_fmt = f"{x_vals[i]:.{num_decimales}f}"
            y_fmt = f"{y_vals[i]:.{num_decimales}f}"
            salida.append(f"x = {x_fmt}, f(x) = {y_fmt}")
        return "\n".join(salida)
    
    except Exception as e:
        return f"❌ Error en precisión {paso}: {str(e)}"

# Procesamiento paralelo
with ThreadPoolExecutor() as executor:
    resultados = list(executor.map(calcular_precision, precisiones))

# Mostrar resultados
for resultado in resultados:
    print("\n" + resultado)
