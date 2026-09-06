/**
 * fiche/risques.tsx — RETOURS-11F4 (découpe de Fiche.tsx, section F6).
 * « Risques et protections », restructurée (cible F6) :
 *  - compteur VRAI (nombre de couches réellement évaluées = vigilances + « sans objet »),
 *  - VIGILANCES D'ABORD, marquées d'une puce ambre ; les « rien à signaler » repliés
 *    (« N couches sans objet — déplier ») pour ne plus noyer les vraies alertes,
 *  - SUP (PM1/AC1/I4/EL7…) rapatriées d'Urbanisme via l'onglet backend (served_cascade `_ONGLET`),
 *    servies par famille dans le libellé,
 *  - ligne HT la plus proche = une CONTRAINTE (distance), seuil de pertinence appliqué en amont (F0).
 * Auto-suffisante : re-dérive ses lignes depuis `f.lines`. Cycle-free (n'importe que primitives).
 */
import type { Fiche } from '../../lib/types'
import { useApp } from '../../store/useApp'
import { IC, RefDrawer, MicroSegments, Line, PorteOutil, GroupLabel, Rappel } from './primitives'
import { Trace } from '../../lib/trace'

export function RisquesSection({ f }: { f: Fiche; idu: string }) {
  const setModule = useApp((s) => s.setModule)
  const lignes = f.lines.filter((l) => l.onglet === 'risques')
  const vigilances = lignes.filter((l) => l.result === 'SOFT_FLAG' || l.result === 'HARD_EXCLUDE')
  const inconnues = lignes.filter((l) => l.result === 'UNKNOWN')
  const sansObjet = lignes.filter((l) => l.result === 'PASS')
  // compteur VRAI : toutes les couches réellement évaluées (vigilance + sans objet + inconnu).
  const evaluees = vigilances.length + sansObjet.length + inconnues.length
  // FICHE-1 lot 3 — les ALÉAS en détail (f.aleas) remplacent les lignes brutes « risques » (layer
  // 'risques') : nature, niveau, part, référence PPR. Les AUTRES vigilances (accès, sol, SUP…)
  // restent affichées telles quelles. Même moteur que Pièges et risques (cascade servie).
  const aleas = f.aleas?.liste ?? []
  const sols = f.sols
  const autresVig = vigilances.filter((l) => l.layer !== 'risques')
  return (
    <RefDrawer id="risques" icon={IC.risques} name="Risques et protections"
      context={`${evaluees} couche${evaluees > 1 ? 's' : ''} évaluée${evaluees > 1 ? 's' : ''}`}
      value={vigilances.length === 0
        ? <span className="pill-mint">rien à signaler</span>
        : <span className="pill-amber">{vigilances.length} vigilance{vigilances.length > 1 ? 's' : ''}</span>}
      micro={<MicroSegments n={evaluees} label={`${evaluees} couches`} />}>
      <div className="flex flex-col gap-3">
        {/* FICHE-1 lot 3 — ALÉAS EN DÉTAIL : nature · niveau · part de la parcelle · référence PPR.
            Compte n_vigilances au-dessus (dans le value du tiroir). Dérivé de la cascade servie. */}
        {aleas.length > 0 && (
          <div data-aleas-detail>
            <GroupLabel>Aléas ({aleas.length})</GroupLabel>
            <div className="flex flex-col gap-1.5">
              {aleas.map((a, i) => (
                <div key={i} className="flex items-start gap-2">
                  <span aria-hidden className={`mt-2 shrink-0 ${a.redhibitoire ? 'text-st-ecartee' : 'text-st-creuser'}`}>▲</span>
                  <div className="min-w-0 flex-1">
                    <div className="text-[13px]">
                      <span className="font-semibold">{a.nature}</span>
                      {a.niveau && <span className="text-txt-mut"> — niveau {a.niveau}</span>}
                      {a.part_pct != null && <span className="text-txt-mut"> · {a.part_pct} % de la parcelle</span>}
                      {a.redhibitoire && <span className="pill-amber ml-1.5">rédhibitoire</span>}
                    </div>
                    {a.ppr && a.ppr.length > 0 && (
                      <div className="text-[11.5px] text-txt-mut">
                        {a.ppr.map((p) => `${p.document}${p.approbation ? ` approuvé le ${p.approbation}` : ''}`).join(' · ')}
                      </div>
                    )}
                    <div className="text-[11.5px] text-txt-dim">
                      {a.source}{a.millesime ? ` · ${a.millesime}` : ''}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
        {/* SOURCES-1 lot 3 — SOLS (SIS / CASIAS) : live, mêmes règles que la cascade sol_pollue.
            SIS = obligations DITES (L556-2, L125-7). CASIAS = inventaire, pas une pollution avérée. */}
        {sols && (sols.sis || sols.casias) && (
          <div data-sols>
            <GroupLabel>Sols (SIS / CASIAS)</GroupLabel>
            <div className="flex flex-col gap-1.5 text-[12.5px]">
              {sols.sis && (
                <div className="flex items-start gap-2">
                  <span aria-hidden className="mt-1.5 shrink-0 text-st-creuser">▲</span>
                  <div className="min-w-0 flex-1">
                    <span className="font-semibold">Secteur d’information sur les sols</span>
                    {sols.sis.nom && <span> — {sols.sis.nom}</span>}
                    <span className="text-txt-mut"> · {sols.sis.part_pct} % de la parcelle</span>
                    <div className="text-[11.5px] text-txt-mut">
                      Étude de sols obligatoire au changement d’usage (L556-2) · information écrite de
                      l’acheteur/locataire obligatoire à la vente ou location (L125-7).
                    </div>
                  </div>
                </div>
              )}
              {sols.casias && (
                <div className="flex items-start gap-2">
                  <span aria-hidden className="mt-1.5 shrink-0 text-txt-dim">▲</span>
                  <div className="min-w-0 flex-1">
                    <span className="font-semibold">Ancien site industriel (CASIAS)</span>
                    {sols.casias.nom && <span> — {sols.casias.nom}</span>}
                    <span className="text-txt-mut">
                      {sols.casias.sur_place ? ' · sur la parcelle' : ` · à ${sols.casias.distance_m} m`}
                    </span>
                    <div className="text-[11.5px] text-txt-mut">
                      Inventaire historique — pas une pollution avérée ; étude de sol à prévoir pour un
                      projet sensible.
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
        {/* AUTRES VIGILANCES (hors aléas structurés) — chaque ligne marquée d'une puce ambre.
            RETOURS-20 Z1·02 — le titre encadré (font-mono caps) devient un KICKER partagé (GroupLabel). */}
        {autresVig.length > 0 && (
          <div>
            <GroupLabel>Vigilances</GroupLabel>
            <div className="flex flex-col gap-1">
              {autresVig.map((l, i) => {
                // CIRCUIT-2 lot 5.2 — le NIVEAU D'ALÉA porte l'étiquette de traçage (classe) :
                // les lignes « Aléa … — niveau … » ouvrent le tiroir de leur couche.
                const detail = (l.detail || '') as string
                const alea = detail.startsWith('Aléa')
                  ? (detail.toLowerCase().includes('inondation') ? 'alea_inondation_couche' : 'alea_mvt_couche')
                  : null
                const ligne = <div className="min-w-0 flex-1"><Line line={l} hideWeight hideDate /></div>
                return (
                  <div key={i} className="flex items-start gap-2">
                    <span aria-hidden className="mt-2 shrink-0 text-st-creuser">▲</span>
                    {alea ? <Trace id={alea}>{ligne}</Trace> : ligne}
                  </div>
                )
              })}
            </div>
          </div>
        )}
        {/* lignes non évaluées (donnée absente) — dites, jamais masquées. */}
        {inconnues.length > 0 && (
          <div className="flex flex-col gap-1">
            {inconnues.map((l, i) => <Line key={i} line={l} hideWeight hideDate />)}
          </div>
        )}
        {/* M106 P4 — ligne HT la plus proche : une CONTRAINTE (distance, jamais un booléen). La servitude
            I4 n'est pas cartographiée (à vérifier gestionnaire). Seuil de pertinence appliqué en amont (F0). */}
        {f.proximites?.ligne_ht && (
          <div data-ligne-ht>
            <Rappel src={f.proximites.ligne_ht.source}>{f.proximites.ligne_ht.libelle}</Rappel>
          </div>
        )}
        {/* « rien à signaler » REPLIÉ — ne noie plus les vraies alertes. */}
        {sansObjet.length > 0 && (
          <details data-risques-sans-objet>
            <summary className="cursor-pointer text-[12px] font-semibold text-txt-mut" style={{ listStyle: 'none' }}>
              <span className="text-mint">✓</span> {sansObjet.length} couche{sansObjet.length > 1 ? 's' : ''} sans objet — déplier
            </summary>
            <div className="mt-1.5 flex flex-col gap-1">
              {sansObjet.map((l, i) => <Line key={i} line={l} hideWeight hideDate />)}
            </div>
          </details>
        )}
        {lignes.length === 0 && <p className="text-xs text-txt-dim">Aucun signal sur cet onglet.</p>}
        {/* M137-T — PORTE Risques : « Pièges et risques » (même moteur que cette section, O5). */}
        <PorteOutil ico="⚑" data="risques" titre="Pièges et risques"
          sous="Servitudes dormantes, risques et propriétaire — cette parcelle en détail, ou un lot au crible"
          onClick={() => setModule('risques')} />
      </div>
    </RefDrawer>
  )
}
