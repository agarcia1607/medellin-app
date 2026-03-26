import { useState, useCallback } from 'react'
import MapaMapbox from './components/MapaMapbox.jsx'
import ChatUI from './components/ChatUI.jsx'
import AgentesVisibles from './components/AgentesVisibles.jsx'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export default function App() {
  const [historial, setHistorial] = useState([])
  const [perfil, setPerfil] = useState(null)
  const [recomendaciones, setRecomendaciones] = useState([])
  const [lugarSeleccionado, setLugarSeleccionado] = useState(null)
  const [clima, setClima] = useState(null)
  const [agentes, setAgentes] = useState({ perfilador: 'idle', clima: 'idle', orquestador: 'idle' })
  const [sessionId, setSessionId] = useState(null)

  const setAgente = (nombre, estado) =>
    setAgentes(prev => ({ ...prev, [nombre]: estado }))

  const enviarMensaje = useCallback(async (mensaje) => {
    const nuevoHistorial = [...historial, { role: 'user', content: mensaje }]
    setHistorial(nuevoHistorial)

    // Paso 1 — Perfilador
    setAgente('perfilador', 'active')
    try {
      const res = await fetch(`${API}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mensaje, historial, session_id: sessionId }),
      })
      const data = await res.json()
      setAgente('perfilador', 'done')

      // Guardar session_id del backend
      if (data.session_id) setSessionId(data.session_id)

      if (data.completo) {
        // Perfil completo — activar orquestador
        setPerfil(data.perfil)
        setHistorial(prev => [...prev, {
          role: 'assistant',
          content: '¡Listo! Buscando los mejores lugares para ti...'
        }])
        await buscarRecomendaciones(data.perfil, nuevoHistorial, data.session_id || sessionId)
      } else {
        // Necesita más info
        setHistorial(prev => [...prev, {
          role: 'assistant',
          content: data.pregunta
        }])
      }
    } catch (e) {
      setAgente('perfilador', 'error')
      console.error(e)
    }
  }, [historial])

  const buscarRecomendaciones = async (perfilCompleto, hist, sid) => {
    setAgente('clima', 'active')
    setAgente('orquestador', 'active')
    try {
      const res = await fetch(`${API}/recomendar`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ perfil: perfilCompleto, historial: hist, session_id: sid || sessionId }),
      })
      const data = await res.json()
      setAgente('clima', 'done')
      setAgente('orquestador', 'done')

      if (data.recomendaciones) {
        setRecomendaciones(data.recomendaciones)
        setClima(data.clima)
        setLugarSeleccionado(data.recomendaciones[0])
        setHistorial(prev => [...prev, {
          role: 'assistant',
          content: data.razonamiento
        }])
      }
    } catch (e) {
      setAgente('orquestador', 'error')
      console.error(e)
    }
  }

  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: '1fr 380px',
      gridTemplateRows: '48px 1fr',
      height: '100vh',
      background: '#f5f5f4',
    }}>
      {/* Topbar */}
      <div style={{
        gridColumn: '1 / -1',
        background: 'white',
        borderBottom: '0.5px solid #e5e5e5',
        display: 'flex',
        alignItems: 'center',
        padding: '0 16px',
        gap: '12px',
      }}>
        <div style={{ fontSize: 15, fontWeight: 500 }}>
          Medellín <span style={{ color: '#1D9E75' }}>Places</span>
        </div>
        {clima && (
          <span style={{
            fontSize: 12, padding: '3px 8px', borderRadius: 99,
            background: '#E1F5EE', color: '#0F6E56', border: '0.5px solid #5DCAA5'
          }}>
            ● {clima.temperatura_c}°C · {clima.descripcion}
          </span>
        )}
        <div style={{ marginLeft: 'auto', display: 'flex', gap: 6 }}>
          {['OSM', 'pb3w-3vmc', 'Open-Meteo'].map(f => (
            <span key={f} style={{
              fontSize: 11, padding: '2px 7px', borderRadius: 99,
              background: '#f5f5f4', border: '0.5px solid #e5e5e5', color: '#737370'
            }}>{f}</span>
          ))}
        </div>
      </div>

      {/* Mapa */}
      <MapaMapbox
        recomendaciones={recomendaciones}
        lugarSeleccionado={lugarSeleccionado}
        onSeleccionar={setLugarSeleccionado}
      />

      {/* Panel lateral */}
      <div style={{
        background: 'white',
        borderLeft: '0.5px solid #e5e5e5',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
      }}>
        <ChatUI
          historial={historial}
          onEnviar={enviarMensaje}
          cargando={agentes.perfilador === 'active' || agentes.orquestador === 'active'}
        />
        <AgentesVisibles agentes={agentes} />
      </div>
    </div>
  )
}
