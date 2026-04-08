import { useFilters } from '../store/filters'

const COUNTRY_OPTIONS = [
  { code: 'BR', label: 'Brazil' },
  { code: 'CO', label: 'Colombia' },
  { code: 'AR', label: 'Argentina' },
  { code: 'CL', label: 'Chile' },
  { code: 'DE', label: 'Germany' },
  { code: 'GB', label: 'UK' },
]

const TAG_OPTIONS = ['coal', 'gas', 'solar', 'wind', 'cop30', 'ndc', 'financing', 'transition', 'petrobras']

export default function GlobalFilterBar() {
  const { countries, tags, setCountries, setTags, reset } = useFilters()

  const toggleCountry = (code: string) => {
    setCountries(countries.includes(code) ? countries.filter(c => c !== code) : [...countries, code])
  }

  const toggleTag = (tag: string) => {
    setTags(tags.includes(tag) ? tags.filter(t => t !== tag) : [...tags, tag])
  }

  return (
    <div className="bg-white border-b border-gray-200 px-6 py-2 flex items-center gap-4 flex-wrap text-sm">
      <span className="text-gray-500 font-medium">Filter:</span>
      <div className="flex gap-1 flex-wrap">
        {COUNTRY_OPTIONS.map(({ code, label }) => (
          <button
            key={code}
            onClick={() => toggleCountry(code)}
            className={`px-2 py-0.5 rounded border text-xs font-medium transition-colors ${
              countries.includes(code)
                ? 'bg-green-600 text-white border-green-600'
                : 'bg-white text-gray-600 border-gray-300 hover:border-green-400'
            }`}
          >
            {label}
          </button>
        ))}
      </div>
      <div className="w-px h-4 bg-gray-300" />
      <div className="flex gap-1 flex-wrap">
        {TAG_OPTIONS.map(tag => (
          <button
            key={tag}
            onClick={() => toggleTag(tag)}
            className={`px-2 py-0.5 rounded border text-xs font-medium transition-colors ${
              tags.includes(tag)
                ? 'bg-blue-600 text-white border-blue-600'
                : 'bg-white text-gray-600 border-gray-300 hover:border-blue-400'
            }`}
          >
            {tag}
          </button>
        ))}
      </div>
      {(countries.length > 0 || tags.length > 0) && (
        <button onClick={reset} className="ml-auto text-gray-400 hover:text-gray-700 text-xs">
          Clear all
        </button>
      )}
    </div>
  )
}
