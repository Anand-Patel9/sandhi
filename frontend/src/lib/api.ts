export const API_BASE: string = (import.meta.env.VITE_API_BASE ?? '').replace(/\/$/, '')

export type Party = 'supplier' | 'buyer' | 'financier'
export type OrgKind = Party | 'platform'
export type Status =
  | 'pending' | 'running' | 'awaiting_approval' | 'agreed' | 'no_deal' | 'rejected' | 'failed' | 'cancelled'

export interface Terms { price: number; days: number; treds: boolean; buyer_share: number; rate: number }
export interface User { id: string; email: string; name: string; org: { id: string; name: string; kind: OrgKind } }
export interface Approval { role: Party; decision: 'approve' | 'reject'; note: string; user_email: string; created_at: string }
export interface Compliance {
  msmed_compliant: boolean; days_to_msme_payment: number; days_over_limit: number
  section_43bh_deduction_deferred: boolean; msmed_interest_exposure: number; notes: string[]
}
export interface Outcome {
  agreed: boolean; terms: Terms | null; round: number; via: string; values: Record<string, number>
  compliance: Compliance | null; transport?: string; engines?: Record<string, string>
  required_approvals?: Party[]; redactions: number; llm_messages: number; template_messages: number
}
export interface Negotiation {
  id: string; scenario_key: string; title: string; status: Status; config: NegotiationConfig
  outcome: Outcome | null; error: string | null; created_by: string | null; approvals: Approval[]
  created_at: string; finished_at: string | null
}
export interface NegotiationEvent {
  seq: number; kind: string; round: number; agent: string; message: string; terms: Terms | null
  utilities: Record<string, number>; meta: Record<string, unknown>; hash: string; created_at: string
}
export interface DealSpec {
  item: string; quantity: number; price_bounds: [number, number]; day_options: number[]
  share_options: number[]; max_rounds: number; legal_limit_days: number; treds_settlement_days: number
}
export interface Scenario {
  key: string; title: string; story: string; spec: DealSpec; market: { bank_rate: number }
  parties: Record<Party, string>; defaults: Record<Party, Record<string, number | string>>
}
export interface Shock { key: string; title: string; description: string }
export interface Approach {
  key: string; label: string; description: string; terms: Terms | null
  surplus: Record<Party, number>; realised: Record<Party, number>; viable: boolean; blocked_by: string[]
}
export interface Evaluation {
  negotiation_id: string; approaches: Approach[]; efficiency: number; pareto_efficient: boolean; balance: number
  deal_zone: { days: number; treds: boolean; min_price: number | null; max_price: number | null }[]
}
export interface AuditResult { negotiation_id: string; valid: boolean; events: number; head_hash: string; broken_at_seq: number | null }
export interface AgentCard {
  name: string; description: string; version: string
  supportedInterfaces: { url: string; protocolBinding: string; protocolVersion: string }[]
  provider?: { organization: string; url: string }
  skills: { id: string; name: string; description: string }[]
}
export interface AgentInfo { role: Party; base_url: string; card_url: string; card: AgentCard }
export interface ToolServer { server: string; url: string; status: 'online' | 'offline'; error?: string; tools: { name: string; description: string }[] }
export interface NegotiationConfig {
  scenario: string; max_rounds?: number; shocks?: { key: string; at_round: number }[]
  llm?: { provider?: string; per_agent?: Record<string, string> }; pace_seconds?: number; require_approval?: boolean
}

const TOKEN_KEY = 'sandhi.token'
export const tokenStore = {
  get: (): string | null => { try { return localStorage.getItem(TOKEN_KEY) } catch { return null } },
  set: (t: string) => { try { localStorage.setItem(TOKEN_KEY, t) } catch { /* storage unavailable */ } },
  clear: () => { try { localStorage.removeItem(TOKEN_KEY) } catch { /* storage unavailable */ } },
}

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) { super(message); this.status = status }
}

let onUnauthorized: () => void = () => {}
export function setUnauthorizedHandler(fn: () => void) { onUnauthorized = fn }

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers)
  const token = tokenStore.get()
  if (token) headers.set('Authorization', `Bearer ${token}`)
  if (init.body && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json')
  let res: Response
  try {
    res = await fetch(`${API_BASE}${path}`, { ...init, headers })
  } catch {
    throw new ApiError(0, 'Cannot reach the Sandhi server. Check that the backend is running.')
  }
  if (res.status === 401 && !path.startsWith('/api/auth/login')) onUnauthorized()
  if (!res.ok) {
    let detail = res.statusText
    try {
      const body = await res.json()
      detail = typeof body.detail === 'string' ? body.detail : body.detail?.[0]?.msg ?? detail
    } catch { /* non-JSON error */ }
    throw new ApiError(res.status, detail)
  }
  const type = res.headers.get('Content-Type') ?? ''
  return (type.includes('application/json') ? res.json() : res.blob()) as Promise<T>
}

export const api = {
  login: (email: string, password: string) =>
    request<{ access_token: string; user: User }>('/api/auth/login', { method: 'POST', body: JSON.stringify({ email, password }) }),
  me: () => request<User>('/api/auth/me'),
  scenarios: () => request<Scenario[]>('/api/scenarios'),
  shocks: () => request<Shock[]>('/api/shocks'),
  agents: () => request<AgentInfo[]>('/api/agents'),
  tools: () => request<ToolServer[]>('/api/tools'),
  negotiations: () => request<Negotiation[]>('/api/negotiations?limit=100'),
  negotiation: (id: string) => request<Negotiation>(`/api/negotiations/${id}`),
  events: (id: string, after = 0) => request<NegotiationEvent[]>(`/api/negotiations/${id}/events?after=${after}`),
  create: (config: NegotiationConfig) => request<Negotiation>('/api/negotiations', { method: 'POST', body: JSON.stringify(config) }),
  cancel: (id: string) => request<Negotiation>(`/api/negotiations/${id}/cancel`, { method: 'POST' }),
  decide: (id: string, decision: 'approve' | 'reject', note: string, role?: Party) =>
    request<Negotiation>(`/api/negotiations/${id}/approval`, { method: 'POST', body: JSON.stringify({ decision, note, role }) }),
  evaluation: (id: string) => request<Evaluation>(`/api/negotiations/${id}/evaluation`),
  audit: (id: string) => request<AuditResult>(`/api/negotiations/${id}/audit`),
  termSheet: (id: string) => request<Blob>(`/api/negotiations/${id}/term-sheet`),
  streamUrl: (id: string, after: number) =>
    `${API_BASE}/api/negotiations/${id}/stream?after=${after}&token=${encodeURIComponent(tokenStore.get() ?? '')}`,
}