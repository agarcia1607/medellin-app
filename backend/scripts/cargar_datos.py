"""
Fuentes reales accesibles:
  pb3w-3vmc — Estructura empresarial Medellín por comunas (REAL, público)
  
Genera:
  data/comunas_empresas.json — densidad empresarial por comuna
  
Nota: seguridad.csv se mantiene como estimación hasta que
      datos.gov.co abra acceso público a los datasets del SISC.
"""
import json, httpx, sys
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

EMPRESAS_URL = "https://www.datos.gov.co/resource/pb3w-3vmc.json"

COMUNAS = [
    "altavista","aranjuez","belen","buenos_aires","castilla",
    "doce_de_octubre","el_poblado","guayabal","la_america",
    "la_candelaria","laureles_estadio","manrique","palmitas",
    "popular","robledo","san_antonio_de_prado","san_cristobal",
    "san_javier","santa_cruz","santa_elena","villa_hermosa"
]

G="\033[92m"; R="\033[91m"; GR="\033[90m"; NC="\033[0m"
ok  = lambda m: print(f"{G}✓{NC} {m}")
err = lambda m: print(f"{R}✗{NC} {m}")
msg = lambda m: print(f"{GR}→{NC} {m}")

def cargar_empresas():
    msg("Descargando estructura empresarial (pb3w-3vmc)...")
    try:
        # Traer año más reciente disponible
        with httpx.Client(timeout=30) as c:
            r = c.get(EMPRESAS_URL, params={"$limit": 1000, "$order": "a_o DESC"})
            r.raise_for_status()
            raw = r.json()
        ok(f"{len(raw)} filas descargadas")
    except Exception as e:
        err(f"Error: {e}"); return False

    # Detectar año más reciente
    anios = sorted(set(row.get("a_o","0") for row in raw), reverse=True)
    anio_target = anios[0] if anios else "2023"
    msg(f"Usando año {anio_target}")

    # Sumar empresas por comuna para ese año
    totales = {c: 0 for c in COMUNAS}
    filas_anio = [r for r in raw if r.get("a_o") == anio_target]
    
    for row in filas_anio:
        for comuna in COMUNAS:
            try: totales[comuna] += int(row.get(comuna) or 0)
            except: pass

    # Filtrar comunas con datos
    totales = {k: v for k, v in totales.items() if v > 0}
    if not totales:
        err("Sin datos por comuna"); return False

    # Clasificar por cuartiles (más empresas = más activo)
    valores = sorted(totales.values())
    n = len(valores)
    q1, q2, q3 = valores[n//4], valores[n//2], valores[3*n//4]

    resultado = {}
    for comuna, total in totales.items():
        if total <= q1:    nivel = "bajo"
        elif total <= q2:  nivel = "medio"
        elif total <= q3:  nivel = "alto"
        else:              nivel = "muy_alto"

        resultado[comuna] = {
            "total_empresas": total,
            "nivel_actividad": nivel,
            "anio": anio_target,
            "fuente": "datos.gov.co/pb3w-3vmc"
        }

    out = DATA_DIR / "comunas_empresas.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(resultado, f, ensure_ascii=False, indent=2)

    top3 = sorted(resultado.items(), key=lambda x: x[1]["total_empresas"], reverse=True)[:3]
    ok(f"comunas_empresas.json → {len(resultado)} comunas (año {anio_target})")
    top3_str = ", ".join(f"{c}({d['total_empresas']})" for c,d in top3)
    ok(f"Top 3 más activas: {top3_str}")
    return True

def main():
    print("\n" + "═"*50)
    print("  Cargando datos reales — datos.gov.co")
    print("═"*50 + "\n")

    ok("pb3w-3vmc — estructura empresarial (accesible)")
    print(f"{GR}  wtnd-h3vi — criminalidad SISC (403 restringido){NC}")
    print(f"{GR}  fsex-j46t — atractivos turísticos (migrado a MEData){NC}")
    print()

    errores = 0
    if not cargar_empresas(): errores += 1

    print()
    color = G if errores == 0 else R
    print(f"{color}{'Listo.' if errores==0 else str(errores)+' error(es).'}{NC}")
    if errores == 0:
        print(f"{GR}comunas_empresas.json disponible para tools.py{NC}\n")
    sys.exit(errores)

if __name__ == "__main__":
    main()
