import { useState, useMemo } from 'react'
import { ComposableMap, Geographies, Geography, Marker, Sphere, Graticule } from 'react-simple-maps'
import { useFindings } from '../api/hooks'
import Badge from '../components/Badge'
import Spinner from '../components/Spinner'
import type { Finding } from '../types'

const GEO_URL = 'https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json'

const COUNTRY_COORDS: Record<string, [number, number]> = {
  BR: [-51.9, -14.2], CO: [-74.3, 4.6], AR: [-63.6, -38.4], CL: [-71.5, -35.7],
  DE: [10.5, 51.2], GB: [-3.4, 55.4], FR: [2.2, 46.2], US: [-99.1, 38.5],
  IN: [78.9, 20.6], ID: [113.9, -0.8], AU: [133.8, -25.3], ZA: [25.1, -28.5],
  MX: [-102.5, 23.6], PE: [-75.0, -9.2], BO: [-64.9, -16.3], EC: [-78.1, -1.8],
}

const PRIORITY_COLOR: Record<Finding['priority'], string> = {
  CRITICAL: '#dc2626',
  HIGH: '#ea580c',
  COALITION: '#9333ea',
  EVIDENCE: '#2563eb',
  MEDIUM: '#ca8a04',
  LOW: '#6b7280',
}

const PRIORITY_ORDER: Finding['priority'][] = ['CRITICAL', 'HIGH', 'COALITION', 'EVIDENCE', 'MEDIUM', 'LOW']

function getHighestPriority(priorities: Finding['priority'][]): Finding['priority'] {
  for (const p of PRIORITY_ORDER) {
    if (priorities.includes(p)) return p
  }
  return 'LOW'
}

export default function WorldMap() {
  const [daysBack, setDaysBack] = useState(7)
  const [selected, setSelected] = useState<string | null>(null)
  const { data, isLoading } = useFindings({ page_size: 100 })

  const cutoff = useMemo(() => {
    const d = new Date()
    d.setDate(d.getDate() - daysBack)
    return d.toISOString().split('T')[0]
  }, [daysBack])

  const filtered = useMemo(
    () => data?.items.filter(f => f.run_date >= cutoff) ?? [],
    [data, cutoff]
  )

  const countryData = useMemo(() => {
    const map: Record<string, { count: number; priorities: Finding['priority'][]; findings: Finding[] }> = {}
    for (const f of filtered) {
      for (const cc of f.country_codes) {
        if (!map[cc]) map[cc] = { count: 0, priorities: [], findings: [] }
        map[cc].count++
        map[cc].priorities.push(f.priority)
        map[cc].findings.push(f)
      }
    }
    return map
  }, [filtered])

  const markers = useMemo(() =>
    Object.entries(countryData)
      .filter(([cc]) => COUNTRY_COORDS[cc])
      .map(([cc, d]) => ({
        cc,
        coords: COUNTRY_COORDS[cc],
        count: d.count,
        priority: getHighestPriority(d.priorities),
        findings: d.findings,
      })),
    [countryData]
  )

  if (isLoading) return <Spinner />

  const selectedData = selected ? countryData[selected] : null

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-900">Intelligence Map</h1>
        <div className="flex items-center gap-3 text-sm text-gray-600">
          <span>Last {daysBack} days</span>
          <input
            type="range" min={1} max={30} value={daysBack}
            onChange={e => setDaysBack(Number(e.target.value))}
            className="w-32 accent-green-600"
          />
        </div>
      </div>

      <div className="flex gap-4">
        <div className="flex-1 bg-white rounded-lg border border-gray-200 overflow-hidden">
          <ComposableMap projectionConfig={{ scale: 147 }} style={{ width: '100%', height: 'auto' }}>
            <Sphere id="sphere" fill="#f0f9ff" stroke="#e2e8f0" strokeWidth={0.5} />
            <Graticule stroke="#e2e8f0" strokeWidth={0.3} />
            <Geographies geography={GEO_URL}>
              {({ geographies }) =>
                geographies.map(geo => (
                  <Geography
                    key={geo.rsmKey}
                    geography={geo}
                    fill="#e5e7eb"
                    stroke="#d1d5db"
                    strokeWidth={0.3}
                    style={{ default: { outline: 'none' }, hover: { outline: 'none' }, pressed: { outline: 'none' } }}
                  />
                ))
              }
            </Geographies>
            {markers.map(({ cc, coords, count, priority }) => (
              <Marker key={cc} coordinates={coords}>
                <circle
                  r={Math.min(4 + count * 3, 18)}
                  fill={PRIORITY_COLOR[priority]}
                  fillOpacity={0.8}
                  stroke="white"
                  strokeWidth={1.5}
                  style={{ cursor: 'pointer' }}
                  onClick={() => setSelected(selected === cc ? null : cc)}
                  className={priority === 'CRITICAL' ? 'animate-pulse' : ''}
                />
                <text
                  textAnchor="middle"
                  y={-Math.min(4 + count * 3, 18) - 3}
                  style={{ fontSize: 9, fill: '#374151', pointerEvents: 'none' }}
                >
                  {cc}
                </text>
              </Marker>
            ))}
          </ComposableMap>
        </div>

        {selected && selectedData && (
          <div className="w-80 bg-white rounded-lg border border-gray-200 p-4 overflow-y-auto max-h-96">
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-semibold text-gray-900">{selected} — {selectedData.count} findings</h3>
              <button onClick={() => setSelected(null)} className="text-gray-400 hover:text-gray-700 text-lg">×</button>
            </div>
            <ul className="space-y-2">
              {selectedData.findings.slice(0, 5).map(f => (
                <li key={f.id} className="border-l-2 pl-2" style={{ borderColor: PRIORITY_COLOR[f.priority] }}>
                  <div className="flex items-center gap-1 mb-0.5">
                    <Badge priority={f.priority} />
                  </div>
                  <div className="text-xs text-gray-700 line-clamp-2">{f.title}</div>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      <div className="flex gap-4 text-xs text-gray-500 flex-wrap">
        {PRIORITY_ORDER.filter(p => markers.some(m => m.priority === p)).map(p => (
          <span key={p} className="flex items-center gap-1">
            <span className="w-3 h-3 rounded-full inline-block" style={{ background: PRIORITY_COLOR[p] }} />
            {p}
          </span>
        ))}
        <span className="text-gray-400">· Circle size = finding count · Click circle for details</span>
      </div>
    </div>
  )
}
