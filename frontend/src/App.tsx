import { useMutation, useQuery } from '@tanstack/react-query'
import { lazy, Suspense, useEffect, useRef, useState } from 'react'
import { createProjet, getPrefsCarte, postPrefsCarte } from './lib/api'
import { AvisIA } from './components/AvisIA'
import { Squelette } from './components/Loading'
import { Bouton } from './components/ui/Bouton'
import { SourceDrawer } from './components/fiche/SourceDrawer'
import { Header } from './components/header/Header'
import { LeftPanel } from './components/panel/LeftPanel'
import { Rail } from './components/Rail'
import { filtersFromHash, filtersToHash, hasOpinion, resumeCriteres } from './lib/filters'
import { CLIENT } from './lib/strings'
import { SCORE_TIP } from './lib/status'
import { useApplySearch } from './lib/useApplySearch'
import { MODULES } from './components/outils/registry'   // GB-059 : valider #m= contre le registre
import { TraceTiroir } from './lib/trace'
import { EMPTY_FILTERS, useApp } from './store/useApp'
import { signalOutil, startHeartbeat } from './lib/usage'   // DASHBOARD-V1 · D1 — capteurs

// M-V V3 — code-splitting maplibre : MapView et TimeMachine chargent maplibre-gl (~800 kB), inutile
// au premier écran (login, fiche directe, outils). On les charge à la DEMANDE (import dynamique),
// derrière un <Suspense> avec un état de chargement propre (jamais d'écran blanc). Le chunk
// maplibre sort ainsi du graphe initial (cf. manualChunks conservé dans vite.config).
const MapView = lazy(() => import('./components/map/MapView').then((m) => ({ default: m.MapView })))
// RADAR-2 (Lot 1) — le hub Radar plein écran SANS carte : deux portes (Radar / Veille), l'écran Radar
// (liste 560 px + marché) et les trois écrans Veille. Remplace l'ancien RadarView (carte) et SurveillancePanel.
const RadarHub = lazy(() => import('./components/radar/RadarHub').then((m) => ({ default: m.RadarHub })))
const TimeMachine = lazy(() => import('./components/outils/TimeMachine').then((m) => ({ default: m.TimeMachine })))

// CARTE-VITESSE-2 lot B (R2) — TOUT ce qui n'est pas sur le chemin du PREMIER écran (le shell +
// la carte) sort du chunk `index` initial et se charge à la DEMANDE. Avant : ModulePanel importait
// statiquement l'arbre des 16 outils (moteurs, EtudeZone, blocB, TaxeAmenagement, Gabarit,
// Communes, Successions, Blocs, Plu, ProspectionSolaire…) + Fiche/ContextePanel/les vues plein
// écran → 1,04 Mo dans `index`, ~4 s de long-tasks avant que les tuiles ne partent. Chaque panneau
// ci-dessous est monté SOUS CONDITION (view/module/état) → son chunk n'arrive que quand on l'ouvre,
// derrière un <Suspense>. Le rendu est identique ; seul le moment du téléchargement change.
const Fiche = lazy(() => import('./components/fiche/Fiche').then((m) => ({ default: m.Fiche })))
const Kanban = lazy(() => import('./components/crm/Kanban').then((m) => ({ default: m.Kanban })))
const SourcesPage = lazy(() => import('./components/sources/SourcesPage').then((m) => ({ default: m.SourcesPage })))
const ProjetsPanel = lazy(() => import('./components/projets/ProjetsPanel').then((m) => ({ default: m.ProjetsPanel })))
const ParcoursTinder = lazy(() => import('./components/projets/ParcoursTinder').then((m) => ({ default: m.ParcoursTinder })))
const ContextePanel = lazy(() => import('./components/contexte/ContextePanel').then((m) => ({ default: m.ContextePanel })))
const ComparePanel = lazy(() => import('./components/compare/ComparePanel').then((m) => ({ default: m.ComparePanel })))
const CommunesTablePanel = lazy(() => import('./components/outils/Communes').then((m) => ({ default: m.CommunesTablePanel })))
const EvolutionTablePanel = lazy(() => import('./components/outils/Communes').then((m) => ({ default: m.EvolutionTablePanel })))
const RadarTablePanel = lazy(() => import('./components/outils/Communes').then((m) => ({ default: m.RadarTablePanel })))
const CopiloteView = lazy(() => import('./components/copilote/CopiloteView').then((m) => ({ default: m.CopiloteView })))
const ModulePanel = lazy(() => import('./components/outils/ModulePanel').then((m) => ({ default: m.ModulePanel })))
const AdminView = lazy(() => import('./components/admin/AdminView').then((m) => ({ default: m.AdminView })))

