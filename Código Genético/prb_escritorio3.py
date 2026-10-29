import pandas as pd
import numpy as np
import random
import json
import os

# --- 1. CONFIGURACIÓN Y CARGA ---
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
    except: return 0.0

print("--- CARGANDO BASE DE DATOS ---")
for cat, file in FILES.items():
    try:
        if not os.path.exists(file):
            print(f"[ALERTA] Falta archivo: {file}")
            # Crear dummy df para que no rompa si falta archivo (solo pruebas)
            DB[cat] = pd.DataFrame({'ID': [1], 'Mejor Precio (MXN)': [1000], 'Modelo': ['Dummy']})
            continue

        df = pd.read_csv(file, encoding='latin-1')
        if 'Precio (MXN)' in df.columns and 'Mejor Precio (MXN)' not in df.columns:
            df.rename(columns={'Precio (MXN)': 'Mejor Precio (MXN)'}, inplace=True)
        df['Mejor Precio (MXN)'] = df['Mejor Precio (MXN)'].apply(clean_price)
        if 'ID' in df.columns: df.set_index('ID', drop=False, inplace=True)
        DB[cat] = df
        print(f"[OK] {cat}: {len(df)} items.")
    except Exception as e: print(f"[ERROR] {file}: {e}")

# --- 2. PERFILES ---
PROFILES = {
    "admin": { "name": "Administrativo", "budget": 8000, "weights": {"price": 0.8, "perf": 0.2}, "min_ram": 8 },
    "student": { "name": "Estudiante", "budget": 15000, "weights": {"price": 0.5, "perf": 0.5}, "req_wifi": True },
    "dev": { "name": "Desarrollador", "budget": 25000, "weights": {"price": 0.3, "perf": 0.7}, "min_ram": 32, "req_nvme": True },
    "isp": { "name": "ISP Empresa", "budget": 30000, "weights": {"price": 0.1, "perf": 0.9}, "req_ups_online": True }
}

# --- 3. LÓGICA AG ---
def get_component(cat, cid):
    try: return DB[cat].loc[cid]
    except: return DB[cat].iloc[0]

def calc_fitness(chrom, p_key):
    prof = PROFILES[p_key]
    budget = prof['budget']
    comps = [get_component(c, g) for c, g in zip(GENES, chrom)]
    
    cost = sum(c['Mejor Precio (MXN)'] for c in comps)
    notes = []

    # Penalización Mortal
    if cost > budget: return 0.001, cost, "Excede Presupuesto", -1.0, 0.0, "N/A"

    mobo, cpu, ram = comps[0], comps[1], comps[3]
    if str(mobo.get('Socket','A')) != str(cpu.get('Socket','B')):
        return 0.001, cost, "Socket Incompatible", 0.0, 0.0, "N/A"

    # Métricas
    n_sav = (budget - cost) / budget
    perf_raw = sum(c['Mejor Precio (MXN)'] for c in comps[:6])
    n_perf = min(perf_raw / budget, 1.0)
    
    fit = (prof['weights']['perf'] * n_perf) + (prof['weights']['price'] * n_sav)

    # Penalizaciones Suaves
    if 'min_ram' in prof:
        try:
            ram_gb = int(''.join(filter(str.isdigit, str(ram.get('Capacidad Total (GB)','0')))))
            if ram_gb < prof['min_ram']:
                fit -= 0.3
                notes.append("Poca RAM")
        except: pass
    
    if p_key == "student" and "WIFI" not in str(mobo.get('Modelo / Serie','')).upper():
        cost += 300
        fit -= 0.2
        notes.append("Sin WiFi")

    if p_key == "isp" and "Online" not in str(comps[8].get('Tipo','')):
        fit -= 0.4
        notes.append("Sin UPS Online")

    # Descripción breve del mejor componente (CPU + RAM)
    desc = f"{cpu.get('Modelo / Serie','CPU')} + {ram.get('Capacidad Total (GB)','RAM')}"

    return max(0.001, fit), cost, ", ".join(notes) if notes else "Válido", n_sav, n_perf, desc

