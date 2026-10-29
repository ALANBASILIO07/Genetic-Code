import pandas as pd
import numpy as np
import random
import json
import os

# --- 1. CONFIGURACIÓN Y CARGA DE DATOS ---
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

def clean_price(val):
    try:
        if isinstance(val, (int, float)): return float(val)
        val = str(val).replace('$', '').replace(',', '').strip()
        if '+' in val: val = val.split('+')[0]
        return float(val)
    except:
        return 0.0

print("Cargando CSVs...")
for cat, file in FILES.items():
    try:
        if not os.path.exists(file):
            print(f"[ERROR] Archivo no encontrado: {file}")
            continue
            
        df = pd.read_csv(file, encoding='latin-1')
        
        # Corrección específica para Aditamentos.csv
        if 'Precio (MXN)' in df.columns and 'Mejor Precio (MXN)' not in df.columns:
            df.rename(columns={'Precio (MXN)': 'Mejor Precio (MXN)'}, inplace=True)
            
        df['Mejor Precio (MXN)'] = df['Mejor Precio (MXN)'].apply(clean_price)
        
        if 'ID' in df.columns:
            df.set_index('ID', drop=False, inplace=True)
        
        DB[cat] = df
        print(f"[OK] {cat}: {len(df)} registros.")
    except Exception as e:
        print(f"[ERROR] Error cargando {file}: {e}")

# --- 2. DEFINICIÓN DE PERFILES ---
PROFILES = {
    "admin": {
        "name": "Trabajador Administrativo",
        "budget": 8000,
        "weights": {"price": 0.8, "perf": 0.2},
        "min_ram": 8,
        "desc_weights": "α(Rend)=0.2, β(Ahorro)=0.8"
    },
    "student": {
        "name": "Estudiante Universitario",
        "budget": 15000,
        "weights": {"price": 0.5, "perf": 0.5},
        "req_wifi": True,
        "desc_weights": "α(Rend)=0.5, β(Ahorro)=0.5"
    },
    "dev": {
        "name": "Desarrollador de Software",
        "budget": 25000,
        "weights": {"price": 0.3, "perf": 0.7},
        "min_ram": 32,
        "req_nvme": True,
        "desc_weights": "α(Rend)=0.7, β(Ahorro)=0.3"
    },
    "isp": {
        "name": "ISP / Micro-empresa",
        "budget": 30000,
        "weights": {"price": 0.1, "perf": 0.9},
        "req_ups_online": True,
        "desc_weights": "α(Rend)=0.9, β(Ahorro)=0.1"
    }
}

# --- 3. LÓGICA DEL AG ---
def get_component_row(category, cid):
    try: return DB[category].loc[cid]
    except: return DB[category].iloc[0]

def calculate_fitness(chromosome, profile_key):
    prof = PROFILES[profile_key]
    budget = prof['budget']
    comps = [get_component_row(cat, gene) for cat, gene in zip(GENES, chromosome)]
    
    total_cost = sum(c['Mejor Precio (MXN)'] for c in comps)
    penalties_log = []
    
    # Penalizaciones Mortales
    if total_cost > budget:
        return 0.001, total_cost, "Excede Presupuesto", -1.0, 0.0
    
    mobo, cpu, ram = comps[0], comps[1], comps[3]
    if str(mobo.get('Socket','A')) != str(cpu.get('Socket','B')):
        return 0.001, total_cost, "Incompatible Socket", 0.0, 0.0
        
    # Métricas
    n_ahorro = (budget - total_cost) / budget
    perf_raw = sum(c['Mejor Precio (MXN)'] for c in comps[:6])
    n_rend = min(perf_raw / budget, 1.0)
    
    fitness = (prof['weights']['perf'] * n_rend) + (prof['weights']['price'] * n_ahorro)
    
    # Penalizaciones Suaves
    if 'min_ram' in prof:
        try:
            ram_cap = int(''.join(filter(str.isdigit, str(ram['Capacidad Total (GB)']))))
            if ram_cap < prof['min_ram']:
                fitness -= 0.3
                penalties_log.append("Poca RAM")
        except: pass

    if profile_key == "student":
        if "WIFI" not in str(mobo['Modelo / Serie']).upper() and "AX" not in str(mobo['Modelo / Serie']).upper():
            total_cost += 300
            fitness -= 0.2
            penalties_log.append("Sin WiFi (+Costo)")
            
    if profile_key == "isp":
        ups = comps[8]
        if "Online" not in str(ups.get('Tipo', '')):
            fitness -= 0.4
            penalties_log.append("Sin UPS Online")

    return max(0.001, fitness), total_cost, ", ".join(penalties_log) if penalties_log else "Válido", n_ahorro, n_rend

