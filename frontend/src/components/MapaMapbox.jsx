import { useEffect, useRef, useState } from 'react'
import ClimaOverlay from './ClimaOverlay.jsx'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

const TIPO_COLOR = {
  naturaleza:      '#1D9E75',
  cultura:         '#534AB7',
  gastronomia:     '#D85A30',
  entretenimiento: '#BA7517',
}

function crearIcono(color, score, seleccionado) {
  const size = seleccionado ? 36 : 28
  const html = `
    <div style="
      width:${size}px;height:${size}px;
      background:${color};
      border-radius:50% 50% 50% 0;
      transform:rotate(-45deg);
      border:2px solid white;
      display:flex;align-items:center;justify-content:center;
      box-shadow:${seleccionado ? `0 0 0 4px ${color}44` : '0 2px 6px rgba(0,0,0,0.2)'};
    ">
      <span style="transform:rotate(45deg);font-size:9px;font-weight:600;color:white;">
        ${score?.toFixed(1) || ''}
      </span>
    </div>`
  return L.divIcon({ html, className: '', iconSize: [size, size], iconAnchor: [size/2, size] })
}

export default function MapaMapbox({ recomendaciones, lugarSeleccionado, onSeleccionar, onClimaListo }) {
  const [climaVisible, setClimaVisible] = useState(true)

  // Esconder nubes cuando llegan recomendaciones
  useEffect(() => {
    if (recomendaciones.length > 0) {
      setTimeout(() => setClimaVisible(false), 800)
    }
  }, [recomendaciones])
  const mapRef = useRef(null)
  const mapInstance = useRef(null)
  const markersRef = useRef([])

  // Inicializar mapa
  useEffect(() => {
    if (mapInstance.current) return
    mapInstance.current = L.map(mapRef.current, {
      center: [6.2442, -75.5812],
      zoom: 12,
      zoomControl: true,
    })
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '© <a href="https://openstreetmap.org">OpenStreetMap</a>',
      maxZoom: 19,
    }).addTo(mapInstance.current)

    return () => { mapInstance.current?.remove(); mapInstance.current = null }
  }, [])

  // Actualizar markers
  useEffect(() => {
    if (!mapInstance.current) return

    markersRef.current.forEach(m => m.remove())
    markersRef.current = []

    recomendaciones.forEach(lugar => {
      const { lat, lng } = lugar.coordenadas || {}
      if (!lat || !lng) return

      const color = TIPO_COLOR[lugar.tipo] || '#888'
      const seleccionado = lugarSeleccionado?.lugar === lugar.lugar
      const icono = crearIcono(color, lugar.score, seleccionado)

      const marker = L.marker([lat, lng], { icon: icono })
        .addTo(mapInstance.current)
        .on('click', () => onSeleccionar(lugar))

      markersRef.current.push(marker)
    })

    if (recomendaciones[0]?.coordenadas) {
      const { lat, lng } = recomendaciones[0].coordenadas
      mapInstance.current.flyTo([lat, lng], 13, { duration: 1.2 })
    }
  }, [recomendaciones, lugarSeleccionado])

  return (
    <div style={{ position: 'relative', height: '100%' }}>
      <div ref={mapRef} style={{ width: '100%', height: '100%' }} />
      <ClimaOverlay visible={climaVisible} onClimaListo={onClimaListo} />

      {/* Tarjeta flotante */}
      {lugarSeleccionado && (
        <div style={{
          position: 'absolute', bottom: 16, left: 16, zIndex: 1000,
          width: 270, background: 'white', borderRadius: 12,
          border: '0.5px solid #e5e5e5', padding: '12px 14px',
          boxShadow: '0 2px 12px rgba(0,0,0,0.08)',
        }}>
          <div style={{
            fontSize: 11, padding: '2px 6px', borderRadius: 4,
            display: 'inline-block', background: '#E1F5EE',
            color: '#0F6E56', marginBottom: 6,
          }}>
            {lugarSeleccionado.tipo || 'lugar'}
          </div>
          <div style={{ fontSize: 14, fontWeight: 500, marginBottom: 4 }}>
            {lugarSeleccionado.lugar}
          </div>
          <div style={{ height: 3, background: '#f0f0ee', borderRadius: 2, marginBottom: 6 }}>
            <div style={{
              height: '100%', borderRadius: 2, background: '#1D9E75',
              width: `${((lugarSeleccionado.score || 8) / 10) * 100}%`
            }}/>
          </div>
          <div style={{ fontSize: 12, color: '#737370', marginBottom: 8 }}>
            Score {lugarSeleccionado.score?.toFixed(1)} · {lugarSeleccionado.tipo}
          </div>
          {lugarSeleccionado.motivo && (
            <div style={{
              fontSize: 12, color: '#5F5E5A', lineHeight: 1.5,
              borderTop: '0.5px solid #e5e5e5', paddingTop: 8,
            }}>
              {lugarSeleccionado.motivo}
            </div>
          )}
        </div>
      )}

      {/* Leyenda */}
      <div style={{
        position: 'absolute', top: 12, left: 12, zIndex: 1000,
        background: 'white', borderRadius: 8, border: '0.5px solid #e5e5e5',
        padding: '8px 10px', display: 'flex', flexDirection: 'column', gap: 5,
      }}>
        {Object.entries(TIPO_COLOR).map(([tipo, color]) => (
          <div key={tipo} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, color: '#5F5E5A' }}>
            <div style={{ width: 10, height: 10, borderRadius: '50%', background: color }}/>
            {tipo.charAt(0).toUpperCase() + tipo.slice(1)}
          </div>
        ))}
      </div>
    </div>
  )
}
