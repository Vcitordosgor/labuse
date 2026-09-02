// ADMIN-1 (AD2) — page « Données » : UNE page pour la question « mes données sont-elles à jour ? ».
// Fusionne les anciennes pages Sources, Cron/Horloge, Flux/Circuit et l'Agent de veille en TROIS
// onglets — Catalogue (l'état, une ligne par source), Circuit (la fourmilière + la garde), Horloge
// (les jobs planifiés). Rien n'est réécrit : chaque onglet réutilise le composant EXISTANT
// (SourcesSection / FluxSection / CronSection). En tête, un bandeau « 3 gestes » condensé, commun
// aux trois onglets (injecter · calculer · basculer), lu du même endpoint /admin/flux que le Circuit.
import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { getAdminFlux } from '../../lib/api'
import { SourcesSection } from './Sources'
import { FluxSection } from './Flux'
import { CronSection } from './Cron'

type Onglet = 'catalogue' | 'circuit' | 'horloge'

// Bandeau « 3 gestes » condensé (AD2.4) — résumé LU de /admin/flux (comptes), boutons → onglet Circuit
// où vivent les commandes réelles (Injecter/Calculer/Basculer, mécanique FLUX-1 inchangée).
function Gestes() {
  const flux = useQuery({ queryKey: ['admin-flux'], queryFn: getAdminFlux, refetchInterval: 60_000 })
  const c = flux.data?.flux.comptes
  const nv = c?.nouvelle_version ?? 0
  const recentes = c?.plus_recentes_que_run ?? 0
  const runs = flux.data?.bascule.runs ?? []
  const aBasculer = runs.filter((r) => !r.servi && r.complet).length
  const Geste = ({ n, titre, detail, tone }: { n: number; titre: string; detail: string; tone: 'warn' | 'off' }) => (
    <div className="flex items-center gap-2.5 rounded-lg border border-line bg-surface-2 px-3 py-2 text-[12.5px]">
      <span className={`flex h-[18px] w-[18px] items-center justify-center rounded-full font-mono text-[11px] font-bold ${tone === 'warn' ? 'bg-amber/15 text-amber' : 'bg-mint/10 text-mint'}`}>{n}</span>
      <span><b className="font-medium">{titre}</b> — <span className={tone === 'warn' ? 'text-amber' : 'text-txt-mut'}>{detail}</span></span>
    </div>
  )
  return (
    <div className="mb-4 flex flex-wrap items-center gap-2">
      <Geste n={1} titre="Injecter" tone={nv > 0 ? 'warn' : 'off'}
        detail={nv > 0 ? `${nv} nouvelle(s) version(s)` : 'rien à injecter'} />
      <span className="text-txt-dim">→</span>
      <Geste n={2} titre="Calculer" tone={recentes > 0 ? 'warn' : 'off'}
        detail={recentes > 0 ? `${recentes} source(s) plus récente(s) que le run` : 'run à jour'} />
      <span className="text-txt-dim">→</span>
      <Geste n={3} titre="Basculer" tone={aBasculer > 0 ? 'warn' : 'off'}
        detail={aBasculer > 0 ? `${aBasculer} run(s) prêt(s)` : 'rien à basculer'} />
      {/* RETOURS-8 (R4.3) — bouton « Ouvrir le Circuit → » retiré : l'onglet Circuit suffit. */}
    </div>
  )
}

export function DonneesSection() {
  const [onglet, setOnglet] = useState<Onglet>('catalogue')
  const Tab = ({ k, children }: { k: Onglet; children: React.ReactNode }) => (
    <button onClick={() => setOnglet(k)}
      className={`-mb-px border-b-2 px-0.5 pb-2.5 pt-2 text-[13.5px] transition-colors duration-quick ${
        onglet === k ? 'border-mint font-semibold text-mint' : 'border-transparent text-txt-mut hover:text-txt'}`}>
      {children}
    </button>
  )
  return (
    <>
      <Gestes />
      <div className="mb-4 flex gap-6 border-b border-line">
        <Tab k="catalogue">Catalogue</Tab>
        <Tab k="circuit">Circuit</Tab>
        <Tab k="horloge">Horloge</Tab>
      </div>
      {onglet === 'catalogue' && <SourcesSection />}
      {onglet === 'circuit' && <FluxSection />}
      {onglet === 'horloge' && <CronSection />}

      {/* AD2.8 — pied « Qui fait quoi » repris tel quel de la maquette. */}
      <div className="mt-4 rounded-xl border border-line px-4 py-3 text-[12.5px] leading-relaxed text-txt-mut">
        <b className="text-txt">Qui fait quoi :</b> l'<b className="text-txt">Horloge</b> (cron) sonne chaque nuit à 07:00 → elle réveille
        l'<b className="text-txt">agent de veille</b>, qui va lire chez chaque fournisseur et remplit la colonne <b className="text-txt">Amont</b> du Catalogue.
        S'il trouve du nouveau : notification + bouton <b className="text-txt">Injecter</b>. Vous seul cliquez — Injecter télécharge et charge (l'ingestion),
        puis <b className="text-txt">Calculer</b> refait les scores (Circuit), puis <b className="text-txt">Basculer</b> les met en service.
        « Relancer l'ingestion » relance la même commande que le cron (réparation). « Cadence attendue » sur une source manuelle n'appelle personne : c'est votre rappel.
      </div>
    </>
  )
}
