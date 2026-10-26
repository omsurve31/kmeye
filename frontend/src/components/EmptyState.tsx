import type { ReactNode } from 'react'

type EmptyStateProps = {
  title: string
  children: ReactNode
}

export function EmptyState({ title, children }: EmptyStateProps) {
  return (
    <div className="state">
      <h3 className="state__title">{title}</h3>
      <p className="state__message">{children}</p>
    </div>
  )
}
