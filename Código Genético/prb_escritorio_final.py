"""
================================================================================
ALGORITMO GENÉTICO OPTIMIZADO v2.1
Selección Óptima de Componentes de Hardware para PC
Universidad Autónoma del Estado de México - Cómputo Evolutivo
================================================================================
"""

import pandas as pd
import numpy as np
import random
import json
import os
import copy
import re
import sys

# Configurar salida para evitar errores de encoding en Windows
sys.stdout.reconfigure(encoding='utf-8')    

# =============================================================================
# 1. PARÁMETROS GLOBALES DE CONTROL
# =============================================================================

POPULATION_SIZE = 100
GENERATIONS = 100
TOURNAMENT_SIZE = 5
CROSSOVER_RATE = 0.9
MUTATION_RATE = 0.15

# --- PERFILES DE USUARIO ---
PROFILES = {
    "admin": { "name": "Administrativo", "budget": 8000, "alpha": 0.3, "beta": 0.7, "min_ram": 8, "requires_igpu": True },
    "student": { "name": "Estudiante", "budget": 15000, "alpha": 0.5, "beta": 0.5, "min_ram": 16, "req_wifi": True, "requires_igpu": False },
    "dev": { "name": "Desarrollador", "budget": 25000, "alpha": 0.7, "beta": 0.3, "min_ram": 32, "req_nvme": True, "requires_igpu": False },
    "isp": { "name": "ISP Empresa", "budget": 30000, "alpha": 0.7, "beta": 0.3, "min_ram": 32, "req_ups_online": True, "requires_igpu": True }
}

# =============================================================================
# 2. CARGA DE BASE DE DATOS
# =============================================================================

FILES = {
    "Motherboard": "Motherboard.csv", "Procesador": "Procesadores.csv", "GPU": "GPU.csv",
    "RAM": "RAM.csv", "Almacenamiento": "Almacenamiento.csv", "Refrigeracion": "Refrigeracion.csv",
    "Fuente": "Fuente.csv", "Gabinete": "Gabinete.csv", "Seguridad": "Aditamentos.csv"
}
GENES = list(FILES.keys())
DB = {}
MAX_PRICES = {}

# Mapeo de columnas para nombres de componentes
NAME_COLS = {
    "Motherboard": "Modelo / Serie", "Procesador": "Modelo/Serie", "GPU": "Modelo Específico (SKU)",
    "RAM": "Modelo / Serie", "Almacenamiento": "Modelo / Serie", "Refrigeracion": "Modelo / Serie",
    "Fuente": "Modelo / Serie", "Gabinete": "Modelo Específico", "Seguridad": "Modelo Específico"
}

def clean_price(val):
    try:
        if isinstance(val, (int, float)): return float(val)
        val = str(val).replace('$', '').replace(',', '').replace('+', '').strip()
        return float(val) if val else 0.0
    except: return 0.0

def extract_number(val, default=0):
    try:
        numbers = re.findall(r'\d+\.?\d*', str(val))
        return float(numbers[0]) if numbers else default
    except: return default

def normalize_columns(df):
    new_cols = {}
    for col in df.columns:
        new_col = col.replace('\ufeff', '').replace('ï»¿', '')
        new_cols[col] = new_col
    return df.rename(columns=new_cols)

print("=" * 70)
print("  ALGORITMO GENÉTICO - SELECCIÓN ÓPTIMA DE HARDWARE v2.1")
print("=" * 70)
print("\n[INFO] CARGANDO BASE DE DATOS DE COMPONENTES...")
print("-" * 50)

for cat, file in FILES.items():
    try:
        if not os.path.exists(file):
            print(f"  [!] Archivo no encontrado: {file}")
            DB[cat] = pd.DataFrame({'ID': [0], 'Mejor Precio (MXN)': [1000]})
            MAX_PRICES[cat] = 1000
            continue
        
        try: df = pd.read_csv(file, encoding='utf-8-sig')
        except: df = pd.read_csv(file, encoding='latin-1')
        
        df = normalize_columns(df)
        
        price_col = None
        for col in ['Mejor Precio (MXN)', 'Precio (MXN)']:
            if col in df.columns:
                price_col = col
                break
        
        if price_col: df['Mejor Precio (MXN)'] = df[price_col].apply(clean_price)
        if 'ID' in df.columns: df.set_index('ID', drop=False, inplace=True)
        
        DB[cat] = df
        MAX_PRICES[cat] = df['Mejor Precio (MXN)'].max()
        print(f"  [OK] {cat:15} : {len(df):3} componentes | Max: ${MAX_PRICES[cat]:,.0f}")
        
    except Exception as e:
        print(f"  [ERROR] Error cargando {file}: {e}")

