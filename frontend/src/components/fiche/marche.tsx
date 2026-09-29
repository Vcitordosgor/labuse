/**
 * fiche/marche.tsx — RETOURS-11F4 (découpe de Fiche.tsx, section F7).
 * « Marché et secteur », recentrée sur le PRIX (cible F7 + doctrine F0 « un fait, une section ») :
 *  - terrain nu secteur (valeur d'en-tête), bâti secteur par type (marcheLines), neuf VEFA commune,
 *  - PRIX DE SORTIE bâti secteur (fait UNIQUE ici ; la Constructibilité y renvoie, cf. F5),
 *  - ventes < 100 m (voisinage proche) — le nombre de PERMIS en est retiré (les permis vivent dans
 *    « Autour », un seul tableau, F0),
 *  - le contexte SOCIO-ÉCO (Filosofi + parc social) et l'historique permis de la parcelle DÉMÉNAGENT
 *    vers « Autour de cette parcelle » (F0) — Marché ne porte plus que du prix.
 * Auto-suffisante : re-dérive dvfSecteur + marcheLines depuis `f` ; bilan via queryKey ['bilan',idu].
 */
import { useQuery } from '@tanstack/react-query'
import { getFaisabilite, getMonSecteur, radarClic } from '../../lib/api'
import { fmtInt, fmtDateNum } from '../../lib/format'
import type { Fiche } from '../../lib/types'
import { useApp } from '../../store/useApp'
import { IC, RefDrawer, MicroSpark, Line, GroupLabel, FactRow, FactNote } from './primitives'
// KELFONCIER-FIX-2 (Lot I) — maquette v3 : Verdict + Tuiles c3 (prix par type) + Réglette (secteur↔commune).
// FICHE-FIX-4 (Lot J) — prix de sortie / valeur / loyers / acquéreur PM en Ligne, méthode en « i ».
import { Verdict, Tuiles, type Tuile, Reglette, Lignes, Ligne, InfoI, OutilsSection } from './formes'

// FICHE-RANGEMENT-2 Lot 1 — §1 Identité : la DERNIÈRE VENTE / mutation DVF de la parcelle (fait
// d'identité du bien), extraite pour la future section. C4 : une mutation multi-parcelles porte le
// prix GLOBAL, jamais celui de cette parcelle seule (dit tel quel).
export function DerniereVenteBlock({ f }: { f: Fiche }) {
  const dm = f.dvf_parcelle?.derniere_mutation as { date_mutation?: string | null; nature?: string | null; valeur?: number | null; multi_parcelles?: boolean; adresse?: string | null; nombre_pieces?: number | null; surface_carrez_m2?: number | null; nombre_lots?: number | null } | null | undefined
  if (!dm?.date_mutation) return null
  const d = new Date(dm.date_mutation)
  const dateFmt = isNaN(d.getTime()) ? String(dm.date_mutation) : d.toLocaleDateString('fr-FR', { month: 'long', year: 'numeric' })
  const detail = [dm.adresse, dm.nombre_pieces ? `${dm.nombre_pieces} pièce${dm.nombre_pieces > 1 ? 's' : ''}` : null,
                  dm.surface_carrez_m2 ? `${fmtInt(dm.surface_carrez_m2)} m² Carrez` : null,
                  dm.nombre_lots && dm.nombre_lots > 1 ? `${dm.nombre_lots} lots` : null].filter(Boolean).join(' · ')
  return (
    <div data-derniere-vente>
      {dm.multi_parcelles
        ? (<>
            <FactRow label="Dernière vente" tone="mute" value={dateFmt} />
            <FactNote>Vente groupée (plusieurs parcelles) — le prix global de la mutation{dm.valeur ? ` (${fmtInt(dm.valeur)} €)` : ''} n'est pas attribuable à cette seule parcelle.</FactNote>
          </>)
        : (<>
            <FactRow label="Dernière vente" value={<>{dateFmt}{dm.valeur ? <> — {fmtInt(dm.valeur)} <small>€</small></> : null}</>} />
            <FactNote>Mutation DVF de la parcelle{dm.nature ? ` — ${dm.nature.toLowerCase()}` : ''}{detail ? ` · ${detail}` : ''}.</FactNote>
          </>)}
    </div>
  )
}

