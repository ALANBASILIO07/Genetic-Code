import numpy as np
import matplotlib.pyplot as plt

# Definimos la función
def f(x):
    return (2 * x**2) + (11 * x / 3)

# ===============================
# Parámetros
NUM_DEC = 4  # Número de decimales deseado
inicio = -10
fin = 10
# ===============================

# Generar lista de precisiones automáticamente
precisiones = [10**-i for i in range(1, NUM_DEC+1)]
print("Precisión generada:", precisiones)

# Crear la figura
plt.figure(figsize=(10, 6))

# Graficar para cada precisión
for paso in precisiones:
    x_vals = np.arange(inicio, fin + paso, paso)
    y_vals = f(x_vals)
    plt.plot(x_vals, y_vals, label=f"Paso = {paso}")

plt.title(f"f(x) = 2x² + 11x/3 con distintas precisiones (hasta {NUM_DEC} decimales)")
plt.xlabel("x")
plt.ylabel("f(x)")
plt.grid(True)
plt.legend()
plt.show()
