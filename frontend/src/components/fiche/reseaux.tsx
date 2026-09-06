/**
 * fiche/reseaux.tsx — RETOURS-11F4 (découpe de Fiche.tsx, section F8).
 * « Réseaux et accès » restructurée en QUATRE blocs courts (cible F8) :
 *   ① ACCÈS — UN verdict (moteur `acces`, source unique — plus de phrase codée en dur qui
 *      contredisait le faisceau de viabilisation) + transport public le plus proche ;
 *   ② RÉSEAUX — gestionnaires eau · assainissement · élec (contact admin, DT-DICT) ;
 *   ③ VIABILISATION — indicateur + faisceau de preuves (accordéon), + ANC ;
 *   ④ AXES ET NUISANCES — l'axe structurant le plus proche (les deux faces).
 * L'ENSOLEILLEMENT ne vit plus ici (détection PV abandonnée, SOLAIRE M2) ; les PERMIS à proximité
 * et l'activité de dépôt DÉMÉNAGENT vers « Autour » (un seul tableau, F0). Piscine/pente restent en
 * tête (caractéristiques du terrain). Auto-suffisante ; cycle-free.
 */
import { useQuery } from '@tanstack/react-query'
import { getOrthoEquipements } from '../../lib/api'
import { fmtDistance as fmtDistanceM } from '../../lib/geo'
import type { Fiche } from '../../lib/types'
import { Tip } from '../Tip'
import { BlocIndisponible } from './BlocIndisponible'
import { ViabilisationBlock } from './ViabilisationBlock'
import { GestionnairesBlock } from './GestionnairesBlock'
import { REF, IC, RefDrawer, Line, GroupLabel, Rappel } from './primitives'

function EquipementsBadges({ idu }: { idu: string }) {
  const { data: e } = useQuery({ queryKey: ['equip', idu], queryFn: () => getOrthoEquipements(idu), retry: false })
  if (!e) return null
  const b: [string, string, string][] = []
  if (e['piscine']) b.push([`Piscine ~${e['piscine_m2']} m²`, '#4fc3d9', `détection ortho — confiance ${e['piscine_confiance']}`])
  if (e['pente_moy_deg'] != null) b.push([`Pente ${Math.round(Number(e['pente_non_batie_deg'] ?? e['pente_moy_deg']))}°`,
    e['flag_terrassement_lourd'] ? '#e8734d' : 'var(--lab)',
    `pente moyenne ${e['pente_non_batie_deg'] != null ? 'hors bâti ' : ''}(RGE ALTI 5 m)${e['flag_terrassement_lourd'] ? ' — terrassement lourd probable' : ''}`])
  if (!b.length) return null
  return (
    <div>
      <div className="flex flex-wrap gap-1.5">
        {b.map(([label, color, tip]) => (
          <Tip key={label} tip={tip}>
            <span className="rounded-full px-2 py-0.5 text-[11px] font-medium" style={{ background: `${color}22`, color }}>{label}</span>
          </Tip>
        ))}
      </div>
      <p className="mt-1 text-[9px] text-txt-dim">{String(e['source'] ?? '')}</p>
    </div>
  )
}

