"""
scripts/enriquecer_score.py
Enriquece places.json con:
  1. Distancia a estación Metro más cercana (OSM)
  2. Penalización hora pico
  3. Índice de accesibilidad (metro + tipo zona)
"""
import json, math, httpx, asyncio
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"

OVERPASS = "https://overpass-api.de/api/interpreter"

G="\033[92m"; R="\033[91m"; GR="\033[90m"; NC="\033[0m"
ok  = lambda m: print(f"{G}✓{NC} {m}")
err = lambda m: print(f"{R}✗{NC} {m}")
msg = lambda m: print(f"{GR}→{NC} {m}")

def haversine(lat1, lng1, lat2, lng2):
    R = 6371000  # metros
    dlat = math.radians(lat2-lat1)
    dlng = math.radians(lng2-lng1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1))*math.cos(math.radians(lat2))*math.sin(dlng/2)**2
    return R * 2 * math.asin(math.sqrt(a))

async def descargar_estaciones_metro():
    msg("Descargando estaciones Metro de Medellín (OSM)...")
    query = '''[out:json][timeout:20];
(
  node["network"="Metro de Medellín"](6.10,-75.70,6.40,-75.45);
  node["operator"="Metro de Medellín"](6.10,-75.70,6.40,-75.45);
);
out;'''
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.post(OVERPASS, data=query)
        elementos = r.json().get("elements", [])
    
    estaciones = [
        {
            "nombre": e["tags"].get("name", "?"),
            "lat": e["lat"],
            "lng": e["lon"],
            "linea": e["tags"].get("line", e["tags"].get("lines", "?")),
        }
        for e in elementos
        if e.get("lat") and e.get("lon")
    ]
    ok(f"{len(estaciones)} estaciones Metro descargadas")
    return estaciones

def bonus_metro(dist_m):
    """Bonus por proximidad al Metro."""
    if dist_m < 300:   return 0.4   # a pie fácil
    if dist_m < 600:   return 0.3   # caminata corta
    if dist_m < 1000:  return 0.2   # 10-12 min
    if dist_m < 2000:  return 0.1   # lejos pero accesible
    return 0.0

def penalizacion_hora_pico():
    """Penaliza lugares de difícil acceso en hora pico."""
    hora = datetime.now().hour
    if 7 <= hora <= 9 or 17 <= hora <= 19:
        return -0.15  # hora pico
    return 0.0

async def main():
    print("\n" + "═"*50)
    print("  Enriqueciendo scores con datos de movilidad")
    print("═"*50 + "\n")

    places = json.loads((DATA_DIR/"places.json").read_text())
    estaciones = await descargar_estaciones_metro()

    if not estaciones:
        err("Sin estaciones — abortando")
        return

    # Guardar estaciones para uso en tools.py
    (DATA_DIR/"estaciones_metro.json").write_text(
        json.dumps(estaciones, ensure_ascii=False, indent=2)
    )
    ok(f"estaciones_metro.json guardado")

    # Enriquecer cada lugar
    msg("Calculando distancias y bonuses...")
    hora_pico_pen = penalizacion_hora_pico()
    
    actualizados = 0
    for p in places:
        lat = p["coordenadas"]["lat"]
        lng = p["coordenadas"]["lng"]

        # Estación más cercana
        dist_min = float("inf")
        estacion_cercana = None
        for e in estaciones:
            d = haversine(lat, lng, e["lat"], e["lng"])
            if d < dist_min:
                dist_min = d
                estacion_cercana = e

        # Calcular bonus metro
        b_metro = bonus_metro(dist_min)

        # Guardar metadatos de accesibilidad
        p["accesibilidad"] = {
            "estacion_metro": estacion_cercana["nombre"] if estacion_cercana else None,
            "distancia_metro_m": round(dist_min),
            "bonus_metro": b_metro,
            "linea": estacion_cercana["linea"] if estacion_cercana else None,
        }

        # Actualizar score base con bonus metro
        p["score_base"] = round(p["score_base"] + b_metro, 2)
        actualizados += 1

    # Guardar
    (DATA_DIR/"places.json").write_text(
        json.dumps(places, ensure_ascii=False, indent=2)
    )

    ok(f"{actualizados} lugares actualizados con accesibilidad Metro")

    # Estadísticas
    con_metro = [p for p in places if p.get("accesibilidad",{}).get("distancia_metro_m",9999) < 600]
    print(f"\n  Lugares a menos de 600m del Metro: {len(con_metro)}")
    
    # Top 5 mejor conectados
    por_metro = sorted(places, key=lambda x: x.get("accesibilidad",{}).get("distancia_metro_m",9999))
    print(f"  Mejor conectados al Metro:")
    for p in por_metro[:5]:
        acc = p.get("accesibilidad",{})
        print(f"    {p['nombre'][:35]} — {acc.get('distancia_metro_m','?')}m de {acc.get('estacion_metro','?')}")

    print(f"\n{G}Listo.{NC}\n")

asyncio.run(main())