print("-" * 50)

# =============================================================================
# 3. FUNCIONES DE COMPATIBILIDAD
# =============================================================================

def get_socket(component, cat): return str(component.get('Socket', '')).strip()

def get_ram_type(component, cat):
    if cat == "Motherboard": ram_support = str(component.get('Soporte RAM', '')).upper()
    elif cat == "RAM": ram_support = str(component.get('Tipo', '')).upper()
    else: return 'UNKNOWN'
    
    if 'DDR5' in ram_support: return 'DDR5'
    elif 'DDR4' in ram_support: return 'DDR4'
    return 'UNKNOWN'

def get_mobo_format(component):
    fmt = str(component.get('Formato', '')).upper()
    if 'MINI-ITX' in fmt or 'ITX' in fmt: return 'ITX'
    elif 'MICRO' in fmt or 'MATX' in fmt: return 'MATX'
    elif 'E-ATX' in fmt: return 'EATX'
    return 'ATX'

def get_case_support(component):
    support = str(component.get('MB Soporte', '')).upper()
    supported = []
    if 'E-ATX' in support: supported.extend(['EATX', 'ATX', 'MATX', 'ITX'])
    elif 'ATX' in support: supported.extend(['ATX', 'MATX', 'ITX'])
    elif 'MATX' in support: supported.extend(['MATX', 'ITX'])
    elif 'ITX' in support: supported.append('ITX')
    return supported if supported else ['ATX', 'MATX', 'ITX']

def get_psu_wattage(component):
    return extract_number(str(component.get('Potencia (W)', '500')), 500)

def get_component_tdp(component, cat):
    if cat == "GPU": return extract_number(str(component.get('Consumo (TDP/TBP)', '0')), 0)
    elif cat == "Procesador":
        modelo = str(component.get('Modelo/Serie', '')).upper()
        if '14900' in modelo or '7950' in modelo: return 253
        elif '14700' in modelo or '7900' in modelo: return 200
        elif '14600' in modelo or '7800' in modelo: return 125
        elif '12600' in modelo or '5800' in modelo: return 105
        return 65
    return 0

def has_igpu(component):
    igpu = str(component.get('Gráficos Integrados', '')).upper()
    return any(x in igpu for x in ['SI', 'YES', 'VEGA', 'UHD', 'RADEON'])

def is_nvme(component):
    tipo = str(component.get('Tipo', '')).upper()
    return 'NVME' in tipo or 'PCIE' in str(component.get('Interfaz', '')).upper()

def has_wifi(component):
    modelo = str(component.get('Modelo / Serie', '')).upper()
    return 'WIFI' in modelo or 'WI-FI' in modelo

def is_ups_online(component):
    return 'ONLINE' in str(component.get('Tipo', '')).upper()

# =============================================================================
# 4. VALIDACIÓN DE COMPATIBILIDAD
# =============================================================================

