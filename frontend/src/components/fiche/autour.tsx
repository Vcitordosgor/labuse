/**
 * fiche/autour.tsx — RETOURS-11F4 (découpe de Fiche.tsx, section F9).
 * « Autour de cette parcelle » = LA section de contexte de voisinage (doctrine F0 « un fait, une
 * section »). Elle rassemble ce qui était éparpillé :
 *   - équipements du quotidien (UN moteur BPE+OSM dédoublonné, distance) — école/commerces/santé/bus ;
 *   - QUI VIT là : socio-éco secteur (Filosofi carreau INSEE = Sourcé, + parc social RPLS) rapatrié
 *     de Marché, et la zone atteignable (isochrone IGN) ;
 *   - PERMIS à proximité : UN tableau cliquable (rapatrié de Réseaux) + l'historique permis DE la
 *     parcelle (rapatrié de Marché) + l'activité de dépôt du secteur.
 * Auto-suffisante ; cycle-free.
 */
import type { Fiche } from '../../lib/types'
import { fmtInt } from '../../lib/format'
import { permisIncoherenceNote } from '../../lib/permis'
import { BlocIndisponible } from './BlocIndisponible'
import { MarcheSecteurBlock } from './MarcheSecteurBlock'
import { PermitsProximityBlock } from './PermitsProximityBlock'
import { DepotsBlock } from './DepotsBlock'
import { AutourZoneBlock } from './AutourZoneBlock'
import { useApp } from '../../store/useApp'
import { IC, RefDrawer, GroupLabel, FactNote } from './primitives'
import { Badge } from '../ui/Badge'
// KELFONCIER-FIX-2 (Lot I) — maquette v3 : Verdict + OutilsSection (Permis commune · Fiche commune).
// FICHE-FIX-4 (Lot K) — Proximité en 3 tuiles, quartier INSEE en tuiles 2 colonnes.
import { Verdict, OutilsSection, type OutilSection, Tuiles, type Tuile } from './formes'

// FICHE-RANGEMENT-2 Lot 1 — §1 Identité : l'historique des permis DE la parcelle (fait d'identité
// du bien), extrait pour la future section.
export function HistoriqueSiteBlock({ f }: { f: Fiche }) {
  const h = f.historique_site
  if (!h) return null
  if (h.indisponible) return <div className="mt-2"><BlocIndisponible titre="Sur cette parcelle (historique)" /></div>
  if (!(h.permis.length > 0 || h.caducite)) return null
  return (
    <div data-historique-site>
      <GroupLabel>🏗️ {h.titre}</GroupLabel>
      <ul className="mt-1 list-disc pl-4 text-[11px] leading-snug text-txt-mut">
        {h.permis.slice(0, 6).map((pm, i) => {
          // DONNEES-6/7 — JAMAIS réordonner les dates : si l'autorisation précède le dépôt (incohérence
          // du producteur SDES/Dido), on montre les deux dates telles quelles et on qualifie l'écart
          // (au-delà d'1 mois = modificatif/transféré probable ; sous 1 mois = incohérence). Voir permis.ts.
          const note = permisIncoherenceNote(pm.date_depot, pm.date_autorisation)
          return (
            // KELFONCIER-FIX-1 (Lot C) — le TYPE libellé (Permis d'aménager / Déclaration préalable…) et
            // l'ÉTAT sont servis ; un permis ANNULÉ le DIT (rouge), plus jamais confondu avec une autorisation.
            <li key={i}>{pm.type_label ?? pm.type ?? 'permis'} — déposé {pm.date_depot ?? pm.date_autorisation ?? '?'}{pm.date_autorisation ? `, autorisé ${pm.date_autorisation}` : ''}
              {pm.annule ? <span className="font-medium text-st-ecartee"> · annulé</span>
                : pm.etat_libelle && pm.etat_libelle !== 'autorisé' && <span className="text-txt-dim"> · {pm.etat_libelle}</span>}
              {note && <span className="text-st-ecartee"> · {note}</span>}
            </li>
          )
        })}
        {h.caducite && (
          <li className="text-st-ecartee">PC {h.caducite.pc_annee ?? ''} — {h.caducite.libelle_court ?? 'caduc'}</li>
        )}
      </ul>
      <FactNote>{h.honnetete}</FactNote>
    </div>
  )
}

