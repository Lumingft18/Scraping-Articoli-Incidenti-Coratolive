import { useEffect, useMemo, useState } from 'react'
import { format, parseISO } from 'date-fns'
import { it } from 'date-fns/locale'
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ComposedChart,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import './App.css'

type Incident = {
  id: number
  date: string
  datetime: string
  year: number
  month: number
  month_name: string
  weekday: string
  title: string
  link: string
  excerpt: string
  content: string
  severity: 'informativo' | 'moderato' | 'grave' | 'fatale'
  keywords: string[]
  roads: string[]
  cities: string[]
}

const severityLabels: Record<Incident['severity'], string> = {
  informativo: 'Informativo',
  moderato: 'Feriti',
  grave: 'Grave',
  fatale: 'Mortale',
}

const severityColors: Record<Incident['severity'], string> = {
  informativo: '#94a3b8',
  moderato: '#38bdf8',
  grave: '#f97316',
  fatale: '#ef4444',
}

const weekdayOrder = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
const weekdayLabels: Record<string, string> = {
  Monday: 'Lunedì',
  Tuesday: 'Martedì',
  Wednesday: 'Mercoledì',
  Thursday: 'Giovedì',
  Friday: 'Venerdì',
  Saturday: 'Sabato',
  Sunday: 'Domenica',
}

// Estrazione veicoli dal testo
const extractVehicles = (text: string): string[] => {
  const vehicles: string[] = []
  const patterns = [
    /\b(?:auto|automobile|vettura|macchina)\b/gi,
    /\b(?:moto|motociclo|motocicletta|scooter)\b/gi,
    /\b(?:bici|bicicletta|ciclista)\b/gi,
    /\b(?:tir|camion|mezzo pesante|autocarro)\b/gi,
    /\b(?:furgone|van)\b/gi,
    /\b(?:bus|autobus|pullman)\b/gi,
  ]
  const labels = ['Auto', 'Moto', 'Bici', 'Tir/Camion', 'Furgone', 'Bus']

  patterns.forEach((pattern, idx) => {
    if (pattern.test(text)) {
      vehicles.push(labels[idx])
    }
  })

  return [...new Set(vehicles)]
}

