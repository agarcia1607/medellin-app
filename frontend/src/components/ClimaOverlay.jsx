import { useEffect, useState, useRef } from 'react'

const OPEN_METEO = 'https://api.open-meteo.com/v1/forecast'

async function fetchClima() {
  const url = `${OPEN_METEO}?latitude=6.2442&longitude=-75.5812&current=temperature_2m,precipitation,cloud_cover,relative_humidity_2m,weather_code&timezone=America/Bogota&forecast_days=1`
  const r = await fetch(url)
  const d = await r.json()
  return d.current
}

function generarNubes(cobertura) {
  const cantidad = Math.round((cobertura / 100) * 8)
  const seed = [0.15, 0.45, 0.72, 0.28, 0.60, 0.88, 0.35, 0.55]
  return Array.from({ length: cantidad }, (_, i) => ({
    id: i,
    x: seed[i % seed.length] * 100,
    y: (i % 3) * 15 + 5,
    w: 18 + (i % 3) * 8,
    dur: 18 + (i % 4) * 6,
    delay: -(i * 3.5),
    opacity: 0.55 + (cobertura / 100) * 0.35,
  }))
}

export default function ClimaOverlay({ visible, onClimaListo }) {
  const [clima, setClima] = useState(null)
  const [nubes, setNubes] = useState([])
  const intervalRef = useRef(null)

  useEffect(() => {
    const cargar = async () => {
      try {
        const cur = await fetchClima()
        setClima(cur)
        setNubes(generarNubes(cur.cloud_cover))
        onClimaListo?.(cur)
      } catch (e) { console.error('Clima:', e) }
    }
    cargar()
    intervalRef.current = setInterval(cargar, 5 * 60 * 1000)
    return () => clearInterval(intervalRef.current)
  }, [])

  if (!visible || !clima) return null

  const { temperature_2m, precipitation, cloud_cover, relative_humidity_2m } = clima

  const impacto = precipitation > 5 ? 'lluvia_fuerte'
    : precipitation > 0 ? 'lluvia_ligera'
    : cloud_cover > 60  ? 'nublado' : 'soleado'

  const badge = {
    soleado:       { label: '☀ Despejado',      bg: '#FFF8E1', color: '#854F0B', border: '#EF9F27' },
    nublado:       { label: '☁ Nublado',        bg: '#F5F5F5', color: '#5F5E5A', border: '#B4B2A9' },
    lluvia_ligera: { label: '🌦 Lluvia ligera', bg: '#E3F2FD', color: '#0C447C', border: '#85B7EB' },
    lluvia_fuerte: { label: '⛈ Lluvia fuerte', bg: '#E8EAF6', color: '#26215C', border: '#AFA9EC' },
  }[impacto]

  return (
    <div style={{ position: 'absolute', inset: 0, pointerEvents: 'none', zIndex: 500, overflow: 'hidden' }}>
      {/* Nubes SVG animadas */}
      <svg width="100%" height="100%" viewBox="0 0 100 50"
        preserveAspectRatio="xMidYMid slice"
        style={{ position: 'absolute', inset: 0 }}>
        <defs>
          <filter id="blur-nube"><feGaussianBlur stdDeviation="1.2"/></filter>
        </defs>
        {nubes.map(({ id, x, y, w, dur, delay, opacity }) => (
          <g key={id} opacity={opacity} filter="url(#blur-nube)">
            <animateTransform attributeName="transform" type="translate"
              from={`${x - 120} ${y}`} to={`${x + 20} ${y}`}
              dur={`${dur}s`} begin={`${delay}s`} repeatCount="indefinite"/>
            <ellipse cx="0" cy="0" rx={w * 0.5}  ry={w * 0.22} fill="white"/>
            <ellipse cx={w * -0.15} cy={w * -0.12} rx={w * 0.28} ry={w * 0.2}  fill="white"/>
            <ellipse cx={w * 0.18}  cy={w * -0.1}  rx={w * 0.22} ry={w * 0.16} fill="white"/>
          </g>
        ))}
        {precipitation > 0 && Array.from({ length: Math.min(20, Math.round(precipitation * 4)) }).map((_, i) => (
          <line key={i}
            x1={(i * 17 + 5) % 95} y1={(i * 23) % 40}
            x2={(i * 17 + 5) % 95 - 0.5} y2={(i * 23) % 40 + 3}
            stroke="#85B7EB" strokeWidth="0.4" strokeLinecap="round" opacity="0.6">
            <animateTransform attributeName="transform" type="translate"
              from="0 -10" to="0 55"
              dur={`${1.2 + (i % 4) * 0.3}s`} begin={`${-(i * 0.4)}s`}
              repeatCount="indefinite"/>
          </line>
        ))}
      </svg>

      {/* Badge esquina superior derecha */}
      <div style={{
        position: 'absolute', top: 12, right: 12,
        background: badge.bg, border: `0.5px solid ${badge.border}`,
        color: badge.color, borderRadius: 8, padding: '8px 12px',
        fontSize: 12, fontWeight: 500, pointerEvents: 'auto',
        boxShadow: '0 2px 8px rgba(0,0,0,0.08)', minWidth: 140,
        display: 'flex', flexDirection: 'column', gap: 4,
      }}>
        <div style={{ fontSize: 13, fontWeight: 600 }}>{badge.label}</div>
        <div style={{ display: 'flex', gap: 10, fontSize: 11, opacity: 0.85 }}>
          <span>🌡 {temperature_2m}°C</span>
          <span>💧 {relative_humidity_2m}%</span>
        </div>
        {precipitation > 0 && <div style={{ fontSize: 11, opacity: 0.85 }}>🌧 {precipitation} mm</div>}
        <div style={{ fontSize: 10, opacity: 0.6, borderTop: `0.5px solid ${badge.border}`, paddingTop: 4 }}>
          ☁ Cobertura {cloud_cover}% · Open-Meteo
        </div>
      </div>
    </div>
  )
}
