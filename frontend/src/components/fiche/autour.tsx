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
import { BlocIndisponible } from './BlocIndisponible'
import { MarcheSecteurBlock } from './MarcheSecteurBlock'
import { PermitsProximityBlock } from './PermitsProximityBlock'
import { DepotsBlock } from './DepotsBlock'
import { AutourZoneBlock } from './AutourZoneBlock'
import { IC, RefDrawer, GroupLabel, FactNote } from './primitives'

export function AutourSection({ f, idu }: { f: Fiche; idu: string }) {
  const eq = f.proximites_equipements
  return (
    <RefDrawer id="autour-zone" icon={IC.contexte} name="Autour de cette parcelle"
      context="Équipements, population et permis du voisinage"
      value={<span className="pill-mint">isochrone</span>}>
      {/* ÉQUIPEMENTS — UN moteur (BPE+OSM dédoublonnés, distance à pied). Absent = omis (jamais « 0 m »).
          Z1·02 — le label-caps « À proximité » devient un kicker ; les tuiles de distance (maquette) restent. */}
      {eq?.items && eq.items.length > 0 && (
        <div data-proximites-equip title={eq.source ?? undefined}>
          <GroupLabel>À proximité</GroupLabel>
          <div className="mt-1 flex flex-wrap items-baseline gap-x-3 gap-y-0.5 text-[11.5px] text-txt-mut">
            {eq.items.map((e, i) => (
              <span key={i}><span className="text-txt">{e.cat}</span>{' '}
                <span className="tnum">{e.distance_m >= 1000
                  ? `${(e.distance_m / 1000).toFixed(1).replace('.', ',')} km`
                  : `${fmtInt(e.distance_m)} m`}</span></span>
            ))}
          </div>
        </div>
      )}

      {/* QUI VIT LÀ — socio-éco secteur (Filosofi Sourcé + parc social) rapatrié de Marché, + isochrone. */}
      {f.marche_secteur && <MarcheSecteurBlock ms={f.marche_secteur} />}
      <AutourZoneBlock idu={idu} />

      {/* PERMIS À PROXIMITÉ — UN tableau cliquable (rapatrié de Réseaux, F0). */}
      <PermitsProximityBlock idu={idu} />

      {/* Historique permis DE la parcelle (rapatrié de Marché). */}
      {f.historique_site?.indisponible && <div className="mt-2"><BlocIndisponible titre="Sur cette parcelle (historique)" /></div>}
      {f.historique_site && !f.historique_site.indisponible && (f.historique_site.permis.length > 0 || f.historique_site.caducite) && (
        <div data-historique-site>
          {/* Z1·02 / Z3 — la boîte (rounded border bg) devient un kicker + liste ; note → FactNote. */}
          <GroupLabel>🏗️ {f.historique_site.titre}</GroupLabel>
          <ul className="mt-1 list-disc pl-4 text-[11px] leading-snug text-txt-mut">
            {f.historique_site.permis.slice(0, 6).map((pm, i) => (
              <li key={i}>{pm.type ?? 'permis'} — déposé {pm.date_depot ?? pm.date_autorisation ?? '?'}{pm.date_autorisation ? `, autorisé ${pm.date_autorisation}` : ''}</li>
            ))}
            {f.historique_site.caducite && (
              <li className="text-st-ecartee">PC {f.historique_site.caducite.pc_annee ?? ''} — {f.historique_site.caducite.libelle_court ?? 'caduc'}</li>
            )}
          </ul>
          <FactNote>{f.historique_site.honnetete}</FactNote>
        </div>
      )}

      {/* Activité de dépôt du secteur (Sitadel) — rapatrié de Réseaux. */}
      {f.depots && <DepotsBlock d={f.depots} />}
    </RefDrawer>
  )
}
