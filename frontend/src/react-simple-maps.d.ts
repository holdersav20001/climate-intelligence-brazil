declare module 'react-simple-maps' {
  import * as React from 'react'

  export interface ComposableMapProps {
    projection?: string
    projectionConfig?: Record<string, unknown>
    width?: number
    height?: number
    style?: React.CSSProperties
    [key: string]: unknown
  }
  export const ComposableMap: React.FC<ComposableMapProps>

  export interface GeographiesProps {
    geography: string | object
    children: (args: { geographies: Geography[] }) => React.ReactNode
    [key: string]: unknown
  }
  export const Geographies: React.FC<GeographiesProps>

  export interface Geography {
    rsmKey: string
    [key: string]: unknown
  }

  export interface GeographyProps {
    geography: Geography
    fill?: string
    stroke?: string
    strokeWidth?: number
    style?: {
      default?: React.CSSProperties
      hover?: React.CSSProperties
      pressed?: React.CSSProperties
    }
    [key: string]: unknown
  }
  export const Geography: React.FC<GeographyProps>

  export interface MarkerProps {
    coordinates: [number, number]
    children?: React.ReactNode
    [key: string]: unknown
  }
  export const Marker: React.FC<MarkerProps>

  export interface SphereProps {
    id: string
    fill?: string
    stroke?: string
    strokeWidth?: number
    [key: string]: unknown
  }
  export const Sphere: React.FC<SphereProps>

  export interface GraticuleProps {
    stroke?: string
    strokeWidth?: number
    [key: string]: unknown
  }
  export const Graticule: React.FC<GraticuleProps>
}