// État de chargement de la zone carte pendant que le chunk maplibre arrive (pas d'écran blanc).
// DA — squelette unique (plus de spinner rotatif), on garde le conteneur flex-1.
function MapLoading() {
  return (
    <div className="relative flex min-h-0 flex-1 bg-bg">
      <Squelette bloc label="Chargement de la carte" />
    </div>
  )
}

// CARTE-VITESSE-2 lot B — fallback d'un panneau/vue chargé à la demande (chunk en vol). Squelette
// sobre, jamais d'écran blanc, cf. MapLoading. Pour les overlays furtifs (drawers/modales) on passe
// plutôt `fallback={null}` (rien à montrer tant que le chunk n'est pas là).
function PanelLoading() {
  return (
    <div className="flex min-h-0 flex-1 bg-bg">
      <Squelette bloc label="Chargement…" />
    </div>
  )
}

// R2/V3 : la restitution du copilote — compteur animé + top cliquables. En mode PROJET, chaque
// parcelle porte son « pourquoi » (moteur) et l'utilisateur peut ENREGISTRER + exporter le PDF.
function IaRestitution() {
  const { iaRestitution, setIaRestitution, select, chercherParCapacite, togglePanel, selectedIdu, setVerdict, setOpenProjet } = useApp()
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
    // M120 — chemin legacy (restitution copilote v1, `projet` jamais renseigné depuis M118) : un
    // projet se crée par son CADRAGE (parcours Projets), plus par une fiche. Conservé compilable.
    mutationFn: () => createProjet({ cadrage: {}, nom: iaRestitution!.projet!.nom }),
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
      <AvisIA className="mb-2 border-[#2E6B4F]/70 bg-[#0c1611] text-txt-mut" />
      <div className="flex items-start justify-between">
        <p className="text-sm text-txt">
          <span data-ia-count className="font-display text-xl font-bold text-mint">{count.toLocaleString('fr-FR')}</span>{' '}
          {iaRestitution.phrase}
        </p>
        <button onClick={() => setIaRestitution(null)} className="ml-2 text-txt-dim hover:text-txt" aria-label="Fermer le résultat">✕</button>
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
                <span className="min-w-0 flex-1 truncate font-mono text-[11.5px] font-medium tracking-tight text-txt-hi">{t.idu}</span>
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
                title={t.mult_v2 != null ? 'position au classement (probabilité de vente sous 1 an)' : SCORE_TIP.q}>
                #{i + 1}
              </span>
              <span className="block truncate font-mono text-[10.5px] tracking-tight text-txt-hi">{t.idu}</span>
              <span className="block truncate text-[11px] text-txt-dim">{t.commune}</span>
            </button>
          ))}
        </div>
      )}

      {projet && (
        <div className="mt-3 flex items-center gap-2 border-t border-line-2 pt-2.5">
          {projetId == null ? (
            <Bouton niveau="primaire" ton="vert" data-projet-enregistrer onClick={() => enregistrer.mutate()} disabled={enregistrer.isPending}>
              {enregistrer.isPending ? 'Enregistrement…' : `Enregistrer « ${projet.nom} »`}
            </Bouton>
          ) : (
            <>
              <span data-projet-enregistre className="rounded-lg bg-[#12241a] px-3 py-1.5 text-[11px] font-medium text-mint"
                title={reprisExistant ? 'Un projet identique existait déjà — repris (pas de doublon)' : undefined}>
                {reprisExistant ? '✓ Projet identique repris' : '✓ Projet enregistré'}
              </span>
              <button data-projet-ouvrir-kanban onClick={() => { setOpenProjet({ id: projetId, nom: projet.nom }); setIaRestitution(null) }}
                className="rounded-lg border border-mint/40 bg-mint/10 px-3 py-1.5 text-[11px] font-medium text-mint hover:bg-mint/20">
                Ouvrir le projet →
              </button>
              {/* PROJETS-CRM-FIX-1 (lot 2) — bouton « PDF » retiré (2ᵉ instance, strip post-création) :
                  /projets/{id}/export.pdf est retiré (410). Plus de lien mort. */}
              <button onClick={() => { setOpenProjet(null); setIaRestitution(null) }}
                className="ml-auto text-[11px] text-txt-mut hover:text-txt-hi">
                Mes projets →
              </button>
            </>
          )}
        </div>
      )}
      {/* FAISABILITE-1 (lot C) — le programme du projet est TRADUIT en filtre Capacité (SDP restante /
          logements) puis la carte s'ouvre sur le panneau Filtre → « Par critères » (retiré) devient le
          groupe Capacité, global. Bouton secondaire VERT (aucun modèle d'IA appelé). */}
      {projet?.programme && (
        <Bouton niveau="secondaire" ton="vert" data-projet-m22 className="mt-2 w-full"
          onClick={() => chercherParCapacite(projet.programme as Record<string, number>)}>
          Chercher des parcelles pour ce programme (filtre Capacité)
        </Bouton>
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
  const { view, selectedIdu, select, setView, filters, setFilters, zone, setZone, module, setModule, setFlyTo, flyTo, commune, setCommune, verdict, setVerdict, outilsOpen, parcours, setMsel, setPermitToOpen, setIaRestitution, compareOpen, contexteCommune, setContexteCommune, togglePanel, setTuyauActives, toggleTuyau } = useApp()

  // Hook d'auto-QA (stable, sans effet produit) : sélection directe d'une parcelle / d'une vue.
  // RECETTE-10 — + setContexteCommune / togglePanel / setFilters exposés pour piloter les captures
  // (fiche commune, volet Résultats, mode analyse) ; aucun effet produit (mêmes actions que l'UI).
  // COUCHES-RECETTE-1 — + setTuyauActives / toggleTuyau pour piloter panneau ET légende dans les captures.
  useEffect(() => {
    ;(window as unknown as Record<string, unknown>).__labuse = { select, setView, setZone, setModule, setFlyTo, setCommune, setVerdict, setMsel, setPermitToOpen, setIaRestitution, setContexteCommune, togglePanel, setFilters, getFilters: () => filters, setTuyauActives, toggleTuyau }
  }, [select, setView, setZone, setModule, setFlyTo, setCommune, setVerdict, setMsel, setPermitToOpen, setIaRestitution, setContexteCommune, togglePanel, setFilters, filters, setTuyauActives, toggleTuyau])

  // DASHBOARD-V1 · D1 — capteurs d'usage (Tour de contrôle) : heartbeat de session au boot,
  // ouverture d'outil (module) et changement de vue. Fire-and-forget, dédoublonné dans usage.ts —
  // aucun poids perceptible, aucune erreur possible côté client.
  useEffect(() => { startHeartbeat() }, [])
  useEffect(() => { if (module) signalOutil(module) }, [module])
  useEffect(() => { signalOutil(`vue:${view}`) }, [view])

  // COMPTE-2 (Lot 6) — MÉMOIRE DU COMPTE : le fond de carte + les couches actives vivent EN BASE (plus
  // seulement en localStorage) → on les retrouve en changeant de poste. Hydratation au boot, puis
  // enregistrement (débounce) à chaque changement. Best-effort : non connecté / erreur = on continue.
  const basemap = useApp((s) => s.basemap)
  const layers = useApp((s) => s.layers)
  const appliquerPrefsCarte = useApp((s) => s.appliquerPrefsCarte)
  const prefsCarteReady = useRef(false)
  useEffect(() => {
    let annule = false
    getPrefsCarte()
      .then((p) => { if (!annule) appliquerPrefsCarte(p) })
      .catch(() => { /* non connecté / indisponible : la carte reste en session */ })
      .finally(() => { if (!annule) prefsCarteReady.current = true })
    return () => { annule = true }
  }, [appliquerPrefsCarte])
  useEffect(() => {
    if (!prefsCarteReady.current) return              // pas avant l'hydratation (sinon on écrase la base)
    const t = setTimeout(() => { postPrefsCarte({ basemap, couches: layers as unknown as Record<string, boolean> }).catch(() => {}) }, 800)
    return () => clearTimeout(t)
  }, [basemap, layers])

  // URL partageable : filtres + zone + commune sérialisés dans le hash (#f=…&c=…). Lecture au
  // chargement, écriture à chaque changement (replaceState : pas de pollution de l'historique).
  useEffect(() => {
    const hash = window.location.hash          // lu AVANT toute écriture (l'effet d'écriture suit)
    const parsed = filtersFromHash(hash)
    if (parsed) {
      const merged = { ...EMPTY_FILTERS, ...parsed.filters }
      // FILTRE (23/08/2026) — la section « Le bien » a quitté le panneau : on NE restaure JAMAIS ses 3
      // facettes depuis l'URL (droitsResiduels · proprietaireType 'public' · signal 'assemblage'), sinon
      // un utilisateur qui les avait cochées avant le retrait garderait un filtre ACTIF sans aucun
      // contrôle pour le décocher. Le backend reste servi (deep-link API) ; le Copilote garde 'assemblage'
      // (il applique setFilters en direct, hors de ce chemin de restauration d'URL).
      merged.droitsResiduels = []
      merged.proprietaireType = merged.proprietaireType.filter((x) => x !== 'public')
      merged.signaux = merged.signaux.filter((x) => x !== 'assemblage')
      // droitsResiduels / proprietaireType 'public' sont des critères d'OPINION : filtersFromHash avait
      // donc pu allumer `analyseLabuse` (hasOpinion) À CAUSE d'eux. Après leur retrait, on RE-DÉRIVE
      // l'analyse sur les critères RESTANTS — sinon l'analyse resterait allumée « à cause » d'une facette
      // désormais invisible (état orphelin). On préserve un `al=1` explicite (analyse voulue à la main).
      merged.analyseLabuse = /(?:^|[#&])al=1(?:$|&)/.test(hash) || hasOpinion(merged)
      setFilters(merged)
      if (parsed.zone) setZone(parsed.zone)
      // M55-D stage 4 : interrupteur allumé (lien portant un critère d'opinion, ex. un tier) ⇒ on
      // AFFICHE l'analyse (verdict) — l'interrupteur et le regard sur la carte sont la même chose.
      // M55-M point 3 : au rechargement, le snapshot de session est perdu — on RÉAMORCE le récap du
      // bandeau depuis les filtres RESTAURÉS, qui SONT ceux du run (persistés en URL, aucune
      // divergence possible à cet instant). L'invariant tient : dès qu'un filtre diverge en session,
      // analyseRecap reste figé (jamais réécrit hors lancer()).
      if (merged.analyseLabuse) {
        setVerdict(true)
        useApp.getState().setAnalyseRecap(resumeCriteres(merged, CLIENT.signaux.labels, Infinity))
      }
    }
    const p = new URLSearchParams(hash.replace(/^#/, ''))
    const c = p.get('c')
    if (c) setCommune(decodeURIComponent(c))
    if (p.get('v') === '1') setVerdict(true)   // les liens de démo ouvrent verdict allumé
    const m = p.get('m')
    // GB-059 (FIX-C6) — ne poser le module que si la clé EXISTE au registre (MODULES, alias
    // hidden compris). Une clé inconnue dans #m= (faute, casse, injection) laissait `module`
    // truthy alors que ModulePanel `MODULES.find` renvoyait undefined → LeftPanel démonté ET
    // panneau vide = colonne gauche blanche muette. Clé invalide → on ignore (état d'accueil).
    if (m && MODULES.some((mod) => mod.key === m)) setModule(m)
    // RADAR-CATÉGORIE (T1) — Radar n'est plus un module d'outil : #radar=1 (ou l'ancien #m=radar,
    // rétro-compat des liens) ouvre la catégorie plein écran.
    if (p.get('radar') === '1' || m === 'radar') useApp.getState().openRadar()
    // GB-032 — FICHE PARTAGEABLE : l'idu sélectionné est sérialisé dans le hash (#idu=…) et réhydraté
    // au boot → une URL de fiche partagée rouvre la MÊME fiche (les deep-links outil/filtres l'étaient
    // déjà, la fiche non). `select` déclenche le fetch parcelle ; la vue par défaut « cartes » l'affiche.
    const pidu = p.get('idu')
    if (pidu && /^[0-9A-Za-z]{10,20}$/.test(pidu)) select(pidu)
    // M104 — lien profond des notifications de secteur (#surveillance=parcelles|secteurs|criteres) :
    // ouvre la section unifiée sur le bon volet (aucun lien mort).
    const sv = p.get('surveillance')
    if (sv) useApp.getState().openSurveillance(sv === 'parcelles' || sv === 'criteres' ? sv : 'secteurs')
    // DASHBOARD-V1 — deep-link de la Tour de contrôle (#admin=1) ; la garde reste au backend.
    if (p.get('admin') === '1') setView('admin')
    // (Alias d'URL #pg=vues / pg=segments retiré avec le spin-off « Vues » — M12 Lot C-bis.)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])
  useEffect(() => {
    let h = filtersToHash(filters, zone)
    const add = (kv: string) => { h = (h ? `${h}&` : '#f=1&') + kv }
    if (commune) add(`c=${encodeURIComponent(commune)}`)
    if (verdict) add('v=1')
    if (module) add(`m=${module}`)
    if (selectedIdu) add(`idu=${selectedIdu}`)   // GB-032 — fiche partageable/réhydratable
    if (view === 'admin') add('admin=1')         // DASHBOARD-V1 — la Tour de contrôle survit au reload
    if (view === 'radar') add('radar=1')         // RADAR-CATÉGORIE (T1) — la catégorie survit au reload
    window.history.replaceState(null, '', h || window.location.pathname + window.location.search)
  }, [filters, zone, module, commune, verdict, view, selectedIdu])


  // DASHBOARD-V1 — la Tour de contrôle est PLEIN ÉCRAN (maquette : son propre rail + sections),
  // elle remplace tout le shell client ; « Ouvrir l'app cliente → » (pied de rail admin) revient.
  if (view === 'admin') {
    return (
      <div className="flex h-screen w-screen overflow-hidden bg-bg font-sans text-txt">
        <Suspense fallback={<PanelLoading />}><AdminView /></Suspense>
        <Toast />
        <TraceTiroir />
      </div>
    )
  }

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-bg font-sans text-txt">
      {/* CIRCUIT-1 lot 7.2 — le tiroir de trace (un seul, admin, invisible traçage éteint). */}
      <TraceTiroir />
      <Rail />
      <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
        <CompteBandeau />
        <Header />
        <div className="relative flex min-h-0 flex-1 overflow-hidden">
          {view === 'cartes' && (
            <>
              {/* P1 : quand le tiroir Outils est ouvert, il REMPLACE le panneau Cartes (COUCHES/
                  résultats) — la carte reste derrière. Un seul panneau gauche à la fois.
                  CARTE-VITESSE-2 lot B : ModulePanel est chargé à la demande (chunk des 16 outils
                  hors du graphe initial) → Suspense avec squelette de panneau. */}
              {outilsOpen ? null : module ? <Suspense fallback={<PanelLoading />}><ModulePanel /></Suspense> : parcours ? null : <LeftPanel />}
              <Suspense fallback={<MapLoading />}>
                {/* M70 décision 11 (bug 10) — TimeMachine centrée sur LA parcelle : le bouton
                    « 1950 » de la fiche pose flyTo{center: coords} avant setModule('temps') ; on le
                    transmet (MapView n'est pas monté ici, flyTo persiste). Sans parcelle → vue large. */}
                {module === 'temps' ? <TimeMachine center={flyTo?.center ?? null} /> : <MapView />}
              </Suspense>
              {parcours && <Suspense fallback={null}><ParcoursTinder /></Suspense>}
              {/* RV2-V3 — la Veille a QUITTÉ l'overlay de droite : c'est désormais une catégorie plein
                  écran (view === 'veille', montée plus bas), au patron Radar. */}
              {/* M55-L point 9 : le comparateur s'ouvre aussi depuis l'outil « Comparer » (Outils),
                  donc SANS parcelle pré-sélectionnée → on rend le panneau dès `compareOpen`
                  (ComparePanel gère l'état vide). */}
              {compareOpen && <Suspense fallback={null}><ComparePanel /></Suspense>}
              {/* §4 — les modales de l'outil « Communes » (table des 24, Évolution, Radar) ne se
                  rendent que si module==='communes' ET leur drapeau est ouvert. CARTE-VITESSE-2 lot
                  B : on GATE le montage sur module==='communes' pour que le chunk Communes n'arrive
                  qu'à l'ouverture de l'outil (le composant garde son propre `return null` interne). */}
              {module === 'communes' && (
                <Suspense fallback={null}>
                  <CommunesTablePanel />
                  {/* RETOURS-13 R13 / RETOURS-14 S1 — deux tableaux, deux modales, deux noms. */}
                  <EvolutionTablePanel />
                  <RadarTablePanel />
                </Suspense>
              )}
              {/* DENSIFIER-PLI (PISCINES-2 Lot B) — le grand tableau « Densifier l'existant » est retiré :
                  l'outil est plié dans le filtre Capacité (« Déjà bâti » + « SDP restante »). */}
            </>
          )}
          {/* RADAR-2 (Lot 1) — le hub Radar plein écran (SANS carte) : deux portes (Radar / Veille),
              l'écran Radar (liste + marché) et les trois écrans Veille. La Veille n'a plus d'entrée de
              rail ni de carte : elle vit derrière la porte « Veille » du hub. */}
          {view === 'radar' && (
            <Suspense fallback={<PanelLoading />}>
              <RadarHub />
            </Suspense>
          )}
          {view === 'crm' && <Suspense fallback={<PanelLoading />}><Kanban /></Suspense>}
          {view === 'sources' && <Suspense fallback={<PanelLoading />}><SourcesPage /></Suspense>}
          {view === 'projets' && <Suspense fallback={<PanelLoading />}><ProjetsPanel /></Suspense>}
          {view === 'copilote' && <Suspense fallback={<PanelLoading />}><CopiloteView /></Suspense>}
          {/* RADAR-CATÉGORIE (T3) — en vue Radar, la fiche du BIEN (overlay RadarView) est maître ;
              le clic-pin surligne la parcelle mais n'ouvre PAS la fiche parcelle. « Ouvrir la fiche
              parcelle → » bascule d'abord sur 'cartes', où la fiche s'affiche normalement.
              CARTE-VITESSE-2 lot B : Fiche (tout son arbre constructibilité/faisabilité) chargée à
              la demande — overlay, fallback null (la fiche a ses propres squelettes internes). */}
          {selectedIdu && view !== 'sources' && view !== 'radar' && (
            <Suspense fallback={null}><Fiche idu={selectedIdu} /></Suspense>
          )}
          {contexteCommune && <Suspense fallback={null}><ContextePanel /></Suspense>}
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
 *  la session meurt côté serveur, ce bandeau n'a donc jamais à la dire. Session locale (dev) : rien. */
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
