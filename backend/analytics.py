"""
analytics.py — Recolección de datos anonimizados en archivos CSV.

Genera 5 CSVs con rotación diaria:
  - sessions_YYYY-MM-DD.csv
  - mensajes_YYYY-MM-DD.csv
  - perfiles_YYYY-MM-DD.csv
  - recomendaciones_YYYY-MM-DD.csv
  - herramientas_YYYY-MM-DD.csv

Principios de anonimización:
  - Sin IPs, cookies, user-agents ni datos de dispositivo
  - Sin texto literal de mensajes (solo longitud y metadatos)
  - session_id son UUID aleatorios sin correlación temporal
  - Nombres de lugares son datos públicos, no personales
"""

import csv
import uuid
import asyncio
from datetime import datetime, date
from pathlib import Path
from typing import Optional

BASE_DIR = Path(__file__).parent / "data" / "analytics"

# ── Esquemas CSV ──────────────────────────────────────────────

SCHEMAS = {
    "sessions": [
        "session_id", "timestamp_inicio", "timestamp_fin",
        "total_mensajes", "perfil_completado", "recomendacion_generada",
    ],
    "mensajes": [
        "mensaje_id", "session_id", "timestamp", "rol",
        "longitud_texto", "idioma_detectado", "paso_flujo",
    ],
    "perfiles": [
        "perfil_id", "session_id", "timestamp",
        "tipo", "momento", "grupo", "precio", "modo_usuario",
        "tiene_restricciones", "preguntas_necesarias",
    ],
    "recomendaciones": [
        "recomendacion_id", "session_id", "perfil_id", "timestamp",
        "lugar_nombre", "lugar_tipo", "lugar_comuna", "score",
        "posicion", "clima_impacto", "tiene_metro_cercano",
    ],
    "herramientas": [
        "uso_id", "session_id", "timestamp",
        "herramienta", "duracion_ms", "exito", "iteracion",
    ],
}

# Lock para escritura concurrente segura
_write_lock = asyncio.Lock()


def _hoy() -> str:
    return date.today().isoformat()


def _csv_path(nombre: str) -> Path:
    return BASE_DIR / f"{nombre}_{_hoy()}.csv"


def _ensure_header(nombre: str):
    """Crea el archivo con encabezado si no existe."""
    path = _csv_path(nombre)
    if not path.exists():
        BASE_DIR.mkdir(parents=True, exist_ok=True)
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(SCHEMAS[nombre])


def _append_row(nombre: str, row: list):
    """Escribe una fila al CSV correspondiente (síncrono, se llama dentro del lock)."""
    _ensure_header(nombre)
    path = _csv_path(nombre)
    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(row)


async def _write(nombre: str, row: list):
    """Escritura thread-safe."""
    async with _write_lock:
        await asyncio.get_event_loop().run_in_executor(None, _append_row, nombre, row)


# ── Detección simple de idioma ────────────────────────────────

_EN_WORDS = {"the", "is", "are", "what", "where", "how", "can", "want", "looking", "for", "with", "please"}
_ES_WORDS = {"el", "la", "los", "las", "es", "son", "qué", "dónde", "cómo", "quiero", "busco", "con", "para"}


def _detectar_idioma(texto: str) -> str:
    words = set(texto.lower().split())
    en_count = len(words & _EN_WORDS)
    es_count = len(words & _ES_WORDS)
    if es_count > en_count:
        return "es"
    if en_count > es_count:
        return "en"
    return "es"  # default para Medellín


# ── API pública ───────────────────────────────────────────────

def nueva_session() -> str:
    """Genera un nuevo session_id."""
    return str(uuid.uuid4())


async def registrar_session(session_id: str, total_mensajes: int,
                            perfil_completado: bool, recomendacion_generada: bool,
                            timestamp_inicio: str, timestamp_fin: str):
    await _write("sessions", [
        session_id, timestamp_inicio, timestamp_fin,
        total_mensajes, perfil_completado, recomendacion_generada,
    ])


async def registrar_mensaje(session_id: str, rol: str, texto: str, paso_flujo: str):
    await _write("mensajes", [
        str(uuid.uuid4()),  # mensaje_id
        session_id,
        datetime.now().isoformat(timespec="seconds"),
        rol,
        len(texto),
        _detectar_idioma(texto) if rol == "usuario" else "",
        paso_flujo,
    ])


async def registrar_perfil(session_id: str, perfil: dict, preguntas_necesarias: int) -> str:
    perfil_id = str(uuid.uuid4())
    await _write("perfiles", [
        perfil_id,
        session_id,
        datetime.now().isoformat(timespec="seconds"),
        perfil.get("tipo", ""),
        perfil.get("momento", ""),
        perfil.get("grupo", ""),
        perfil.get("precio", ""),
        perfil.get("modo_usuario", ""),
        bool(perfil.get("restricciones")),
        preguntas_necesarias,
    ])
    return perfil_id


async def registrar_recomendacion(session_id: str, perfil_id: str,
                                   lugar: dict, posicion: int, clima_impacto: str):
    metro_info = lugar.get("metro", "")
    tiene_metro = bool(metro_info and metro_info != "N/D" and "no" not in metro_info.lower())
    await _write("recomendaciones", [
        str(uuid.uuid4()),
        session_id,
        perfil_id,
        datetime.now().isoformat(timespec="seconds"),
        lugar.get("lugar", ""),
        "",  # lugar_tipo — se infiere del perfil
        "",  # lugar_comuna — no siempre disponible en respuesta
        lugar.get("score", ""),
        posicion,
        clima_impacto,
        tiene_metro,
    ])


async def registrar_herramienta(session_id: str, herramienta: str,
                                 duracion_ms: int, exito: bool, iteracion: int):
    await _write("herramientas", [
        str(uuid.uuid4()),
        session_id,
        datetime.now().isoformat(timespec="seconds"),
        herramienta,
        duracion_ms,
        exito,
        iteracion,
    ])
