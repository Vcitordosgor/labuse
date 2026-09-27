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
import { BlocIndisponible } from './BlocIndisponible'
import { ViabilisationBlock, assainissementResume } from './ViabilisationBlock'
import { GestionnairesBlock } from './GestionnairesBlock'
import { IC, RefDrawer, Line, GroupLabel } from './primitives'
import { Badge } from '../ui/Badge'
// KELFONCIER-FIX-2 (Lot H) — maquette v3 : Verdict + CasesEtat (glance eau·élec / fibre / bus /
// assainissement), le détail (accès, gestionnaires, viabilisation…) reste rendu en dessous.
import { Verdict, CasesEtat, type CaseEtat, Lignes, Ligne, InfoI } from './formes'

// RETOURS-23 — les caractéristiques du terrain (piscine / pente) vivent SOUS un kicker « Terrain »
// comme les autres faits : valeur chiffrée à droite en mono, source sous la ligne (pente en ambre
// quand terrassement lourd probable). Donnée inchangée (mêmes chiffres, même source ortho).
export function EquipementsBadges({ idu }: { idu: string }) {
  const { data: e } = useQuery({ queryKey: ['equip', idu], queryFn: () => getOrthoEquipements(idu), retry: false })
  if (!e || !e['piscine']) return null
  // FICHE-FIX-5 (Lot D) — sous-bloc « Détections » : la piscine en une Ligne « Piscine ~N m² ·
  // confiance X », la méthode (BD ORTHO) derrière le « i ». La pente vit dans la tuile d'en-tête.
  return (
    <div data-terrain>
      <GroupLabel>Détections</GroupLabel>
      <Lignes>
        <Ligne label={<>Piscine<InfoI aria="Sur la détection piscine" tip={`Détection par imagerie ortho (BD ORTHO IGN)${e['source'] ? ` · ${String(e['source'])}` : ''}.`} /></>}
          valeur={<>~{e['piscine_m2']} <small>m² · confiance {String(e['piscine_confiance']).replace('.', ',')}</small></>} />
      </Lignes>
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
  // KELFONCIER-FIX-2 (Lot H) — glance CasesEtat, dérivé de faits DÉJÀ servis (aucun calcul de score).
  const cases: CaseEtat[] = []
  if (viabMot) cases.push({ etat: viabMot.ton === 'vert' ? 'ok' : 'q', label: 'Eau/élec', valeur: viabMot.mot })
  if (f.fibre) cases.push({ etat: f.fibre.ftth ? 'ok' : (f.fibre.etat === 'servi' ? 'ko' : 'q'), label: 'Fibre',
    valeur: f.fibre.ftth ? 'FttH' : (f.fibre.distance_m != null ? `${f.fibre.distance_m} m` : '—') })
  if (trans?.arret) cases.push({ etat: 'ok', label: 'Bus', valeur: fmtDistanceM(trans.arret.distance_m) })
  cases.push({ etat: assain.ton === 'vert' ? 'ok' : 'q', label: 'Assainis.', valeur: assain.court })
  return (
    <RefDrawer id="reseaux" icon={IC.viab} name="Réseaux et desserte" context={viabContext}
      value={viabBadge}>
      <div className="flex flex-col gap-3">
        {/* KELFONCIER-FIX-2 (Lot H) — Verdict (viabilisation servie) + CasesEtat en glance. Le détail
            (accès, transport, gestionnaires, viabilisation, axes…) reste rendu en dessous, inchangé. */}
        <Verdict ton={viabMot?.ton === 'vert' ? 'vert' : viabMot?.ton === 'ambre' ? 'ambre' : 'gris'}
          reponse={viabMot ? `Viabilisation eau/élec ${viabMot.mot}` : (f.gestionnaires ? 'Réseaux renseignés' : 'Réseaux non renseignés')}
          contexte={(f.gestionnaires || f.viabilisation || f.anc) ? `assainissement ${assain.court}` : undefined} />
        {cases.length > 0 && <CasesEtat cases={cases} />}
        {/* FICHE-RANGEMENT-2 Lot 1 — les caractéristiques du terrain (piscine, EquipementsBadges) sont
            relocalisées en §2 Terrain ; §6 Réseaux et desserte ne porte plus que réseaux/accès/desserte. */}

        {/* FICHE-FIX-4 (Lot H) — toute la desserte en Lignes : fibre, arrêt/ligne/pôle, TCSP, trafic.
            Les paragraphes (détail Arcep, discordance de pôle, plafond L151-36, sources) passent
            derrière le « i ». Aucune donnée retirée. */}
        <Lignes>
          {f.fibre && (
            <Ligne ton={f.fibre.etat === 'servi' ? (f.fibre.ftth ? undefined : 'gris') : 'gris'}
              label={<>Fibre (Arcep)<InfoI aria="Sur la fibre" tip={`${f.fibre.etat === 'servi' ? `Immeuble Arcep le plus proche à ~${f.fibre.distance_m} m.${f.fibre.operateurs?.length ? ` Opérateurs : ${f.fibre.operateurs.join(', ')}.` : ''}` : (f.fibre.detail ?? '')} Arcep, Ma connexion internet (${f.fibre.millesime}).`} /></>}
              valeur={f.fibre.etat === 'servi'
                ? <>{f.fibre.ftth ? 'FttH' : 'non FttH'}{f.fibre.distance_m != null ? <small> · {f.fibre.distance_m} m</small> : null}{f.fibre.ftth && f.fibre.operateurs?.length ? <small> · {f.fibre.operateurs.length} op.</small> : null}</>
                : 'non renseignée'} />
          )}
          {trans?.arret && <Ligne label="Arrêt de bus" title={trans.arret.nom} valeur={<>{trans.arret.nom}<small> · {fmtDistanceM(trans.arret.distance_m)}</small></>} />}
          {trans?.transport_ligne && <Ligne label="Ligne de transport" valeur={<>{trans.transport_ligne.reseau ?? 'ligne'}<small> · {fmtDistanceM(trans.transport_ligne.distance_m)}</small></>} />}
          {trans?.pole && (
            <Ligne title={trans.pole.nom}
              label={<>Pôle d’échange{(trans.pole.concordance === 'osm_seul' || trans.pole.concordance === 'gtfs_seul') ? <InfoI aria="Sur le pôle" tip={trans.pole.concordance === 'osm_seul' ? 'La desserte GTFS ne confirme pas ce pôle (sources discordantes).' : 'Aucune station OSM à proximité (sources discordantes).'} /> : null}</>}
              valeur={<>{trans.pole.nom}<small> · {fmtDistanceM(trans.pole.distance_m)}</small></>} />
          )}
          {trans?.telepherique && <Ligne label="Téléphérique Papang" valeur={<>{trans.telepherique.station}<small> · {fmtDistanceM(trans.telepherique.distance_m)}</small></>} />}
          {trans?.tcsp && (
            <Ligne ton={trans.tcsp.sous_800m ? 'vert' : undefined} title={trans.tcsp.station}
              label={<>Stationnement allégé (TCSP)<InfoI aria="Sur le TCSP" tip={`${trans.tcsp.libelle} ${trans.tcsp.source}`} /></>}
              valeur={<>{trans.tcsp.sous_800m ? 'rayon 800 m' : 'hors rayon'}<small> · {trans.tcsp.distance_m} m</small></>} />
          )}
          {f.trafic_rn?.disponible && (
            <Ligne label={<>Trafic {f.trafic_rn.route}<InfoI aria="Sur le trafic" tip={`${f.trafic_rn.source}${f.trafic_rn.millesime ? ` · ${f.trafic_rn.millesime}` : ''}`} /></>}
              valeur={<>{f.trafic_rn.tmja?.toLocaleString('fr-FR')} <small>véh./j{f.trafic_rn.poids_lourds != null ? ` · ${f.trafic_rn.poids_lourds.toLocaleString('fr-FR')} PL` : ''}</small></>} />
          )}
        </Lignes>

        {/* ① ACCÈS — le verdict d'accès (moteur `acces`) reste en primitive Line (fait scoré + source). */}
        {(accesLignes.length > 0 || trans?.indisponible) && (
          <div data-bloc-acces>
            <GroupLabel>Accès</GroupLabel>
            {accesLignes.length > 0 && <div className="flex flex-col gap-1">{accesLignes.map((l, i) => <Line key={i} line={l} hideWeight hideDate />)}</div>}
            {trans?.indisponible && <div className="mt-1"><BlocIndisponible titre="Proximités (transport)" /></div>}
          </div>
        )}

        {/* ② RÉSEAUX — gestionnaires eau · assainissement · élec (contact admin, DT-DICT). */}
        {f.gestionnaires && <GestionnairesBlock g={f.gestionnaires} />}

        {/* ③ VIABILISATION — indicateur + faisceau de preuves (accordéon) + ANC. */}
        {f.viabilisation && <ViabilisationBlock via={f.viabilisation} anc={f.anc} />}

        {/* FICHE-FIX-4 (Lot H) — axe structurant + raccordement électrique en Lignes (source en « i »). */}
        {(f.proximites?.axe || f.proximites?.poste_transformation) && (
          <Lignes>
            {f.proximites?.axe && (
              <Ligne title={f.proximites.axe.libelle}
                label={<>Axe structurant<InfoI aria="Sur l'axe" tip={f.proximites.axe.source} /></>}
                valeur={f.proximites.axe.libelle} />
            )}
            {f.proximites?.poste_transformation && (
              <Ligne title={f.proximites.poste_transformation.libelle}
                label={<>Raccordement élec.<InfoI aria="Sur le raccordement" tip={f.proximites.poste_transformation.source} /></>}
                valeur={f.proximites.poste_transformation.libelle} />
            )}
          </Lignes>
        )}
      </div>
    </RefDrawer>
  )
}
