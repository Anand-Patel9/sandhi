import { useCallback, useEffect, useRef, useState } from 'react'
import { api, type Negotiation, type NegotiationEvent, type Scenario, type Shock } from './api'

export function useAsync<T>(load: () => Promise<T>, deps: unknown[] = []) {
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const loadRef = useRef(load)
  loadRef.current = load

  const reload = useCallback(async () => {
    setLoading(true)
    try {
      setData(await loadRef.current())
      setError(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { void reload() }, deps)
  return { data, error, loading, reload, setData }
}

let catalogCache: Promise<{ scenarios: Scenario[]; shocks: Shock[] }> | null = null
export function loadCatalog() {
  catalogCache ??= Promise.all([api.scenarios(), api.shocks()])
    .then(([scenarios, shocks]) => ({ scenarios, shocks }))
    .catch((e) => { catalogCache = null; throw e })
  return catalogCache
}
export function useCatalog() {
  return useAsync(loadCatalog, [])
}

const LIVE = new Set(['pending', 'running'])

/** Loads a negotiation and follows it live over Server-Sent Events until the agents finish. */
export function useNegotiation(id: string) {
  const [negotiation, setNegotiation] = useState<Negotiation | null>(null)
  const [events, setEvents] = useState<NegotiationEvent[]>([])
  const [error, setError] = useState<string | null>(null)
  const lastSeq = useRef(0)

  const refresh = useCallback(async () => {
    try {
      setNegotiation(await api.negotiation(id))
      setError(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    }
  }, [id])

  const appendEvents = useCallback((batch: NegotiationEvent[]) => {
    const fresh = batch.filter((e) => e.seq > lastSeq.current)
    if (!fresh.length) return
    lastSeq.current = fresh[fresh.length - 1].seq
    setEvents((prev) => [...prev, ...fresh])
  }, [])

  useEffect(() => {
    let source: EventSource | null = null
    let cancelled = false
    lastSeq.current = 0
    setEvents([])
    setNegotiation(null)

    const start = async () => {
      try {
        const [n, evs] = await Promise.all([api.negotiation(id), api.events(id)])
        if (cancelled) return
        setNegotiation(n)
        appendEvents(evs)
        if (!LIVE.has(n.status)) return
        source = new EventSource(api.streamUrl(id, lastSeq.current))
        const onEvent = (msg: MessageEvent) => appendEvents([JSON.parse(msg.data) as NegotiationEvent])
        source.onmessage = onEvent
        for (const kind of ['info', 'rate', 'offer', 'shock', 'privacy', 'mediation', 'accept', 'reject', 'deal',
          'no_deal', 'approval_required', 'cancelled']) {
          source.addEventListener(kind, onEvent as EventListener)
        }
        source.addEventListener('end', () => { source?.close(); void refresh() })
        source.onerror = () => { source?.close(); void refresh() }
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : String(e))
      }
    }
    void start()
    return () => { cancelled = true; source?.close() }
  }, [id, appendEvents, refresh])

  const reloadEvents = useCallback(async () => {
    appendEvents(await api.events(id, lastSeq.current))
  }, [id, appendEvents])

  return { negotiation, setNegotiation, events, error, refresh, reloadEvents }
}