export function AutourSection({ f, idu }: { f: Fiche; idu: string }) {
  const eq = f.proximites_equipements
  // FICHE-FIX-4 (Lot K) — Verdict utile (secteur + niveau de vie + pauvreté + commerces) + tuiles.
  const eqItems0 = (eq?.items ?? []).filter((e) => !/^bus$|transport/i.test(e.cat))
  const fmtDist = (m: number) => m >= 1000 ? `${(m / 1000).toFixed(1).replace('.', ',')} km` : `${fmtInt(m)} m`
  const commerce = eqItems0.find((e) => /commerce/i.test(e.cat))
  const filo = f.marche_secteur?.filosofi_200m
  const iris = f.iris_quartier
  const verdictCtx = [
    filo?.nivvie_moyen_eur != null ? `niveau de vie ${fmtInt(filo.nivvie_moyen_eur)} €` : null,
    filo?.taux_pauvrete_pct != null ? `${filo.taux_pauvrete_pct} % sous le seuil de pauvreté` : null,
    commerce ? `commerces à ${fmtDist(commerce.distance_m)}` : null,
  ].filter(Boolean).join(', ') || undefined
  // FICHE-FIX-5 (Lot I) — outils alignés sur l'outil ÉTUDE DE ZONE (ouvert SUR LA PARCELLE, ses deux
  // portes) + Permis / Fiche commune.
  const zPref = { idu, commune: f.commune ?? null, zone: null }
  const outils: OutilSection[] = [
    { label: 'Étude de zone · Chalandise', data: 'etude-chalandise', principal: true,
      onClick: () => { const st = useApp.getState(); st.setEtudeZonePrefill({ ...zPref, sous_destination: 'Commerce de détail' }); st.setModule('etude-zone') } },
    { label: 'Étude de zone · Particulier', data: 'etude-particulier',
      onClick: () => { const st = useApp.getState(); st.setEtudeZonePrefill({ ...zPref, sous_destination: '' }); st.setModule('etude-zone') } },
  ]
  if (f.commune) {
    outils.push({ label: 'Permis commune', data: 'permis',
      onClick: () => { const st = useApp.getState(); st.setCommune(f.commune!); st.setCommunesFilter([f.commune!]); st.setModule('permis') } })
    outils.push({ label: 'Fiche commune', data: 'fiche-commune',
      onClick: () => { const st = useApp.getState(); st.setCommune(f.commune!); st.setContexteCommune(f.commune!) } })
  }
  return (
    <RefDrawer id="quartier" icon={IC.contexte} name="Quartier"
      context="Équipements, population et permis du voisinage"
      value={<Badge ton="vert">isochrone</Badge>}>
      {/* FICHE-FIX-4 (Lot K) — Verdict utile : secteur + niveau de vie + pauvreté + commerces (servis). */}
      <Verdict ton="vert"
        reponse={f.secteur ? `Secteur ${f.secteur}` : (iris?.nom ? `Quartier ${iris.nom}` : 'Voisinage')}
        contexte={verdictCtx} />
      {/* FICHE-FIX-4 (Lot K) — Proximité en 3 tuiles (École · Commerces · Santé). Bus vit dans Réseaux. */}
      {eqItems0.length > 0 && (
        <div data-proximites-equip>
          <GroupLabel>À proximité (à pied)</GroupLabel>
          <Tuiles cols={eqItems0.length >= 3 ? 3 : 2}
            items={eqItems0.slice(0, 3).map((e): Tuile => ({ label: e.cat, valeur: fmtDist(e.distance_m) }))} />
        </div>
      )}

      {/* QUI VIT LÀ — socio-éco secteur (Filosofi Sourcé + parc social) rapatrié de Marché, + isochrone. */}
      {f.marche_secteur && <MarcheSecteurBlock ms={f.marche_secteur} />}

      {/* FICHE-FIX-4 (Lot K) — le QUARTIER INSEE (IRIS) en tuiles 2 colonnes ; source en note. */}
      {iris && (() => {
        const t: Tuile[] = []
        if (iris.logements != null) t.push({ label: 'Logements', valeur: fmtInt(iris.logements) })
        if (iris.vacance_pct != null) t.push({ label: 'Vacance', valeur: <>{String(iris.vacance_pct).replace('.', ',')} <small>%</small></> })
        if (iris.part_bati_avant_1990_pct != null) t.push({ label: 'Bâti avant 1990', valeur: <>{String(iris.part_bati_avant_1990_pct).replace('.', ',')} <small>%</small></> })
        if (iris.taille_menages != null) t.push({ label: 'Pers./ménage', valeur: String(iris.taille_menages).replace('.', ',') })
        if (iris.part_60_plus_pct != null) t.push({ label: '60 ans et +', valeur: <>{String(iris.part_60_plus_pct).replace('.', ',')} <small>%</small></> })
        if (iris.part_hlm_pct != null) t.push({ label: 'HLM', valeur: <>{String(iris.part_hlm_pct).replace('.', ',')} <small>%</small></> })
        return (
          <div data-iris-quartier>
            <GroupLabel>Quartier INSEE{iris.nom ? ` — ${iris.nom}` : ''}</GroupLabel>
            {t.length > 0 && <Tuiles cols={2} items={t} />}
            <FactNote>{iris.source} — {iris.millesime}. Maille quartier (IRIS) : affine la commune, ne la remplace pas.</FactNote>
          </div>
        )
      })()}
      <AutourZoneBlock idu={idu} />

      {/* PERMIS À PROXIMITÉ — UN tableau cliquable (rapatrié de Réseaux, F0). */}
      <PermitsProximityBlock idu={idu} />

      {/* FICHE-RANGEMENT-2 Lot 1 — l'historique permis DE la parcelle (fait d'identité) est relocalisé
          en §1 Identité (HistoriqueSiteBlock composé là) ; §9 Quartier ne garde que le voisinage. */}

      {/* Activité de dépôt du secteur (Sitadel) — rapatrié de Réseaux. */}
      {f.depots && <DepotsBlock d={f.depots} />}
      {/* KELFONCIER-FIX-2 (Lot I) — outils de section en pied (maquette v3) : Permis de la commune
          (M03, principal) + Fiche commune (contexte commune). */}
      {outils.length > 0 && <OutilsSection outils={outils} />}
    </RefDrawer>
  )
}
