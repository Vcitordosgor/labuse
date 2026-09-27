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
import { IC, RefDrawer, Line, GroupLabel, FactNote } from './primitives'
import { Badge } from '../ui/Badge'
// KELFONCIER-FIX-2 (Lot H) — maquette v3 : Verdict en tête + aléas en Jauge3 (3 crans + % servi).
// FICHE-FIX-4 (Lot G) — CASIAS/EnR/mesures en Ligne de vigilance, CatNat en Repli, Pièges en bouton.
import { Verdict, Jauge3, Lignes, Ligne, Repli, OutilsSection, InfoI } from './formes'
import { fmtDateNum } from '../../lib/format'

// niveau d'aléa (catégoriel servi) → cran 0..3 de la Jauge3 (présentation, aucun seuil inventé).
const ALEA_CRAN: Record<string, 1 | 2 | 3> = { faible: 1, modéré: 2, modere: 2, moyen: 2, fort: 3, élevé: 3, eleve: 3 }
const aleaCran = (niveau: string | null | undefined, redhibitoire: boolean): 0 | 1 | 2 | 3 =>
  redhibitoire ? 3 : (niveau ? (ALEA_CRAN[niveau.toLowerCase()] ?? 1) : 0)

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
    <RefDrawer id="risques" icon={IC.risques} name="Risques et environnement"
      context={`${evaluees} couche${evaluees > 1 ? 's' : ''} évaluée${evaluees > 1 ? 's' : ''}`}
      value={vigilances.length === 0
        ? <Badge ton="vert">rien à signaler</Badge>
        : <Badge ton="ambre">{vigilances.length} vigilance{vigilances.length > 1 ? 's' : ''}</Badge>}>
      {/* FICHE-FIX-4 (Lot G) — la barre « N couches ▬▬▬ » en tête (micro) est RETIRÉE : doublon du
          sous-titre « N couches évaluées ». */}
      <div className="flex flex-col gap-3">
        {/* FICHE-FIX-4 (Lot G) — Verdict LISIBLE : l'aléa dominant (nature + niveau + part) puis le
            fait marquant (ancien site industriel CASIAS). Réagence des faits servis, aucun recalcul. */}
        {(() => {
          const dom = aleas.find((a) => a.niveau) ?? aleas[0]
          const cs = sols?.casias
          const reponse = vigilances.length === 0 ? 'Rien à signaler'
            : dom ? `${dom.nature.replace(/_/g, ' ')}${dom.niveau ? ` ${dom.niveau}` : ''}${dom.part_pct != null ? ` sur ${dom.part_pct} %` : ''}`
            : `${vigilances.length} vigilance${vigilances.length > 1 ? 's' : ''}`
          const ctx = [
            cs ? `ancien site industriel ${cs.sur_place ? 'sur la parcelle' : `à ${cs.distance_m} m`}` : null,
            aleas.length > 1 ? `${aleas.length} aléas au total` : null,
          ].filter(Boolean).join(' · ') || undefined
          return <Verdict ton={vigilances.length === 0 ? 'vert' : 'ambre'} reponse={reponse} contexte={ctx} />
        })()}
        {/* FICHE-1 lot 3 — ALÉAS : nature · niveau (Jauge3, 3 crans) · part de la parcelle · réf PPR.
            Les aléas sans niveau (PPR — zone bleue) portent une pastille au lieu des crans. Références
            PPR + sources consolidées en note (aucune donnée perdue). Compte n_vigilances au-dessus. */}
        {aleas.length > 0 && (
          <div data-aleas-detail>
            <GroupLabel>Aléas ({aleas.length})</GroupLabel>
            {aleas.map((a, i) => a.niveau != null || a.redhibitoire ? (
              <Jauge3 key={i} niveau={aleaCran(a.niveau, a.redhibitoire)}
                label={<>{a.nature}{a.niveau ? <small className="ml-1 text-txt-mut"> niveau {a.niveau}</small> : null}{a.redhibitoire && <Badge ton="ambre" className="ml-1.5">rédhibitoire</Badge>}</>}
                pct={a.part_pct != null ? `${a.part_pct} %` : undefined} />
            ) : (
              <div key={i} className="flex items-center justify-between border-b border-line py-[5px] text-[12.5px]">
                <span>{a.nature}</span>
                <span className="flex items-center gap-2"><Badge ton="ambre">zone bleue</Badge><span className="font-mono text-[11px] text-txt-dim">{a.part_pct != null ? `${a.part_pct} %` : ''}</span></span>
              </div>
            ))}
            <FactNote>
              {[...new Set(aleas.flatMap((a) => (a.ppr ?? []).map((p) => `${p.document}${p.approbation ? ` (approuvé le ${p.approbation})` : ''}`)))].join(' · ')}
              {aleas.some((a) => a.ppr && a.ppr.length) ? ' — ' : ''}
              {[...new Set(aleas.map((a) => `${a.source}${a.millesime ? ` · ${a.millesime}` : ''}`))].join(' · ')}
            </FactNote>
          </div>
        )}
        {/* SOURCES-1 lot 3 — SOLS (SIS / CASIAS) : live, mêmes règles que la cascade sol_pollue.
            SIS = obligations DITES (L556-2, L125-7). CASIAS = inventaire, pas une pollution avérée. */}
        {sols && (sols.sis || sols.casias) && (
          <div data-sols>
            <GroupLabel>Sols (SIS / CASIAS)</GroupLabel>
            <Lignes>
              {sols.sis && (
                <Ligne ton="ambre"
                  label={<>Secteur d’information sur les sols (SIS)<InfoI aria="Sur le SIS" tip="Étude de sols obligatoire au changement d’usage (L556-2) · information écrite de l’acheteur/locataire obligatoire à la vente ou location (L125-7)." /></>}
                  valeur={<>{sols.sis.nom ? `${sols.sis.nom} · ` : ''}{sols.sis.part_pct} <small>% de la parcelle</small></>} />
              )}
              {sols.casias && (
                <Ligne ton="gris"
                  label={<>Ancien site industriel (CASIAS)<InfoI aria="Sur le CASIAS" tip="Inventaire historique — pas une pollution avérée ; étude de sol à prévoir pour un projet sensible." /></>}
                  valeur={<>{sols.casias.nom ? `${sols.casias.nom} · ` : ''}{sols.casias.sur_place ? 'sur la parcelle' : `à ${sols.casias.distance_m} m`}</>} />
              )}
            </Lignes>
          </div>
        )}
        {/* RETOUCHES-1 lot C.9 — CARTOFRICHES : la parcelle recoupe-t-elle une friche recensée ? */}
        {f.cartofriches && (
          <div data-cartofriches>
            <GroupLabel>Friche recensée (Cartofriches)</GroupLabel>
            {f.cartofriches.disponible ? (
              <div className="flex flex-col gap-1 text-[12.5px]">
                {f.cartofriches.friches.map((fr, i) => (
                  <div key={i} className="flex items-start gap-2">
                    <span aria-hidden className="mt-1.5 shrink-0 text-st-creuser">▲</span>
                    <div className="min-w-0 flex-1">
                      <span className="font-semibold">{fr.nom ?? 'Friche'}</span>
                      {fr.statut && <span className="text-txt-mut"> — {fr.statut}</span>}
                      {fr.surface_m2 != null && <span className="text-txt-mut"> · {fr.surface_m2.toLocaleString('fr-FR')} m²</span>}
                      {fr.etat && <div className="text-[11.5px] text-txt-mut">{fr.etat}</div>}
                    </div>
                  </div>
                ))}
                <div className="text-[11px] text-txt-dim">{f.cartofriches.source} · {f.cartofriches.millesime}</div>
              </div>
            ) : (
              <div className="text-[12px] text-txt-dim"><span className="text-mint">✓</span> Sans objet — parcelle non recensée comme friche. <span className="text-txt-dim">({f.cartofriches.millesime})</span></div>
            )}
          </div>
        )}
        {/* SOURCES-FIX-1 A1 — EnR au sol exclues (loi APER, sauf toiture). FICHE-FIX-4 (Lot G) : en Ligne. */}
        {f.enr_exclue_toiture && (
          <div data-enr-exclue><Lignes>
            {f.enr_exclue_toiture.disponible
              ? f.enr_exclue_toiture.zones.map((zn, i) => (
                <Ligne key={i} ton="ambre"
                  label={<>EnR au sol interdites (APER)<InfoI aria="Sur l'exclusion EnR" tip={`Photovoltaïque/ombrière au sol exclu ; en toiture non concerné. ${f.enr_exclue_toiture!.source} · ${f.enr_exclue_toiture!.millesime}`} /></>}
                  valeur={<>{zn.libelle ?? 'zone exclue'}{zn.gestionnaire ? <small> · {zn.gestionnaire}</small> : null}</>} />
              ))
              : <Ligne ton="gris"
                  label={<>EnR au sol (APER)<InfoI aria="Sur l'exclusion EnR" tip={`Zone d'exclusion des EnR au sol — sauf toiture. ${f.enr_exclue_toiture.millesime}`} /></>}
                  valeur="hors zone d'exclusion" />}
          </Lignes></div>
        )}
        {/* SOURCES-FIX-1 A2 — mesures compensatoires (GéoMCE). FICHE-FIX-4 (Lot G) : en Ligne. */}
        {f.mesures_compensatoires && (
          <div data-mesures-compensatoires><Lignes>
            {f.mesures_compensatoires.disponible
              ? f.mesures_compensatoires.mesures.map((m, i) => (
                <Ligne key={i} ton="ambre"
                  label={<>Mesure compensatoire (GéoMCE)<InfoI aria="Sur la mesure compensatoire" tip={`${f.mesures_compensatoires!.source} · ${f.mesures_compensatoires!.millesime}`} /></>}
                  valeur={<>{m.type_mesure ?? 'mesure'}{m.projet ? <small> · {m.projet}</small> : null}{m.date_decision ? <small> · {fmtDateNum(m.date_decision)}</small> : null}</>} />
              ))
              : <Ligne ton="gris"
                  label={<>Mesure compensatoire (GéoMCE)<InfoI aria="Sur la mesure compensatoire" tip={`Base GéoMCE. ${f.mesures_compensatoires.millesime}`} /></>}
                  valeur="aucune sur la parcelle" />}
          </Lignes></div>
        )}
        {/* RETOUCHES-1 lot C.12 — CatNat. FICHE-FIX-4 (Lot G) : replié « N arrêtés · dernier JJ/MM/AAAA ». */}
        {f.catnat?.disponible && f.catnat.arretes.length > 0 ? (
          <div data-catnat>
            <Repli compteur={f.catnat.total}
              label={<>arrêtés CatNat (commune){f.catnat.arretes[0]?.date_arrete ? ` · dernier ${fmtDateNum(f.catnat.arretes[0].date_arrete)}` : ''}</>}>
              <Lignes>
                {f.catnat.arretes.map((a, i) => (
                  <Ligne key={i} label={a.peril} valeur={a.date_arrete ? fmtDateNum(a.date_arrete) : '—'} ton={a.date_arrete ? undefined : 'gris'} />
                ))}
              </Lignes>
              <FactNote>{f.catnat.total} arrêté{f.catnat.total > 1 ? 's' : ''} au total (commune) · {f.catnat.source}</FactNote>
            </Repli>
          </div>
        ) : f.catnat && !f.catnat.disponible ? (
          <div data-catnat><Lignes><Ligne label="Catastrophes naturelles (commune)" valeur="aucun arrêté" ton="gris" /></Lignes></div>
        ) : null}
        {/* AUTRES VIGILANCES (hors aléas structurés) — chaque ligne marquée d'une puce ambre.
            RETOURS-20 Z1·02 — le titre encadré (font-mono caps) devient un KICKER partagé (GroupLabel). */}
        {/* FICHE-FIX-5 (Lot F) — VIGILANCES en Lignes AMBRE (plus de puce ▲ ni d'encadré) : le libellé
            avant « — », le détail après, la source derrière le « i ». Les lignes HT/HTA (ex-Rappel
            encadré) rejoignent la même liste. Aucune donnée retirée. */}
        {(autresVig.length > 0 || f.proximites?.ligne_ht || f.proximites?.ligne_mt) && (
          <div>
            <GroupLabel>Vigilances</GroupLabel>
            <Lignes>
              {autresVig.map((l, i) => {
                const det = (l.detail || '') as string
                const dash = det.indexOf('—')
                const label = dash >= 0 ? det.slice(0, dash).trim() : det
                const val = dash >= 0 ? det.slice(dash + 1).trim() : ''
                const src = l.source ? String(l.source) : ''
                return (
                  <Ligne key={`v-${i}`} ton="ambre" title={det}
                    label={<><span className="text-amber">{label}</span>{src ? <InfoI aria="Source de la vigilance" tip={src} /> : null}</>}
                    valeur={val} />
                )
              })}
              {f.proximites?.ligne_ht && (
                <Ligne ton="ambre" title={f.proximites.ligne_ht.libelle}
                  label={<><span className="text-amber">Ligne haute tension</span><InfoI aria="Sur la ligne HT" tip={`${f.proximites.ligne_ht.libelle} — ${f.proximites.ligne_ht.source}`} /></>}
                  valeur="au contact" />
              )}
              {f.proximites?.ligne_mt && (
                <Ligne ton="ambre" title={f.proximites.ligne_mt.libelle}
                  label={<><span className="text-amber">Ligne moyenne tension</span><InfoI aria="Sur la ligne HTA" tip={`${f.proximites.ligne_mt.libelle} — ${f.proximites.ligne_mt.source}`} /></>}
                  valeur="à proximité" />
              )}
            </Lignes>
          </div>
        )}
        {/* lignes non évaluées (donnée absente) — dites, jamais masquées. */}
        {inconnues.length > 0 && (
          <div className="flex flex-col gap-1">
            {inconnues.map((l, i) => <Line key={i} line={l} hideWeight hideDate />)}
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
        {/* FICHE-FIX-4 (Lot G) — Pièges & risques en bouton OutilsSection (plus de grande carte). */}
        <OutilsSection outils={[{ label: 'Pièges & risques', principal: true, full: true, data: 'risques',
          onClick: () => setModule('risques') }]} />
      </div>
    </RefDrawer>
  )
}
