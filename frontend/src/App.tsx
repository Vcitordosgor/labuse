import { useEffect } from 'react'
import { Fiche } from './components/fiche/Fiche'
import { SourceDrawer } from './components/fiche/SourceDrawer'
import { Header } from './components/header/Header'
import { IAStub } from './components/ia/IAStub'
import { Kanban } from './components/crm/Kanban'
import { LeftPanel } from './components/panel/LeftPanel'
import { MapView } from './components/map/MapView'
import { Rail } from './components/Rail'
import { SourcesPage } from './components/sources/SourcesPage'
import { filtersFromHash, filtersToHash } from './lib/filters'
import { ModulePanel } from './components/outils/ModulePanel'
import { TimeMachine } from './components/outils/TimeMachine'
import { EMPTY_FILTERS, useApp } from './store/useApp'

export default function App() {
  const { view, selectedIdu, select, setView, filters, setFilters, zone, setZone, module, setModule, setFlyTo } = useApp()

  // Hook d'auto-QA (stable, sans effet produit) : sélection directe d'une parcelle / d'une vue.
  useEffect(() => {
    ;(window as unknown as Record<string, unknown>).__labuse = { select, setView, setZone, setModule, setFlyTo }
  }, [select, setView, setZone, setModule, setFlyTo])

  // URL partageable : filtres + zone sérialisés dans le hash (#f=…). Lecture au chargement,
  // écriture à chaque changement (replaceState : pas de pollution de l'historique).
  useEffect(() => {
    const hash = window.location.hash          // lu AVANT toute écriture (l'effet d'écriture suit)
    const parsed = filtersFromHash(hash)
    if (parsed) {
      setFilters({ ...EMPTY_FILTERS, ...parsed.filters })
      if (parsed.zone) setZone(parsed.zone)
    }
    const m = new URLSearchParams(hash.replace(/^#/, '')).get('m')
    if (m) setModule(m)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])
  useEffect(() => {
    let h = filtersToHash(filters, zone)
    if (module) h = (h ? `${h}&` : '#f=1&') + `m=${module}`
    window.history.replaceState(null, '', h || window.location.pathname + window.location.search)
  }, [filters, zone, module])


  return (
    <div className="flex h-screen w-screen overflow-hidden bg-bg font-sans text-txt">
      <Rail />
      <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
        <Header />
        <div className="relative flex min-h-0 flex-1 overflow-hidden">
          {view === 'cartes' && (
            <>
              {module ? <ModulePanel /> : <LeftPanel />}
              {module === 'temps' ? <TimeMachine /> : <MapView />}
            </>
          )}
          {view === 'crm' && <Kanban />}
          {view === 'sources' && <SourcesPage />}
          {view === 'ia' && <IAStub />}
          {selectedIdu && view !== 'sources' && <Fiche idu={selectedIdu} />}
          <SourceDrawer />
        </div>
      </div>
    </div>
  )
}
