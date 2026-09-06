import { useQuery } from '@tanstack/react-query'
import { useRef, useState } from 'react'
import { motSimulPluProcedures, motSimulPluZones, type SimulPluProcedure } from '../../lib/api'
import { useApp } from '../../store/useApp'
import { Loading } from '../Loading'
import { CommuneScope } from './ModulePanel'
import { M15 } from './moteurs'
import { VerifProcedure } from './VerifProcedure'

// M137-Q — VOIE UNIFIÉE « Procédure & changement PLU ». Relie les deux écrans qui s'ignoraient :
//   1. en tête, les communes RÉELLEMENT en procédure (radar Sudocuh, point de calcul unique) ;
//   2. « Simuler ce que ça changerait → » lance la simulation AU→U préremplie SUR CETTE COMMUNE ;
//   3. la simulation reste libre pour toute commune — hors procédure, l'écran le DIT (hypothétique).
// La commune est un choix EXPLICITE (CommuneScope), plus hérité muettement du filtre global.
// Aucun calcul touché : VerifProcedure (parcelle) et M15 (simulation) sont réutilisés tels quels.

// O8(d) — l'état d'une procédure vient du backend en langage interne (« procédure Sudocuh sans suite
// connue — clôture probable »). On le reformule en français simple pour le client, sans changer le
// fond. On retire aussi la mention « (confiance …) » et le nom d'outil « Sudocuh ».
function etatClient(etat: string | null | undefined): string | null {
  if (!etat) return null
  const t = etat.toLowerCase()
  if (t.includes('sans suite') || t.includes('clôture probable') || t.includes('cloture probable')) {
    return 'Procédure lancée mais sans suite connue — probablement abandonnée. À vérifier en mairie.'
  }
  // sinon, on nettoie a minima : on masque le nom d'outil interne et la parenthèse de confiance.
  return etat.replace(/\s*\(confiance[^)]*\)/i, '').replace(/\bSudocuh\b/gi, '').replace(/\s{2,}/g, ' ').trim()
}

