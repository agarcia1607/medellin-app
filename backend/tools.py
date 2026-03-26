"""
tools.py — Las 3 herramientas del Orquestador (Claude tool_use)
  get_clima()          → Open-Meteo API (sin key)
  buscar_lugares()     → places.json local
  servicios_cercanos() → datos.gov.co + Google Places
"""
import csv, json, math, os
from pathlib import Path
import httpx
from dotenv import load_dotenv

load_dotenv()

BASE_DIR       = Path(__file__).parent
PLACES_PATH    = BASE_DIR / "data" / "places.json"
SEGURIDAD_PATH = BASE_DIR / "data" / "seguridad.csv"

OPEN_METEO_URL    = "https://api.open-meteo.com/v1/forecast"
DATOS_GOV_URL     = "https://www.datos.gov.co/resource/pb3w-3vmc.json"
GOOGLE_PLACES_URL = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"

MEDELLIN_LAT = 6.2442
MEDELLIN_LNG = -75.5812


def _load_places():
    with open(PLACES_PATH, encoding="utf-8") as f:
        return json.load(f)

def _hora_pico_factor() -> float:
    """Penalización en hora pico (7-9am y 5-7pm)."""
    from datetime import datetime
    hora = datetime.now().hour
    if 7 <= hora <= 9 or 17 <= hora <= 19:
        return -0.15
    return 0.0

