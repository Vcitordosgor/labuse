import { useMutation, useQuery } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { getFiche, scoreurAdresse, type ScoreurResult } from '../../lib/api'
import { fmtEur, fmtEurCompact, fmtInt, fmtM2 } from '../../lib/format'
import { PERIM_POTENTIEL, PERIM_RESIDUEL } from '../../lib/perimetres'
import { useApp } from '../../store/useApp'
import { ParcelInput } from '../ParcelInput'
import { Calculette, type CalcResult } from '../fiche/Fiche'
import { TierBadge } from './TierBadge'
import { SecteurResultats } from './MonSecteur'   // RETOURS-3 R5 — fusion : le bloc « prix du secteur »

// FUSION (Vic 21/08/2026) — « Étudier un bien » = scoreur d'adresse + calculette foncière en UN outil,
// deux entrées (adresse OU parcelle), un moteur (compute_bilan). Parcours : le CONSTAT d'abord (le
// verdict servi + la charge CALIBRÉE, gratuit), les HYPOTHÈSES ensuite (votre coût/marge/VRD).
// Mandat ETUDIER (refonte) : la charge NÉGATIVE s'affiche en négatif (plus de clamp à 0), un SEUL
// bloc-verdict avec bascule [Calibrées LABUSE | Vos hypothèses] (fini les deux bandeaux empilés),
// « SHAB vendable » (pas « SDP »), et une alerte de cohérence résiduel-bâti reliée à Pièges & risques.
//   • Garde-fou : 100 % présentation — aucun moteur touché. La charge « vos hypothèses » vient de la
//     même calculette (compute_bilan), simplement HISSÉE dans le verdict via onResult.

// RETOURS-11 R7 — la JAUGE horizontale (barre situant charge/zéro/prix) est RETIRÉE du bloc-verdict :
// le liseré coloré et la barre disparaissent, le bloc garde une hauteur stable (min-h). Le chiffre de
// charge et la phrase d'écart suffisent ; plus rien ne fait sauter la hauteur du bloc au changement.

