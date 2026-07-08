import { useMutation } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { createProjet, projetPdfUrl } from './lib/api'
import { Fiche } from './components/fiche/Fiche'
import { SourceDrawer } from './components/fiche/SourceDrawer'
import { Header } from './components/header/Header'
import { IAStub } from './components/ia/IAStub'
import { Kanban } from './components/crm/Kanban'
import { LeftPanel } from './components/panel/LeftPanel'
import { MapView } from './components/map/MapView'
import { Rail } from './components/Rail'
import { SourcesPage } from './components/sources/SourcesPage'
import { ProjetsPanel } from './components/projets/ProjetsPanel'
import { ContextePanel } from './components/contexte/ContextePanel'
import { filtersFromHash, filtersToHash } from './lib/filters'
import { ModulePanel } from './components/outils/ModulePanel'
import { TimeMachine } from './components/outils/TimeMachine'
import { EMPTY_FILTERS, useApp } from './store/useApp'

// R2/V3 : la restitution du copilote — compteur animé + top cliquables. En mode PROJET, chaque
// parcelle porte son « pourquoi » (moteur) et l'utilisateur peut ENREGISTRER + exporter le PDF.
function IaRestitution() {
  const { iaRestitution, setIaRestitution, select, setView, setM22Prefill, setModule } = useApp()
  const [count, setCount] = useState(0)
  const [projetId, setProjetId] = useState<number | null>(null)
  useEffect(() => {
    if (!iaRestitution) return
    setCount(0)
    setProjetId(iaRestitution.projet?.id ?? null)
    const n = iaRestitution.n
    const t0 = performance.now()
    let raf = 0
    const tick = (ts: number) => {
      const p = Math.min(1, (ts - t0) / 900)
      setCount(Math.round(n * (1 - Math.pow(1 - p, 3))))
      if (p < 1) raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [iaRestitution])
  const enregistrer = useMutation({
    mutationFn: () => createProjet({ fiche: iaRestitution!.projet!.fiche, nom: iaRestitution!.projet!.nom }),
    onSuccess: (d) => setProjetId(d.projet.id),
  })
  if (!iaRestitution) return null
  const projet = iaRestitution.projet
  const wide = !!projet
  return (
    <div data-ia-restitution className={`absolute bottom-6 left-1/2 z-40 -translate-x-1/2 rounded-xl border border-[#2E6B4F] bg-[#0F1A14] px-4 py-3 shadow-2xl ${wide ? 'w-[520px]' : 'w-[440px]'}`}>
      <div className="flex items-start justify-between">
        <p className="text-sm text-txt">
          <span data-ia-count className="font-display text-xl font-bold text-mint">{count.toLocaleString('fr-FR')}</span>{' '}
          {iaRestitution.phrase}
        </p>
        <button onClick={() => setIaRestitution(null)} className="ml-2 text-txt-dim hover:text-txt" title="Fermer">✕</button>
      </div>

      {wide ? (
        <div className="mt-2 space-y-1.5">
          {iaRestitution.top.map((t, i) => (
            <button key={t.idu} data-ia-top onClick={() => select(t.idu)}
              className="block w-full rounded-lg border border-line-2 bg-surface-3 px-3 py-2 text-left hover:border-mint">
              <span className="font-mono text-[10px] text-mint">#{i + 1}</span>
              <span className="ml-1.5 font-mono text-[11px] text-txt-hi">{t.idu.slice(8)}</span>
              <span className="ml-1.5 text-[10px] text-txt-dim">{t.commune}</span>
              {t.pourquoi && (
                <ul data-ia-pourquoi className="mt-1 space-y-0.5">
                  {t.pourquoi.map((l, k) => (
                    <li key={k} className="text-[10px] leading-snug text-txt-mut">· {l}</li>
                  ))}
                </ul>
              )}
            </button>
          ))}
        </div>
      ) : (
        <div className="mt-2 flex gap-1.5">
          {iaRestitution.top.map((t, i) => (
            <button key={t.idu} data-ia-top onClick={() => select(t.idu)}
              className="min-w-0 flex-1 rounded-lg border border-line-2 bg-surface-3 px-2 py-1.5 text-left hover:border-mint">
              <span className="font-mono text-[10px] text-mint">#{i + 1} · Q {t.q_score}</span>
              <span className="block truncate font-mono text-[11px] text-txt-hi">{t.idu.slice(8)}</span>
              <span className="block truncate text-[9.5px] text-txt-dim">{t.commune}</span>
            </button>
          ))}
        </div>
      )}

      {projet && (
        <div className="mt-3 flex items-center gap-2 border-t border-line-2 pt-2.5">
          {projetId == null ? (
            <button data-projet-enregistrer onClick={() => enregistrer.mutate()} disabled={enregistrer.isPending}
              className="rounded-lg bg-mint px-3 py-1.5 text-[11px] font-semibold text-[#06130C] hover:brightness-110 disabled:opacity-50">
              {enregistrer.isPending ? 'Enregistrement…' : `Enregistrer « ${projet.nom} »`}
            </button>
          ) : (
            <>
              <span data-projet-enregistre className="rounded-lg bg-[#12241a] px-3 py-1.5 text-[11px] font-medium text-mint">✓ Projet enregistré</span>
              <a data-projet-pdf href={projetPdfUrl(projetId)} target="_blank" rel="noreferrer"
                className="rounded-lg border border-line-2 px-3 py-1.5 text-[11px] text-txt hover:border-mint hover:text-txt-hi">
                Exporter le PDF
              </a>
              <button onClick={() => { setView('projets'); setIaRestitution(null) }}
                className="ml-auto text-[11px] text-txt-mut hover:text-txt-hi" title="Voir mes projets">
                Mes projets →
              </button>
            </>
          )}
        </div>
      )}
      {projet?.programme && (
        <button data-projet-m22
          onClick={() => { setM22Prefill(projet.programme as Record<string, unknown>); setModule('programme'); setView('cartes'); setIaRestitution(null) }}
          className="mt-2 w-full rounded-lg border border-[#B497F0]/40 py-1.5 text-[11px] text-[#B497F0] hover:border-[#B497F0]"
          title="Ouvrir le formulaire M22 pré-rempli — la vérité reste le formulaire (éditable)">
          Affiner la capacité dans M22 (formulaire pré-rempli)
        </button>
      )}
    </div>
  )
}

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
  const { view, selectedIdu, select, setView, filters, setFilters, zone, setZone, module, setModule, setFlyTo, commune, setCommune, verdict, setVerdict } = useApp()

  // Hook d'auto-QA (stable, sans effet produit) : sélection directe d'une parcelle / d'une vue.
  useEffect(() => {
    ;(window as unknown as Record<string, unknown>).__labuse = { select, setView, setZone, setModule, setFlyTo, setCommune, setVerdict }
  }, [select, setView, setZone, setModule, setFlyTo, setCommune, setVerdict])

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
    if (p.get('v') === '1') setVerdict(true)   // les liens de démo ouvrent verdict allumé
    const m = p.get('m')
    if (m) setModule(m)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])
  useEffect(() => {
    let h = filtersToHash(filters, zone)
    const add = (kv: string) => { h = (h ? `${h}&` : '#f=1&') + kv }
    if (commune) add(`c=${encodeURIComponent(commune)}`)
    if (verdict) add('v=1')
    if (module) add(`m=${module}`)
    window.history.replaceState(null, '', h || window.location.pathname + window.location.search)
  }, [filters, zone, module, commune, verdict])


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
          {view === 'projets' && <ProjetsPanel />}
          {view === 'ia' && <IAStub />}
          {selectedIdu && view !== 'sources' && <Fiche idu={selectedIdu} />}
          <ContextePanel />
          <SourceDrawer />
          <Toast />
          <IaRestitution />
        </div>
      </div>
    </div>
  )
}
