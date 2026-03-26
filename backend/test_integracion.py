import asyncio, sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from agents import perfilador, orquestador
from tools import get_clima, buscar_lugares

G="\033[92m"; R="\033[91m"; GR="\033[90m"; NC="\033[0m"
ok  = lambda m: print(f"{G}✓{NC} {m}")
err = lambda m: print(f"{R}✗{NC} {m}")

async def main():
    print("\n" + "═"*50)
    print("  PRUEBA INTEGRACIÓN — Medellín App")
    print("═"*50)
    resultados = {"ok": 0, "fail": 0}

    async def run(nombre, coro):
        print(f"\n{GR}{'─'*50}{NC}\nTEST · {nombre}")
        try:
            r = await coro
            resultados["ok"] += 1
            return r
        except Exception as e:
            err(f"{nombre}: {e}")
            resultados["fail"] += 1

    # 1. Clima
    async def t_clima():
        r = await get_clima()
        assert "impacto" in r
        ok(f"{r['descripcion']} · {r['temperatura_c']}°C · {r['impacto']}")
        return r
    await run("get_clima", t_clima())

    # 2. Buscar lugares
    async def t_buscar():
        r = await buscar_lugares(grupo="familia", momento="tarde")
        assert len(r) >= 1
        ok(f"{len(r)} candidatos · top: {r[0]['nombre']} (score {r[0]['score_ajustado']})")
    await run("buscar_lugares", t_buscar())

    # 3. Perfilador turno 1
    async def t_perfil1():
        r = await perfilador("quiero salir hoy", [])
        assert "completo" in r
        if r["completo"]: ok(f"Perfil directo: {r['perfil']}")
        else:              ok(f"Pregunta: {r['pregunta']}")
        return r
    r1 = await run("perfilador turno 1", t_perfil1())

    # 4. Perfilador turno 2
    async def t_perfil2():
        hist = [{"role":"user","content":"quiero salir hoy"}]
        if r1 and not r1.get("completo"):
            hist.append({"role":"assistant","content": r1.get("pregunta","")})
        r = await perfilador("con mi familia en la tarde, algo al aire libre y económico", hist)
        assert "completo" in r
        if r["completo"]: ok(f"Perfil: {r['perfil']}")
        else:              ok(f"Aún pregunta: {r.get('pregunta')}")
        return r
    r2 = await run("perfilador turno 2", t_perfil2())

    # 5. Orquestador
    perfil = (r2 or {}).get("perfil") or (r1 or {}).get("perfil") or \
             {"tipo":"naturaleza","momento":"tarde","grupo":"familia","precio":"bajo"}
    async def t_orquestador():
        r = await orquestador(perfil, [])
        assert "recomendaciones" in r and len(r["recomendaciones"]) >= 1
        ok(f"Razonamiento: {r['razonamiento'][:70]}...")
        for i, rec in enumerate(r["recomendaciones"], 1):
            print(f"  {i}. {rec['lugar']} — score {rec.get('score','?')}")
            print(f"     {GR}{rec.get('motivo','')[:65]}{NC}")
    await run("orquestador", t_orquestador())

    print(f"\n{'─'*50}")
    color = G if resultados["fail"] == 0 else R
    print(f"{color}{resultados['ok']}/{resultados['ok']+resultados['fail']} tests pasaron{NC}\n")
    sys.exit(0 if resultados["fail"] == 0 else 1)

asyncio.run(main())
