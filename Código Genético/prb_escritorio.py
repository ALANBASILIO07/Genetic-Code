import pandas as pd
import numpy as np
import random
import copy

# --- 1. CONFIGURACIÓN Y CARGA DE DATOS ---

# Mapeo de archivos CSV (Ajustado a los nombres que subiste)
FILES = {
    "Motherboard": "Motherboard.csv",
    "Procesador": "Procesadores.csv",
    "GPU": "GPU.csv",
    "RAM": "RAM.csv",
    "Almacenamiento": "Almacenamiento.csv",
    "Refrigeracion": "Refrigeracion.csv",
    "Fuente": "Fuente.csv",
    "Gabinete": "Gabinete.csv",
    "Seguridad": "Aditamentos.csv"
}

GENES = list(FILES.keys())
DB = {}

# Carga de datos con manejo de errores simple para precios
def clean_price(val):
    try:
        if isinstance(val, (int, float)): return float(val)
        val = str(val).replace('$', '').replace(',', '').strip()
        if '+' in val: val = val.split('+')[0] # Manejar "$15,000+"
        return float(val)
    except:
        return 0.0

print("Cargando CSVs...")
for cat, file in FILES.items():
    try:
        df = pd.read_csv(file, encoding='latin-1') # Encoding usual en excel
        
        # Normalizar nombre de columna de precio (Corrección para Aditamentos.csv)
        if 'Precio (MXN)' in df.columns and 'Mejor Precio (MXN)' not in df.columns:
            df.rename(columns={'Precio (MXN)': 'Mejor Precio (MXN)'}, inplace=True)
            
        df['Mejor Precio (MXN)'] = df['Mejor Precio (MXN)'].apply(clean_price)
        
        # Asegurar que ID sea el índice para búsquedas rápidas
        if 'ID' in df.columns:
            df.set_index('ID', drop=False, inplace=True)
        
        DB[cat] = df
        print(f"[OK] {cat}: {len(df)} registros.")
    except Exception as e:
        print(f"[ERROR] Error cargando {file}: {e}")

# --- 2. DEFINICIÓN DE PERFILES (Reglas de Negocio) ---

PROFILES = {
    "Administrativo": {
        "budget": 8000,
        "weights": {"price": 0.8, "perf": 0.2},
        "min_ram": 8,
        "human_sol": [18, 28, 0, 36, 9, 0, 0, 0, 9] 
    },
    "Estudiante": {
        "budget": 15000,
        "weights": {"price": 0.5, "perf": 0.5},
        "req_wifi": True,
        "human_sol": [15, 4, 12, 0, 28, 1, 5, 4, 9]
    },
    "Desarrollador": {
        "budget": 25000,
        "weights": {"price": 0.3, "perf": 0.7},
        "min_ram": 32,
        "req_nvme": True,
        "human_sol": [10, 8, 15, 20, 39, 6, 10, 12, 10]
    },
    "ISP": {
        "budget": 30000,
        "weights": {"price": 0.1, "perf": 0.9},
        "req_ups_online": True,
        "human_sol": [29, 22, 0, 21, 45, 21, 32, 26, 25]
    }
}

# --- 3. LÓGICA DEL AG (Fitness y Operadores) ---

def get_component_row(category, cid):
    """Recupera la fila del componente por ID"""
    try:
        return DB[category].loc[cid]
    except:
        # Fallback si el ID no existe
        return DB[category].iloc[0]

def calculate_fitness(chromosome, profile_name):
    """Calcula el fitness y devuelve detalles para el reporte"""
    prof = PROFILES[profile_name]
    budget = prof['budget']
    
    # Obtener componentes
    comps = [get_component_row(cat, gene) for cat, gene in zip(GENES, chromosome)]
    
    # Costo Total
    total_cost = sum(c['Mejor Precio (MXN)'] for c in comps)
    
    # --- Penalizaciones Mortales ---
    if total_cost > budget:
        return 0.001, total_cost, "Excede Presupuesto", 0.0, 0.0 # Fitness mínimo
    
    # Validar Compatibilidad (Simplificada)
    mobo, cpu, ram = comps[0], comps[1], comps[3]
    
    # Socket
    if str(mobo.get('Socket','A')) != str(cpu.get('Socket','B')):
        return 0.001, total_cost, "Incompatible Socket", 0.0, 0.0
    
    # RAM Tipo
    mobo_ram = str(mobo.get('Soporte RAM',''))
    ram_type = str(ram.get('Tipo',''))
    if ('DDR4' in mobo_ram and 'DDR5' in ram_type) or ('DDR5' in mobo_ram and 'DDR4' in ram_type):
        return 0.001, total_cost, "Incompatible RAM", 0.0, 0.0

    # --- Métricas Normalizadas ---
    # Ahorro
    n_ahorro = (budget - total_cost) / budget
    
    # Rendimiento
    perf_raw = sum(c['Mejor Precio (MXN)'] for c in comps[:6]) 
    max_perf_proxy = budget 
    n_rend = min(perf_raw / max_perf_proxy, 1.0)
    
    # --- Fitness Base ---
    alpha = prof['weights']['perf']
    beta = prof['weights']['price']
    
    fitness = (alpha * n_rend) + (beta * n_ahorro)
    
    # --- Penalizaciones Suaves ---
    penalties_log = []
    
    # RAM Mínima
    if 'min_ram' in prof:
        try:
            ram_cap = int(''.join(filter(str.isdigit, str(ram['Capacidad Total (GB)']))))
            if ram_cap < prof['min_ram']:
                fitness -= 0.3
                penalties_log.append("Poca RAM")
        except: pass

    # WiFi (Estudiante)
    if profile_name == "Estudiante":
        if "WIFI" not in str(mobo['Modelo / Serie']).upper() and "AX" not in str(mobo['Modelo / Serie']).upper():
            total_cost += 300 # Costo virtual
            fitness -= 0.2
            penalties_log.append("Sin WiFi")
            
    # UPS Online (ISP)
    if profile_name == "ISP":
        ups = comps[8] # Seguridad
        if "Online" not in str(ups.get('Tipo', '')):
            fitness -= 0.4
            penalties_log.append("Sin UPS Online")

    return max(0.001, fitness), total_cost, ", ".join(penalties_log) if penalties_log else "OK", n_ahorro, n_rend

