import { useMutation } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { scoreurAdresse, type ScoreurResult } from '../../lib/api'
import { fmtEur, fmtEurCompact, fmtInt, fmtM2 } from '../../lib/format'
import { useApp } from '../../store/useApp'
import { ParcelInput } from '../ParcelInput'
import { Calculette } from '../fiche/Fiche'
import { TierBadge } from './TierBadge'

// FUSION (Vic 21/08/2026) — « Étudier un bien » = scoreur d'adresse + calculette foncière en UN outil,
// deux entrées (adresse OU parcelle), un moteur (compute_bilan). Parcours : le CONSTAT d'abord (le
// verdict servi + la charge CALIBRÉE, gratuit), les HYPOTHÈSES ensuite (votre coût/marge/VRD).
//   • M128-6 tient : AUCUN badge marché, on sert des NOMBRES (le lecteur conclut).
//   • Référentiel marché UNIQUE = prix terrain nu de zone (constat ET calculette lisent le même).
//   • La marge apparaît deux fois, chacune DIT son référentiel : « aux hypothèses calibrées »
//     (constat, bilan servi par secteur) puis « selon vos hypothèses » (calculette réglable).
export function EtudierBien() {
  const calcPrefill = useApp((s) => s.calcPrefill)         // porte fiche/copilote (IDU pré-rempli)
  const setCalcPrefill = useApp((s) => s.setCalcPrefill)
  const select = useApp((s) => s.select)
  const setModule = useApp((s) => s.setModule)

  const [prix, setPrix] = useState<number | null>(null)    // prix demandé, SAISI à la main — jamais scrapé
  const [showHyp, setShowHyp] = useState(false)

  const m = useMutation({
    mutationFn: (arg: { q: string; id: string | null }) => scoreurAdresse(arg.q, null, arg.id, true),
  })
  const lancer = (q: string, id: string | null) => { setShowHyp(false); m.mutate({ q, id }) }

  // PORTE (fiche / copilote) : un IDU pré-rempli → on résout le constat directement, sans saisie.
  useEffect(() => {
    if (calcPrefill) { lancer(calcPrefill, calcPrefill); setCalcPrefill(null) }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [calcPrefill])

  const d: ScoreurResult | undefined = m.data
  const c = d?.constat
  const cal = c?.charge_calibree
  const tz = c?.terrain_zone
  const resultIdu = d?.idu ?? null

  return (
    <div data-etudier-panel className="flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto">
      <div className="rounded-lg border border-mint/40 bg-mint/[0.07] px-3 py-2 text-[10.5px] leading-relaxed text-txt-mut">
        Seconde opinion avant d’offrir. Collez une <b>adresse</b> (ou une référence cadastrale) — LA BUSE
        rend le <b>constat</b> (verdict + charge calibrée) ; réglez ensuite <b>vos hypothèses</b>.
      </div>

      {/* ENTRÉE UNIFIÉE (patron omnibox M137) — UN SEUL champ : adresse OU IDU + clic carte */}
      <div data-etudier-form className="flex flex-col gap-2 rounded-lg border border-line-2 bg-surface-2 p-3">
        <ParcelInput dataAttr="etudier-adresse" autoFocus
          placeholder="Adresse ou IDU (ex. 12 rue du Général de Gaulle, ou 97415000DK1044)"
          onPick={(idu) => lancer(idu, idu)}
          onAddress={(label) => lancer(label, null)} />
      </div>

      {m.isPending && <p className="text-[11px] text-txt-mut">Analyse…</p>}
      {m.isError && <p className="text-[11px] text-st-ecartee">Erreur — vérifiez l’adresse et réessayez.</p>}

      {d && !m.isPending && (
        <div data-etudier-resultat className="rounded-lg border border-line-2 bg-surface-1 p-3">
          {!d.ok ? (
            /* hors base : réponse honnête, jamais un verdict inventé */
            <p className="text-[11.5px] leading-relaxed text-txt-mut"><span className="text-txt">{d.adresse}</span> — {d.message}</p>
          ) : (
            <>
              {/* en-tête : le VERDICT servi (tier) — référentiel unique parcel_p_score_v2 */}
              <div className="flex items-center justify-between gap-2">
                <span className="truncate text-[11.5px] text-txt">{d.adresse}</span>
                <TierBadge tier={d.verdict?.tier} etage0={null} statut={null} />
              </div>
              <p className="mt-0.5 text-[10.5px] text-txt-mut">{d.commune} · {fmtM2(d.surface_m2)} · <span className="font-mono">{d.idu}</span></p>

              {/* LE CONSTAT — aux hypothèses CALIBRÉES (bilan servi par secteur, non réglable) */}
              <div data-etudier-constat className="mt-2 border-t border-line pt-2">
                {c?.sourced && (
                  <p className="text-[11px] text-txt-dim">
                    LA BUSE (sourcé) : SDP vendable <b className="tnum text-txt">{fmtInt(c.sourced.shab_vendable_m2)} m²</b>
                    {c.sourced.prix_sortie_median != null && <> · prix de sortie bâti <b className="tnum text-txt">{fmtInt(c.sourced.prix_sortie_median)} €/m²</b></>}
                    {c.sourced.terrain_m2 != null && <> · terrain <b className="tnum text-txt">{fmtInt(c.sourced.terrain_m2)} m²</b></>}
                  </p>
                )}
                {cal ? (
                  <>
                    <p className="mt-1.5 text-[11px] text-txt-dim">Charge foncière <span className="text-txt-mut">— aux hypothèses calibrées</span></p>
                    <p className="mt-0.5">
                      <b data-etudier-charge-calibree className="num-key text-lg text-mint">{fmtEurCompact(Math.max(0, cal.central))}</b>
                      <span className="ml-1.5 text-[11px] text-txt-mut">≈ {fmtInt(cal.par_m2_terrain)} €/m² de terrain</span>
                    </p>
                    {cal.ca_central != null && (
                      <p className="text-[11px] text-txt-dim">CA visé <b className="tnum text-txt-mut">{fmtEurCompact(cal.ca_central)}</b>{c?.sourced?.shab_vendable_m2 != null && <> sur {fmtInt(c.sourced.shab_vendable_m2)} m² vendables</>}.</p>
                    )}
                    {tz && (
                      <p data-etudier-terrain-zone className="mt-1.5 rounded-lg bg-surface-2 px-2.5 py-1.5 text-[11px] leading-snug text-txt-dim">
                        Confrontation — aux hypothèses calibrées vous pouvez payer <b className="tnum text-mint">{fmtInt(cal.par_m2_terrain)} €/m²</b> de terrain ;
                        le marché de la zone vend le terrain nu à <b className="tnum text-txt">{fmtInt(tz.eur_m2)} €/m²</b> <span className="text-txt-dim">(DVF terrains, fiabilité {tz.fiabilite})</span>.
                        {cal.par_m2_terrain >= tz.eur_m2 ? ' Votre charge couvre le prix du marché.' : ' Votre charge est sous le prix du marché — négociation ou densité à retrouver.'}
                      </p>
                    )}
                    {/* PRIX DEMANDÉ (saisi à la main) → marge à ce prix, aux hypothèses calibrées */}
                    <div className="mt-2 flex items-end gap-2">
                      <label className="flex-1 text-[10.5px] text-txt-mut">
                        Prix demandé du terrain
                        <input data-etudier-prix type="number" min={0} value={prix ?? ''} placeholder="si connu"
                          onChange={(e) => setPrix(e.target.value === '' ? null : Number(e.target.value))}
                          title="Le prix affiché/demandé, saisi à la main — jamais scrapé."
                          className="mt-0.5 w-full rounded-lg border border-line-2 bg-surface-3 px-3 py-1.5 text-xs text-txt placeholder:text-txt-dim focus:border-mint focus:outline-none" />
                      </label>
                    </div>
                    {prix != null && (
                      <p data-etudier-marge-calibree className={`mt-2 rounded-lg px-3 py-2 text-[11px] font-medium ${cal.central - prix >= 0 ? 'bg-mint/10 text-mint' : 'bg-st-ecartee/10 text-st-ecartee'}`}>
                        {cal.central - prix >= 0
                          ? <>Marge à ce prix (aux hypothèses calibrées) : <b>{fmtEurCompact(cal.central - prix)}</b> sous votre charge foncière.</>
                          : <>À {fmtEur(prix)}, le prix dépasse de <b>{fmtEurCompact(Math.abs(cal.central - prix))}</b> ce que la charge calibrée supporte.</>}
                      </p>
                    )}
                  </>
                ) : (
                  <p className="mt-1.5 text-[11px] leading-snug text-st-creuser">
                    {c?.motif === 'prix_sortie_non_calculable'
                      ? 'Prix de sortie non calculable ici (commune à dominante sociale) — charge foncière non chiffrée. Le verdict et les faits restent servis.'
                      : 'Capacité constructible non résolue pour cette parcelle (zone non calibrée / non constructible) — charge foncière non calculable.'}
                  </p>
                )}
                <p className="mt-1 text-[9px] leading-snug text-txt-dim">Estimé — ni un prix ni une promesse ; charge « aux hypothèses calibrées » = bilan par secteur (méthode documents). Réglez vos propres hypothèses ci-dessous.</p>
              </div>

              {/* LES HYPOTHÈSES — la calculette, selon VOS hypothèses (même moteur, même référentiel zone) */}
              {resultIdu && (
                <div className="mt-2 border-t border-line pt-2">
                  <button data-etudier-hyp-toggle onClick={() => setShowHyp((v) => !v)}
                    className="min-h-7 text-[11.5px] font-medium text-mint hover:underline">
                    {showHyp ? '▾ Régler vos hypothèses (coût, marge, VRD)' : '▸ Régler vos hypothèses (coût, marge, VRD) →'}
                  </button>
                  {showHyp && (
                    <div className="mt-1.5">
                      <Calculette idu={resultIdu} hideSource prixDemandeExterne={prix} />
                    </div>
                  )}
                </div>
              )}

              {resultIdu && (
                <button data-etudier-fiche onClick={() => { select(resultIdu); setModule(null) }}
                  className="mt-2 min-h-7 text-[11px] font-medium text-mint hover:underline">Ouvrir la fiche complète →</button>
              )}
            </>
          )}
        </div>
      )}
    </div>
  )
}