export function EtudierBien() {
  const calcPrefill = useApp((s) => s.calcPrefill)         // porte fiche/copilote (IDU pré-rempli)
  const setCalcPrefill = useApp((s) => s.setCalcPrefill)
  const select = useApp((s) => s.select)
  const setModule = useApp((s) => s.setModule)

  const [prix, setPrix] = useState<number | null>(null)    // prix demandé, SAISI à la main — jamais scrapé
  // Verdict UNIQUE à bascule : 'calibree' (constat servi) | 'hypotheses' (votre calculette).
  const [verdictMode, setVerdictMode] = useState<'calibree' | 'hypotheses'>('calibree')
  const [hypResult, setHypResult] = useState<CalcResult | null>(null)   // remonté par la calculette embarquée

  const m = useMutation({
    mutationFn: (arg: { q: string; id: string | null }) => scoreurAdresse(arg.q, null, arg.id, true),
  })
  const lancer = (q: string, id: string | null) => { setVerdictMode('calibree'); setHypResult(null); m.mutate({ q, id }) }

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
  const vendable = c?.sourced?.shab_vendable_m2 ?? null

  // ALERTE DE COHÉRENCE (mandat point 4) : la SDP résiduelle NETTE du bâti (parcel_residuel, la même
  // que Pièges « Un lot ») confrontée à la SHAB théorique vendue. Résiduel < vendable = le CA suppose un
  // terrain libéré → on le DIT au lieu de laisser les deux outils se contredire en silence. Lecture
  // seule d'un endpoint existant (getFiche, cache partagé avec la fiche) — aucun calcul nouveau.
  const ficheQ = useQuery({ queryKey: ['fiche', resultIdu], queryFn: () => getFiche(resultIdu!), enabled: !!resultIdu, retry: false })
  const residuel = ficheQ.data?.potentiel_transformation?.sdp_residuelle_m2 ?? null
  const alerteResiduel = residuel != null && vendable != null && residuel < vendable

  // La charge affichée dans le verdict unique, selon la bascule. En 'hypotheses', on attend le retour
  // de la calculette (hypResult) — jamais un chiffre inventé en attendant.
  const chargeCourante = verdictMode === 'calibree' ? (cal?.central ?? null) : (hypResult?.central ?? null)
  const parM2Courant = verdictMode === 'calibree' ? (cal?.par_m2_terrain ?? null) : (hypResult?.par_m2_terrain ?? null)
  const chargeNeg = chargeCourante != null && chargeCourante < 0
  const ecart = prix != null && chargeCourante != null ? prix - chargeCourante : null   // >0 : prix dépasse la charge
  const provenanceCourt = verdictMode === 'calibree' ? 'la charge calibrée' : 'vos hypothèses'

  return (
    <div data-etudier-panel className="flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto">
      <div className="rounded-lg border border-mint/40 bg-mint/[0.07] px-3 py-2 text-[10.5px] leading-relaxed text-txt-mut">
        {/* RETOURS-12 T7 — accueil DESCRIPTIF, neutre, utile à tous les métiers (agence, notaire,
            architecte, particulier), pas seulement à un promoteur : ce qu'est la parcelle et ce qu'elle
            porte. Le raisonnement d'opération (bilan, charge) est un second niveau, plus bas. */}
        Un bien vous intéresse ? Tapez son adresse. LABUSE vous donne les vrais prix du secteur (ventes actées DVF, annonces en cours) et, pour une parcelle, ce qu’on peut y construire, ce qui la contraint et ce que valent les biens autour.
      </div>

      {/* ENTRÉE UNIFIÉE (patron omnibox M137) — UN SEUL champ : adresse OU IDU + clic carte.
          RETOURS-5 T6 — plus d'autoFocus : le champ ouvre en bord NEUTRE, vert seulement au focus réel
          (le contour vert « déjà focalisé » à l'ouverture trompait sur l'état). */}
      <div data-etudier-form className="flex flex-col gap-2 rounded-lg border border-line-2 bg-surface-2 p-3">
        <ParcelInput dataAttr="etudier-adresse"
          placeholder="Adresse ou IDU (ex. 12 rue du Général de Gaulle, ou 97415000DK1044)"
          onPick={(idu) => lancer(idu, idu)}
          onAddress={(label) => lancer(label, null)} />
      </div>

      {m.isPending && <p className="text-[11px] text-txt-mut">Analyse…</p>}
      {m.isError && <p className="text-[11px] text-st-ecartee">Erreur — vérifiez l’adresse et réessayez.</p>}

      {/* RETOURS-3 R5 (fusion « Mon secteur ») — dès qu'une adresse/parcelle est résolue, le BLOC SECTEUR
          (prix du secteur, rayon effectif ; moteur sector_price) s'affiche au-dessus de l'étude complète. */}
      {resultIdu && d?.ok && (
        <div data-etudier-secteur className="rounded-lg border border-line-2 bg-surface-1 p-3">
          <p className="label-caps mb-2 text-txt-dim">Prix du secteur</p>
          <SecteurResultats idu={resultIdu} embedded />
        </div>
      )}

      {d && !m.isPending && (
        <div data-etudier-resultat className="rounded-lg border border-line-2 bg-surface-1 p-3">
          {!d.ok ? (
            /* hors base : réponse honnête, jamais un verdict inventé */
            <p className="text-[11.5px] leading-relaxed text-txt-mut"><span className="text-txt">{d.adresse}</span> — {d.message}</p>
          ) : (
            <>
              {/* en-tête : le VERDICT servi (tier) — référentiel unique parcel_p_score_v2.
                  LOT1 — la puce est ÉTIQUETÉE « Classement » : on identifie le tier canonique de la
                  parcelle (Neutre/Faible/…), pas un badge d'état anonyme. */}
              <div className="flex items-center justify-between gap-2">
                <span className="truncate text-[11.5px] text-txt">{d.adresse}</span>
                <span className="flex shrink-0 items-center gap-1.5" title="Classement canonique de la parcelle (même tier que la fiche et la carte)">
                  <span className="text-[9px] uppercase tracking-[.08em] text-txt-dim">Classement</span>
                  <TierBadge tier={d.verdict?.tier} etage0={null} statut={null} />
                </span>
              </div>
              <p className="mt-0.5 text-[10.5px] text-txt-mut">{d.commune} · {fmtM2(d.surface_m2)} · <span className="font-mono">{d.idu}</span></p>

              {/* LE CONSTAT — aux hypothèses CALIBRÉES (bilan servi par secteur, non réglable) */}
              <div data-etudier-constat className="mt-2 border-t border-line pt-2">
                {c?.sourced && (
                  <p className="text-[11px] text-txt-dim">
                    {/* mandat point 3 : 123 m² est une SHAB, pas une SDP — libellé corrigé. O2-5 : périmètre. */}
                    LA BUSE (sourcé) : SHAB vendable <b className="tnum text-txt">{fmtInt(c.sourced.shab_vendable_m2)} m²</b>
                    <span className="text-txt-dim"> ({PERIM_POTENTIEL})</span>
                    {c.sourced.prix_sortie_median != null && <> · prix de sortie bâti <b className="tnum text-txt">{fmtInt(c.sourced.prix_sortie_median)} €/m²</b>{c.sourced.prix_neuf_label && <span className="text-txt-dim"> ({c.sourced.prix_neuf_label})</span>}</>}
                    {c.sourced.terrain_m2 != null && <> · terrain <b className="tnum text-txt">{fmtInt(c.sourced.terrain_m2)} m²</b></>}
                  </p>
                )}

                {/* ALERTE DE COHÉRENCE — résiduel net du bâti vs SHAB vendue (relié à Pièges & risques). */}
                {alerteResiduel && (
                  <div data-etudier-residuel className="mt-1.5 rounded-lg border border-st-creuser/40 bg-st-creuser/[0.08] px-2.5 py-1.5 text-[10.5px] leading-snug text-st-creuser">
                    <b>⚠ Bâti existant.</b> {PERIM_RESIDUEL} : <b className="tnum">{fmtInt(residuel)} m²</b> (Pièges &amp; risques) —
                    la SHAB vendable ci-dessus est un {PERIM_POTENTIEL}.{' '}
                    <button data-etudier-residuel-lien onClick={() => setModule('risques')}
                      className="font-medium text-mint hover:underline">voir Pièges &amp; risques →</button>
                  </div>
                )}

                {cal ? (
                  <>
                    {/* BASCULE — un seul verdict à la fois : la bascule change tout le bloc. */}
                    <div data-etudier-bascule className="mt-2 flex gap-1 rounded-lg border border-line-2 bg-surface-2 p-1">
                      {([['calibree', 'Calibrées LABUSE'], ['hypotheses', 'Vos hypothèses']] as const).map(([k, lbl]) => (
                        <button key={k} data-etudier-mode={k} onClick={() => setVerdictMode(k)}
                          className={`flex-1 rounded-md py-1 text-[11px] font-medium transition-colors duration-quick ${verdictMode === k ? 'bg-mint text-bg' : 'text-txt-mut hover:text-txt'}`}>
                          {lbl}
                        </button>
                      ))}
                    </div>

                    {/* LE VERDICT UNIQUE — charge (négative en rouge, jamais écrêtée) + écart.
                        RETOURS-11 R7 — le liseré vert et la jauge horizontale sont retirés ; le bloc a une
                        hauteur minimale (min-h) pour ne PLUS sauter quand le résultat change (charge ±,
                        écart apparaît/disparaît). Fond neutre (surface-2), plus de bordure de couleur. */}
                    {chargeCourante == null ? (
                      <p className="mt-2 text-[11px] text-txt-mut">Calcul de vos hypothèses…</p>
                    ) : (
                      <div data-etudier-verdict className="mt-2 flex min-h-[104px] flex-col rounded-lg border border-line-2 bg-surface-2 px-3 py-2">
                        <p className="text-[10px] uppercase tracking-wide text-txt-mut">{verdictMode === 'calibree' ? 'Hypothèses calibrées LABUSE' : 'Selon vos hypothèses'}</p>
                        <p className="mt-0.5">
                          <b data-etudier-charge className={`num-key text-lg ${chargeNeg ? 'text-st-ecartee' : 'text-mint'}`}>{fmtEurCompact(chargeCourante)}</b>
                          <span className="ml-1.5 text-[11px] text-txt-mut">de charge foncière{parM2Courant != null && <> ≈ {fmtInt(parM2Courant)} €/m² de terrain</>}</span>
                        </p>
                        {/* RETOURS-12 T7 — le résultat est présenté comme celui d'UN scénario d'opération
                            aux hypothèses affichées, jamais comme un verdict sur la parcelle elle-même.
                            Négatif : on le dit sobrement (« ne dégage rien pour le terrain ») sans conclure
                            que la parcelle « ne vaut rien ». */}
                        <p className="mt-0.5 text-[10.5px] leading-snug text-txt-dim">
                          {chargeNeg
                            ? 'À ces hypothèses, une opération de ce type ne dégage rien pour le terrain — c’est le résultat d’un scénario, pas la valeur de la parcelle.'
                            : 'Ce qu’une opération de ce type pourrait payer le terrain, à ces hypothèses.'}
                        </p>
                        {ecart != null && (
                          <p data-etudier-ecart className={`mt-1.5 text-[11px] font-medium ${ecart >= 0 ? 'text-st-ecartee' : 'text-mint'}`}>
                            {ecart >= 0
                              ? <>Le prix demandé <b>{fmtEur(prix)}</b> dépasse de <b>{fmtEurCompact(ecart)}</b> ce que {provenanceCourt} supporte.</>
                              : <>Le prix demandé <b>{fmtEur(prix)}</b> laisse une marge de <b>{fmtEurCompact(-ecart)}</b> sous {provenanceCourt}.</>}
                          </p>
                        )}
                      </div>
                    )}

                    {/* RETOURS-12 T7 — français d'abord, terme technique entre parenthèses. */}
                    {cal.ca_central != null && (
                      <p className="mt-1.5 text-[11px] text-txt-dim">Chiffre d’affaires visé (CA) <b className="tnum text-txt-mut">{fmtEurCompact(cal.ca_central)}</b>{vendable != null && <> sur {fmtInt(vendable)} m² vendables</>}.</p>
                    )}

                    {/* PRIX DEMANDÉ (saisi à la main) — pilote l'écart du verdict, quel que soit le mode. */}
                    <div className="mt-2 flex items-end gap-2">
                      <label className="flex-1 text-[10.5px] text-txt-mut">
                        Prix demandé du terrain
                        <input data-etudier-prix type="number" min={0} value={prix ?? ''} placeholder="si connu"
                          onChange={(e) => setPrix(e.target.value === '' ? null : Number(e.target.value))}
                          title="Le prix affiché/demandé, saisi à la main — jamais scrapé."
                          className="mt-0.5 w-full rounded-lg border border-line-2 bg-surface-3 px-3 py-1.5 text-xs text-txt placeholder:text-txt-dim focus:border-mint focus:outline-none" />
                      </label>
                    </div>

                    {/* Référentiel marché — terrain nu de zone (constat ET calculette lisent le même). */}
                    {tz && (
                      <p data-etudier-terrain-zone className="mt-1.5 rounded-lg bg-surface-2 px-2.5 py-1.5 text-[11px] leading-snug text-txt-dim">
                        Terrain nu dans la zone : <b className="tnum text-txt">{fmtInt(tz.eur_m2)} €/m²</b> <span className="text-txt-dim">(DVF terrains, fiabilité {tz.fiabilite})</span>.
                        {parM2Courant != null && (parM2Courant >= tz.eur_m2 ? ' Votre charge couvre le prix du marché.' : ' Votre charge est sous le prix du marché — négociation ou densité à retrouver.')}
                      </p>
                    )}

                    {/* LES RÉGLAGES — la calculette (coût, marge, VRD) apparaît quand on passe en « Vos
                        hypothèses » ; elle rend SES réglages et HISSE sa charge dans le verdict ci-dessus
                        (hideResult → plus de second bandeau). */}
                    {verdictMode === 'hypotheses' && resultIdu && (
                      <div className="mt-2 border-t border-line pt-2">
                        <Calculette idu={resultIdu} hideSource hideResult prixDemandeExterne={prix} onResult={setHypResult} />
                      </div>
                    )}
                  </>
                ) : (
                  <p className="mt-1.5 text-[11px] leading-snug text-st-creuser">
                    {c?.motif === 'prix_sortie_non_calculable'
                      ? 'Prix de sortie non calculable ici (commune à dominante sociale) — charge foncière non chiffrée. Le verdict et les faits restent servis.'
                      : 'Capacité constructible non résolue pour cette parcelle (zone non calibrée / non constructible) — charge foncière non calculable.'}
                  </p>
                )}
                <p className="mt-1 text-[9px] leading-snug text-txt-dim">Estimé — ni un prix ni une promesse ; charge « aux hypothèses calibrées » = bilan par secteur (méthode documents). Réglez vos propres hypothèses via la bascule.</p>
              </div>

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
