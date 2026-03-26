import pytest, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from tools import buscar_lugares, _haversine_km, _coordenadas_a_comuna, _wmo_a_impacto
import pytest
pytest_plugins = ('pytest_asyncio',)




def test_haversine_mismo_punto():
    assert _haversine_km(6.24, -75.58, 6.24, -75.58) == 0.0

def test_haversine_poblado_laureles():
    assert 3 < _haversine_km(6.2097, -75.5680, 6.2442, -75.5912) < 6

def test_comuna_poblado():
    assert _coordenadas_a_comuna(6.2097, -75.5680) == "El Poblado"

def test_comuna_laureles():
    assert _coordenadas_a_comuna(6.2442, -75.5912) == "Laureles"

def test_wmo_soleado():
    assert _wmo_a_impacto(0, 0)[1] == "soleado"

def test_wmo_lluvia_fuerte():
    assert _wmo_a_impacto(80, 10)[1] == "lluvia_fuerte"

@pytest.mark.asyncio
async def test_buscar_sin_filtros():
    r = await buscar_lugares()
    assert 1 <= len(r) <= 6

@pytest.mark.asyncio
async def test_lluvia_fuerte_solo_cubiertos():
    r = await buscar_lugares(clima_impacto="lluvia_fuerte")
    assert all(p["cubierto"] for p in r)

@pytest.mark.asyncio
async def test_familia_tarde():
    r = await buscar_lugares(grupo="familia", momento="tarde")
    for p in r:
        assert "familia" in p["grupos"] and "tarde" in p["momentos"]

@pytest.mark.asyncio
async def test_excluir_ids():
    todos = await buscar_lugares()
    excluir = [todos[0]["id"]]
    sin_primero = await buscar_lugares(excluir_ids=excluir)
    assert excluir[0] not in [p["id"] for p in sin_primero]

@pytest.mark.asyncio
async def test_score_presente():
    assert all("score_ajustado" in p for p in await buscar_lugares())

@pytest.mark.asyncio
async def test_score_ordenado():
    scores = [p["score_ajustado"] for p in await buscar_lugares()]
    assert scores == sorted(scores, reverse=True)