def validate_compatibility(chrom, p_key):
    prof = PROFILES[p_key]
    problems = []
    penalty = 0
    
    try:
        mobo = DB["Motherboard"].loc[chrom[0]]
        cpu = DB["Procesador"].loc[chrom[1]]
        gpu = DB["GPU"].loc[chrom[2]]
        ram = DB["RAM"].loc[chrom[3]]
        storage = DB["Almacenamiento"].loc[chrom[4]]
        cooling = DB["Refrigeracion"].loc[chrom[5]]
        psu = DB["Fuente"].loc[chrom[6]]
        case = DB["Gabinete"].loc[chrom[7]]
        security = DB["Seguridad"].loc[chrom[8]]
    except: return False, ["Error de componentes"], 10
    
    # 1. Socket
    s_mobo = get_socket(mobo, "Motherboard")
    s_cpu = get_socket(cpu, "Procesador")
    if s_mobo != s_cpu:
        problems.append(f"Socket: {s_mobo}!={s_cpu}")
        penalty += 5
    
    # 2. RAM
    r_mobo = get_ram_type(mobo, "Motherboard")
    r_mem = get_ram_type(ram, "RAM")
    if r_mobo != 'UNKNOWN' and r_mem != 'UNKNOWN' and r_mobo != r_mem:
        problems.append(f"RAM: {r_mobo}!={r_mem}")
        penalty += 5
    
    # 3. Gabinete
    m_fmt = get_mobo_format(mobo)
    c_sup = get_case_support(case)
    if m_fmt not in c_sup:
        problems.append(f"Case no soporta {m_fmt}")
        penalty += 2
    
    # 4. Fuente
    p_watts = get_psu_wattage(psu)
    total_tdp = get_component_tdp(cpu, "Procesador") + get_component_tdp(gpu, "GPU") + 100
    if p_watts < total_tdp:
        problems.append(f"PSU:{p_watts}W<{total_tdp}W")
        penalty += 3
    
    # 5. Requisitos Perfil
    if 'min_ram' in prof:
        r_gb = extract_number(str(ram.get('Capacidad Total (GB)', '8')), 8)
        if r_gb < prof['min_ram']:
            problems.append(f"RAM:{r_gb}GB<{prof['min_ram']}GB")
            penalty += 1
            
    if prof.get('req_wifi', False) and not has_wifi(mobo):
        problems.append("Sin WiFi")
        penalty += 1
        
    if prof.get('req_nvme', False) and not is_nvme(storage):
        problems.append("Sin NVMe")
        penalty += 0.5
        
    if prof.get('req_ups_online', False) and not is_ups_online(security):
        problems.append("Sin UPS Online")
        penalty += 2
        
    if prof.get('requires_igpu', False):
        g_price = clean_price(gpu.get('Mejor Precio (MXN)', 0))
        if g_price == 0 and not has_igpu(cpu):
            problems.append("Sin Graficos")
            penalty += 5
            
    return penalty < 5, problems, penalty

# =============================================================================
# 5. FUNCIÓN DE FITNESS
# =============================================================================

def calc_fitness(chrom, p_key):
    prof = PROFILES[p_key]
    budget = prof['budget']
    
    try: comps = [DB[cat].loc[chrom[i]] for i, cat in enumerate(GENES)]
    except: return 0.001, 99999, "Error", 0, 0, prof['alpha'], prof['beta']
    
    # Costo
    cost_total = sum(clean_price(c.get('Mejor Precio (MXN)', 0)) for c in comps)
    
    # N_Ahorro
    if cost_total <= budget: n_ahorro = (budget - cost_total) / budget
    else: n_ahorro = -((cost_total - budget) / budget)
    
    # N_Rend (Simplificado para brevedad, misma lógica de precios relativos)
    cpu_p = clean_price(comps[1].get('Mejor Precio (MXN)', 0))
    gpu_p = clean_price(comps[2].get('Mejor Precio (MXN)', 0))
    ram_gb = extract_number(str(comps[3].get('Capacidad Total (GB)', '8')), 8)
    sto_sp = extract_number(str(comps[4].get('Vel. Lectura (MB/s)', '150')), 150)
    
    cpu_s = min(1.0, cpu_p / 12000)
    gpu_s = 0.1 if gpu_p == 0 else min(1.0, gpu_p / 33000)
    ram_s = min(1.0, ram_gb / 64)
    sto_s = min(1.0, sto_sp / 7000)
    cool_s = 0.5
    
    if p_key == "admin": n_rend = (cpu_s*0.3 + ram_s*0.3 + sto_s*0.3 + cool_s*0.1)
    elif p_key == "student": n_rend = (cpu_s*0.25 + gpu_s*0.35 + ram_s*0.2 + sto_s*0.15 + cool_s*0.05)
    elif p_key == "dev": n_rend = (cpu_s*0.35 + gpu_s*0.2 + ram_s*0.25 + sto_s*0.15 + cool_s*0.05)
    else: n_rend = (cpu_s*0.4 + ram_s*0.3 + sto_s*0.2 + cool_s*0.1)
    
    # Penalizaciones
    is_valid, probs, p_pen = validate_compatibility(chrom, p_key)
    
    b_pen = 0
    if cost_total > budget:
        excess = (cost_total - budget) / budget
        if excess <= 0.1: b_pen = 0.5
        elif excess <= 0.5: b_pen = 3
        else: b_pen = 5
        
    alpha, beta = prof['alpha'], prof['beta']
    base = (alpha * n_rend) + (beta * max(0, n_ahorro))
    fitness = max(0.001, base - ((p_pen + b_pen) * 0.1))
    
    if not probs and cost_total <= budget: note = "[OK] Optimo"
    elif cost_total > budget: note = f"Excede ${cost_total-budget:,.0f}"
    else: note = ", ".join(probs[:2])
    
    return fitness, cost_total, note, n_ahorro, n_rend, alpha, beta