export function ReseauxSection({ f, idu }: { f: Fiche; idu: string }) {
  const viabValue = f.viabilisation?.libelle?.replace(/^Viabilisation\s+/i, '') ?? (f.gestionnaires ? 'réseaux renseignés' : '—')
  const viabColor = f.viabilisation?.band === 'confirmee' ? REF.ok : REF.gris
  const viabConfirmee = f.viabilisation?.band === 'confirmee'
  const viabContext = f.gestionnaires
    ? [f.gestionnaires.eau?.operateur, f.gestionnaires.assainissement?.operateur, f.gestionnaires.electricite?.gestionnaire].filter(Boolean).join(' · ') || null
    : null
  // ① ACCÈS — le VERDICT vient du moteur `acces` (source unique). Plus de phrase codée en dur.
  const accesLignes = f.lines.filter((l) => l.layer === 'acces')
  const trans = f.proximites
  return (
    <RefDrawer id="viabilisation" icon={IC.viab} name="Réseaux et accès" context={viabContext}
      value={viabConfirmee ? <span className="pill-mint">confirmée</span> : viabValue}
      valueColor={viabConfirmee ? undefined : viabColor}>
      <div className="flex flex-col gap-3">
        {/* caractéristiques du terrain (piscine / pente) — informatif. */}
        <EquipementsBadges idu={idu} />

        {/* ① ACCÈS — un verdict + transport le plus proche. RETOURS-20 Z1·02 : sous-titre → kicker. */}
        <div data-bloc-acces>
          <GroupLabel>Accès</GroupLabel>
          {accesLignes.length > 0
            ? <div className="flex flex-col gap-1">{accesLignes.map((l, i) => <Line key={i} line={l} hideWeight hideDate />)}</div>
            : <p className="text-[11px] text-txt-dim">Accès non évalué sur cette parcelle.</p>}
          {trans?.indisponible && <div className="mt-1"><BlocIndisponible titre="Proximités (transport)" /></div>}
          {trans && !trans.indisponible && (trans.arret || trans.pole || trans.telepherique) && (
            <div data-proximites-transport className="mt-1.5 flex flex-col gap-1 text-[11.5px] leading-snug text-txt">
              <p className="text-[11px] font-semibold text-txt-hi">Transport public — au plus proche</p>
              {trans.arret && <p>Arrêt « {trans.arret.nom} » ({trans.arret.reseau}) à ~{fmtDistanceM(trans.arret.distance_m)}.</p>}
              {trans.pole && (
                <p>Pôle d’échange « {trans.pole.nom} » à ~{fmtDistanceM(trans.pole.distance_m)}{' '}
                  <b className="text-txt-hi">{trans.pole.statut}</b> ({trans.pole.source}
                  {trans.pole.nb_lignes ? `, ${trans.pole.nb_lignes} lignes` : ''})
                  {trans.pole.concordance === 'osm_seul' && <span className="text-txt-dim"> — la desserte GTFS ne confirme pas ce pôle (sources discordantes, dit tel quel)</span>}
                  {trans.pole.concordance === 'gtfs_seul' && <span className="text-txt-dim"> — aucune station OSM à proximité (sources discordantes, dit tel quel)</span>}.
                </p>
              )}
              {trans.telepherique && <p>Téléphérique Papang — station « {trans.telepherique.station} » à ~{fmtDistanceM(trans.telepherique.distance_m)} <span className="text-txt-dim">(tracé {trans.telepherique.licence})</span>.</p>}
            </div>
          )}
          {/* RETOURS-13 R5 — STATION TCSP : le plafond de stationnement de l'art. L151-36 (800 m
              depuis la STATION, à vol d'oiseau) s'impose au PLU — un fait qui change la valeur.
              Mis en avant quand < 800 m ; ce qui reste à instruire (qualité de la desserte) est dit. */}
          {/* RETOURS-20 Z3 — la boîte bordée TCSP devient un RAPPEL (fond un cran plus clair, sans
              bordure) ; libellé et source inchangés. */}
          {trans && !trans.indisponible && trans.tcsp && (
            <div data-proximite-tcsp className="mt-1.5">
              <Rappel src={trans.tcsp.source}>{trans.tcsp.libelle}</Rappel>
            </div>
          )}
        </div>

        {/* ② RÉSEAUX — gestionnaires eau · assainissement · élec (contact admin, DT-DICT). */}
        {f.gestionnaires && <GestionnairesBlock g={f.gestionnaires} />}

        {/* ③ VIABILISATION — indicateur + faisceau de preuves (accordéon) + ANC. */}
        {f.viabilisation && <ViabilisationBlock via={f.viabilisation} anc={f.anc} />}

        {/* ④ AXES ET NUISANCES — l'axe structurant le plus proche (les deux faces). RETOURS-20 Z1·02 /
            Z3 : sous-titre → kicker, la boîte bordée → rappel. Libellé et source inchangés. */}
        {f.proximites?.axe && (
          <div data-proximite-axe>
            <GroupLabel>Axes et nuisances</GroupLabel>
            <Rappel src={f.proximites.axe.source}>{f.proximites.axe.libelle}</Rappel>
          </div>
        )}
      </div>
    </RefDrawer>
  )
}