// Estrazione morti/feriti dal testo (versione bilanciata)
const extractCasualties = (text: string): { morti: number; feriti: number } => {
  let morti = 0
  let feriti = 0

  // Pattern negativi: escludi contesti non legati all'incidente
  const negativePatterns = [
    /mort[io]\s+(?:in|durante|per)\s+(?:guerra|battaglia|strage|attentato|omicidio)/gi,
    /ferit[io]\s+(?:in|durante|per)\s+(?:guerra|battaglia|strage|attentato)/gi,
    /vittim[ae]\s+(?:di|della|del)\s+(?:guerra|violenza|omicidio|strage)/gi,
    /mort[io]\s+(?:per|a causa di)\s+(?:malattia|cancro|infarto|ictus)/gi,
  ]

  // Se contiene pattern negativi chiari, non estrarre dati
  if (negativePatterns.some(pattern => pattern.test(text))) {
    return { morti: 0, feriti: 0 }
  }

  // Verifica se il testo parla di incidenti (per validare i pattern generici)
  const isAccidentContext = /\b(?:incidente|sinistro|scontro|schianto|tamponamento|ribaltamento|collisione)\b/gi.test(text)

  // Pattern per morti - mix di specifici e generici
  const mortiPatterns = [
    // Pattern specifici con contesto incidente
    /\b(\d+)\s+(?:person[ae]|persone)\s+(?:mort[ae]|decedut[ae]|hanno perso la vita)\b/gi,
    /\b(\d+)\s+(?:mort[io]|decedut[io]|vittim[ae])\s+(?:in|nell'|nello|nel)\s+(?:incidente|sinistro|scontro|schianto)\b/gi,
    /\b(?:mort[io]|decedut[io]|ha perso la vita|hanno perso la vita)\s+(?:in|nell'|nello|nel)\s+(?:incidente|sinistro|scontro|schianto)\b/gi,
    /\b(?:un|una|uno)\s+(?:mort[io]|decedut[io]|vittima)\s+(?:in|nell'|nello|nel)\s+(?:incidente|sinistro|scontro|schianto)\b/gi,
    // Pattern generici (solo se c'è contesto incidente)
    ...(isAccidentContext ? [
      /\b(\d+)\s+(?:mort[io]|decedut[io]|vittim[ae])\b/gi,
      /\b(?:un|una|uno)\s+(?:mort[io]|decedut[io]|vittima)\b/gi,
      /\b(?:mort[io]|decedut[io])\s+(?:in|nell'|nello|nel)\s+(?:ospedale|pronto\s+soccorso)\b/gi,
    ] : []),
  ]

  const foundMorti = new Set<number>()
  mortiPatterns.forEach((pattern) => {
    const matches = text.matchAll(pattern)
    for (const match of matches) {
      const numMatch = match[1] || (match[0].match(/\d+/) ? match[0].match(/\d+/)?.[0] : null)
      if (numMatch) {
        const num = parseInt(numMatch, 10)
        if (num > 0 && num <= 50) {
          foundMorti.add(num)
        }
      } else if (match[0].toLowerCase().includes('mort') || match[0].toLowerCase().includes('decedut')) {
        foundMorti.add(1)
      }
    }
  })
  
  morti = Array.from(foundMorti).reduce((sum, val) => sum + val, 0)

  // Pattern per feriti - mix di specifici e generici
  const feritiPatterns = [
    // Pattern specifici con contesto incidente
    /\b(\d+)\s+(?:person[ae]|persone)\s+(?:ferit[ae]|les[ae]|rimast[ae] ferit[ae])\b/gi,
    /\b(\d+)\s+(?:ferit[io]|les[io])\s+(?:in|nell'|nello|nel)\s+(?:incidente|sinistro|scontro|schianto)\b/gi,
    /\b(?:ferit[io]|les[io]|rimast[io] ferit[io])\s+(?:in|nell'|nello|nel)\s+(?:incidente|sinistro|scontro|schianto)\b/gi,
    /\b(?:un|una|uno)\s+(?:ferit[io]|les[io])\s+(?:in|nell'|nello|nel)\s+(?:incidente|sinistro|scontro|schianto)\b/gi,
    // Pattern con trasporto in ospedale
    /\b(?:trasportat[io]|soccors[io]|portat[io])\s+(?:in|al|all')\s+(?:ospedale|pronto\s+soccorso|ps)\b/gi,
    // Pattern generici (solo se c'è contesto incidente)
    ...(isAccidentContext ? [
      /\b(\d+)\s+(?:ferit[io]|les[io])\b/gi,
      /\b(?:un|una|uno|alcun[ie]|divers[ie])\s+(?:ferit[io]|les[io])\b/gi,
      /\b(?:ferit[io]|les[io])\s+(?:in|nell'|nello|nel)\s+(?:ospedale|pronto\s+soccorso|ps)\b/gi,
      /\b(?:rimast[io]|rimast[ae])\s+(?:ferit[io]|ferit[ae]|les[io]|les[ae])\b/gi,
    ] : []),
  ]

  const foundFeriti = new Set<number>()
  feritiPatterns.forEach((pattern) => {
    const matches = text.matchAll(pattern)
    for (const match of matches) {
      const numMatch = match[1] || (match[0].match(/\d+/) ? match[0].match(/\d+/)?.[0] : null)
      if (numMatch) {
        const num = parseInt(numMatch, 10)
        if (num > 0 && num <= 100) {
          foundFeriti.add(num)
        }
      } else if (match[0].toLowerCase().includes('ferit') || match[0].toLowerCase().includes('les')) {
        foundFeriti.add(1)
      }
    }
  })
  
  feriti = Array.from(foundFeriti).reduce((sum, val) => sum + val, 0)

  // Limiti conservativi
  return { 
    morti: Math.min(morti, 10), 
    feriti: Math.min(feriti, 20) 
  }
}

function App() {
  const [incidents, setIncidents] = useState<Incident[]>([])
  const [removedIncidents, setRemovedIncidents] = useState<Incident[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [search, setSearch] = useState('')
  const [severityFilter, setSeverityFilter] =
    useState<Incident['severity'] | 'all'>('all')
  const [yearFilter, setYearFilter] = useState<number | 'all'>('all')
  const [dateFrom, setDateFrom] = useState<string | null>(null)
  const [dateTo, setDateTo] = useState<string | null>(null)
  const [showRemoved, setShowRemoved] = useState(false)
  const [currentPage, setCurrentPage] = useState(1)
  const itemsPerPage = 50

  useEffect(() => {
    const loadData = async () => {
      try {
        setLoading(true)
        const incidentsRes = await fetch('/data/incidents.json')
        const removedRes = await fetch('/data/incidents_removed.json')

        if (!incidentsRes.ok) {
          throw new Error('Errore durante il caricamento dei dati')
        }

        const incidentsData = (await incidentsRes.json()) as Incident[]
        setIncidents(incidentsData)

        // Carica anche i record rimossi se disponibili
        if (removedRes.ok) {
          const removedData = (await removedRes.json()) as Incident[]
          setRemovedIncidents(removedData)
        }
      } catch (err) {
        setError(
          err instanceof Error ? err.message : 'Errore sconosciuto durante il fetch',
        )
      } finally {
        setLoading(false)
      }
    }

    loadData()
  }, [])

  const years = useMemo(() => {
    const values = Array.from(new Set(incidents.map((incident) => incident.year)))
    return values.sort((a, b) => b - a)
  }, [incidents]) as number[]

  const datasetRange = useMemo(() => {
    if (!incidents.length) {
      return null
    }
    let minDate = incidents[0].date
    let maxDate = incidents[0].date
    incidents.forEach((incident) => {
      if (incident.date < minDate) minDate = incident.date
      if (incident.date > maxDate) maxDate = incident.date
    })
    return { min: minDate, max: maxDate }
  }, [incidents])

  useEffect(() => {
    if (!datasetRange) return
    setDateFrom((current) => current ?? datasetRange.min)
    setDateTo((current) => current ?? datasetRange.max)
  }, [datasetRange])

  const handleResetRange = () => {
    if (!datasetRange) return
    setDateFrom(datasetRange.min)
    setDateTo(datasetRange.max)
  }

  const filteredIncidents = useMemo(() => {
    const allIncidents = showRemoved ? [...incidents, ...removedIncidents] : incidents
    return allIncidents.filter((incident) => {
      const matchesSearch =
        search.length === 0 ||
        incident.title.toLowerCase().includes(search.toLowerCase()) ||
        incident.excerpt.toLowerCase().includes(search.toLowerCase()) ||
        incident.cities?.some((city) =>
          city.toLowerCase().includes(search.toLowerCase()),
        ) ||
        incident.roads?.some((road) =>
          road.toLowerCase().includes(search.toLowerCase()),
        )

      const matchesSeverity =
        severityFilter === 'all' || incident.severity === severityFilter

      const matchesYear =
        yearFilter === 'all' ||
        new Date(incident.date).getFullYear() === Number(yearFilter)

      const matchesRange =
        (!dateFrom || incident.date >= dateFrom) &&
        (!dateTo || incident.date <= dateTo)

      return matchesSearch && matchesSeverity && matchesYear && matchesRange
    })
  }, [incidents, removedIncidents, showRemoved, search, severityFilter, yearFilter, dateFrom, dateTo])

  // Paginazione
  const totalPages = Math.ceil(filteredIncidents.length / itemsPerPage)
  const paginatedIncidents = useMemo(() => {
    const start = (currentPage - 1) * itemsPerPage
    return filteredIncidents.slice(start, start + itemsPerPage)
  }, [filteredIncidents, currentPage, itemsPerPage])

  useEffect(() => {
    // Reset alla prima pagina quando cambiano i filtri
    setCurrentPage(1)
  }, [search, severityFilter, yearFilter, dateFrom, dateTo, showRemoved])

  const analytics = useMemo(() => {
    // Usa solo incidents per gli analytics, non i removed
    const incidentsForAnalytics = incidents
    const severityCounts: Record<Incident['severity'], number> = {
      informativo: 0,
      moderato: 0,
      grave: 0,
      fatale: 0,
    }
    const perMonth = new Map<string, number>()
    const perYear = new Map<number, number>()
    const perWeekday = new Map<string, number>()
    const roadCounter = new Map<string, { total: number; bySeverity: Record<Incident['severity'], number> }>()
    const cityCounter = new Map<string, { total: number; bySeverity: Record<Incident['severity'], number> }>()
    const vehicleCounter = new Map<string, number>()
    let totalMorti = 0
    let totalFeriti = 0
    const casualtiesByYear = new Map<number, { morti: number; feriti: number }>()

    incidentsForAnalytics.forEach((incident) => {
      severityCounts[incident.severity] += 1
      const monthKey = incident.date.slice(0, 7)
      perMonth.set(monthKey, (perMonth.get(monthKey) ?? 0) + 1)
      perYear.set(incident.year, (perYear.get(incident.year) ?? 0) + 1)
      perWeekday.set(incident.weekday, (perWeekday.get(incident.weekday) ?? 0) + 1)

      const fullText = `${incident.title} ${incident.excerpt} ${incident.content}`
      const vehicles = extractVehicles(fullText)
      vehicles.forEach((v) => {
        vehicleCounter.set(v, (vehicleCounter.get(v) ?? 0) + 1)
      })

      const casualties = extractCasualties(fullText)
      totalMorti += casualties.morti
      totalFeriti += casualties.feriti
      const yearCasualties = casualtiesByYear.get(incident.year) || { morti: 0, feriti: 0 }
      casualtiesByYear.set(incident.year, {
        morti: yearCasualties.morti + casualties.morti,
        feriti: yearCasualties.feriti + casualties.feriti,
      })

      incident.roads?.forEach((road) => {
        const key = road.trim()
        if (!key) return
        const existing = roadCounter.get(key) || { total: 0, bySeverity: { informativo: 0, moderato: 0, grave: 0, fatale: 0 } }
        existing.total += 1
        existing.bySeverity[incident.severity] += 1
        roadCounter.set(key, existing)
      })

      incident.cities?.forEach((city) => {
        const key = city.trim()
        if (!key) return
        const existing = cityCounter.get(key) || { total: 0, bySeverity: { informativo: 0, moderato: 0, grave: 0, fatale: 0 } }
        existing.total += 1
        existing.bySeverity[incident.severity] += 1
        cityCounter.set(key, existing)
      })
    })

    const monthlyTrend = Array.from(perMonth.entries())
      .sort((a, b) => a[0].localeCompare(b[0]))
      .slice(-36)
      .map(([month, value]) => ({
        month: format(parseISO(`${month}-01`), "MMM ''yy", { locale: it }),
        value,
      }))

    const yearlyTrend = Array.from(perYear.entries())
      .sort((a, b) => a[0] - b[0])
      .map(([year, value]) => ({ year: year.toString(), value }))

    const weekdayData = weekdayOrder
      .map((day) => ({
        day: weekdayLabels[day] || day,
        value: perWeekday.get(day) || 0,
      }))
      .filter((d) => d.value > 0)

    const rankRoads = (limit = 15) =>
      Array.from(roadCounter.entries())
        .sort((a, b) => b[1].total - a[1].total)
        .slice(0, limit)
        .map(([name, data]) => ({
          name,
          value: data.total,
          ...data.bySeverity,
        }))

    const rankCities = (limit = 15) =>
      Array.from(cityCounter.entries())
        .sort((a, b) => b[1].total - a[1].total)
        .slice(0, limit)
        .map(([name, data]) => ({
          name,
          value: data.total,
          ...data.bySeverity,
        }))

    const vehiclesData = Array.from(vehicleCounter.entries())
      .sort((a, b) => b[1] - a[1])
      .map(([name, value]) => ({ name, value }))

    const casualtiesByYearData = Array.from(casualtiesByYear.entries())
      .sort((a, b) => a[0] - b[0])
      .map(([year, data]) => ({
        year: year.toString(),
        morti: data.morti,
        feriti: data.feriti,
      }))

    return {
      severity: severityCounts,
      monthlyTrend,
      yearlyTrend,
      weekdayData,
      topRoads: rankRoads(20),
      topCities: rankCities(20),
      vehicles: vehiclesData,
      casualties: { totalMorti, totalFeriti },
      casualtiesByYear: casualtiesByYearData,
    }
  }, [incidents])

  const severityData = useMemo(() => {
    return (Object.entries(analytics.severity) as Array<[Incident['severity'], number]>)
      .filter(([, value]) => value > 0)
      .map(([key, value]) => ({
        name: severityLabels[key],
        value,
        fill: severityColors[key],
      }))
  }, [analytics])

  const { monthlyTrend, yearlyTrend, weekdayData, topRoads, topCities, vehicles, casualties, casualtiesByYear } = analytics

  const periodLabel = useMemo(() => {
    const start = dateFrom ?? datasetRange?.min
    const end = dateTo ?? datasetRange?.max
    if (!start || !end) return 'n/d'
    const formattedStart = format(parseISO(start), 'dd MMM yyyy', { locale: it })
    const formattedEnd = format(parseISO(end), 'dd MMM yyyy', { locale: it })
    return `${formattedStart} → ${formattedEnd}`
  }, [dateFrom, dateTo, datasetRange])

  if (loading) {
    return (
      <div className="dashboard loading">
        <p>Caricamento dati in corso…</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="dashboard error">
        <p>{error}</p>
      </div>
    )
  }

  return (
    <div className="dashboard">
      <header>
        <div>
          <p className="eyebrow">Osservatorio Incidenti • Coratolive.it</p>
          <h1>Analisi approfondita degli incidenti stradali nell'area di Corato</h1>
          <p className="subtitle">
            Aggregato automatico degli articoli pubblicati da CoratoLive: keyword
            «incidenti stradali», tag «incidente» e sinonimi correlati.
          </p>
        </div>
        <div className="periodo">
          <span>Periodo coperto</span>
          <strong>{periodLabel}</strong>
        </div>
      </header>

      <section className="filters">
        <div className="filter">
          <label htmlFor="search">Ricerca testuale</label>
          <input
            id="search"
            type="search"
            placeholder="Strada, città o parola chiave…"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
        </div>
        <div className="filter">
          <label htmlFor="severity">Gravità</label>
          <select
            id="severity"
            value={severityFilter}
            onChange={(event) =>
              setSeverityFilter(event.target.value as Incident['severity'] | 'all')
            }
          >
            <option value="all">Tutte</option>
            {Object.entries(severityLabels).map(([key, label]) => (
              <option key={key} value={key}>
                {label}
              </option>
            ))}
          </select>
        </div>
        <div className="filter">
          <label htmlFor="year">Anno</label>
          <select
            id="year"
            value={yearFilter}
            onChange={(event) =>
              setYearFilter(
                event.target.value === 'all' ? 'all' : Number(event.target.value),
              )
            }
          >
            <option value="all">Tutti</option>
            {years.map((year) => (
              <option key={year} value={year}>
                {year}
              </option>
            ))}
          </select>
        </div>
        <div className="filter filter-range">
          <label>Periodo personalizzato</label>
          <div className="range-inputs">
            <input
              type="date"
              value={dateFrom ?? ''}
              max={dateTo ?? datasetRange?.max ?? undefined}
              onChange={(event) => setDateFrom(event.target.value || null)}
            />
            <span>→</span>
            <input
              type="date"
              value={dateTo ?? ''}
              min={dateFrom ?? datasetRange?.min ?? undefined}
              onChange={(event) => setDateTo(event.target.value || null)}
            />
          </div>
          <div className="range-actions">
            <button type="button" onClick={handleResetRange} disabled={!datasetRange}>
              Reset periodo
            </button>
          </div>
        </div>
        <div className="filter">
          <label htmlFor="showRemoved">
            <input
              id="showRemoved"
              type="checkbox"
              checked={showRemoved}
              onChange={(event) => setShowRemoved(event.target.checked)}
            />
            Mostra anche articoli rimossi ({removedIncidents.length})
          </label>
        </div>
      </section>

      <section className="cards">
        <article>
          <p>Articoli selezionati</p>
          <strong>{filteredIncidents.length}</strong>
          <span>su {incidents.length} totali</span>
        </article>
        <article>
          <p>Incidenti gravi/fatali</p>
          <strong>
            {analytics.severity.grave + analytics.severity.fatale}
          </strong>
          <span>nel periodo selezionato</span>
        </article>
        <article>
          <p>Morti stimati</p>
          <strong>{casualties.totalMorti}</strong>
          <span>dall'analisi del testo</span>
        </article>
        <article>
          <p>Feriti stimati</p>
          <strong>{casualties.totalFeriti}</strong>
          <span>dall'analisi del testo</span>
        </article>
        <article>
          <p>Strade analizzate</p>
          <strong>{topRoads.length}</strong>
          <span>Top 20 nel periodo</span>
        </article>
        <article>
          <p>Comuni analizzati</p>
          <strong>{topCities.length}</strong>
          <span>Top 20 nel periodo</span>
        </article>
      </section>

      <section className="charts-grid-wide">
        <div className="card chart chart-large">
          <div className="card-header">
            <h2>Trend mensile (ultimi 36 mesi)</h2>
            <p>Conteggio articoli pubblicati nel tempo</p>
          </div>
          <ResponsiveContainer width="100%" height={400}>
            <AreaChart data={monthlyTrend} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="colorTrend" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#2563eb" stopOpacity={0.8} />
                  <stop offset="95%" stopColor="#2563eb" stopOpacity={0.1} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="month" tick={{ fontSize: 11 }} angle={-45} textAnchor="end" height={80} />
              <YAxis allowDecimals={false} />
              <Tooltip />
              <Area
                type="monotone"
                dataKey="value"
                stroke="#2563eb"
                strokeWidth={2}
                fillOpacity={1}
                fill="url(#colorTrend)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </section>

      <section className="charts-grid">
        <div className="card chart">
          <div className="card-header">
            <h2>Distribuzione per gravità</h2>
            <p>Classificazione automatica sulle parole chiave</p>
          </div>
          <ResponsiveContainer width="100%" height={350}>
            <PieChart>
              <Pie
                data={severityData}
                dataKey="value"
                nameKey="name"
                cx="50%"
                cy="50%"
                innerRadius={70}
                outerRadius={120}
                paddingAngle={4}
                label={({ name, percent }) => `${name}: ${percent ? (percent * 100).toFixed(0) : 0}%`}
              >
                {severityData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.fill} />
                ))}
              </Pie>
              <Tooltip />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        </div>

        <div className="card chart">
          <div className="card-header">
            <h2>Distribuzione per giorno della settimana</h2>
            <p>Giorni con più incidenti riportati</p>
          </div>
          <ResponsiveContainer width="100%" height={350}>
            <BarChart data={weekdayData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="day" />
              <YAxis allowDecimals={false} />
              <Tooltip />
              <Bar dataKey="value" fill="#8b5cf6" radius={[8, 8, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="card chart">
          <div className="card-header">
            <h2>Trend annuale</h2>
            <p>Evoluzione nel tempo per anno</p>
          </div>
          <ResponsiveContainer width="100%" height={350}>
            <LineChart data={yearlyTrend} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="year" />
              <YAxis allowDecimals={false} />
              <Tooltip />
              <Line type="monotone" dataKey="value" stroke="#10b981" strokeWidth={3} dot={{ r: 5 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </section>

      <section className="charts-grid-wide">
        <div className="card chart chart-large">
          <div className="card-header">
            <h2>Morti e feriti stimati per anno</h2>
            <p>Analisi estratta dal testo degli articoli</p>
          </div>
          <ResponsiveContainer width="100%" height={400}>
            <ComposedChart data={casualtiesByYear} margin={{ top: 20, right: 30, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="year" />
              <YAxis yAxisId="left" allowDecimals={false} />
              <YAxis yAxisId="right" orientation="right" allowDecimals={false} />
              <Tooltip />
              <Legend />
              <Bar yAxisId="left" dataKey="morti" fill="#ef4444" name="Morti" radius={[8, 8, 0, 0]} />
              <Bar yAxisId="left" dataKey="feriti" fill="#f97316" name="Feriti" radius={[8, 8, 0, 0]} />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </section>

      <section className="charts-grid">
        <div className="card chart">
          <div className="card-header">
            <h2>Veicoli coinvolti</h2>
            <p>Tipi di veicoli menzionati negli articoli</p>
          </div>
          <ResponsiveContainer width="100%" height={400}>
            <BarChart data={vehicles} layout="vertical" margin={{ left: 80, top: 20, right: 30, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis type="number" allowDecimals={false} />
              <YAxis dataKey="name" type="category" width={100} />
              <Tooltip />
              <Bar dataKey="value" fill="#06b6d4" radius={[0, 8, 8, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="card chart">
          <div className="card-header">
            <h2>Strade più pericolose (Top 15)</h2>
            <p>Con distribuzione per gravità</p>
          </div>
          <ResponsiveContainer width="100%" height={400}>
            <BarChart data={topRoads.slice(0, 15)} layout="vertical" margin={{ left: 120, top: 20, right: 30, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis type="number" allowDecimals={false} />
              <YAxis dataKey="name" type="category" width={140} tick={{ fontSize: 11 }} />
              <Tooltip />
              <Legend />
              <Bar dataKey="informativo" stackId="a" fill={severityColors.informativo} name="Informativo" />
              <Bar dataKey="moderato" stackId="a" fill={severityColors.moderato} name="Feriti" />
              <Bar dataKey="grave" stackId="a" fill={severityColors.grave} name="Grave" />
              <Bar dataKey="fatale" stackId="a" fill={severityColors.fatale} name="Mortale" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </section>

      <section className="charts-grid">
        <div className="card chart">
          <div className="card-header">
            <h2>Comuni più colpiti (Top 15)</h2>
            <p>Con distribuzione per gravità</p>
          </div>
          <ResponsiveContainer width="100%" height={400}>
            <BarChart data={topCities.slice(0, 15)} layout="vertical" margin={{ left: 100, top: 20, right: 30, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis type="number" allowDecimals={false} />
              <YAxis dataKey="name" type="category" width={120} tick={{ fontSize: 11 }} />
              <Tooltip />
              <Legend />
              <Bar dataKey="informativo" stackId="a" fill={severityColors.informativo} name="Informativo" />
              <Bar dataKey="moderato" stackId="a" fill={severityColors.moderato} name="Feriti" />
              <Bar dataKey="grave" stackId="a" fill={severityColors.grave} name="Grave" />
              <Bar dataKey="fatale" stackId="a" fill={severityColors.fatale} name="Mortale" />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="card chart">
          <div className="card-header">
            <h2>Strade più citate (Top 20)</h2>
            <p>Totale menzioni</p>
          </div>
          <ResponsiveContainer width="100%" height={400}>
            <BarChart data={topRoads.slice(0, 20)} layout="vertical" margin={{ left: 120, top: 20, right: 30, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis type="number" allowDecimals={false} />
              <YAxis dataKey="name" type="category" width={140} tick={{ fontSize: 10 }} />
              <Tooltip />
              <Bar dataKey="value" fill="#0ea5e9" radius={[0, 8, 8, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </section>

      <section className="charts-grid">
        <div className="card chart">
          <div className="card-header">
            <h2>Comuni menzionati (Top 20)</h2>
            <p>Totale menzioni</p>
          </div>
          <ResponsiveContainer width="100%" height={400}>
            <BarChart data={topCities.slice(0, 20)} layout="vertical" margin={{ left: 100, top: 20, right: 30, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis type="number" allowDecimals={false} />
              <YAxis dataKey="name" type="category" width={120} tick={{ fontSize: 10 }} />
              <Tooltip />
              <Bar dataKey="value" fill="#facc15" radius={[0, 8, 8, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </section>

      <section className="card incidents">
        <div className="card-header">
          <h2>Articoli correlati</h2>
          <p>
            {filteredIncidents.length} articoli trovati
            {showRemoved && removedIncidents.length > 0 && ` (${removedIncidents.length} rimossi inclusi)`}
            {!showRemoved && removedIncidents.length > 0 && ` (${removedIncidents.length} rimossi nascosti)`}
          </p>
        </div>
        {totalPages > 1 && (
          <div style={{ padding: '1rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid #e2e8f0' }}>
            <div>
              Pagina {currentPage} di {totalPages} 
              <span style={{ marginLeft: '1rem', color: '#64748b' }}>
                ({(currentPage - 1) * itemsPerPage + 1}-{Math.min(currentPage * itemsPerPage, filteredIncidents.length)} di {filteredIncidents.length})
              </span>
            </div>
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <button
                type="button"
                onClick={() => setCurrentPage(1)}
                disabled={currentPage === 1}
                style={{ padding: '0.5rem 1rem', border: '1px solid #e2e8f0', borderRadius: '4px', background: currentPage === 1 ? '#f1f5f9' : 'white', cursor: currentPage === 1 ? 'not-allowed' : 'pointer' }}
              >
                Prima
              </button>
              <button
                type="button"
                onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                disabled={currentPage === 1}
                style={{ padding: '0.5rem 1rem', border: '1px solid #e2e8f0', borderRadius: '4px', background: currentPage === 1 ? '#f1f5f9' : 'white', cursor: currentPage === 1 ? 'not-allowed' : 'pointer' }}
              >
                Precedente
              </button>
              <button
                type="button"
                onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                disabled={currentPage === totalPages}
                style={{ padding: '0.5rem 1rem', border: '1px solid #e2e8f0', borderRadius: '4px', background: currentPage === totalPages ? '#f1f5f9' : 'white', cursor: currentPage === totalPages ? 'not-allowed' : 'pointer' }}
              >
                Successiva
              </button>
              <button
                type="button"
                onClick={() => setCurrentPage(totalPages)}
                disabled={currentPage === totalPages}
                style={{ padding: '0.5rem 1rem', border: '1px solid #e2e8f0', borderRadius: '4px', background: currentPage === totalPages ? '#f1f5f9' : 'white', cursor: currentPage === totalPages ? 'not-allowed' : 'pointer' }}
              >
                Ultima
              </button>
            </div>
          </div>
        )}
        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>Data</th>
                <th>Titolo</th>
                <th>Luoghi</th>
                <th>Parole chiave</th>
              </tr>
            </thead>
            <tbody>
              {paginatedIncidents.map((incident) => {
                const isRemoved = removedIncidents.some(r => r.id === incident.id)
                return (
                  <tr key={incident.id} style={isRemoved ? { opacity: 0.6, backgroundColor: '#fef2f2' } : {}}>
                    <td>
                      {format(parseISO(incident.date), "dd MMM ''yy", { locale: it })}
                      {isRemoved && <span style={{ display: 'block', fontSize: '0.75rem', color: '#ef4444', marginTop: '0.25rem' }}>RIMOSSO</span>}
                    </td>
                    <td>
                      <a href={incident.link} target="_blank" rel="noreferrer">
                        {incident.title}
                      </a>
                      <p className="excerpt">{incident.excerpt}</p>
                      <span
                        className="severity-pill"
                        style={{ backgroundColor: severityColors[incident.severity] }}
                      >
                        {severityLabels[incident.severity]}
                      </span>
                    </td>
                    <td>
                      <div className="tag-list">
                        {incident.roads?.map((road) => (
                          <span key={road} className="tag">
                            {road}
                          </span>
                        ))}
                        {incident.cities
                          ?.filter((city) => city.trim().length > 0)
                          .map((city) => (
                            <span key={city} className="tag city">
                              {city}
                            </span>
                          ))}
                      </div>
                    </td>
                    <td>
                      <div className="tag-list">
                        {incident.keywords?.map((keyword) => (
                          <span key={keyword} className="tag keyword">
                            {keyword}
                          </span>
                        ))}
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
        {totalPages > 1 && (
          <div style={{ padding: '1rem', display: 'flex', justifyContent: 'center', borderTop: '1px solid #e2e8f0' }}>
            <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
              {Array.from({ length: Math.min(10, totalPages) }, (_, i) => {
                let pageNum
                if (totalPages <= 10) {
                  pageNum = i + 1
                } else if (currentPage <= 5) {
                  pageNum = i + 1
                } else if (currentPage >= totalPages - 4) {
                  pageNum = totalPages - 9 + i
                } else {
                  pageNum = currentPage - 4 + i
                }
                return (
                  <button
                    key={pageNum}
                    type="button"
                    onClick={() => setCurrentPage(pageNum)}
                    style={{
                      padding: '0.5rem 0.75rem',
                      border: '1px solid #e2e8f0',
                      borderRadius: '4px',
                      background: currentPage === pageNum ? '#2563eb' : 'white',
                      color: currentPage === pageNum ? 'white' : '#1e293b',
                      cursor: 'pointer',
                      minWidth: '2.5rem',
                    }}
                  >
                    {pageNum}
                  </button>
                )
              })}
            </div>
          </div>
        )}
      </section>
    </div>
  )
}

export default App