def _load_seguridad() -> dict:
    """
    Prioridad:
      1. comunas_empresas.json — datos reales pb3w-3vmc (actividad por comuna)
      2. seguridad.csv         — fallback estimado
    """
    empresas_json = BASE_DIR / "data" / "comunas_empresas.json"
    if empresas_json.exists():
        with open(empresas_json, encoding="utf-8") as f:
            return json.load(f)
    result = {}
    with open(SEGURIDAD_PATH, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            result[row["lugar_id"]] = row
    return result

def _haversine_km(lat1, lng1, lat2, lng2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (math.sin(dlat/2)**2
         + math.cos(math.radians(lat1))
         * math.cos(math.radians(lat2))
         * math.sin(dlng/2)**2)
    return R * 2 * math.asin(math.sqrt(a))

def _coordenadas_a_comuna(lat, lng):
    comunas = {
        "El Poblado":    (6.2097, -75.5680),
        "Laureles":      (6.2442, -75.5912),
        "La Candelaria": (6.2518, -75.5636),
        "Aranjuez":      (6.2681, -75.5659),
        "Popular":       (6.2878, -75.5480),
        "Belen":         (6.2231, -75.6020),
        "Robledo":       (6.2697, -75.6010),
        "Manrique":      (6.2750, -75.5480),
        "Buenos Aires":  (6.2350, -75.5490),
    }
    return min(comunas, key=lambda n: _haversine_km(lat, lng, *comunas[n]))

def _wmo_a_impacto(code, lluvia_mm):
    if code <= 1:   return "Despejado",            "soleado",       "Perfecto para actividades al aire libre"
    if code <= 3:   return "Parcialmente nublado", "nublado",       "Buenas condiciones, puede refrescar"
    if code <= 49:  return "Nublado",              "nublado",       "Buenas condiciones en general"
    if code <= 67 or lluvia_mm < 5:
                    return "Lluvia ligera",         "lluvia_ligera", "Preferir lugares cubiertos"
    return              "Lluvia fuerte",            "lluvia_fuerte", "Solo lugares 100% cubiertos"

def _tipos_a_keyword(tipo):
    return {"restaurant":"restaurante","cafe":"cafe","bar":"bar",
            "pharmacy":"farmacia","bank":"bancario","supermarket":"supermercado",
            "parking":"parqueadero"}.get(tipo, "")


async def get_clima():
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            r = await client.get(OPEN_METEO_URL, params={
                "latitude": MEDELLIN_LAT, "longitude": MEDELLIN_LNG,
                "current": "temperature_2m,precipitation,relative_humidity_2m,weather_code",
                "timezone": "America/Bogota", "forecast_days": 1,
            })
            r.raise_for_status()
            cur = r.json()["current"]
        desc, impacto, rec = _wmo_a_impacto(cur["weather_code"], cur["precipitation"])
        return {"temperatura_c": cur["temperature_2m"], "lluvia_mm": cur["precipitation"],
                "humedad_pct": cur["relative_humidity_2m"], "descripcion": desc,
                "impacto": impacto, "recomendacion": rec}
    except Exception as exc:
        return {"temperatura_c": 24.0, "lluvia_mm": 0.0, "humedad_pct": 70,
                "descripcion": "Sin datos (estimado)", "impacto": "soleado",
                "recomendacion": "Condiciones normales estimadas", "_error": str(exc)}


async def buscar_lugares(tipo=None, momento=None, grupo=None,
                         cubierto=None, precio=None, clima_impacto=None, excluir_ids=None):
    places    = _load_places()
    seguridad = _load_seguridad()
    excluir   = set(excluir_ids or [])
    if clima_impacto == "lluvia_fuerte":
        cubierto = True
    resultados = []
    for p in places:
        if p["id"] in excluir:                                continue
        if tipo    and p["tipo"] != tipo:                     continue
        if momento and momento not in p.get("momentos", []): continue
        if grupo   and grupo not in p.get("grupos", []):      continue
        if cubierto is True and not p.get("cubierto", False): continue
        if precio  and p.get("precio_promedio") != precio:    continue
        score = p["score_base"]
        # Buscar por comuna del lugar (comunas_empresas.json) o por id (seguridad.csv)
        comuna_key = (p.get("comuna") or "").lower().replace(" ", "_").replace("-","_")
        seg   = seguridad.get(comuna_key) or seguridad.get(p["id"], {})
        nivel = seg.get("nivel_actividad") or seg.get("nivel_seguridad", "medio")
        score += {"muy_alto": 0.3, "alto": 0.1, "medio": 0.0, "bajo": -0.5}.get(nivel, 0)
        if clima_impacto == "soleado" and not p.get("cubierto"):         score += 0.2
        if clima_impacto in ("lluvia_ligera","lluvia_fuerte") and p.get("cubierto"): score += 0.4

        # Bonus Metro (pre-calculado en places.json)
        acc = p.get("accesibilidad", {})
        score += acc.get("bonus_metro", 0)

        # Hora pico — penalizar en rush hour
        score += _hora_pico_factor()
        resultados.append({**p, "score_ajustado": round(score, 2),
                           "seguridad": {"nivel": nivel, "nota": seg.get("nota",""),
                                         "recomendacion_horario": seg.get("recomendacion_horario","")}})
    resultados.sort(key=lambda x: x["score_ajustado"], reverse=True)

    # Diversificar — máx 1 por cadena comercial y máx 2 por comuna
    def nombre_base(nombre):
        """Extrae nombre base sin sufijo de comuna."""
        if " (" in nombre:
            return nombre.split(" (")[0].lower().strip()
        return nombre.lower().strip()

    cadenas_vistas = {}
    comunas_vistas = {}
    diversificados = []
    resto = []

    for p in resultados:
        base = nombre_base(p["nombre"])
        comuna = p.get("comuna", "")
        n_cadena = cadenas_vistas.get(base, 0)
        n_comuna = comunas_vistas.get(comuna, 0)

        if n_cadena == 0 and n_comuna < 2:
            diversificados.append(p)
            cadenas_vistas[base] = n_cadena + 1
            comunas_vistas[comuna] = n_comuna + 1
        else:
            resto.append(p)

        if len(diversificados) >= 6:
            break

    # Si no hay suficientes, completar con el resto
    if len(diversificados) < 3:
        for p in resto:
            if p not in diversificados:
                diversificados.append(p)
            if len(diversificados) >= 6:
                break

    return diversificados[:6]


async def servicios_cercanos(lat, lng, radio_m=500, tipos=None):
    resultado = {"fuente_oficial": [], "fuente_google": [], "resumen": ""}
    try:
        comuna = _coordenadas_a_comuna(lat, lng)
        where  = f"comuna='{comuna}'"
        if tipos:
            kw = _tipos_a_keyword(tipos[0])
            if kw: where += f" AND upper(actividad_economica) like upper('%{kw}%')"
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(DATOS_GOV_URL, params={
                "$limit": 20, "$where": where,
                "$select": "nombre_comercial,actividad_economica,comuna,direccion,telefono",
                "$order": "nombre_comercial ASC"})
            if r.status_code == 200:
                resultado["fuente_oficial"] = [
                    {"nombre": row.get("nombre_comercial","N/D"), "actividad": row.get("actividad_economica","N/D"),
                     "comuna": row.get("comuna","N/D"), "direccion": row.get("direccion","N/D"),
                     "telefono": row.get("telefono","")} for row in r.json()[:10]]
    except Exception as exc:
        resultado["_error_oficial"] = str(exc)
    google_key = os.getenv("GOOGLE_PLACES_API_KEY","")
    if google_key:
        try:
            params = {"location": f"{lat},{lng}", "radius": radio_m, "key": google_key, "language": "es"}
            if tipos: params["type"] = tipos[0]
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.get(GOOGLE_PLACES_URL, params=params)
                if r.status_code == 200:
                    resultado["fuente_google"] = [
                        {"nombre": p.get("name"), "tipo": (p.get("types") or ["N/D"])[0],
                         "calificacion": p.get("rating"), "abierto": p.get("opening_hours",{}).get("open_now"),
                         "direccion": p.get("vicinity")} for p in r.json().get("results",[])[:8]]
        except Exception as exc:
            resultado["_error_google"] = str(exc)
    # 3. OpenStreetMap
    try:
        tipo_lugar = tipos[0] if tipos else "gastronomia"
        osm = await servicios_osm(lat, lng, tipo_lugar, radio_m)
        resultado["fuente_osm"] = osm
    except Exception as exc:
        resultado["_error_osm"] = str(exc)

    resultado["resumen"] = (f"{len(resultado['fuente_oficial'])} negocios oficiales MDE, "
                            f"{len(resultado['fuente_google'])} en Google Maps — radio {radio_m}m")
    return resultado


TOOLS_SCHEMA = [
    {"name": "get_clima",
     "description": "Clima actual de Medellín. Llama esto primero, antes de buscar lugares.",
     "input_schema": {"type": "object", "properties": {}, "required": []}},
    {"name": "buscar_lugares",
     "description": "Filtra y rankea los 15 lugares según perfil del usuario. Devuelve top 6.",
     "input_schema": {"type": "object", "properties": {
         "tipo":          {"type": "string", "enum": ["naturaleza","cultura","entretenimiento","gastronomia"]},
         "momento":       {"type": "string", "enum": ["mañana","tarde","noche"]},
         "grupo":         {"type": "string", "enum": ["familia","pareja","amigos","solo","turista"]},
         "cubierto":      {"type": "boolean"},
         "precio":        {"type": "string", "enum": ["gratis","bajo","medio","alto"]},
         "clima_impacto": {"type": "string", "enum": ["soleado","nublado","lluvia_ligera","lluvia_fuerte"]},
         "excluir_ids":   {"type": "array", "items": {"type": "string"}}}, "required": []}},
    {"name": "servicios_cercanos",
     "description": "Negocios en 500m de un lugar. Usa datos.gov.co + Google Places.",
     "input_schema": {"type": "object",
                      "properties": {"lat": {"type": "number"}, "lng": {"type": "number"},
                                     "radio_m": {"type": "integer", "default": 500},
                                     "tipos": {"type": "array", "items": {"type": "string"}}},
                      "required": ["lat","lng"]}},
]


async def ejecutar_tool(nombre, inputs):
    if nombre == "get_clima":           return await get_clima()
    if nombre == "buscar_lugares":      return {"candidatos": await buscar_lugares(**inputs)}
    if nombre == "servicios_cercanos":  return await servicios_cercanos(**inputs)
    return {"error": f"Tool desconocida: {nombre}"}


# ══════════════════════════════════════════════════════════════
# FUENTE EXTRA · OpenStreetMap via Overpass API
# ══════════════════════════════════════════════════════════════
OVERPASS_URL = "https://overpass-api.de/api/interpreter"

OSM_AMENITY_MAP = {
    "gastronomia":     "restaurant|cafe|bar|fast_food|food_court",
    "cultura":         "theatre|cinema|museum|library|arts_centre",
    "naturaleza":      "park",
    "entretenimiento": "restaurant|bar|nightclub|cafe",
}

async def servicios_osm(lat: float, lng: float, tipo: str = "gastronomia", radio_m: int = 500) -> list[dict]:
    """
    Busca servicios cercanos usando OpenStreetMap (Overpass API).
    100% público, sin API key, datos reales.
    """
    amenity_filter = OSM_AMENITY_MAP.get(tipo, "restaurant|cafe|bar")
    delta = radio_m / 111320  # metros a grados aprox
    bbox = f"{lat-delta},{lng-delta},{lat+delta},{lng+delta}"

    query = f"""[out:json][timeout:15];
node["amenity"~"{amenity_filter}"]({bbox});
out 10;"""

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.post(OVERPASS_URL, data=query)
            r.raise_for_status()
            elementos = r.json().get("elements", [])

        return [
            {
                "nombre":    e["tags"].get("name", "Sin nombre"),
                "tipo":      e["tags"].get("amenity", "N/D"),
                "lat":       e["lat"],
                "lng":       e["lon"],
                "fuente":    "OpenStreetMap",
            }
            for e in elementos
            if e.get("tags", {}).get("name")  # solo con nombre
        ][:8]
    except Exception as exc:
        return [{"error": str(exc), "fuente": "OpenStreetMap"}]
