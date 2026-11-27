import { useMutation } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { messageChargement, verifProcedure, type VerifProcedure as VP } from '../../lib/api'
import { useApp } from '../../store/useApp'
import { EntreeParcelle, type SourceParcelle } from './EntreeParcelle'   // RECETTE-1 F2 (H1)
import { Reinitialiser } from '../ui/Reinitialiser'   // RECETTE-1 F3 (H1)
import { ErrorState } from '../States'
import { fmtDateNum } from '../../lib/format'   // FIX-12 LOT 2 — date du débat PADD tenu (mois/jour)

// M41 Phase 2.6 — OUTIL « VÉRIF PROCÉDURE » : un IDU → la commune a-t-elle une procédure PLU en
// cours ? L'outil LIT le radar (point de calcul unique, mêmes libellés que la fiche) — il ne calcule
// rien. L'absence est DATÉE elle aussi. Jamais d'affirmation sur l'issue de la procédure.
// M60 P1d — PORTE depuis la fiche : le champ IDU s'AMORCE de selectedIdu (préservé par setModule).
export function VerifProcedure() {
  const selectedIdu = useApp((s) => s.selectedIdu)
  const select = useApp((s) => s.select)   // RECETTE-1 F3 (H1) — fermer la fiche au Réinitialiser
  const pluPrefill = useApp((s) => s.pluPrefill)       // OUTIL-COMMUNES-FIX-14 LOT 1 — IDU porté depuis la fiche
  const setPluPrefill = useApp((s) => s.setPluPrefill)
  const m = useMutation({ mutationFn: (i: string) => verifProcedure(i.trim()) })
  const lancer = (i: string) => { if (i.trim().length >= 10) m.mutate(i) }
  // RECETTE-1 (F2, H1) — source de la parcelle (grise l'autre entrée). INVARIANT : 'carte' seulement
  // quand la parcelle vient de selectedIdu.
  const [source, setSource] = useState<SourceParcelle>(selectedIdu ? 'carte' : null)
  // RECETTE-1 (F1, H1) — porte fiche / clic carte (selectedIdu) → amorce + vérifie ; fermer la fiche
  // (selectedIdu → null) alors que la parcelle venait de la carte VIDE la vérification.
  useEffect(() => {
    if (selectedIdu) { lancer(selectedIdu); if (source == null) setSource('carte') }
    else if (source === 'carte') { m.reset(); setSource(null) }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedIdu])
  // OUTIL-COMMUNES-FIX-14 LOT 1 — porte « Vérif procédure » depuis la fiche : setModule('plu') a effacé
  // selectedIdu ; l'IDU arrive par le prefill (qui survit au changement d'outil). On l'amorce UNE fois
  // puis on le consomme (remis à null) pour ne pas re-vérifier à chaque passage dans l'outil.
  useEffect(() => {
    if (pluPrefill?.idu) { lancer(pluPrefill.idu); setSource('carte'); setPluPrefill(null) }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])
  // RECETTE-1 (F3, H1) — Réinitialiser : vide le résultat + rend les deux entrées + ferme la fiche.
  const resetAll = () => { if (selectedIdu) select(null); m.reset(); setSource(null) }
  const d: VP | undefined = m.data
  const cons = d?.consequences
  const aParcelle = m.variables != null || m.isPending || d != null

  return (
    <div data-verif-procedure className="flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto">
      <div className="flex flex-col gap-2 rounded-lg border border-line-2 bg-surface-2 p-3">
        {/* RECETTE-2 (T3) — Réinitialiser SEUL sur sa ligne (haut-droite) ; l'intro vient EN DESSOUS,
            pleine largeur (plus côte à côte). Présent ssi une parcelle est vérifiée. */}
        <div className="flex flex-col gap-1.5">
          {aParcelle && <div className="flex justify-end"><Reinitialiser onReset={resetAll} /></div>}
          <p className="text-[10.5px] leading-snug text-txt-mut">
            Une parcelle → la commune est-elle en procédure PLU, et qu’en découle-t-il
            pour la parcelle. Radar Sudocuh + registre curaté ; jamais l’issue de la procédure.
          </p>
        </div>
        {/* RECETTE-1 (F2, H1) — EntreeParcelle : adresse/IDU OU clic carte, l'une grise l'autre.
            (Remplace le ParcelInput RETOURS-13 R24 ; même moteur de résolution.) */}
        <EntreeParcelle source={source}
          onPick={(i, src) => { setSource(src); lancer(i) }} />
      </div>

      {m.isError && <ErrorState message={messageChargement(m.error, "Parcelle inconnue ou erreur.")} retry={m.variables ? () => m.mutate(m.variables!) : undefined} />}

      {d && (
        <div data-verif-result className="flex flex-col gap-2">
          <div className="text-[11px] text-txt-mut">
            {d.commune} · {d.idu}{d.tier_servi ? ` · tier ${d.tier_servi}` : ''} · consulté le {d.consulte_le}
          </div>

          {d.procedure_en_cours === true ? (
            <div className="rounded-lg border border-st-creuser/40 bg-st-creuser/10 px-3 py-2 text-[11.5px] text-txt">
              <div className="font-medium">▲ Procédure PLU en cours</div>
              <div className="mt-1">{d.synthese}</div>
              {/* OUTIL-COMMUNES-FIX-14 LOT 6 — le client lit une CITATION propre (organisme · objet ·
                  date · réf), jamais le nom de tour interne du registre (« FIX-13 LOT 1 … »). */}
              <div className="mt-1 text-[10px] text-txt-dim">
                Sourcé {d.source_citation ?? d.source} · confiance {d.confiance} · constaté le {d.date_constat}
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
              ) : cons?.debat_padd_tenu && cons?.sursis_autorise ? (
                /* OUTIL-COMMUNES-FIX-14 LOT 5 — débat tenu ET autorisation expresse de surseoir (conseil) :
                   les DEUX faits ensemble, sans conclure à un sursis sur la parcelle (aucune décision
                   individuelle connue). Saint-Louis : délibération du 29/10/2024, art. 2. */
                <div className="mt-2 border-t border-line-2 pt-2 text-[10px] text-txt-dim">
                  Débat PADD tenu le {fmtDateNum(cons.debat_padd_tenu)}. Le conseil a autorisé le maire à surseoir à statuer (délibération du {cons.sursis_autorise.date_fr ?? fmtDateNum(cons.sursis_autorise.date)}, {cons.sursis_autorise.article ?? 'art. 2'}) — aucune décision de sursis connue pour cette parcelle.
                  {cons.sursis_autorise.source_url && <> · <a href={cons.sursis_autorise.source_url} target="_blank" rel="noreferrer" className="text-mint hover:underline">pièce ↗</a></>}
                </div>
              ) : cons?.debat_padd_tenu ? (
                /* OUTIL-COMMUNES-FIX-12 LOT 2 — « débat tenu » séparé de « sursis applicable » :
                   même libellé que la fiche parcelle (point de calcul unique = radar). */
                <div className="mt-2 border-t border-line-2 pt-2 text-[10px] text-txt-dim">
                  Débat PADD tenu le {fmtDateNum(cons.debat_padd_tenu)} — sursis à statuer non armé (décision discrétionnaire du maire, non constatée).
                </div>
              ) : cons?.debat_recherche_le ? (
                /* OUTIL-COMMUNES-FIX-14 LOT 6 — recherche infructueuse DATÉE (distincte du constat
                   général) : Étang-Salé / Saint-Denis / Saint-Paul. */
                <div className="mt-2 border-t border-line-2 pt-2 text-[10px] text-txt-dim">
                  Pièce du débat PADD non retrouvée lors de la recherche du {fmtDateNum(cons.debat_recherche_le)} — pas de sursis servi.
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
