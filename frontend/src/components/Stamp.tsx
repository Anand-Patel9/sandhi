import type { Status } from '../lib/api'
import { statusStamp } from '../lib/format'

export function Stamp({ status, large = false }: { status: Status; large?: boolean }) {
  const { label, cls } = statusStamp(status)
  return <span className={`stamp ${cls}${large ? ' stamp-lg' : ''}`}>{label}</span>
}