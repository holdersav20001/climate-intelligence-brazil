import { create } from 'zustand'

interface FiltersState {
  countries: string[]
  tags: string[]
  setCountries: (c: string[]) => void
  setTags: (t: string[]) => void
  reset: () => void
}

export const useFilters = create<FiltersState>((set) => ({
  countries: [],
  tags: [],
  setCountries: (countries) => set({ countries }),
  setTags: (tags) => set({ tags }),
  reset: () => set({ countries: [], tags: [] }),
}))