# --- 4. EJECUCIÓN Y EXPORTACIÓN JSON ---
def run_simulation_json():
    # Parámetros AG
    POP_SIZE = 50
    GENERATIONS = 3
    P_CROSSOVER = 0.8
    P_MUTATION = 0.1
    K_TOURNAMENT = 5
    
    final_data = {}
    
    for p_key, p_val in PROFILES.items():
        print(f"Procesando {p_val['name']}...")
        profile_data = {
            "name": f"{p_val['name']} (${p_val['budget']})",
            "weights": p_val['desc_weights'],
            "gens": []
        }
        
        # G0
        population = [[random.choice(DB[cat].index.tolist()) for cat in GENES] for _ in range(POP_SIZE)]
        
        for gen in range(GENERATIONS):
            gen_results = []
            fitness_values = []
            
            evaluated_pop = []
            
            for ind in population:
                fit, cost, note, n_sav, n_perf = calculate_fitness(ind, p_key)
                fitness_values.append(fit)
                
                # Datos del individuo para JSON
                ind_data = {
                    "id": f"I-{len(evaluated_pop)+1:02d}",
                    "fit": round(fit, 4),
                    "cost": cost,
                    "chrom": str(ind),
                    "n_sav": round(n_sav, 3),
                    "n_perf": round(n_perf, 3),
                    "note": note
                }
                gen_results.append(ind_data)
                evaluated_pop.append({"genome": ind, "fitness": fit, "data": ind_data})
            
            # Estadísticas
            best = max(evaluated_pop, key=lambda x: x['fitness'])
            worst = min(evaluated_pop, key=lambda x: x['fitness'])
            avg = sum(fitness_values) / len(fitness_values)
            
            # Descripción del mejor (componentes clave)
            best_desc = "Optimizado"
            try:
                cpu_name = get_component_row("Procesador", best['genome'][1])['Modelo/Serie']
                ram_name = get_component_row("RAM", best['genome'][3])['Capacidad Total (GB)']
                best_desc = f"{cpu_name}, {ram_name}"
            except: pass
            
            # Guardar generación
            profile_data["gens"].append({
                "id": gen,
                "best": {**best['data'], "desc": best_desc},
                "worst": {**worst['data'], "desc": "Peor Fitness"},
                "avg": avg,
                "samples": gen_results[:10] # Guardamos los primeros 10 para la tabla (o todos si prefieres)
            })
            
            # Evolución
            if gen < GENERATIONS - 1:
                new_pop = [best['genome']] # Elitismo
                while len(new_pop) < POP_SIZE:
                    # Torneo
                    def tournament():
                        cands = random.sample(evaluated_pop, K_TOURNAMENT)
                        return max(cands, key=lambda x: x['fitness'])['genome']
                    p1, p2 = tournament(), tournament()
                    
                    # Cruza
                    if random.random() < P_CROSSOVER:
                        pt = random.randint(1, len(GENES)-1)
                        c1 = p1[:pt] + p2[pt:]
                        c2 = p2[:pt] + p1[pt:]
                    else: c1, c2 = p1[:], p2[:]
                    
                    # Mutación
                    def mutate(ind):
                        if random.random() < P_MUTATION:
                            mp = random.randint(0, len(GENES)-1)
                            ind[mp] = random.choice(DB[GENES[mp]].index.tolist())
                        return ind
                    
                    new_pop.append(mutate(c1))
                    if len(new_pop) < POP_SIZE: new_pop.append(mutate(c2))
                population = new_pop
                
        final_data[p_key] = profile_data

    # Guardar JSON
    with open('datos_ag.json', 'w', encoding='utf-8') as f:
        json.dump(final_data, f, ensure_ascii=False, indent=4)
    print("\n[OK] Listo! Archivo 'datos_ag.json' generado con exito.")

if __name__ == "__main__":
    run_simulation_json()