# --- 4. SIMULACIÓN PRINCIPAL ---
def run():
    POP_SIZE = 50
    GENS = 5 # Generaciones a simular
    
    # Estructuras de salida
    json_output = {}
    excel_writer = pd.ExcelWriter('Resultados_AG.xlsx', engine='openpyxl')
    
    for p_key, p_val in PROFILES.items():
        print(f"Procesando: {p_val['name']}...")
        
        # Estructura JSON por perfil
        json_output[p_key] = {
            "name": p_val['name'],
            "budget": p_val['budget'],
            "weights": f"P:{p_val['weights']['price']}, R:{p_val['weights']['perf']}",
            "gens": []
        }
        
        # Estructura Excel (Lista de diccionarios)
        excel_rows = []
        
        # Población Inicial
        pop = [[random.choice(DB[cat].index.tolist()) for cat in GENES] for _ in range(POP_SIZE)]
        
        for g in range(GENS):
            gen_data = [] # Datos para JSON de esta gen
            fits = []
            
            # Evaluar 50 individuos
            evaluated_pop = []
            for i, ind in enumerate(pop):
                fit, cost, note, ns, np_val, desc = calc_fitness(ind, p_key)
                fits.append(fit)
                
                # Objeto de datos común
                item_data = {
                    "id": f"I-{i+1:02d}",
                    "chrom": str(ind),
                    "cost": cost,
                    "n_sav": round(ns, 3),
                    "n_perf": round(np_val, 3),
                    "fit": round(fit, 4),
                    "note": note,
                    "desc": desc
                }
                
                # Guardar en Excel
                excel_row = item_data.copy()
                excel_row["Generacion"] = g
                excel_row["Perfil"] = p_val['name']
                del excel_row["desc"] # No necesario en tabla excel cruda
                excel_rows.append(excel_row)
                
                # Guardar en lista temporal para JSON y evolución
                evaluated_pop.append({"genome": ind, "fitness": fit, "data": item_data})
                gen_data.append(item_data)

            # Estadísticas
            best = max(evaluated_pop, key=lambda x: x['fitness'])
            worst = min(evaluated_pop, key=lambda x: x['fitness'])
            avg = sum(fits) / len(fits)

            # Agregar Resumen a Excel (Filas separadoras)
            excel_rows.append({"Generacion": f"RESUMEN G{g}", "id": "MEJOR", "fit": round(best['fitness'],4), "note": "Max Fit"})
            excel_rows.append({"Generacion": f"RESUMEN G{g}", "id": "PEOR", "fit": round(worst['fitness'],4), "note": "Min Fit"})
            excel_rows.append({"Generacion": f"RESUMEN G{g}", "id": "PROMEDIO", "fit": round(avg,4), "note": "Avg Fit"})
            excel_rows.append({}) # Fila vacía visual

            # Agregar a JSON principal
            json_output[p_key]["gens"].append({
                "id": g,
                "avg": avg,
                "best": best['data'],
                "worst": worst['data'],
                "population": gen_data # ¡AQUÍ VAN LOS 50 INDIVIDUOS!
            })
            
            # Operadores Genéticos (Torneo, Cruza, Mutación)
            if g < GENS - 1:
                new_pop = [best['genome']] # Elitismo
                while len(new_pop) < POP_SIZE:
                    # Torneo simple
                    p1 = max(random.sample(evaluated_pop, 3), key=lambda x: x['fitness'])['genome']
                    p2 = max(random.sample(evaluated_pop, 3), key=lambda x: x['fitness'])['genome']
                    
                    # Cruza
                    if random.random() < 0.8:
                        pt = random.randint(1, len(GENES)-1)
                        child = p1[:pt] + p2[pt:]
                    else: child = p1[:]
                    
                    # Mutación
                    if random.random() < 0.1:
                        idx = random.randint(0, len(GENES)-1)
                        child[idx] = random.choice(DB[GENES[idx]].index.tolist())
                    
                    new_pop.append(child)
                pop = new_pop

        # Escribir hoja de Excel para este perfil
        df_sheet = pd.DataFrame(excel_rows)
        # Reordenar columnas para legibilidad
        cols = ["Generacion", "id", "chrom", "cost", "n_sav", "n_perf", "fit", "note"]
        # Filtrar columnas que existan (por las filas vacías)
        df_sheet = df_sheet[[c for c in cols if c in df_sheet.columns]]
        df_sheet.to_excel(excel_writer, sheet_name=p_key, index=False)

    excel_writer.close()
    
    # Guardar JSON
    with open('datos_ag1.json', 'w', encoding='utf-8') as f:
        json.dump(json_output, f, ensure_ascii=False, indent=2)

    print("\n[EXITO] Se generaron:")
    print("1. Resultados_AG.xlsx (Para ver en Excel)")
    print("2. datos_ag1.json (Para ver en la Web)")

if __name__ == "__main__":
    run()