# =============================================================================
# 6. GENERACIÓN & MUTACIÓN INTELIGENTE
# =============================================================================

def get_smart_id(cat, max_p=None, query=None):
    df = DB[cat]
    mask = pd.Series([True]*len(df), index=df.index)
    if max_p: mask &= (df['Mejor Precio (MXN)'] <= max_p)
    if query: 
        cols = [c for c in df.columns if 'Modelo' in c or 'Nombre' in c or 'Socket' in c or 'Tipo' in c]
        q_mask = pd.Series([False]*len(df), index=df.index)
        for c in cols: q_mask |= df[c].astype(str).str.contains(query, case=False, na=False)
        mask &= q_mask
        
    filtered = df[mask]
    if len(filtered) == 0: return random.choice(df.index.tolist())
    return random.choice(filtered.index.tolist())

def generate_smart_individual(p_key):
    prof = PROFILES[p_key]
    budget = prof['budget']
    chrom = []
    
    # Lógica simplificada de presupuesto
    if p_key == "admin": s_sock, s_ram = "AM4", "DDR4"
    elif p_key == "student": s_sock, s_ram = "AM4", "DDR4"
    elif p_key == "dev": s_sock, s_ram = "LGA 1700", "DDR5"
    else: s_sock, s_ram = "AM5", "DDR5"
    
    # 1. Mobo
    chrom.append(get_smart_id("Motherboard", budget*0.2, s_sock))
    # 2. CPU
    chrom.append(get_smart_id("Procesador", budget*0.3, s_sock))
    # 3. GPU
    if prof['requires_igpu']: chrom.append(0)
    else: chrom.append(get_smart_id("GPU", budget*0.3))
    # 4. RAM
    chrom.append(get_smart_id("RAM", budget*0.15, s_ram))
    # Resto
    for cat in ["Almacenamiento", "Refrigeracion", "Fuente", "Gabinete", "Seguridad"]:
        chrom.append(get_smart_id(cat, budget*0.1))
        
    return chrom

def smart_mutation(chrom, p_key):
    new_c = chrom[:]
    prof = PROFILES[p_key]
    valid, probs, pen = validate_compatibility(new_c, p_key)
    
    if "Socket" in str(probs):
        mobo = DB["Motherboard"].loc[new_c[0]]
        sock = get_socket(mobo, "Motherboard")
        new_c[1] = get_smart_id("Procesador", None, sock)
    elif "RAM" in str(probs):
        mobo = DB["Motherboard"].loc[new_c[0]]
        rtype = get_ram_type(mobo, "Motherboard")
        if rtype != 'UNKNOWN': new_c[3] = get_smart_id("RAM", None, rtype)
    elif "WiFi" in str(probs):
        new_c[0] = get_smart_id("Motherboard", None, "WIFI")
    elif "NVMe" in str(probs):
        new_c[4] = get_smart_id("Almacenamiento", None, "NVMe")
    elif "UPS" in str(probs):
        new_c[8] = get_smart_id("Seguridad", None, "Online")
    else:
        # Mutación aleatoria
        idx = random.randint(0, 8)
        new_c[idx] = random.choice(DB[GENES[idx]].index.tolist())
        
    return new_c

# =============================================================================
# 7. DECODIFICACIÓN
# =============================================================================

def decode_chromosome(chrom):
    decoded = {}
    for i, cat in enumerate(GENES):
        try:
            row = DB[cat].loc[chrom[i]]
            name_col = NAME_COLS.get(cat, "Modelo / Serie")
            if name_col in row: m_name = str(row[name_col])
            else: m_name = f"ID:{chrom[i]}"
            brand = str(row.get('Marca', ''))
            decoded[cat] = f"{brand} {m_name}".strip()
        except: decoded[cat] = "Unknown"
    return decoded

# =============================================================================
# 8. MOTOR PRINCIPAL
# =============================================================================

HUMAN_SOLUTIONS = {
    "admin": [18, 28, 0, 36, 9, 0, 0, 0, 9],
    "student": [15, 4, 12, 0, 28, 1, 5, 4, 9],
    "dev": [10, 8, 15, 20, 39, 6, 10, 12, 10],
    "isp": [29, 22, 0, 21, 45, 21, 32, 26, 25]
}

