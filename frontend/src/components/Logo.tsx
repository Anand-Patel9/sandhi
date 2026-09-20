interface MarkProps { size?: number; onDark?: boolean; stroke?: number }

export function Mark({ size = 34, onDark = false, stroke = 6 }: MarkProps) {
  const [s, b, f, seal] = onDark
    ? ['#E0A93A', '#8FA8E6', '#6FC2B6', '#F6F7F4']
    : ['#B9800E', '#3B5BA9', '#2B7A71', '#1B2440']
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" aria-hidden="true">
      <path d="M8 14 C 22 14, 26 32, 40 32" stroke={s} strokeWidth={stroke} fill="none" strokeLinecap="round" />
      <path d="M8 32 L 40 32" stroke={b} strokeWidth={stroke} fill="none" strokeLinecap="round" />
      <path d="M8 50 C 22 50, 26 32, 40 32" stroke={f} strokeWidth={stroke} fill="none" strokeLinecap="round" />
      <circle cx="46" cy="32" r="9.5" fill={seal} />
    </svg>
  )
}

export function ConvergenceArt() {
  return (
    <svg className="art-svg" width="420" height="220" viewBox="0 0 420 220" aria-hidden="true">
      <path d="M20 30 C 150 30, 190 110, 290 110" stroke="#E0A93A" strokeWidth="10" fill="none" strokeLinecap="round" />
      <path d="M20 110 L 290 110" stroke="#8FA8E6" strokeWidth="10" fill="none" strokeLinecap="round" />
      <path d="M20 190 C 150 190, 190 110, 290 110" stroke="#6FC2B6" strokeWidth="10" fill="none" strokeLinecap="round" />
      <circle cx="336" cy="110" r="38" fill="#F6F7F4" />
      <text x="20" y="18" fill="#E0A93A" fontSize="15" fontFamily="Instrument Sans, sans-serif" fontWeight="600">MSME supplier</text>
      <text x="20" y="96" fill="#8FA8E6" fontSize="15" fontFamily="Instrument Sans, sans-serif" fontWeight="600">Corporate buyer</text>
      <text x="20" y="216" fill="#6FC2B6" fontSize="15" fontFamily="Instrument Sans, sans-serif" fontWeight="600">TReDS financier</text>
    </svg>
  )
}