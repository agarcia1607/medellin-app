import { useState, useRef, useEffect } from 'react'

export default function ChatUI({ historial, onEnviar, cargando }) {
  const [input, setInput] = useState('')
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [historial])

  const enviar = () => {
    if (!input.trim() || cargando) return
    onEnviar(input.trim())
    setInput('')
  }

  const onKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); enviar() }
  }

  return (
    <>
      {/* Mensajes */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '14px', display: 'flex', flexDirection: 'column', gap: 10 }}>
        {historial.length === 0 && (
          <div style={{ textAlign: 'center', color: '#a0a09a', fontSize: 13, marginTop: 40 }}>
            <div style={{ fontSize: 28, marginBottom: 8 }}>🗺️</div>
            <div>¿A dónde quieres ir hoy en Medellín?</div>
          </div>
        )}
        {historial.map((msg, i) => (
          <div key={i} style={{
            display: 'flex',
            justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start',
          }}>
            <div style={{
              maxWidth: 260,
              padding: '8px 12px',
              borderRadius: msg.role === 'user' ? '12px 12px 2px 12px' : '12px 12px 12px 2px',
              fontSize: 13,
              lineHeight: 1.5,
              background: msg.role === 'user' ? '#1D9E75' : '#f5f5f4',
              color: msg.role === 'user' ? 'white' : '#1a1a18',
              border: msg.role === 'user' ? 'none' : '0.5px solid #e5e5e5',
            }}>
              {msg.content}
            </div>
          </div>
        ))}
        {cargando && (
          <div style={{ display: 'flex' }}>
            <div style={{
              padding: '8px 14px', borderRadius: '12px 12px 12px 2px',
              background: '#f5f5f4', border: '0.5px solid #e5e5e5',
              fontSize: 13, color: '#737370',
            }}>
              <span style={{ animation: 'none' }}>···</span>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div style={{
        padding: '10px 14px',
        borderTop: '0.5px solid #e5e5e5',
        display: 'flex', gap: 8, alignItems: 'center',
      }}>
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={onKey}
          placeholder="Escribe tu mensaje..."
          disabled={cargando}
          style={{
            flex: 1, padding: '8px 12px',
            borderRadius: 8, border: '0.5px solid #d5d5d5',
            background: '#f9f9f8', fontSize: 13,
            outline: 'none', color: '#1a1a18',
          }}
        />
        <button
          onClick={enviar}
          disabled={cargando || !input.trim()}
          style={{
            width: 32, height: 32, borderRadius: '50%',
            background: cargando ? '#a0d5bf' : '#1D9E75',
            border: 'none', cursor: cargando ? 'default' : 'pointer',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2">
            <line x1="22" y1="2" x2="11" y2="13"/>
            <polygon points="22 2 15 22 11 13 2 9 22 2"/>
          </svg>
        </button>
      </div>
    </>
  )
}
