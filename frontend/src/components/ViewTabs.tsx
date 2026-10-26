import { useRef, type KeyboardEvent } from 'react'

export type View = 'decision' | 'accuracy'

type ViewTabsProps = {
  view: View
  onChange: (view: View) => void
}

const TABS: { view: View; label: string }[] = [
  { view: 'decision', label: "Tomorrow's forecast" },
  { view: 'accuracy', label: 'Forecast accuracy' },
]

export const tabId = (view: View): string => `tab-${view}`
export const panelId = (view: View): string => `panel-${view}`

export function ViewTabs({ view, onChange }: ViewTabsProps) {
  const tabElements = useRef<Partial<Record<View, HTMLButtonElement | null>>>({})

  // Arrow keys move between tabs (wrapping around), the usual keyboard pattern for tabs.
  const handleKeyDown = (event: KeyboardEvent<HTMLButtonElement>, index: number) => {
    const step = event.key === 'ArrowRight' ? 1 : event.key === 'ArrowLeft' ? -1 : 0
    if (step === 0) {
      return
    }
    const next = TABS[(index + step + TABS.length) % TABS.length]
    if (next) {
      onChange(next.view)
      tabElements.current[next.view]?.focus()
    }
  }

  return (
    <div className="tabs" role="tablist" aria-label="Views">
      {TABS.map((tab, index) => {
        const isSelected = tab.view === view
        return (
          <button
            key={tab.view}
            ref={(element) => {
              tabElements.current[tab.view] = element
            }}
            type="button"
            role="tab"
            id={tabId(tab.view)}
            className="tab"
            aria-selected={isSelected}
            aria-controls={panelId(tab.view)}
            tabIndex={isSelected ? 0 : -1}
            onClick={() => onChange(tab.view)}
            onKeyDown={(event) => handleKeyDown(event, index)}
          >
            {tab.label}
          </button>
        )
      })}
    </div>
  )
}
