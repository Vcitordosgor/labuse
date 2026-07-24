import { useMutation, useQuery } from '@tanstack/react-query'
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
import { ParcoursTinder } from './components/projets/ParcoursTinder'
import { ContextePanel } from './components/contexte/ContextePanel'
import { filtersFromHash, filtersToHash } from './lib/filters'
import { SCORE_TIP } from './lib/status'
import { useApplySearch } from './lib/useApplySearch'
import { ModulePanel } from './components/outils/ModulePanel'
import { TimeMachine } from './components/outils/TimeMachine'
import { EMPTY_FILTERS, useApp } from './store/useApp'

// R2/V3 : la restitution du copilote — compteur animé + top cliquables. En mode PROJET, chaque
// parcelle porte son « pourquoi » (moteur) et l'utilisateur peut ENREGISTRER + exporter le PDF.
function IaRestitution() {
  const { iaRestitution, setIaRestitution, select, setView, setM22Prefill, setModule, togglePanel, selectedIdu, setVerdict, setOpenProjet } = useApp()
  const apply = useApplySearch()   // ajout C (UX V1) : relance sans le critère le plus serré
  const [count, setCount] = useState(0)
  const [projetId, setProjetId] = useState<number | null>(null)
  const [reprisExistant, setReprisExistant] = useState(false)   // dédup douce : projet identique déjà là
  useEffect(() => {
    if (!iaRestitution) return
    setCount(0)
    setProjetId(iaRestitution.projet?.id ?? null)
    setReprisExistant(false)
    const n = iaRestitution.n
    const t0 = performance.now()
    let raf = 0
    const tick = (ts: number) => {
      // clamp bas : le 1er timestamp rAF peut PRÉCÉDER t0 (début de frame) → p négatif
      // → compteur négatif affiché (« -9 parcelles »), figé si la carte affame les frames.
      const p = Math.min(1, Math.max(0, (ts - t0) / 900))
      setCount(Math.max(0, Math.round(n * (1 - Math.pow(1 - p, 3)))))
      if (p < 1) raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [iaRestitution])
  const enregistrer = useMutation({
    mutationFn: () => createProjet({ fiche: iaRestitution!.projet!.fiche, nom: iaRestitution!.projet!.nom }),
    // dédup douce : si un projet identique existait, le serveur le renvoie (existing) — on le REPREND
    // au lieu d'empiler un doublon ; le front le signale et propose de l'ouvrir.
    onSuccess: (d) => { setProjetId(d.projet.id); setReprisExistant(!!d.existing) },
  })
  if (!iaRestitution) return null
  const projet = iaRestitution.projet
  const wide = !!projet
  // P2 (dernière passe) : accès à TOUS les résultats + persistance. « Voir les N résultats »
  // ouvre la liste filtrée à gauche (verdict allumé). La restitution RESTE affichée quand une
  // fiche s'ouvre — on décale légèrement vers la gauche pour ne pas la masquer sous la fiche.
  // A1 (post-revue) : le bouton était INERTE car la liste était DÉJÀ affichée derrière la carte-
  // résumé (rien ne changeait à l'écran). Désormais le clic FERME le résumé flottant et fait
  // passer la LISTE COMPLÈTE (gauche) au premier plan — transition visible. La liste porte les
  // filtres du résultat (persistante : ouvrir une fiche ne la perd pas, on enchaîne #1, #2…).
  const voirTout = () => {
    setVerdict(true)
    if (!useApp.getState().panelOpen) togglePanel()
    setIaRestitution(null)
    setTimeout(() => document.querySelector('[data-results-scroll]')?.scrollTo({ top: 0 }), 60)
  }
  return (
    <div data-ia-restitution
      className={`absolute bottom-6 z-40 rounded-xl border border-[#2E6B4F] bg-[#0F1A14] px-4 py-3 shadow-2xl ${wide ? 'w-[520px]' : 'w-[440px]'} ${
        selectedIdu ? 'left-6' : 'left-1/2 -translate-x-1/2'}`}>
      <div className="flex items-start justify-between">
        <p className="text-sm text-txt">
          <span data-ia-count className="font-display text-xl font-bold text-mint">{count.toLocaleString('fr-FR')}</span>{' '}
          {iaRestitution.phrase}
        </p>
        <button onClick={() => setIaRestitution(null)} className="ml-2 text-txt-dim hover:text-txt" title="Fermer le résultat">✕</button>
      </div>
      {/* Item 2 (UX V1) : la traduction EXACTE du serveur, DANS la restitution. En mode
          mots-clés (stub), le badge + la phrase disent ce qui n'a PAS été traduit — un repli
          ne se fait jamais passer pour une vraie traduction. */}
      {(iaRestitution.explanation || iaRestitution.stub) && (
        <p data-ia-explication className="mt-2 rounded-lg border border-line-2 bg-surface-2 px-2.5 py-1.5 text-[11px] leading-snug text-txt-mut">
          {iaRestitution.stub && (
            <span data-ia-badge-stub className="mr-1.5 inline-block rounded-full border border-st-creuser/50 bg-[#211a10] px-1.5 py-0.5 text-[11px] font-medium text-st-creuser">
              mode mots-clés
            </span>
          )}
          {iaRestitution.explanation}
          {iaRestitution.stub && (
            <span className="text-txt-dim"> Les critères absents de cette liste n'ont pas été traduits — réessayez plus tard pour la traduction complète.</span>
          )}
        </p>
      )}
      {/* M11 B1 : critères COMPRIS mais hors des 14 champs de la recherche simple — signalés,
          jamais avalés en silence, jamais confondus avec un résultat servi. Coexiste avec les
          résultats valides ci-dessous : on ne cache rien, on prévient de l'écart. */}
      {!!iaRestitution.criteres_non_appliques?.length && (
        <p data-ia-non-appliques className="mt-1.5 rounded-lg border border-[#6b5a2e] bg-[#1a170f] px-2.5 py-1.5 text-[11px] leading-snug text-txt">
          ⚠ Certains critères n'ont pas pu être appliqués :{' '}
          <span className="text-txt-dim">{iaRestitution.criteres_non_appliques.join(', ')}.</span>
        </p>
      )}
      {/* Ajout C (UX V1) : jamais de zéro sec — à 0 résultat on propose le relâchement du
          critère numérique le plus serré, relançable d'un clic. */}
      {iaRestitution.n === 0 ? (
        <div data-ia-zero className="mt-1.5 rounded-lg border border-st-creuser/40 bg-[#211a10] px-3 py-2 text-[11px] leading-snug text-st-creuser">
          Aucun résultat avec tous ces critères.
          {iaRestitution.relance ? (
            <button data-ia-relance
              onClick={() => {
                const r = iaRestitution.relance!
                apply(r.raw, iaRestitution.phrase, {
                  explanation: `Critère « ${r.label} » retiré. ${iaRestitution.explanation ?? ''}`.trim(),
                  stub: iaRestitution.stub,
                })
              }}
              className="mt-1.5 flex w-full items-center justify-center rounded-lg border border-st-creuser/60 bg-st-creuser/10 py-1.5 font-medium text-st-creuser hover:bg-st-creuser/20">
              Réessayer sans le critère « {iaRestitution.relance.label} » →
            </button>
          ) : (
            <span className="text-txt-dim"> Élargissez le périmètre ou retirez un critère.</span>
          )}
        </div>
      ) : (
        <button data-ia-voir-tout onClick={voirTout}
          className="mt-1.5 flex w-full items-center justify-center gap-1.5 rounded-lg border border-mint/40 bg-mint/10 py-1.5 text-[11px] font-medium text-mint hover:bg-mint/20">
          Voir les {count.toLocaleString('fr-FR')} résultats dans la liste →
        </button>
      )}

      {wide ? (
        <div className="mt-2.5 space-y-2">
          {iaRestitution.top.map((t, i) => (
            <button key={t.idu} data-ia-top onClick={() => select(t.idu)}
              className="block w-full rounded-lg border border-line-2 bg-surface-3 px-3 py-2.5 text-left transition-colors hover:border-mint">
              {/* en-tête lisible : rang (pastille) · IDU en avant · commune alignée à droite */}
              <div className="flex items-baseline gap-2">
                <span className="shrink-0 rounded bg-mint/15 px-1.5 py-0.5 font-mono text-[10px] font-semibold text-mint">#{i + 1}</span>
                <span className="min-w-0 flex-1 truncate font-mono text-[12px] font-medium text-txt-hi">{t.idu.slice(8)}</span>
                <span className="shrink-0 text-[11px] text-txt-dim">{t.commune}</span>
              </div>
              {t.pourquoi && t.pourquoi.length > 0 && (
                <ul data-ia-pourquoi className="mt-1.5 space-y-1 border-t border-line-2/60 pt-1.5">
                  {t.pourquoi.map((l, k) => (
                    <li key={k} className="flex gap-1.5 text-[11px] leading-snug text-txt-mut">
                      <span className="shrink-0 text-mint">·</span><span className="min-w-0 flex-1">{l}</span>
                    </li>
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
              <span className="font-mono text-[11px] text-mint"
                title={t.mult_v2 != null ? '×N vs moyenne du parc (scoring v2)' : SCORE_TIP.q}>
                #{i + 1}{t.mult_v2 != null ? ` · ×${t.mult_v2.toFixed(1)}` : ` · Q ${t.q_score}`}
              </span>
              <span className="block truncate font-mono text-[11px] text-txt-hi">{t.idu.slice(8)}</span>
              <span className="block truncate text-[11px] text-txt-dim">{t.commune}</span>
            </button>
          ))}
        </div>
      )}

      {projet && (
        <div className="mt-3 flex items-center gap-2 border-t border-line-2 pt-2.5">
          {projetId == null ? (
            <button data-projet-enregistrer onClick={() => enregistrer.mutate()} disabled={enregistrer.isPending}
              className="rounded-lg bg-mint px-3 py-1.5 text-[11px] font-semibold text-mint-ink hover:brightness-110 disabled:opacity-50">
              {enregistrer.isPending ? 'Enregistrement…' : `Enregistrer « ${projet.nom} »`}
            </button>
          ) : (
            <>
              <span data-projet-enregistre className="rounded-lg bg-[#12241a] px-3 py-1.5 text-[11px] font-medium text-mint"
                title={reprisExistant ? 'Un projet identique existait déjà — repris (pas de doublon)' : undefined}>
                {reprisExistant ? '✓ Projet identique repris' : '✓ Projet enregistré'}
              </span>
              <button data-projet-ouvrir-kanban onClick={() => { setOpenProjet({ id: projetId, nom: projet.nom }); setIaRestitution(null) }}
                className="rounded-lg border border-mint/40 bg-mint/10 px-3 py-1.5 text-[11px] font-medium text-mint hover:bg-mint/20"
                title="Ouvrir le projet (kanban : à trier / retenues / écartées)">
                Ouvrir le projet →
              </button>
              <a data-projet-pdf href={projetPdfUrl(projetId)} target="_blank" rel="noreferrer"
                className="rounded-lg border border-line-2 px-3 py-1.5 text-[11px] text-txt hover:border-mint hover:text-txt-hi">
                PDF
              </a>
              <button onClick={() => { setOpenProjet(null); setIaRestitution(null) }}
                className="ml-auto text-[11px] text-txt-mut hover:text-txt-hi" title="Voir mes projets">
                Mes projets →
              </button>
            </>
          )}
        </div>
      )}
      {projet?.programme && (
        <button data-projet-m22
          onClick={() => { setView('cartes'); setM22Prefill(projet.programme as Record<string, unknown>); setModule('programme') }}
          className="mt-2 w-full rounded-lg border border-violet/40 py-1.5 text-[11px] text-violet hover:border-violet"
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
  const { view, selectedIdu, select, setView, filters, setFilters, zone, setZone, module, setModule, setFlyTo, commune, setCommune, verdict, setVerdict, outilsOpen, parcours, setMsel } = useApp()

  // Hook d'auto-QA (stable, sans effet produit) : sélection directe d'une parcelle / d'une vue.
  useEffect(() => {
    ;(window as unknown as Record<string, unknown>).__labuse = { select, setView, setZone, setModule, setFlyTo, setCommune, setVerdict, setMsel }
  }, [select, setView, setZone, setModule, setFlyTo, setCommune, setVerdict, setMsel])

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
    // (Alias d'URL #pg=vues / pg=segments retiré avec le spin-off « Vues » — M12 Lot C-bis.)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])
  useEffect(() => {
    let h = filtersToHash(filters, zone)
    const add = (kv: string) => { h = (h ? `${h}&` : '#f=1&') + kv }
    if (commune) add(`c=${encodeURIComponent(commune)}`)
    if (verdict) add('v=1')
    if (module) add(`m=${module}`)
    window.history.replaceState(null, '', h || window.location.pathname + window.location.search)
  }, [filters, zone, module, commune, verdict, view])


  return (
    <div className="flex h-screen w-screen overflow-hidden bg-bg font-sans text-txt">
      <Rail />
      <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
        <CompteBandeau />
        <Header />
        <div className="relative flex min-h-0 flex-1 overflow-hidden">
          {view === 'cartes' && (
            <>
              {/* P1 : quand le tiroir Outils est ouvert, il REMPLACE le panneau Cartes (COUCHES/
                  résultats) — la carte reste derrière. Un seul panneau gauche à la fois. */}
              {outilsOpen ? null : module ? <ModulePanel /> : parcours ? null : <LeftPanel />}
              {module === 'temps' ? <TimeMachine /> : <MapView />}
              {parcours && <ParcoursTinder />}
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


/** PREMIER EURO · E2 — l'état d'abonnement AFFICHÉ, jamais un 500 : « paiement requis »
 *  en bandeau st-creuser (l'accès continue pendant les relances Stripe) ; suspension =
 *  la session meurt côté serveur, ce bandeau n'a donc jamais à la dire. Mode pilote : rien. */
function CompteBandeau() {
  const moi = useQuery({
    queryKey: ['moi'],
    queryFn: async () => { const r = await fetch('/moi'); return r.ok ? r.json() : null },
    staleTime: 300_000, retry: false,
  })
  if (moi.data?.mode !== 'compte' || moi.data?.statut_compte !== 'paiement_requis') return null
  return (
    <div data-compte-bandeau className="flex shrink-0 items-center gap-2 border-b border-st-creuser/40 bg-st-creuser/10 px-4 py-1.5 text-[11.5px] text-st-creuser">
      <span aria-hidden>▲</span>
      Paiement requis — le dernier prélèvement n'a pas abouti. Mettez à jour votre moyen de
      paiement depuis la facture Stripe reçue par email ; l'accès sera suspendu sans régularisation.
    </div>
  )
}