# --- 4. EJECUCIÓN POR PERFIL ---

def run_simulation():
    # Configuración de simulación
    POP_SIZE = 50 
    GENERATIONS = 3
    P_CROSSOVER = 0.8
    P_MUTATION = 0.1
    K_TOURNAMENT = 5
    
    writer = pd.ExcelWriter('Pruebas_Escritorio_AG.xlsx', engine='openpyxl')
    
    for profile_name in PROFILES.keys():
        print(f"Simulando perfil: {profile_name}...")
        
        # Estructura para guardar datos de excel
        rows = []
        
        # 1. Generación 0 (Aleatoria)
        population = []
        for _ in range(POP_SIZE):
            # Crear individuo random válido (IDs existen en CSV)
            ind = [random.choice(DB[cat].index.tolist()) for cat in GENES]
            population.append(ind)
            
        # Ciclo evolutivo
        for gen in range(GENERATIONS):
            
            # Evaluar toda la población
            evaluated_pop = []
            fitness_scores = []
            
            for i, ind in enumerate(population):
                fit, cost, status, n_ahorro, n_rend = calculate_fitness(ind, profile_name)
                fitness_scores.append(fit)
                
                # Guardar datos para reporte
                ind_str = str(ind)
                row = {
                    "Generación": gen,
                    "ID Ind": i + 1,
                    "Cromosoma": ind_str,
                    "Costo Total": cost,
                    "N_Ahorro": round(n_ahorro, 3),
                    "N_Rend": round(n_rend, 3),
                    "Fitness": round(fit, 4),
                    "Estado/Penalizaciones": status
                }
                rows.append(row)
                
                evaluated_pop.append({
                    "genome": ind,
                    "fitness": fit
                })
            
            # Estadísticas de la generación
            best_ind = max(evaluated_pop, key=lambda x: x['fitness'])
            worst_ind = min(evaluated_pop, key=lambda x: x['fitness'])
            avg_fit = sum(fitness_scores) / len(fitness_scores)
            
            # --- SECCIÓN DE RESUMEN AL FINAL DE LA GENERACIÓN ---
            rows.append({}) # Espacio vacío
            
            # 1. Mejor Individuo
            rows.append({
                "Generación": f"RESUMEN G{gen}",
                "ID Ind": "MEJOR",
                "Cromosoma": str(best_ind['genome']),
                "Costo Total": "-",
                "Fitness": round(best_ind['fitness'], 4),
                "Estado/Penalizaciones": "Max Fitness de Gen"
            })
            
            # 2. Peor Individuo
            rows.append({
                "Generación": f"RESUMEN G{gen}",
                "ID Ind": "PEOR",
                "Cromosoma": str(worst_ind['genome']),
                "Costo Total": "-",
                "Fitness": round(worst_ind['fitness'], 4),
                "Estado/Penalizaciones": "Min Fitness de Gen"
            })
            
            # 3. Promedio
            rows.append({
                "Generación": f"RESUMEN G{gen}",
                "ID Ind": "PROMEDIO",
                "Cromosoma": "-",
                "Costo Total": "-",
                "Fitness": round(avg_fit, 4),
                "Estado/Penalizaciones": "Promedio Fitness"
            })
            
            rows.append({}) # Separador grande para la siguiente gen

            # --- OPERADORES GENÉTICOS (Siguiente Generación) ---
            if gen < GENERATIONS - 1: 
                new_pop = []
                
                # Elitismo
                new_pop.append(best_ind['genome'])
                
                while len(new_pop) < POP_SIZE:
                    # Selección
                    def tournament():
                        candidates = random.sample(evaluated_pop, K_TOURNAMENT)
                        return max(candidates, key=lambda x: x['fitness'])['genome']
                    
                    p1 = tournament()
                    p2 = tournament()
                    
                    # Cruza
                    if random.random() < P_CROSSOVER:
                        point = random.randint(1, len(GENES)-1)
                        c1 = p1[:point] + p2[point:]
                        c2 = p2[:point] + p1[point:]
                    else:
                        c1, c2 = p1[:], p2[:]
                        
                    # Mutación
                    def mutate(ind):
                        if random.random() < P_MUTATION:
                            m_point = random.randint(0, len(GENES)-1)
                            cat = GENES[m_point]
                            ind[m_point] = random.choice(DB[cat].index.tolist())
                        return ind
                    
                    new_pop.append(mutate(c1))
                    if len(new_pop) < POP_SIZE:
                        new_pop.append(mutate(c2))
                
                population = new_pop

        # Guardar en hoja de Excel
        df_sheet = pd.DataFrame(rows)
        df_sheet.to_excel(writer, sheet_name=profile_name, index=False)
        
    writer.close()
    print("\n[OK] ¡Listo! Archivo 'Pruebas_Escritorio_AG.xlsx' generado con éxito.")

if __name__ == "__main__":
    run_simulation()