export function ProcedureChangement() {
  const globalCommune = useApp((s) => s.commune)
  // périmètre explicite de l'outil — amorcé sur le filtre global, puis piloté ICI.
  const [commune, setCommune] = useState<string | null>(globalCommune)
  const [openProc, setOpenProc] = useState(false)   // §5 — bandeau replié par défaut (compact)
  // OUTILS-FIX-2 C1 — deux onglets (même patron que Scan patrimoine) : « Par parcelle » (VerifProcedure)
  // et « Simuler l'ouverture » (radar procédures + simulation AU→U). Contenu de chaque onglet inchangé.
  const [tab, setTab] = useState<'parcelle' | 'simuler'>('parcelle')
  const proc = useQuery({ queryKey: ['simulplu-procedures'], queryFn: motSimulPluProcedures })
  // O8(b) — zones AU réellement proposées pour la commune choisie (dynamique, jamais figé au front).
  const zonesQ = useQuery({
    queryKey: ['simulplu-zones', commune],
    queryFn: () => motSimulPluZones(commune),
    enabled: !!commune,
  })
  const zonesAU = (zonesQ.data ?? []).map((z) => z.zone)
  const communes = proc.data?.communes ?? []
  const enProcedure: SimulPluProcedure | undefined = commune
    ? communes.find((c) => c.commune === commune)
    : undefined
  const simRef = useRef<HTMLDivElement>(null)

  const choisir = (c: string) => {
    setCommune(c)
    // laisser le rendu se faire puis amener la simulation à l'écran
    requestAnimationFrame(() => simRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }))
  }

  return (
    <div data-plu-procchg className="flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto">
      {/* OUTILS-FIX-2 C1 — onglets (même patron que Scan patrimoine possède/construit). */}
      <div className="flex gap-6 border-b border-line-2" role="tablist">
        {([['parcelle', 'Par parcelle'], ['simuler', "Simuler l’ouverture"]] as const).map(([k, label]) => (
          <button key={k} data-procchg-tab={k} role="tab" aria-selected={tab === k} onClick={() => setTab(k)}
            className={`-mb-px whitespace-nowrap border-b-2 pb-2 pt-1 text-[13px] transition-colors ${tab === k ? 'border-mint font-medium text-mint' : 'border-transparent text-txt-mut hover:text-txt'}`}>
            {label}
          </button>
        ))}
      </div>

      {/* ONGLET « Simuler l'ouverture » — 1. COMMUNES EN PROCÉDURE (radar) — §5 : REPLIÉES sous un
          BANDEAU cliquable « ⚠ N communes en procédure PLU » (compact par défaut). Le déplié garde TOUT
          (type/état, date, source, bouton Simuler). 0 procédure → message factuel, pas de bandeau. */}
      {tab === 'simuler' && (
      <div className="flex flex-col gap-1.5">
        {proc.isLoading && <div className="py-3"><Loading accent="mint" label="Radar procédures…" /></div>}
        {proc.isError && (
          <div className="rounded-lg border border-st-ecartee/40 bg-st-ecartee/10 px-3 py-2 text-[11px] text-st-ecartee">
            Radar indisponible.
          </div>
        )}
        {proc.data && communes.length === 0 && (
          <div className="rounded-lg border border-line-2 bg-surface-2 px-3 py-2 text-[11px] text-txt-mut">
            Aucune procédure PLU lourde active au radar à ce jour.
          </div>
        )}
        {communes.length > 0 && (
          <>
            <button data-procchg-banner aria-expanded={openProc} onClick={() => setOpenProc((o) => !o)}
              className="flex w-full items-center gap-2 rounded-lg border border-st-creuser/40 bg-st-creuser/[0.08] px-3 py-2 text-left transition-colors duration-quick hover:bg-st-creuser/[0.14]">
              <span className="shrink-0 text-st-creuser">⚠</span>
              {/* LOT4 — bandeau sur UNE seule ligne : le libellé ne se coupe plus (whitespace-nowrap),
                  le toggle reste à droite et ne pousse pas le texte à la ligne (shrink-0). */}
              <span className="truncate whitespace-nowrap text-[12px] font-medium text-txt-hi">
                {communes.length} commune{communes.length > 1 ? 's' : ''} en procédure PLU
              </span>
              <span className="ml-auto shrink-0 whitespace-nowrap text-[11px] text-st-creuser">{openProc ? 'Replier ▾' : 'Détail ▸'}</span>
            </button>
            {openProc && communes.map((c) => (
              <div key={c.insee} data-procchg-commune={c.commune}
                className="ml-2 flex flex-col gap-1 rounded-lg border border-st-creuser/40 bg-st-creuser/[0.08] px-3 py-2">
                <div className="flex items-center gap-2">
                  <span className="text-[12px] font-medium text-txt-hi">{c.commune}</span>
                  <span className="rounded-full bg-st-creuser/15 px-2 py-0.5 text-[10px] text-st-creuser">▲ {c.type}</span>
                </div>
                <div className="text-[10.5px] leading-snug text-txt-mut">{etatClient(c.etat)}</div>
                <div className="text-[9.5px] text-txt-dim">
                  Prescrite le {c.date_acte} · sourcé {c.source} · constaté le {c.date_constat}
                  {c.source_url && <> · <a href={c.source_url} target="_blank" rel="noreferrer" className="text-mint hover:underline">source ↗</a></>}
                </div>
                <button data-procchg-simuler onClick={() => choisir(c.commune)}
                  className="mt-0.5 self-start rounded-md border border-mint/50 bg-mint/15 px-2.5 py-1 text-[11px] font-medium text-mint transition-colors duration-quick hover:bg-mint/25">
                  Simuler ce que ça changerait →
                </button>
              </div>
            ))}
          </>
        )}
      </div>
      )}

      {/* ONGLET « Par parcelle » — « Cette parcelle est-elle concernée par une procédure ? »
          (IDU / adresse) = VerifProcedure, au grain parcelle (sursis, veille AU). Contenu inchangé. */}
      {tab === 'parcelle' && (
      <div data-procchg-entree="1" className="flex flex-col gap-1.5">
        <div className="text-[12px] font-medium text-txt-hi">
          Cette parcelle est-elle concernée par une procédure ?
        </div>
        <p className="text-[10.5px] leading-snug text-txt-mut">
          Saisissez un IDU ou une adresse — sursis à statuer, veille AU.
        </p>
        <VerifProcedure />
      </div>
      )}

      {/* ONGLET « Simuler l'ouverture » (suite) — « Simuler l'ouverture d'une zone AU ». Périmètre
          explicite (CommuneScope) + statut procédure, puis la simulation M15 (réutilisée, calcul intact). */}
      {tab === 'simuler' && (
      <div ref={simRef} data-procchg-entree="2" className="flex flex-col gap-1.5 border-t border-line-2 pt-2">
        <div className="text-[12px] font-medium text-txt-hi">
          Simuler l’ouverture d’une zone AU
        </div>
        <CommuneScope commune={commune} onChange={setCommune} />
        {/* RETOURS-14 S10 — UN SEUL accordéon « Attention (2) », replié, qui contient LES DEUX
            paragraphes (périmètre/simulation + recalcul à blanc) ; le fait « procédure en
            cours » (quand il existe) reste visible d'emblée, hors accordéon. */}
        {commune && enProcedure && (
          <div data-procchg-statut="en_cours" className="rounded-lg border border-st-creuser/40 bg-st-creuser/[0.08] px-3 py-2 text-[11px] text-txt">
            <b className="text-st-creuser">▲ {commune}</b> est en {enProcedure.type} (prescrite le {enProcedure.date_acte}).
            La simulation montre ce que la bascule AU→U y changerait.
          </div>
        )}
        <details data-procchg-attention className="rounded-lg border border-line-2 bg-surface-2 px-3 py-1.5 text-[11px] text-txt-mut">
          <summary className="cursor-pointer list-none py-0.5 font-medium text-txt marker:hidden">
            Attention ({commune && enProcedure ? 1 : 2}) ▾</summary>
          {!(commune && enProcedure) && (commune ? (
            <p data-procchg-statut="hypothetique" className="mt-1">
              <b className="text-txt">Aucune procédure PLU en cours</b> à {commune} au radar —
              <b> simulation hypothétique</b> (« et si cette zone AU passait en U ? »).
            </p>
          ) : (
            <p data-procchg-statut="ile" className="mt-1">
              Périmètre : <b className="text-txt">toute l'île</b> — simulation hypothétique, aucune procédure ciblée.
              Choisissez une commune ci-dessus pour la relier à sa procédure.
            </p>
          ))}
          <p className="mt-1">Recalcul <b className="text-txt">à blanc</b> — rien n'est persisté. SDP estimée par
            <b className="text-txt"> analogie</b> aux parcelles U de la commune (méthode affichée).
            Le vrai recalcul règlementaire = prochain cycle.</p>
        </details>

        {/* O8(b) — les zones AU réellement disponibles pour la commune sont listées explicitement à
            l'écran (dynamique, depuis le backend). Ex. Saint-Paul : AUc, AUs. */}
        {commune && zonesAU.length > 0 && (
          <div data-procchg-zones-au className="text-[10.5px] leading-snug text-txt-mut">
            Zones AU de <b className="text-txt">{commune}</b> :{' '}
            <span className="font-mono text-mint">{zonesAU.join(', ')}</span>
          </div>
        )}

        {/* SIMULATION (M15 réutilisé, périmètre = choix explicite) */}
        <div className="flex flex-col gap-2">
          <M15 communeOverride={commune} />
        </div>
      </div>
      )}
    </div>
  )
}
