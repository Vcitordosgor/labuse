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
import { fmtDateNum, fmtAlea, fmtIntensite, fmtDec } from '../../lib/format'

// niveau d'aléa (catégoriel servi) → cran 0..3 de la Jauge3 (présentation, aucun seuil inventé).
const ALEA_CRAN: Record<string, 1 | 2 | 3> = { faible: 1, modéré: 2, modere: 2, moyen: 2, fort: 3, élevé: 3, eleve: 3 }
const aleaCran = (niveau: string | null | undefined, redhibitoire: boolean): 0 | 1 | 2 | 3 =>
  redhibitoire ? 3 : (niveau ? (ALEA_CRAN[niveau.toLowerCase()] ?? 1) : 0)

export function RisquesSection({ f }: { f: Fiche; idu: string }) {
  const setModule = useApp((s) => s.setModule)
  const lignes = f.lines.filter((l) => l.onglet === 'risques')
  // FICHE-ORFEVRERIE-1 (Lot D, pt 29) — le BASSIN VERSANT est un CONTEXTE hydrographique, pas une
  // vigilance (pas une contrainte opposable) : il sort des vigilances (bandeau/badge passent à 3) et
  // devient une ligne d'information. Il reste compté parmi les couches évaluées.
  const vigilancesAll = lignes.filter((l) => l.result === 'SOFT_FLAG' || l.result === 'HARD_EXCLUDE')
  const bassinVersant = vigilancesAll.find((l) => l.layer === 'bassin_versant') ?? null
  const vigilances = vigilancesAll.filter((l) => l.layer !== 'bassin_versant')
  const inconnues = lignes.filter((l) => l.result === 'UNKNOWN')
  const sansObjet = lignes.filter((l) => l.result === 'PASS')
  // compteur VRAI : toutes les couches réellement évaluées (vigilance + info + sans objet + inconnu).
  const evaluees = vigilances.length + sansObjet.length + inconnues.length + (bassinVersant ? 1 : 0)
  // FICHE-1 lot 3 — les ALÉAS en détail (f.aleas) remplacent les lignes brutes « risques » (layer
  // 'risques') : nature, niveau, part, référence PPR. Les AUTRES vigilances (accès, sol, SUP…)
  // restent affichées telles quelles. Même moteur que Pièges et risques (cascade servie).
  const aleas = f.aleas?.liste ?? []
  const sols = f.sols
  // FICHE-ORFEVRERIE-1 (Lot B, pt 14) — les SERVITUDES d'utilité publique (SUP, layer 'sup') vivent
  // UNE fois, en §Urbanisme (« Dispositifs et périmètres ») : ici on ne les répète pas, on RENVOIE.
  const autresVig = vigilances.filter((l) => l.layer !== 'risques' && l.layer !== 'sup')
  const aUneSup = vigilances.some((l) => l.layer === 'sup')
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
            : dom ? `${fmtAlea(dom.nature)}${dom.niveau ? ` ${fmtIntensite(dom.niveau)}` : ''}${dom.part_pct != null ? ` sur ${dom.part_pct} %` : ''}`
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
                label={<>{fmtAlea(a.nature)}{a.niveau ? <small className="ml-1 text-txt-mut"> niveau {fmtIntensite(a.niveau)}</small> : null}{a.redhibitoire && <Badge ton="ambre" className="ml-1.5">rédhibitoire</Badge>}</>}
                pct={a.part_pct != null ? `${a.part_pct} %` : undefined} />
            ) : (
              /* FICHE-ORFEVRERIE-1 (Lot A, pts 8 & 9) — plus de « PPR — zone bleue » nu : on sert la
                 ligne COMPLÈTE (aléa + zone + prescription), c.-à-d. le libellé servi, et la part « % »
                 porte sa nature MESURÉE (intersection géométrique parcelle × zonage) au survol. */
              <div key={i} data-aleas-ligne className="border-b border-line py-[6px] text-[12.5px]">
                <div className="flex items-start justify-between gap-2">
                  <span className="min-w-0 flex-1">{a.libelle || fmtAlea(a.nature)}</span>
                  <span className="flex flex-none items-center gap-2">
                    <Badge ton="ambre">zone bleue</Badge>
                    {a.part_pct != null && <span className="font-mono text-[11px] text-txt-dim" title="Part de la parcelle mesurée (intersection géométrique parcelle × zonage PPR)">{a.part_pct} %</span>}
                  </span>
                </div>
              </div>
            ))}
            <FactNote>
              {[...new Set(aleas.flatMap((a) => (a.ppr ?? []).map((p) => `${p.document}${p.approbation ? ` (approuvé le ${fmtDateNum(p.approbation)})` : ''}`)))].join(' · ')}
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
        ) : f.catnat?.disponible ? (
          /* CHASSE-DONNEES-FIX-1 (Lot 4, E-82) — source DISPONIBLE, 0 arrêté : « aucun arrêté »
             est un vrai 0 mesuré. */
          <div data-catnat><Lignes><Ligne label="Catastrophes naturelles (commune)" valeur="aucun arrêté" ton="gris" /></Lignes></div>
        ) : f.catnat ? (
          /* source INDISPONIBLE (table absente / panne d'ingestion) : « non renseigné », JAMAIS
             « aucun arrêté » (à La Réunion aucune commune n'a zéro arrêté CatNat). */
          <div data-catnat><Lignes><Ligne label="Catastrophes naturelles (commune)" valeur="non renseigné" ton="gris" /></Lignes></div>
        ) : null}
        {/* AUTRES VIGILANCES (hors aléas structurés) — chaque ligne marquée d'une puce ambre.
            RETOURS-20 Z1·02 — le titre encadré (font-mono caps) devient un KICKER partagé (GroupLabel). */}
        {/* FICHE-FIX-5 (Lot F) — VIGILANCES en Lignes AMBRE (plus de puce ▲ ni d'encadré) : le libellé
            avant « — », le détail après, la source derrière le « i ». Les lignes HT/HTA (ex-Rappel
            encadré) rejoignent la même liste. Aucune donnée retirée. */}
        {(autresVig.length > 0 || f.proximites?.ligne_ht || f.proximites?.ligne_mt || aUneSup) && (
          <div>
            <GroupLabel>Vigilances</GroupLabel>
            <Lignes>
              {/* RECETTE-2 (A6, affichage sans run) — la vigilance PENTE est servie par le run épinglé avec
                  un « ~56 % tres_fort » (max des cellules de la grille) qui CONTREDIT la pente unique de la
                  fiche. Côté affichage, on réécrit cette ligne à partir de la SEULE pente servie à la fiche
                  (terrain.pente_moy_deg + pente_bande), identique à la tuile Pente et à §2 Terrain. Aucun
                  run, aucun recalcul : simple lecture de la valeur déjà servie. */}
              {autresVig.map((l, i) => {
                let det = (l.detail || '') as string
                if (l.layer === 'pente' && f.terrain?.pente_moy_deg != null) {
                  const deg = f.terrain.pente_moy_deg
                  const pct = Math.tan((deg * Math.PI) / 180) * 100
                  const bande = f.terrain.pente_bande ?? 'calculée'
                  det = `Pente ${bande} (${fmtDec(deg)}° · ${fmtDec(pct)} %) — terrassement et accès renchéris (majoration VRD du bilan), pas une exclusion.`
                }
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
                /* FICHE-ORFEVRERIE-1 (Lot A, pt 24) — la distance en mètres, pas un « à proximité » muet. */
                <Ligne ton="ambre" title={f.proximites.ligne_mt.libelle}
                  label={<><span className="text-amber">Ligne moyenne tension</span><InfoI aria="Sur la ligne HTA" tip={`${f.proximites.ligne_mt.libelle} — ${f.proximites.ligne_mt.source}`} /></>}
                  valeur={f.proximites.ligne_mt.distance_m != null ? <>~{f.proximites.ligne_mt.distance_m} <small>m</small></> : 'à proximité'} />
              )}
              {/* FICHE-ORFEVRERIE-1 (Lot B, pt 14) — RENVOI : la SUP est détaillée en §Urbanisme (plus de
                  doublon), on signale seulement sa présence ici. */}
              {aUneSup && (
                <Ligne label={<span className="text-amber">Servitude d'utilité publique</span>}
                  valeur={<small className="text-txt-dim">détail en « Urbanisme »</small>} />
              )}
            </Lignes>
          </div>
        )}
        {/* FICHE-ORFEVRERIE-1 (Lot D, pt 29 · Lot C, pt 20/21) — BASSIN VERSANT : ligne d'INFORMATION
            (contexte hydrographique), hors vigilances. Le « code hydro » brut est retiré de l'affichage
            (il reste au survol via le titre complet) ; le libellé n'est pas tronqué. */}
        {bassinVersant && (() => {
          const det = (bassinVersant.detail || '') as string
          const propre = det.replace(/\s*\(code hydro[^)]*\)/i, '')
          return (
            <div data-bassin-versant-info>
              <GroupLabel>Information</GroupLabel>
              <p className="text-[11.5px] leading-snug text-txt-mut" title={det}>
                {propre}{bassinVersant.source ? <InfoI aria="Source du bassin versant" tip={String(bassinVersant.source)} /> : null}
              </p>
            </div>
          )
        })()}
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
