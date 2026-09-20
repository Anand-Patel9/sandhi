const PATHS = {
  deals: <><path d="M5 4h14v16H5z" /><path d="M9 9h6M9 13h6M9 17h3" /></>,
  plus: <path d="M12 5v14M5 12h14" />,
  new: <><circle cx="12" cy="12" r="8" /><path d="M12 8v8M8 12h8" /></>,
  agents: <><circle cx="7" cy="8" r="3" /><circle cx="17" cy="8" r="3" /><path d="M3 19c0-3 2-5 4-5s4 2 4 5M13 19c0-3 2-5 4-5s4 2 4 5" /></>,
  data: <><ellipse cx="12" cy="6" rx="7" ry="3" /><path d="M5 6v12c0 1.7 3.1 3 7 3s7-1.3 7-3V6" /><path d="M5 12c0 1.7 3.1 3 7 3s7-1.3 7-3" /></>,
  audit: <><path d="M12 3l7 3v6c0 4.5-3 7.5-7 9-4-1.5-7-4.5-7-9V6z" /><path d="M9 12l2 2 4-4" /></>,
  bolt: <path d="M13 2L4 14h7l-1 8 9-12h-7z" />,
  lock: <><rect x="5" y="11" width="14" height="10" rx="2" /><path d="M8 11V8a4 4 0 0 1 8 0v3" /></>,
  check: <path d="M5 12l5 5L20 7" />,
  x: <path d="M6 6l12 12M18 6L6 18" />,
  download: <><path d="M12 4v11" /><path d="M7 10l5 5 5-5" /><path d="M5 20h14" /></>,
  signout: <><path d="M15 4h4v16h-4" /><path d="M10 8l-4 4 4 4" /><path d="M6 12h10" /></>,
  scale: <><path d="M12 4v16M6 20h12" /><path d="M5 8h14" /><path d="M5 8l-2 6h4zM19 8l-2 6h4z" /></>,
  arrow: <path d="M5 12h14M13 6l6 6-6 6" />,
} as const

export type IconName = keyof typeof PATHS

export function Icon({ name, size = 20, color = 'currentColor', strokeWidth = 1.8 }:
  { name: IconName; size?: number; color?: string; strokeWidth?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth={strokeWidth}
      strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      {PATHS[name]}
    </svg>
  )
}