export function MarcheSection({ f, idu }: { f: Fiche; idu: string }) {
  const setRadarToOpen = useApp((s) => s.setRadarToOpen)
  const openRadar = useApp((s) => s.openRadar)
  const annonces = f.radar_annonces?.liste ?? []
  const faisa = useQuery({ queryKey: ['bilan', idu], queryFn: () => getFaisabilite(idu), enabled: !!f })
  // SECTEUR = prix du TERRAIN NU SEUL (dvf_marche `bati_m2=0`) — jamais moyenné avec le bâti (M137-G).
  const dvfSecteur = f.dvf_parcelle?.secteur?.find((s) => s.type_bien === 'terrain')
  // FICHE-RANGEMENT-3 Lot 1 — « Commerces et services à proximité » (layer amenites) et « Permis
  // SITADEL » (layer sitadel) vivent déjà en §9 Quartier (proximites_equipements, PermitsProximityBlock,
  // DepotsBlock) → retirés de §8 Marché pour qu'un fait ne vive qu'une fois.
  const marcheLines = f.lines.filter((l) => l.onglet === 'marche' && l.layer !== 'amenites' && l.layer !== 'sitadel')
  const mb = faisa.data?.marche
  const horizon = mb?.fraicheur?.horizon_libelle || mb?.dvf_couverture?.libelle
  // ETUDIER-BIEN-2 Lot A — les 3 faits UNIQUES de l'outil « Étudier un bien » (supprimé, cf.
  // ETUDIER-BIEN-1) rapatriés ICI, servis par le MÊME endpoint /outils/mon-secteur (rendu, pas
  // nouveau calcul) : écart secteur ↔ commune entière, médiane par type au rayon, annonces Radar
  // dans le rayon. Le terrain nu par type reste la médiane de SECTION (`dvfSecteur`, valeur foi de
  // la fiche) — jamais le rayon (ETUDIER-BIEN-2 Lot B tranche la divergence terrain nu).
  const secteurQ = useQuery({ queryKey: ['mon-secteur', idu], queryFn: () => getMonSecteur(idu), enabled: !!idu })
  const ms = secteurQ.data
  const ec = ms?.secteur_bati?.ecart_commune
  // FRONT-CHIFFRES-2 (F10) — le seuil de suffisance (n < 5 → « — ») est appliqué au BACK (mon_secteur
  // SEUIL_N : `medianes_par_type` renvoie None sous le seuil) ; le front ne le recalcule plus, il lit
  // les médianes déjà filtrées. Le terrain nu utilise la MÉTHODE CANONIQUE `_terrain_section`
  // (ms.par_type.terrain_nu, « une seule méthode partout ») au lieu de refiltrer dvf_parcelle.secteur.
  const parTypeMaison = ms?.par_type?.maison ?? null
  const parTypeAppart = ms?.par_type?.appartement ?? null
  const parTypeTerrain = ms?.par_type?.terrain_nu ?? null
  const annoncesRayon = ms?.annonces_radar ?? []
  const contexte = (dvfSecteur?.n_ventes ? `${dvfSecteur.n_ventes} vente${dvfSecteur.n_ventes > 1 ? 's' : ''} secteur` : 'comparables DVF') + (horizon ? ` · DVF — ${horizon}` : '')
  return (
    <RefDrawer id="marche" icon={IC.marche} name="Marché"
      context={contexte}
      value={dvfSecteur?.mediane_prix_m2 != null ? `${fmtInt(dvfSecteur.mediane_prix_m2)} €/m²` : '—'}
      micro={<MicroSpark label={contexte} />}>
      {/* KELFONCIER-FIX-2 (Lot I) — Verdict + Tuiles c3 (médiane par type, servie) + Réglette
          (écart secteur ↔ commune, servi). Aucun prix recalculé. */}
      {(() => {
        // FICHE-FIX-4 (Lot J) — Tuiles UNIQUEMENT pour les types servis (rayon ajouté à la sous-ligne) ;
        // le Verdict ne cite QUE des valeurs présentes dans les tuiles (plus de « terrain nu X » sans tuile).
        const typeTuiles: Tuile[] = []
        const cite: string[] = []
        if (parTypeTerrain) { typeTuiles.push({ label: 'Terrain nu', valeur: fmtInt(parTypeTerrain.eur_m2), sous: `€/m² · ${parTypeTerrain.n} ventes` }); cite.push(`terrain nu ${fmtInt(parTypeTerrain.eur_m2)} €/m²`) }
        if (parTypeMaison) { typeTuiles.push({ label: 'Maison', valeur: fmtInt(parTypeMaison.eur_m2), sous: `€/m² · ${parTypeMaison.n} ventes${parTypeMaison.rayon_m != null ? ` · ${fmtInt(parTypeMaison.rayon_m)} m` : ''}` }); cite.push(`maison ${fmtInt(parTypeMaison.eur_m2)} €/m²`) }
        if (parTypeAppart) { typeTuiles.push({ label: 'Appartement', valeur: fmtInt(parTypeAppart.eur_m2), sous: `€/m² · ${parTypeAppart.n} ventes${parTypeAppart.rayon_m != null ? ` · ${fmtInt(parTypeAppart.rayon_m)} m` : ''}` }); cite.push(`appartement ${fmtInt(parTypeAppart.eur_m2)} €/m²`) }
        const rep = cite.length ? cite.slice(0, 2).join(', ') : 'Marché de secteur'
        return (
          <>
            <Verdict ton="vert"
              reponse={rep.charAt(0).toUpperCase() + rep.slice(1)}
              contexte={ec?.ecart_pct != null
                ? `secteur ${ec.ecart_pct > 0 ? '+' : ''}${ec.ecart_pct} % vs commune${mb?.tendance ? `, tendance ${mb.tendance}` : ''}`
                : (mb?.tendance ? `tendance ${mb.tendance}` : undefined)} />
            {typeTuiles.length > 0 && <Tuiles cols={typeTuiles.length >= 3 ? 3 : 2} items={typeTuiles} />}
            {ec?.ecart_pct != null && (
              /* FICHE-FIX-5 (Lot H) — la phrase « secteur vs commune » passe derrière le « i » de la droite. */
              <div data-secteur-ecart-commune>
                <Reglette secteurPct={Math.max(4, Math.min(96, 50 + ec.ecart_pct))}
                  gauche="commune"
                  droite={<>secteur {ec.ecart_pct > 0 ? '+' : ''}{ec.ecart_pct} %<InfoI aria="Sur l'écart secteur/commune" tip={`${ec.phrase} — le secteur est ${ec.ecart_pct < 0 ? 'sous' : 'au-dessus de'} la commune.`} /></>} />
              </div>
            )}
          </>
        )
      })()}
      {marcheLines.length
        ? <div className="flex flex-col gap-1">{marcheLines.map((l, i) => <Line key={i} line={l} hideWeight hideDate />)}</div>
        : <p className="text-xs text-txt-dim">Aucun signal sur cet onglet.</p>}
      {/* FICHE-RANGEMENT-2 Lot 1 — la DERNIÈRE VENTE (fait d'identité du bien) est relocalisée en
          §1 Identité (DerniereVenteBlock composé là) ; Marché ne porte plus que du prix de secteur. */}

      {/* RETOURS-11F4 F7/F0 — PRIX DE SORTIE bâti secteur : le fait vit ICI (la Constructibilité y renvoie).
          Même moteur que le bilan (`marche.median`). Sous le seuil : dit tel quel, jamais un chiffre inventé.
          RETOURS-20 Z1·03 — plus de boîte : FactRow (valeur mono à droite), méthode en FactNote. */}
      {/* FICHE-FIX-4 (Lot J) — prix de sortie + valeur au prix du secteur en Lignes, méthode en « i ». */}
      {(mb?.median != null || (f.surface_m2 != null && dvfSecteur?.mediane_prix_m2 != null && dvfSecteur.mediane_prix_m2 > 0)) && (
        <Lignes>
          {mb?.median != null && (
            <Ligne label={<>Prix de sortie — bâti secteur<InfoI aria="Méthode du prix de sortie" tip={`${mb.type_prix}, ${mb.n} ventes ≤ ${Math.round(mb.radius_m)} m (rayon adaptatif) · fiabilité ${mb.fiabilite}${mb.tendance ? ` · tendance ${mb.tendance}` : ''}${horizon ? ` · DVF — ${horizon}` : ''}`} /></>}
              valeur={<>{fmtInt(Number(mb.median))} <small>€/m²</small></>} />
          )}
          {f.surface_m2 != null && dvfSecteur?.mediane_prix_m2 != null && dvfSecteur.mediane_prix_m2 > 0 && (
            <Ligne label={<>Valeur au prix du secteur<InfoI aria="Méthode de la valeur" tip="Contenance × prix médian du terrain nu au m² du secteur — estimé, pas une valeur vénale." /></>}
              valeur={<>≈ {fmtInt(Math.round(f.surface_m2 * dvfSecteur.mediane_prix_m2))} <small>€</small></>} />
          )}
        </Lignes>
      )}
      {/* NEUF (VEFA) commune — grandeur nommée, effectif, fenêtre ; sous le seuil : « échantillon insuffisant ». */}
      {(() => { const nv = f.dvf_parcelle?.neuf_vefa
        return nv ? (
          <div data-fiche-neuf-vefa>
            {nv.effectif_suffisant && nv.mediane_prix_m2_bati != null ? (
              <FactRow label="Neuf (VEFA) — commune" value={<>{fmtInt(nv.mediane_prix_m2_bati)} <small>€/m² bâti</small></>}
                src={<>{nv.n} ventes / {nv.fenetre_ans} ans</>} />
            ) : (
              <FactRow label="Neuf (VEFA) — commune" tone="mute" value={nv.insuffisant_libelle} />
            )}
            <FactNote>{nv.grandeur} · {nv.reserve}</FactNote>
          </div>
        ) : null })()}
      {/* ETUDIER-BIEN-2 Lot A (2/3) — MÉDIANE PAR TYPE (secteur) : maison / appartement au RAYON
          adaptatif (médiane locale mono-type, fait unique de l'ex-outil, via /outils/mon-secteur) ;
          terrain nu = médiane de la SECTION cadastrale (`dvfSecteur`, la valeur foi de la fiche —
          jamais le rayon, cf. Lot B). Sous 5 ventes → « — ». */}
      {/* ETUDIER-BIEN-2 Lot A (2/3) — la MÉDIANE PAR TYPE (secteur) est portée par les Tuiles c3 en
          tête de section (KELFONCIER-FIX-2 Lot I). Note de méthode conservée ici. */}
      {(parTypeMaison || parTypeAppart || parTypeTerrain) && (
        <FactNote>Prix par type : maison / appartement = médiane locale par type au rayon adaptatif (DVF) ; terrain nu = médiane de la section cadastrale (même source que la valeur du secteur).</FactNote>
      )}
      {/* signal de marché condensé (DVF actes + Sitadel) — jamais un mot nu. */}
      {(() => { const sig = (f as unknown as { market_signal?: Record<string, any> }).market_signal
        return sig?.disponible ? (
          <div data-fiche-market-signal>
            <GroupLabel>Signal de marché : {sig.label}</GroupLabel>
            {(sig.composantes as Record<string, any>[]).map((c, i) => (
              <FactRow key={i} label={<>{c.sens} {c.cle}</>} value={c.valeur} />
            ))}
            <FactNote>{sig.source} · outil « Marché » pour le détail commune</FactNote>
          </div>
        ) : null })()}
      {/* Ventes < 100 m (proximité) — RETOURS-11F4 F7/F0 : le NOMBRE DE PERMIS est retiré ici (les permis
          à proximité vivent dans « Autour », un seul tableau). Marché ne garde que les VENTES. */}
      {/* FICHE-FIX-5 (Lot H) — Ventes < 100 m en deux Lignes (nombre · prix médian). */}
      {f.voisinage_proche && !f.voisinage_proche.indisponible && f.voisinage_proche.ventes_dvf > 0 && (
        <div data-voisinage-proche>
          <GroupLabel>Ventes à moins de 100 m</GroupLabel>
          <Lignes>
            <Ligne label={<>Ventes <small className="text-txt-dim">(&lt; 100 m · 36 mois)</small><InfoI aria="Sur les ventes proches" tip={f.voisinage_proche.honnetete} /></>}
              valeur={<>{f.voisinage_proche.ventes_dvf} <small>vente{f.voisinage_proche.ventes_dvf > 1 ? 's' : ''}</small></>} />
            {(f.voisinage_proche.prix_median_eur || f.voisinage_proche.prix_note) && (
              <Ligne label="Prix médian" ton={f.voisinage_proche.prix_median_eur ? undefined : 'gris'}
                valeur={f.voisinage_proche.prix_median_eur ? <>~{Math.round(f.voisinage_proche.prix_median_eur / 1000)} <small>k€</small></> : f.voisinage_proche.prix_note} />
            )}
          </Lignes>
        </div>
      )}
      {/* FICHE-1 lot 6 — ANNONCES RADAR rattachées à la parcelle : datées, prix demandé, statut,
          lien vers la fiche annonce (interne). Écart demandé/acté pour une annonce en cours + DVF. */}
      {annonces.length > 0 && (
        <div data-radar-annonces>
          <GroupLabel>Annonces Radar — cette parcelle ({annonces.length})</GroupLabel>
          <div className="flex flex-col gap-1.5">
            {annonces.map((a) => (
              <div key={a.bien_id} className="text-[12px]">
                <div className="flex items-center gap-2">
                  <b className="text-txt-hi">{a.prix_demande_eur != null ? a.prix_demande_eur.toLocaleString('fr-FR') + ' €' : '—'}</b>
                  {a.type_bien && <span className="text-txt-mut">{a.type_bien}</span>}
                  <span className="rounded-full bg-surface-3 px-1.5 text-[10px] text-txt-mut">{a.statut}</span>
                  {a.date && <span className="text-[10.5px] text-txt-dim">{a.date}</span>}
                </div>
                {a.ecart_demande_acte_pct != null && (
                  <div className="text-[11px] text-txt-mut">
                    écart demandé / dernière vente : {a.ecart_demande_acte_pct > 0 ? '+' : ''}{a.ecart_demande_acte_pct} %
                  </div>
                )}
                <div className="mt-0.5 flex gap-3">
                  <button type="button" className="text-[11px] text-mint underline decoration-dotted"
                    onClick={() => { setRadarToOpen(a.bien_id); openRadar() }}>
                    Voir la fiche annonce
                  </button>
                  {a.url_sortante && (
                    <a href={a.url_sortante} target="_blank" rel="noopener noreferrer"
                      onClick={() => { radarClic(a.bien_id).catch(() => {}) }}
                      className="text-[11px] text-txt-dim underline decoration-dotted">
                      annonce sur {a.portail} ↗
                    </a>
                  )}
                </div>
              </div>
            ))}
          </div>
          <FactNote>Annonces rattachées à cette parcelle (Radar). Prix demandés — jamais un prix LABUSE.</FactNote>
        </div>
      )}
      {/* ETUDIER-BIEN-2 Lot A (3/3) — ANNONCES RADAR DANS LE RAYON : les annonces actives AUTOUR de
          la parcelle (rayon 1,5 km), fait unique de l'ex-outil, via /outils/mon-secteur. Libellé
          DISTINCT du bloc « cette parcelle » ci-dessus (Lot B : jamais confondre les deux portées). */}
      {annoncesRayon.length > 0 && (
        <div data-secteur-radar-rayon>
          <GroupLabel>Annonces Radar — autour (rayon 1,5 km)</GroupLabel>
          <div className="flex flex-col gap-1">
            {annoncesRayon.slice(0, 8).map((a, i) => (
              <div key={i} className="flex items-center gap-2 text-[12px]">
                <span className="flex-1 truncate text-txt">{a.type_bien} · {a.commune}{a.distance_m != null ? ` · ${a.distance_m} m` : ''}</span>
                <span className="whitespace-nowrap font-mono text-[11.5px] text-txt-mut">{a.prix != null ? `${fmtInt(a.prix)} €` : '—'}{a.prix_m2_affiche != null ? ` · ${fmtInt(a.prix_m2_affiche)} €/m²` : ''}</span>
                {a.ecart_pct != null && <span className={`whitespace-nowrap font-mono text-[11.5px] ${a.ecart_pct < 0 ? 'text-mint' : 'text-st-ecartee'}`}>{a.ecart_pct > 0 ? '+' : ''}{a.ecart_pct} %</span>}
              </div>
            ))}
          </div>
          <FactNote>Annonces actives dans un rayon de 1,5 km autour de la parcelle (Radar) — distinctes des annonces rattachées à cette parcelle ci-dessus. Prix demandés.</FactNote>
        </div>
      )}
      {/* FICHE-FIX-4 (Lot J) — loyers OLL + acquéreur PM voisin en Lignes, méthode en « i ». */}
      {(f.loyers_oll || (f.pm_voisines?.disponible && f.pm_voisines.acquereurs.length > 0)) && (
        <Lignes>
          {f.loyers_oll?.disponible ? (
            <Ligne label={<>Loyers (OLL)<InfoI aria="Sur les loyers OLL" tip={`${f.loyers_oll.par_type && (f.loyers_oll.par_type.maison != null || f.loyers_oll.par_type.appartement != null) ? `Maison ${f.loyers_oll.par_type.maison ?? '—'} · appart. ${f.loyers_oll.par_type.appartement ?? '—'} €/m². ` : ''}${f.loyers_oll.source} · ${f.loyers_oll.millesime}`} /></>}
              valeur={<>{f.loyers_oll.loyer_median_eur_m2} <small>€/m²/mois · zone {f.loyers_oll.zone}</small></>} />
          ) : f.loyers_oll ? (
            <Ligne label="Loyers (OLL)" ton="gris" valeur="zone non couverte" />
          ) : null}
          {f.pm_voisines?.disponible && f.pm_voisines.acquereurs.length > 0 && (
            <Ligne title={f.pm_voisines.acquereurs[0].denomination ?? undefined}
              label={<>Acquéreur PM voisin{f.pm_voisines.acquereurs.length > 1 ? ` (${f.pm_voisines.acquereurs.length})` : ''}<InfoI aria="Sur les acquéreurs PM voisins" tip={`PM ayant acquis dans ${f.pm_voisines.rayon_m} m sur ${f.pm_voisines.mois} mois · ${f.pm_voisines.source}`} /></>}
              valeur={<>{f.pm_voisines.acquereurs[0].denomination}{f.pm_voisines.acquereurs[0].date ? <small> · {fmtDateNum(f.pm_voisines.acquereurs[0].date)}</small> : null}</>} />
          )}
        </Lignes>
      )}
      {/* FICHE-FIX-5 (Lot H) — un SEUL outil : « Outil Communes » (le hub qui a absorbé Marché ·
          Comparateur · Vélocité · Rareté), ouvert sur la commune de la parcelle. Comparer et Remonter
          le temps sont retirés d'ici (même décision que Scan/Écrire au propriétaire). */}
      {f.commune && (
        <OutilsSection outils={[{ label: `Outil Communes — ${f.commune}`, principal: true, full: true, data: 'communes',
          onClick: () => { const st = useApp.getState(); st.setCommune(f.commune!); st.setModule('communes') } }]} />
      )}
    </RefDrawer>
  )
}