def run():
    print("\n" + "=" * 60)
    print(f"  INICIANDO SIMULACION GENETICA (ASCII SAFE)")
    print(f"  Poblacion: {POPULATION_SIZE} | Generaciones: {GENERATIONS}")
    print("=" * 60)
    
    # Evaluar Humano
    h_res = {}
    print("\n[INFO] Evaluando Soluciones Humanas...")
    for k, c in HUMAN_SOLUTIONS.items():
        f, cost, _, _, _, _, _ = calc_fitness(c, k)
        h_res[k] = {"fitness": f, "cost": cost, "decoded": decode_chromosome(c)}
        print(f"  > {k}: Fit={f:.4f} Cost=${cost:,.0f}")

    json_out = {"human_solutions": h_res}
    
    for p_key, p_val in PROFILES.items():
        print(f"\n[{p_val['name']}] Procesando...")
        json_out[p_key] = {"name": p_val['name'], "gens": []}
        
        # G0
        pop = []
        for _ in range(POPULATION_SIZE):
            if random.random() < 0.8: c = generate_smart_individual(p_key)
            else: c = [random.choice(DB[cat].index.tolist()) for cat in GENES]
            f, cost, note, ns, nr, a, b = calc_fitness(c, p_key)
            pop.append({"id": "G0", "chrom": c, "fit": f, "cost": cost, "n_sav": ns, 
                        "n_perf": nr, "alpha": a, "beta": b, "note": note, 
                        "parents": "N/A", "operator": "Init", "delta": 0})
            
        # Evolución
        for g in range(GENERATIONS):
            if g > 0:
                pop.sort(key=lambda x: x['fit'], reverse=True)
                new_pop = []
                
                # Elitismo
                elite = copy.deepcopy(pop[0])
                elite["id"] = f"G{g}-E"
                elite["operator"] = "Elitismo"
                new_pop.append(elite)
                
                while len(new_pop) < POPULATION_SIZE:
                    # Torneo
                    p1 = max(random.sample(pop, TOURNAMENT_SIZE), key=lambda x: x['fit'])
                    p2 = max(random.sample(pop, TOURNAMENT_SIZE), key=lambda x: x['fit'])
                    
                    ops = []
                    child = p1['chrom'][:]
                    
                    if random.random() < CROSSOVER_RATE:
                        pt = random.randint(1, 8)
                        child = p1['chrom'][:pt] + p2['chrom'][pt:]
                        ops.append("Cruza")
                    else: ops.append("Clon")
                    
                    if random.random() < MUTATION_RATE:
                        child = smart_mutation(child, p_key)
                        ops.append("Mut.Int")
                        
                    f, cost, note, ns, nr, a, b = calc_fitness(child, p_key)
                    delta = f - max(p1['fit'], p2['fit'])
                    
                    new_pop.append({"id": f"G{g}-{len(new_pop)}", "chrom": child, "fit": f, 
                                    "cost": cost, "n_sav": ns, "n_perf": nr, "alpha": a, 
                                    "beta": b, "note": note, "parents": "P1+P2", 
                                    "operator": "+".join(ops), "delta": delta})
                pop = new_pop

            # Stats Gen
            best = max(pop, key=lambda x: x['fit'])
            worst = min(pop, key=lambda x: x['fit'])
            avg = sum(p['fit'] for p in pop) / len(pop)
            
            # Guardar JSON (MODIFICADO PARA INCLUIR DATOS COMPLETOS DE WORST)
            json_out[p_key]["gens"].append({
                "id": g, "avg": round(avg, 4),
                # Aseguramos que 'chrom' sea string para que no falle el JSON y agregamos decoded al worst
                "best": {**best, "chrom": str(best['chrom']), "decoded": decode_chromosome(best['chrom'])},
                "worst": {**worst, "chrom": str(worst['chrom']), "decoded": decode_chromosome(worst['chrom'])}, 
                "population": [{**p, "chrom": str(p['chrom'])} for p in pop]
            })
            
            if g % 20 == 0:
                print(f"  G{g}: Best={best['fit']:.4f} Avg={avg:.4f}")

    with open('datos_ag_mejorado.json', 'w', encoding='utf-8') as f:
        json.dump(json_out, f, ensure_ascii=False, indent=2)
        
    print("\n[OK] ARCHIVO JSON GENERADO: datos_ag_mejorado.json")

if __name__ == "__main__":
    run()