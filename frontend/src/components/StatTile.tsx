type StatTileProps = {
  label: string
  value: string
  caption?: string
}

// Render inside a <dl>: the label is the term and the value is its description.
export function StatTile({ label, value, caption }: StatTileProps) {
  return (
    <div className="stat">
      <dt className="stat__label">{label}</dt>
      <dd className="stat__value">{value}</dd>
      {caption && <dd className="stat__caption">{caption}</dd>}
    </div>
  )
}
