import { useQuery } from '@tanstack/react-query'
import { useRef, useState } from 'react'
import { motSimulPluProcedures, type SimulPluProcedure } from '../../lib/api'
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

export function ProcedureChangement() {
  const globalCommune = useApp((s) => s.commune)
  // périmètre explicite de l'outil — amorcé sur le filtre global, puis piloté ICI.
  const [commune, setCommune] = useState<string | null>(globalCommune)
  const [openProc, setOpenProc] = useState(false)   // §5 — bandeau replié par défaut (compact)
  const proc = useQuery({ queryKey: ['simulplu-procedures'], queryFn: motSimulPluProcedures })
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
      {/* 1. COMMUNES EN PROCÉDURE (radar) — §5 : REPLIÉES sous un BANDEAU cliquable « ⚠ N communes en
          procédure PLU » (compact par défaut). Le déplié garde TOUT (type/état, date, source, bouton
          Simuler). 0 procédure → message factuel, pas de bandeau ; loading/erreur inchangés. */}
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
              <span className="text-st-creuser">⚠</span>
              <span className="text-[12px] font-medium text-txt-hi">
                {communes.length} commune{communes.length > 1 ? 's' : ''} en procédure PLU
              </span>
              <span className="ml-auto text-[11px] text-st-creuser">{openProc ? 'Replier ▾' : 'Voir le détail ▸'}</span>
            </button>
            {openProc && communes.map((c) => (
              <div key={c.insee} data-procchg-commune={c.commune}
                className="ml-2 flex flex-col gap-1 rounded-lg border border-st-creuser/40 bg-st-creuser/[0.08] px-3 py-2">
                <div className="flex items-center gap-2">
                  <span className="text-[12px] font-medium text-txt-hi">{c.commune}</span>
                  <span className="rounded-full bg-st-creuser/15 px-2 py-0.5 text-[10px] text-st-creuser">▲ {c.type}</span>
                </div>
                <div className="text-[10.5px] leading-snug text-txt-mut">{c.etat}</div>
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

      {/* 2. PÉRIMÈTRE EXPLICITE + statut procédure */}
      <div ref={simRef} className="flex flex-col gap-1.5 border-t border-line-2 pt-2">
        <CommuneScope commune={commune} onChange={setCommune} />
        {commune ? (
          enProcedure ? (
            <div data-procchg-statut="en_cours" className="rounded-lg border border-st-creuser/40 bg-st-creuser/[0.08] px-3 py-2 text-[11px] text-txt">
              <b className="text-st-creuser">▲ {commune}</b> est en {enProcedure.type} (prescrite le {enProcedure.date_acte}).
              La simulation montre ce que la bascule AU→U y changerait.
            </div>
          ) : (
            <div data-procchg-statut="hypothetique" className="rounded-lg border border-line-2 bg-surface-2 px-3 py-2 text-[11px] text-txt-mut">
              <span className="mr-1">🕓</span><b className="text-txt">Aucune procédure PLU en cours</b> à {commune} au radar —
              <b> simulation hypothétique</b> (« et si cette zone AU passait en U ? »).
            </div>
          )
        ) : (
          <div data-procchg-statut="ile" className="rounded-lg border border-line-2 bg-surface-2 px-3 py-2 text-[11px] text-txt-mut">
            Périmètre : <b className="text-txt">toute l'île</b> — simulation hypothétique, aucune procédure ciblée.
            Choisissez une commune ci-dessus pour la relier à sa procédure.
          </div>
        )}
      </div>

      {/* 3. SIMULATION (M15 réutilisé, périmètre = choix explicite) */}
      <div className="flex flex-col gap-2">
        <M15 communeOverride={commune} />
      </div>

      {/* 4. PARCELLE PRÉCISE (VerifProcedure réutilisé) — le grain parcelle : sursis, veille AU */}
      <details className="mt-1 border-t border-line-2 pt-2">
        <summary className="cursor-pointer text-[11px] text-txt-mut hover:text-txt">
          Vérifier une parcelle précise (sursis à statuer, veille AU) →
        </summary>
        <div className="mt-2">
          <VerifProcedure />
        </div>
      </details>
    </div>
  )
}
