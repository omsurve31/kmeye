type LoadingStateProps = {
  label: string
}

// A grey skeleton keeps the page layout steady while data loads; the hidden text is for screen readers.
export function LoadingState({ label }: LoadingStateProps) {
  return (
    <div className="loading-state" role="status">
      <div className="skeleton skeleton--tall" aria-hidden="true" />
      <div className="skeleton" aria-hidden="true" />
      <span className="visually-hidden">Loading {label}…</span>
    </div>
  )
}
