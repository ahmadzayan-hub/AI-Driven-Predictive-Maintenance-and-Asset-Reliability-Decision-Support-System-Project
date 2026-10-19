/** Decorative identity mark, never an operational health indicator. */
export function MiyaarMark({ large = false }: { large?: boolean }) {
  return <span className={`miyaar-mark${large ? ' miyaar-mark--large' : ''}`} aria-hidden="true">
    <svg viewBox="0 0 64 64" fill="none" focusable="false">
      <circle cx="32" cy="32" r="27" stroke="currentColor" strokeOpacity=".25" />
      <path d="M13 32a19 19 0 0 1 38 0M51 32a19 19 0 0 1-38 0" stroke="currentColor" strokeWidth="2" strokeDasharray="36 24" />
      <path d="M20 39V25l12 8 12-8v14" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx="32" cy="15" r="2" fill="currentColor" />
    </svg>
  </span>
}
