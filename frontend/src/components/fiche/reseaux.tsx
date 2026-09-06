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
import type { ReactNode } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getOrthoEquipements } from '../../lib/api'
import { fmtDistance as fmtDistanceM } from '../../lib/geo'
import type { Fiche } from '../../lib/types'
import { BlocIndisponible } from './BlocIndisponible'
import { ViabilisationBlock } from './ViabilisationBlock'
import { GestionnairesBlock } from './GestionnairesBlock'
import { REF, IC, RefDrawer, Line, GroupLabel, FactRow, FactNote } from './primitives'

// RETOURS-23 — les caractéristiques du terrain (piscine / pente) vivent SOUS un kicker « Terrain »
// comme les autres faits : valeur chiffrée à droite en mono, source sous la ligne (pente en ambre
// quand terrassement lourd probable). Donnée inchangée (mêmes chiffres, même source ortho).
function EquipementsBadges({ idu }: { idu: string }) {
  const { data: e } = useQuery({ queryKey: ['equip', idu], queryFn: () => getOrthoEquipements(idu), retry: false })
  if (!e) return null
  const rows: { label: string; value: ReactNode; tone?: 'warn'; src?: string }[] = []
  if (e['piscine']) rows.push({ label: 'Piscine', value: <>~{e['piscine_m2']} <small>m²</small></>,
    src: `détection ortho — confiance ${e['piscine_confiance']}` })
  if (e['pente_moy_deg'] != null) rows.push({ label: 'Pente',
    value: <>{Math.round(Number(e['pente_non_batie_deg'] ?? e['pente_moy_deg']))}<small>°</small></>,
    tone: e['flag_terrassement_lourd'] ? 'warn' : undefined,
    src: `pente moyenne ${e['pente_non_batie_deg'] != null ? 'hors bâti ' : ''}(RGE ALTI 5 m)${e['flag_terrassement_lourd'] ? ' — terrassement lourd probable' : ''}` })
  if (!rows.length) return null
  return (
    <div data-terrain>
      <GroupLabel>Terrain</GroupLabel>
      {rows.map((r) => <FactRow key={r.label} label={r.label} value={r.value} tone={r.tone} src={r.src} />)}
      {e['source'] ? <FactNote>{String(e['source'])}</FactNote> : null}
    </div>
  )
}

export function ReseauxSection({ f, idu }: { f: Fiche; idu: string }) {
  const viabValue = f.viabilisation?.libelle?.replace(/^Viabilisation\s+/i, '') ?? (f.gestionnaires ? 'réseaux renseignés' : '—')
  const viabColor = f.viabilisation?.band === 'confirmee' ? REF.ok : REF.gris
  const viabConfirmee = f.viabilisation?.band === 'confirmee'
  // RETOURS-23 — l'en-tête ne répète plus le CORPS : le sous-titre nommait l'opérateur d'eau
  // (« CISE Réunion (SAUR)… », tronqué) alors que le gestionnaire est détaillé trois lignes plus bas.
  // On donne la PORTÉE de la section (catégories), pas une valeur re-dite dans les gestionnaires.
  const viabContext = (f.gestionnaires || f.viabilisation) ? 'eau · assainissement · élec' : null
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
          {/* RETOURS-23 — plus aucun cadre : fait à plat (phrase + source en note), le kicker « Accès »
              sépare déjà. Libellé et source inchangés. */}
          {trans && !trans.indisponible && trans.tcsp && (
            <div data-proximite-tcsp className="mt-1.5">
              <p className="text-[11.5px] leading-snug text-txt">{trans.tcsp.libelle}</p>
              <FactNote>{trans.tcsp.source}</FactNote>
            </div>
          )}
        </div>

        {/* ② RÉSEAUX — gestionnaires eau · assainissement · élec (contact admin, DT-DICT). */}
        {f.gestionnaires && <GestionnairesBlock g={f.gestionnaires} />}

        {/* ③ VIABILISATION — indicateur + faisceau de preuves (accordéon) + ANC. */}
        {f.viabilisation && <ViabilisationBlock via={f.viabilisation} anc={f.anc} />}

        {/* ④ AXES ET NUISANCES — l'axe structurant le plus proche (les deux faces). RETOURS-23 : plus
            de cadre (le pavé gardait sa boîte) — kicker + fait à plat + source en note. Inchangé. */}
        {f.proximites?.axe && (
          <div data-proximite-axe>
            <GroupLabel>Axes et nuisances</GroupLabel>
            <p className="text-[11.5px] leading-snug text-txt">{f.proximites.axe.libelle}</p>
            <FactNote>{f.proximites.axe.source}</FactNote>
          </div>
        )}
      </div>
    </RefDrawer>
  )
}
