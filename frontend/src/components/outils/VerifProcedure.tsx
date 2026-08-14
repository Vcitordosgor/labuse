import { useMutation } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { verifProcedure, type VerifProcedure as VP } from '../../lib/api'
import { useApp } from '../../store/useApp'

// M41 Phase 2.6 — OUTIL « VÉRIF PROCÉDURE » : un IDU → la commune a-t-elle une procédure PLU en
// cours ? L'outil LIT le radar (point de calcul unique, mêmes libellés que la fiche) — il ne calcule
// rien. L'absence est DATÉE elle aussi. Jamais d'affirmation sur l'issue de la procédure.
// M60 P1d — PORTE depuis la fiche : le champ IDU s'AMORCE de selectedIdu (préservé par setModule).
export function VerifProcedure() {
  const selectedIdu = useApp((s) => s.selectedIdu)
  const [idu, setIdu] = useState(selectedIdu ?? '')
  useEffect(() => { if (selectedIdu) setIdu(selectedIdu) }, [selectedIdu])
  const m = useMutation({ mutationFn: () => verifProcedure(idu.trim()) })
  const d: VP | undefined = m.data
  const run = () => { if (idu.trim().length >= 10) m.mutate() }
  const cons = d?.consequences

  return (
    <div data-verif-procedure className="flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto">
      <div className="flex flex-col gap-2 rounded-lg border border-line-2 bg-surface-2 p-3">
        <p className="text-[10.5px] leading-snug text-txt-mut">
          Un identifiant de parcelle (IDU) → la commune est-elle en procédure PLU, et qu’en découle-t-il
          pour la parcelle. Radar Sudocuh + registre curaté ; jamais l’issue de la procédure.
        </p>
        <div className="flex gap-2">
          <input
            data-verif-idu value={idu} onChange={(e) => setIdu(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') run() }}
            placeholder="IDU (ex. 97413000CJ0096)"
            className="flex-1 rounded-md border border-line-2 bg-surface-3 px-2 py-1.5 text-[12px] text-txt" />
          <button onClick={run} disabled={idu.trim().length < 10 || m.isPending}
            className="rounded-md border border-mint/50 bg-mint/15 px-3 py-1.5 text-[12px] font-medium text-mint disabled:opacity-40">
            {m.isPending ? '…' : 'Vérifier'}
          </button>
        </div>
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
