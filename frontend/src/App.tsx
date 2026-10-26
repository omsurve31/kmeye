import { useState } from 'react'

import { AboutData } from './components/AboutData'
import { type DayRange } from './components/DateRangeControl'
import { panelId, tabId, ViewTabs, type View } from './components/ViewTabs'
import {
  APP_SUBTITLE,
  APP_TITLE,
  DEFAULT_CUTOFF_TIME_UK,
  DEFAULT_DECISION_DAY,
  FIRST_DELIVERY_DAY,
  LAST_DELIVERY_DAY,
} from './constants'
import { useMeta } from './hooks/useMeta'
import { AccuracyView } from './pages/AccuracyView'
import { DecisionView } from './pages/DecisionView'

function App() {
  const [view, setView] = useState<View>('decision')
  const [decisionDay, setDecisionDay] = useState(DEFAULT_DECISION_DAY)
  const [range, setRange] = useState<DayRange>({
    from: FIRST_DELIVERY_DAY,
    to: LAST_DELIVERY_DAY,
  })
  // One cutoff for both views: the assumption behind every number should not change between tabs.
  const [cutoff, setCutoff] = useState(DEFAULT_CUTOFF_TIME_UK)
  const { state: metaState } = useMeta()

  return (
    <>
      <header className="app-header">
        <div className="app-header__inner">
          <h1 className="app-header__title">{APP_TITLE}</h1>
          <p className="app-header__subtitle">{APP_SUBTITLE}</p>
          <ViewTabs view={view} onChange={setView} />
        </div>
      </header>
      <main className="app-main">
        <div role="tabpanel" id={panelId(view)} aria-labelledby={tabId(view)}>
          {view === 'decision' ? (
            <DecisionView
              day={decisionDay}
              onDayChange={setDecisionDay}
              cutoff={cutoff}
              onCutoffChange={setCutoff}
            />
          ) : (
            <AccuracyView
              from={range.from}
              to={range.to}
              onRangeChange={setRange}
              cutoff={cutoff}
              onCutoffChange={setCutoff}
            />
          )}
        </div>
        {metaState.status === 'success' && <AboutData meta={metaState.data} />}
      </main>
    </>
  )
}

export default App
