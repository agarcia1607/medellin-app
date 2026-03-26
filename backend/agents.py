import json, os, time
from dotenv import load_dotenv
import anthropic
from tools import TOOLS_SCHEMA, ejecutar_tool
import analytics

load_dotenv()
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
MODEL  = "claude-sonnet-4-5"

PERFILADOR_SYSTEM = """
Eres un asistente que ayuda a recomendar lugares en Medellín.
Con MÁX 2 preguntas extrae: tipo de actividad, momento del día y con quién va.

Cuando tengas suficiente info responde ÚNICAMENTE con JSON:
{"completo": true, "perfil": {"tipo": "naturaleza"|"cultura"|"entretenimiento"|"gastronomia"|null, "momento": "mañana"|"tarde"|"noche"|null, "grupo": "familia"|"pareja"|"amigos"|"solo"|"turista"|null, "precio": "gratis"|"bajo"|"medio"|"alto"|null, "restricciones": [], "modo_usuario": "explorador"|"decidido"|"con_prisa"}}

Si necesitas más info:
{"completo": false, "pregunta": "tu pregunta aquí"}

Responde en español, cálido y breve.
""".strip()

ORQUESTADOR_SYSTEM = """
Eres un experto recomendador de lugares en Medellín.
Proceso obligatorio:
1. Llama get_clima SIEMPRE primero
2. Llama buscar_lugares con el perfil + clima_impacto
3. Elige top 3 por score_ajustado
4. Llama servicios_cercanos para cada uno
5. Al elegir el top 3, aplica estas reglas:
   - NO repitas la misma cadena comercial (ej: dos Crepes & Waffles = rechazar uno)
   - Prefiere diversidad geográfica (diferentes comunas/barrios)
   - Si hay empate en score, elige el de mayor diversidad respecto a los ya elegidos
   - Excluye lugares que no sean destinos turísticos (universidades, infraestructura, etc.)
6. Devuelve ÚNICAMENTE este JSON:
{"razonamiento": "texto breve", "clima": {"descripcion": "...", "impacto": "...", "recomendacion": "..."}, "recomendaciones": [{"lugar": "nombre", "score": 9.1, "motivo": "...", "coordenadas": {"lat": 0.0, "lng": 0.0}, "metro": "Estación más cercana y distancia", "servicios_cercanos": ["..."]}], "descartados": [{"lugar": "nombre", "razon_descarte": "..."}]}

Responde en español.
""".strip()

async def perfilador(mensaje: str, historial: list) -> dict:
    messages = historial + [{"role": "user", "content": mensaje}]
    response = client.messages.create(model=MODEL, max_tokens=512,
                                      system=PERFILADOR_SYSTEM, messages=messages)
    texto = response.content[0].text.strip()
    try:
        if "```" in texto:
            texto = texto.split("```")[1]
            if texto.startswith("json"): texto = texto[4:]
        return json.loads(texto.strip())
    except json.JSONDecodeError:
        return {"completo": False, "pregunta": texto}

async def orquestador(perfil: dict, historial: list, session_id: str = "") -> dict:
    messages = [{"role": "user", "content": f"Encuentra los mejores 3 lugares para: {json.dumps(perfil, ensure_ascii=False)}"}]
    for iteracion in range(8):
        response = client.messages.create(model=MODEL, max_tokens=2048,
                                          system=ORQUESTADOR_SYSTEM,
                                          tools=TOOLS_SCHEMA, messages=messages)
        messages.append({"role": "assistant", "content": response.content})
        if response.stop_reason == "end_turn":
            for block in response.content:
                if hasattr(block, "text"):
                    texto = block.text.strip()
                    try:
                        if "```" in texto:
                            texto = texto.split("```")[1]
                            if texto.startswith("json"): texto = texto[4:]
                        return json.loads(texto.strip())
                    except: return {"error": "JSON inválido", "raw": texto}
        if response.stop_reason == "tool_use":
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    t_inicio = time.time()
                    exito = True
                    try:
                        resultado = await ejecutar_tool(block.name, block.input)
                    except Exception:
                        resultado = {"error": "Tool falló"}
                        exito = False
                    duracion_ms = int((time.time() - t_inicio) * 1000)

                    # Registrar uso de herramienta
                    if session_id:
                        await analytics.registrar_herramienta(
                            session_id, block.name, duracion_ms, exito, iteracion + 1
                        )

                    tool_results.append({"type": "tool_result", "tool_use_id": block.id,
                                         "content": json.dumps(resultado, ensure_ascii=False)})
            messages.append({"role": "user", "content": tool_results})
    return {"error": "Máximo de iteraciones alcanzado"}
