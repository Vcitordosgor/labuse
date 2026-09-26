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
import { ViabilisationBlock, assainissementResume } from './ViabilisationBlock'
import { GestionnairesBlock } from './GestionnairesBlock'
import { IC, RefDrawer, Line, GroupLabel, FactRow, FactNote } from './primitives'
import { Badge } from '../ui/Badge'

// RETOURS-23 — les caractéristiques du terrain (piscine / pente) vivent SOUS un kicker « Terrain »
// comme les autres faits : valeur chiffrée à droite en mono, source sous la ligne (pente en ambre
// quand terrassement lourd probable). Donnée inchangée (mêmes chiffres, même source ortho).
export function EquipementsBadges({ idu }: { idu: string }) {
  const { data: e } = useQuery({ queryKey: ['equip', idu], queryFn: () => getOrthoEquipements(idu), retry: false })
  if (!e) return null
  const rows: { label: string; value: ReactNode; tone?: 'warn'; src?: string }[] = []
  if (e['piscine']) rows.push({ label: 'Piscine', value: <>~{e['piscine_m2']} <small>m²</small></>,
    src: `détection ortho — confiance ${e['piscine_confiance']}` })
  // FICHE-RANGEMENT-1 Lot 1 (doublon #4) — la PENTE vit UNE fois, dans la tuile d'en-tête « Pente »
  // (triage glance, même source RGE ALTI ; son sous-titre dit plat/modérée/forte/très forte). On ne
  // la répète plus ici ; « Terrain » ne garde que la piscine (fait propre à l'ortho).
  if (!rows.length) return null
  return (
    <div data-terrain>
      <GroupLabel>Terrain</GroupLabel>
      {rows.map((r) => <FactRow key={r.label} label={r.label} value={r.value} tone={r.tone} src={r.src} />)}
      {e['source'] ? <FactNote>{String(e['source'])}</FactNote> : null}
    </div>
  )
}

// FICHE-FIX-2 P1 — le badge d'en-tête ne couvre QUE ce que le score de viabilisation teste :
// eau/élec (permis proches + voie + bâti + zone PLU). L'assainissement N'ENTRE PAS dans le score
// (viabilisation.py compute_score) ; il vit à part, sourcé du zonage SIG (anc). Deux faits distincts.
const VIAB_MOT: Record<string, { mot: string; ton: 'vert' | 'ambre' | 'neutre' }> = {
  confirmee:  { mot: 'confirmée',    ton: 'vert' },
  probable:   { mot: 'probable',     ton: 'ambre' },
  incertaine: { mot: 'à confirmer',  ton: 'neutre' },
  lourde:     { mot: 'à confirmer',  ton: 'ambre' },
}

