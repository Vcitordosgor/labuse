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
import { ContextePanel } from './components/contexte/ContextePanel'
import { filtersFromHash, filtersToHash } from './lib/filters'
import { ModulePanel } from './components/outils/ModulePanel'
import { TimeMachine } from './components/outils/TimeMachine'
import { EMPTY_FILTERS, useApp } from './store/useApp'

// C6 (revue Vic) : message sobre, VISIBLE, auto-éteint — pas un title de survol
function Toast() {
  const { toast, setToast } = useApp()
  useEffect(() => {
    if (!toast) return
    const t = setTimeout(() => setToast(null), 4000)
    return () => clearTimeout(t)
  }, [toast, setToast])
  if (!toast) return null
  return (
    <div data-toast className="pointer-events-none absolute bottom-16 left-1/2 z-50 -translate-x-1/2 rounded-lg border border-[#2E6B4F] bg-[#0F1A14] px-4 py-2 text-xs text-txt shadow-xl">
      {toast}
    </div>
  )
}

export default function App() {
  const { view, selectedIdu, select, setView, filters, setFilters, zone, setZone, module, setModule, setFlyTo, commune, setCommune } = useApp()

  // Hook d'auto-QA (stable, sans effet produit) : sélection directe d'une parcelle / d'une vue.
  useEffect(() => {
    ;(window as unknown as Record<string, unknown>).__labuse = { select, setView, setZone, setModule, setFlyTo, setCommune }
  }, [select, setView, setZone, setModule, setFlyTo, setCommune])

  // URL partageable : filtres + zone + commune sérialisés dans le hash (#f=…&c=…). Lecture au
  // chargement, écriture à chaque changement (replaceState : pas de pollution de l'historique).
  useEffect(() => {
    const hash = window.location.hash          // lu AVANT toute écriture (l'effet d'écriture suit)
    const parsed = filtersFromHash(hash)
    if (parsed) {
      setFilters({ ...EMPTY_FILTERS, ...parsed.filters })
      if (parsed.zone) setZone(parsed.zone)
    }
    const p = new URLSearchParams(hash.replace(/^#/, ''))
    const c = p.get('c')
    if (c) setCommune(decodeURIComponent(c))
    const m = p.get('m')
    if (m) setModule(m)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])
  useEffect(() => {
    let h = filtersToHash(filters, zone)
    const add = (kv: string) => { h = (h ? `${h}&` : '#f=1&') + kv }
    if (commune) add(`c=${encodeURIComponent(commune)}`)
    if (module) add(`m=${module}`)
    window.history.replaceState(null, '', h || window.location.pathname + window.location.search)
  }, [filters, zone, module, commune])


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
          <ContextePanel />
          <SourceDrawer />
          <Toast />
        </div>
      </div>
    </div>
  )
}
