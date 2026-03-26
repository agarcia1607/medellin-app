from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import os
from datetime import datetime
from dotenv import load_dotenv
from agents import perfilador, orquestador
import analytics

load_dotenv()

app = FastAPI(title="Medellín App API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("FRONTEND_URL", "http://localhost:5173"), "*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    mensaje: str
    historial: list[dict] = []
    session_id: Optional[str] = None

class RecomendarRequest(BaseModel):
    perfil: dict
    historial: list[dict] = []
    session_id: Optional[str] = None

@app.get("/health")
def health():
    return {"status": "ok", "version": "0.2.0"}

@app.post("/chat")
async def chat(req: ChatRequest):
    session_id = req.session_id or analytics.nueva_session()
    try:
        # Registrar mensaje del usuario
        await analytics.registrar_mensaje(
            session_id, "usuario", req.mensaje, "perfilado"
        )

        resultado = await perfilador(req.mensaje, req.historial)

        # Registrar respuesta del asistente
        respuesta_texto = resultado.get("pregunta", "Perfil completado")
        await analytics.registrar_mensaje(
            session_id, "asistente", respuesta_texto, "perfilado"
        )

        # Si el perfil se completó, registrarlo
        if resultado.get("completo"):
            preguntas = len([m for m in req.historial if m.get("role") == "assistant"])
            perfil_id = await analytics.registrar_perfil(
                session_id, resultado["perfil"], preguntas
            )
            resultado["perfil_id"] = perfil_id

        resultado["session_id"] = session_id
        return resultado
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/recomendar")
async def recomendar(req: RecomendarRequest):
    session_id = req.session_id or analytics.nueva_session()
    timestamp_inicio = datetime.now().isoformat(timespec="seconds")
    try:
        resultado = await orquestador(req.perfil, req.historial, session_id)

        # Registrar recomendaciones
        clima_impacto = ""
        if resultado.get("clima"):
            clima_impacto = resultado["clima"].get("impacto", "")

        perfil_id = req.perfil.get("_perfil_id", "")
        for i, rec in enumerate(resultado.get("recomendaciones", []), 1):
            await analytics.registrar_recomendacion(
                session_id, perfil_id, rec, i, clima_impacto
            )

        # Registrar sesión completa
        total_mensajes = len(req.historial) + 1
        await analytics.registrar_session(
            session_id, total_mensajes,
            perfil_completado=True,
            recomendacion_generada=bool(resultado.get("recomendaciones")),
            timestamp_inicio=timestamp_inicio,
            timestamp_fin=datetime.now().isoformat(timespec="seconds"),
        )

        resultado["session_id"] = session_id
        return resultado
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
