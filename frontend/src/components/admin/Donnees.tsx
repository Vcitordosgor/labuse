// ADMIN-1 (AD2) → DONNEES-2 — page « Données » : UNE page pour la question « mes données sont-elles
// à jour ? ». QUATRE onglets. Le premier, MISE À JOUR (DONNEES-2, cf. maquette-admin-donnees-v2.html),
// est le cœur : trois étapes verticales (injecter · calculer · basculer), une action = un endroit.
// Les trois autres sont des VUES sans action de mise à jour — Catalogue (l'état, une ligne par source),
// Circuit (la fourmilière + la garde), CRON (les jobs planifiés). Chaque onglet réutilise le composant
// EXISTANT ; rien n'est réécrit. Le bandeau « 3 gestes » condensé a disparu : ses chiffres vivent
// désormais dans le badge de l'onglet Mise à jour et dans les étapes elles-mêmes.
import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { getAdminFlux, getAdminFluxRuns } from '../../lib/api'
import { MiseAJour } from './MiseAJour'
import { SourcesSection } from './Sources'
import { FluxSection } from './Flux'
import { CronSection } from './Cron'

type Onglet = 'maj' | 'catalogue' | 'circuit' | 'cron'

// en-tête de page (commun aux onglets) + badge de l'onglet Mise à jour : LU du même endpoint que le
// Circuit (/admin/flux) et des runs (/admin/flux/runs, rendu progressif). Le badge compte les ÉTAPES
// qui demandent une action (source à injecter · run en retard · run prêt à basculer).
function useMajEtat() {
  const flux = useQuery({ queryKey: ['admin-flux'], queryFn: getAdminFlux, refetchInterval: 60_000 })
  const runsQ = useQuery({ queryKey: ['admin-flux-runs'], queryFn: getAdminFluxRuns, refetchInterval: 60_000 })
  const d = flux.data
  const injectables = d ? d.flux.sources.filter((s) => s.dot === 'warn' && s.injectable).length : 0
  const plusRecentes = d?.flux.comptes.plus_recentes_que_run ?? 0
  const aBasculer = (runsQ.data?.runs ?? []).filter((r) => !r.servi && r.complet).length
  const aFaire = (injectables > 0 ? 1 : 0) + (plusRecentes > 0 ? 1 : 0) + (aBasculer > 0 ? 1 : 0)
  return { d, aFaire, nCatalogue: d?.flux.comptes.total ?? null }
}