export function ReseauxSection({ f }: { f: Fiche; idu: string }) {
  // FICHE-FIX-2 P1 — deux faits distincts dans l'en-tête :
  //   ① le badge = viabilisation EAU/ÉLEC (le score, rattaché à ce qu'il teste) ;
  //   ② le sous-titre = ASSAINISSEMENT (zonage SIG sourcé, hors score).
  const viabMot = f.viabilisation ? (VIAB_MOT[f.viabilisation.band] ?? VIAB_MOT.incertaine) : null
  const assain = assainissementResume(f.anc)
  const viabBadge = viabMot ? <Badge ton={viabMot.ton}>eau/élec {viabMot.mot}</Badge>
    : (f.gestionnaires ? <Badge ton="neutre">réseaux renseignés</Badge> : undefined)
  const viabContext = (f.gestionnaires || f.viabilisation || f.anc)
    ? `Assainissement : ${assain.court}` : null
  // ① ACCÈS — le VERDICT vient du moteur `acces` (source unique). Plus de phrase codée en dur.
  const accesLignes = f.lines.filter((l) => l.layer === 'acces')
  const trans = f.proximites
  return (
    <RefDrawer id="reseaux" icon={IC.viab} name="Réseaux et desserte" context={viabContext}
      value={viabBadge}>
      <div className="flex flex-col gap-3">
        {/* FICHE-RANGEMENT-2 Lot 1 — les caractéristiques du terrain (piscine, EquipementsBadges) sont
            relocalisées en §2 Terrain ; §6 Réseaux et desserte ne porte plus que réseaux/accès/desserte. */}

        {/* SOURCES-1 lot 5 — fibre Arcep : immeuble le plus proche, DISTANCE DITE, jamais un
            booléen nu ; bloc omis si la source n'est pas ingérée (f.fibre absent). */}
        {f.fibre && (
          <div data-bloc-fibre className="flex flex-col gap-0.5">
            <GroupLabel>Fibre (Arcep)</GroupLabel>
            {f.fibre.etat === 'servi' ? (
              <p className="text-[11.5px] leading-snug text-txt">
                Immeuble Arcep à ~{f.fibre.distance_m} m :{' '}
                {f.fibre.ftth
                  ? <><b className="text-txt-hi">raccordable FttH</b>{f.fibre.operateurs && f.fibre.operateurs.length > 0 ? ` (${f.fibre.operateurs.join(', ')})` : ''}</>
                  : <b className="text-txt-hi">non raccordable FttH à ce jour</b>}
                <span className="text-txt-dim"> — Arcep, Ma connexion internet ({f.fibre.millesime}).</span>
              </p>
            ) : (
              <p className="text-[11.5px] text-txt-dim">{f.fibre.detail} — Arcep ({f.fibre.millesime}).</p>
            )}
          </div>
        )}

        {/* RETOUCHES-1 lot C.11 — AXES ET NUISANCES : TMJA de l'axe RN le plus proche (≤ 300 m). */}
        {f.trafic_rn && (
          <div data-trafic-rn className="flex flex-col gap-0.5">
            <GroupLabel>Axes et nuisances (trafic RN)</GroupLabel>
            {f.trafic_rn.disponible ? (
              <p className="text-[11.5px] leading-snug text-txt">
                <b className="text-txt-hi">{f.trafic_rn.route}</b> à ~{f.trafic_rn.distance_m} m —{' '}
                <b className="text-txt-hi">{f.trafic_rn.tmja?.toLocaleString('fr-FR')}</b> véh./j (TMJA)
                {f.trafic_rn.poids_lourds != null ? `, dont ${f.trafic_rn.poids_lourds.toLocaleString('fr-FR')} PL` : ''}.
                <span className="text-txt-dim"> {f.trafic_rn.source}{f.trafic_rn.millesime ? ` · ${f.trafic_rn.millesime}` : ''}.</span>
              </p>
            ) : (
              <p className="text-[11px] text-txt-dim"><span className="text-mint">✓</span> Sans objet — aucune route nationale à moins de {f.trafic_rn.rayon_m} m. <span className="text-txt-dim">({f.trafic_rn.source})</span></p>
            )}
          </div>
        )}

        {/* ① ACCÈS — un verdict + transport le plus proche. RETOURS-20 Z1·02 : sous-titre → kicker. */}
        <div data-bloc-acces>
          <GroupLabel>Accès</GroupLabel>
          {accesLignes.length > 0
            ? <div className="flex flex-col gap-1">{accesLignes.map((l, i) => <Line key={i} line={l} hideWeight hideDate />)}</div>
            : <p className="text-[11px] text-txt-dim">Accès non évalué sur cette parcelle.</p>}
          {trans?.indisponible && <div className="mt-1"><BlocIndisponible titre="Proximités (transport)" /></div>}
          {trans && !trans.indisponible && (trans.arret || trans.pole || trans.telepherique || trans.transport_ligne) && (
            <div data-proximites-transport className="mt-1.5 flex flex-col gap-1 text-[11.5px] leading-snug text-txt">
              <p className="text-[11px] font-semibold text-txt-hi">Transport public — au plus proche</p>
              {trans.arret && <p>Arrêt « {trans.arret.nom} » ({trans.arret.reseau}) à ~{fmtDistanceM(trans.arret.distance_m)}.</p>}
              {/* FICHE-COUCHES-2 lot 1 — tracé de ligne de transport public (desserte). */}
              {trans.transport_ligne && <p data-transport-ligne>Ligne de transport{trans.transport_ligne.reseau ? ` « ${trans.transport_ligne.reseau} »` : ''} à ~{fmtDistanceM(trans.transport_ligne.distance_m)}.</p>}
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
              {/* FICHE-1 lot 4 — « dans le rayon » scannable : pastille + station + distance ; le
                  plafond L151-36 et la référence d'article restent dans le libellé en dessous. */}
              <div className="text-[13px]">
                <span className="font-semibold">Stationnement allégé (TCSP)</span>
                {trans.tcsp.sous_800m
                  ? <Badge ton="vert" className="ml-1.5">dans le rayon 800 m</Badge>
                  : <span className="ml-1.5 text-[11.5px] text-txt-mut">hors rayon</span>}
                <span className="text-txt-mut"> · {trans.tcsp.station} · {trans.tcsp.distance_m} m</span>
              </div>
              <p className="text-[11.5px] leading-snug text-txt mt-0.5">{trans.tcsp.libelle}</p>
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

        {/* GEOPF-3 — POSTE DE TRANSFORMATION le plus proche : signal de coût de raccordement. */}
        {f.proximites?.poste_transformation && (
          <div data-proximite-poste>
            <GroupLabel>Raccordement électrique</GroupLabel>
            <p className="text-[11.5px] leading-snug text-txt">{f.proximites.poste_transformation.libelle}</p>
            <FactNote>{f.proximites.poste_transformation.source}</FactNote>
          </div>
        )}
      </div>
    </RefDrawer>
  )
}
