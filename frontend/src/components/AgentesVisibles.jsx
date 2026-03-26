const AGENTES = [
  { key: 'perfilador', label: 'Perfilador' },
  { key: 'clima',      label: 'Clima' },
  { key: 'orquestador', label: 'Orquestador' },
]

const COLORES = {
  idle:   { bg: 'transparent', color: '#a0a09a', border: '#e5e5e5' },
  active: { bg: '#E1F5EE',     color: '#0F6E56', border: '#5DCAA5' },
  done:   { bg: '#f5f5f4',     color: '#5F5E5A', border: '#e5e5e5' },
  error:  { bg: '#FCEBEB',     color: '#A32D2D', border: '#F09595' },
}

export default function AgentesVisibles({ agentes }) {
  return (
    <div style={{
      padding: '8px 14px',
      borderTop: '0.5px solid #e5e5e5',
      display: 'flex', gap: 6, alignItems: 'center',
    }}>
      <span style={{ fontSize: 11, color: '#a0a09a', marginRight: 2 }}>Agentes:</span>
      {AGENTES.map(({ key, label }) => {
        const estado = agentes[key] || 'idle'
        const { bg, color, border } = COLORES[estado]
        return (
          <div key={key} style={{
            fontSize: 11, padding: '3px 8px', borderRadius: 99,
            background: bg, color, border: `0.5px solid ${border}`,
            display: 'flex', alignItems: 'center', gap: 4,
            transition: 'all 0.2s',
          }}>
            {estado === 'active' && (
              <span style={{
                width: 6, height: 6, borderRadius: '50%',
                background: '#1D9E75', display: 'inline-block',
                animation: 'pulse 1s infinite',
              }}/>
            )}
            {estado === 'done' && '✓ '}
            {estado === 'error' && '✗ '}
            {label}
          </div>
        )
      })}
      <style>{`@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.3} }`}</style>
    </div>
  )
}
