import { useMutation } from '@tanstack/react-query'
import { useEffect } from 'react'
import { verifProcedure, type VerifProcedure as VP } from '../../lib/api'
import { useApp } from '../../store/useApp'
import { ParcelInput } from '../ParcelInput'

// M41 Phase 2.6 — OUTIL « VÉRIF PROCÉDURE » : un IDU → la commune a-t-elle une procédure PLU en
// cours ? L'outil LIT le radar (point de calcul unique, mêmes libellés que la fiche) — il ne calcule
// rien. L'absence est DATÉE elle aussi. Jamais d'affirmation sur l'issue de la procédure.
// M60 P1d — PORTE depuis la fiche : le champ IDU s'AMORCE de selectedIdu (préservé par setModule).
export function VerifProcedure() {
  const selectedIdu = useApp((s) => s.selectedIdu)
  const m = useMutation({ mutationFn: (i: string) => verifProcedure(i.trim()) })
  const lancer = (i: string) => { if (i.trim().length >= 10) m.mutate(i) }
  useEffect(() => { if (selectedIdu) lancer(selectedIdu) }, [selectedIdu])   // porte fiche → amorce + run
  const d: VP | undefined = m.data
  const cons = d?.consequences

  return (
    <div data-verif-procedure className="flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto">
      <div className="flex flex-col gap-2 rounded-lg border border-line-2 bg-surface-2 p-3">
        <p className="text-[10.5px] leading-snug text-txt-mut">
          Une parcelle → la commune est-elle en procédure PLU, et qu’en découle-t-il
          pour la parcelle. Radar Sudocuh + registre curaté ; jamais l’issue de la procédure.
        </p>
        {/* RETOURS-13 R24 — la barre passe sur le MOTEUR UNIQUE (ParcelInput) : IDU 14, référence
            cadastrale courte (« BZ1065 », désambiguïsation par commune), adresse. Le champ maison qui
            n'acceptait que l'IDU brut est retiré (promesse T1 tenue sur TOUTES les barres). */}
        <ParcelInput dataAttr="verif-idu" withCarte={false} onPick={(i) => lancer(i)}
          placeholder="IDU, référence (ex. BZ1065) ou adresse" />
      </div>

      {m.isError && <div className="rounded-lg border border-st-ecartee/40 bg-st-ecartee/10 px-3 py-2 text-[11px] text-st-ecartee">Parcelle inconnue ou erreur.</div>}

      {d && (
        <div data-verif-result className="flex flex-col gap-2">
          <div className="text-[11px] text-txt-mut">
            {d.commune} · {d.idu}{d.tier_servi ? ` · tier ${d.tier_servi}` : ''} · consulté le {d.consulte_le}
          </div>

          {d.procedure_en_cours === true ? (
            <div className="rounded-lg border border-st-creuser/40 bg-st-creuser/10 px-3 py-2 text-[11.5px] text-txt">
              <div className="font-medium">▲ Procédure PLU en cours</div>
              <div className="mt-1">{d.synthese}</div>
              <div className="mt-1 text-[10px] text-txt-dim">
                Sourcé {d.source} · confiance {d.confiance} · constaté le {d.date_constat}
                {d.source_url && <> · <a href={d.source_url} target="_blank" rel="noreferrer" className="text-mint hover:underline">source ↗</a></>}
              </div>
              {cons?.veille_au && (
                <div className="mt-2 border-t border-line-2 pt-2 text-[11px]">
                  <span className="font-medium text-mint">Veille AU</span> — {cons.veille_au}
                </div>
              )}
              {cons?.sursis ? (
                <div className="mt-2 border-t border-line-2 pt-2 text-[11px]">
                  <span className="font-medium text-st-ecartee">Sursis à statuer</span> — {cons.sursis.texte}
                  <div className="mt-0.5 text-[10px] text-txt-dim">{cons.sursis.base_legale}</div>
                </div>
              ) : (
                <div className="mt-2 border-t border-line-2 pt-2 text-[10px] text-txt-dim">
                  Sursis à statuer : non servi (débat PADD non constaté à ce jour).
                </div>
              )}
            </div>
          ) : (
            <div className="rounded-lg border border-line-2 bg-surface-2 px-3 py-2 text-[11.5px] text-txt-mut">
              <span className="mr-1">🕓</span>{d.message}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