export function DonneesSection() {
  const [onglet, setOnglet] = useState<Onglet>('maj')
  const { d, aFaire, nCatalogue } = useMajEtat()

  // en-tête « Mes données sont-elles à jour ? » (maquette v2) — run servi, garde, phrase surfaces.
  const run = d?.flux.run
  const coh = d?.coherence
  const nOk = coh?.checks.filter((c) => c.ok).length ?? 0
  const nTot = coh?.checks.length ?? 0
  const surfTotal = d?.flux.comptes.n_surfaces ?? 0
  const surfRun = coh?.n_surfaces ?? surfTotal
  const surfVivantes = Math.max(0, surfTotal - surfRun)
  const phraseSurfaces = surfVivantes > 0
    ? `${surfTotal} surfaces · ${surfRun} sur le run servi · ${surfVivantes} vivante${surfVivantes > 1 ? 's' : ''} (hors run)`
    : `${surfTotal} surfaces, toutes sur ce run`

  // RETOURS-9 (Q9) — onglet ACTIF = plein de sa couleur (vert, encre sombre).
  const Tab = ({ k, children, badge }: { k: Onglet; children: React.ReactNode; badge?: React.ReactNode }) => (
    <button onClick={() => setOnglet(k)} aria-pressed={onglet === k}
      className={`mb-1.5 flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-[13.5px] transition-colors duration-quick ${
        onglet === k ? 'bg-mint font-semibold text-mint-ink' : 'text-txt-mut hover:text-txt'}`}>
      {children}{badge}
    </button>
  )

  return (
    <>
      {/* en-tête de page (maquette v2) */}
      <div className="font-mono text-[10.5px] uppercase tracking-[0.26em] text-txt-dim">Admin · Données</div>
      <h1 className="mt-1.5 font-display text-[22px] font-semibold text-txt-hi">Mes données sont-elles à jour ?</h1>
      {run && (
        <div className="mt-1 text-[12.5px] text-txt-dim">
          Run servi <span className="font-mono text-mint">{run.label}</span>
          {run.calcule_le && <> · calculé le {new Intl.DateTimeFormat('fr-FR', { timeZone: 'Indian/Reunion', day: '2-digit', month: '2-digit' }).format(new Date(run.calcule_le))}</>}
          {nTot > 0 && <> · garde de cohérence <span className={nOk === nTot ? 'text-mint' : 'text-coral'}>{nOk}/{nTot} {nOk === nTot ? '✓' : '✕'}</span></>}
          {' · '}{phraseSurfaces}
        </div>
      )}

      <div className="mb-4 mt-4 flex gap-6 border-b border-line">
        <Tab k="maj" badge={aFaire > 0
          ? <span className="rounded-full bg-amber/15 px-1.5 py-px font-mono text-[11px] font-semibold text-amber">{aFaire}</span>
          : <span className="rounded-full bg-mint/10 px-1.5 py-px font-mono text-[11px] font-semibold text-mint">✓</span>}>Mise à jour</Tab>
        <Tab k="catalogue" badge={nCatalogue != null
          ? <span className="rounded-full bg-white/5 px-1.5 py-px font-mono text-[11px] text-txt-dim">{nCatalogue}</span>
          : undefined}>Catalogue</Tab>
        <Tab k="circuit">Circuit</Tab>
        <Tab k="cron">CRON</Tab>
      </div>

      {onglet === 'maj' && <MiseAJour />}
      {onglet === 'catalogue' && <SourcesSection />}
      {onglet === 'circuit' && <FluxSection />}
      {onglet === 'cron' && <CronSection />}

      {/* pied « Qui fait quoi » — commun aux onglets. RETOURS-9 Q6 : « Horloge » = CRON ; Q2.5 : le
          CRON ne sonne pas en local. */}
      <div className="mt-4 rounded-xl border border-line px-4 py-3 text-[12.5px] leading-relaxed text-txt-mut">
        <b className="text-txt">Qui fait quoi :</b> le <b className="text-txt">CRON</b> sonne chaque nuit à 07:00 → il réveille
        l'<b className="text-txt">agent de veille</b>, qui va lire chez chaque producteur et remplit la colonne <b className="text-txt">Amont</b> du Catalogue.
        S'il trouve du nouveau : notification + l'étape <b className="text-txt">Injecter</b> vous le propose. Vous seul cliquez — Injecter charge la version (l'ingestion),
        <b className="text-txt"> Calculer</b> refait les scores, <b className="text-txt">Basculer</b> les met en service. Rien n'est automatique.
        {' '}<b className="text-txt">En local, le CRON ne sonne pas</b> : cliquez <b className="text-txt">Vérifier toutes les sources</b> à l'étape 1.
      </div>

      {/* rappel des autres onglets (maquette v2) — vues, pas d'action de mise à jour */}
      <div className="mt-3 border-l-2 border-line pl-3 text-[12px] leading-relaxed text-txt-mut">
        <b className="text-txt-dim">Les autres onglets sont des vues.</b> <b className="text-txt">Catalogue</b> : une ligne par source (servi · amont · dernier passage · fraîcheur · alimente).
        {' '}<b className="text-txt">Circuit</b> : la fourmilière (sources → moteurs → surfaces) et les compteurs Radar — lecture seule, clic-surlignage.
        {' '}<b className="text-txt">CRON</b> : les jobs, dernier passage, prochain, « lancer maintenant ».
      </div>
    </>
  )
}
