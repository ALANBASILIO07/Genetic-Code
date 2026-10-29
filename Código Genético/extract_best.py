import json

data = json.load(open('datos_ag_mejorado.json', encoding='utf-8'))

for perfil in ['admin', 'student', 'dev', 'isp']:
    best = data[perfil]['gens'][-1]['best']
    print(f'\n{"="*70}')
    print(f'PERFIL: {data[perfil]["name"].upper()}')
    print(f'{"="*70}')
    print(f'Cromosoma: {best["chrom"]}')
    print(f'Fitness: {best["fit"]:.4f}')
    print(f'Costo: ${best["cost"]:,.0f}')
    print(f'\nDecodificación Completa:')
    for i, (k, v) in enumerate(best['decoded'].items(), 1):
        print(f'  Gen {i} - {k:15}: {v}')
