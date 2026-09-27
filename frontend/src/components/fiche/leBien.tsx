/**
 * fiche/leBien.tsx — FICHE-1 lot 1, tiroir « Le bien ».
 * Le bâtiment EXISTANT de la parcelle : emprise bâtie au sol (BD TOPO), nombre de bâtiments,
 * hauteur du bâti, surface au sol libre restante, et nature/pente du toit (LiDAR HD, cache seul).
 * Trois états jamais confondus (RETOURS-15 U5) : servie · « non déterminée » · « non calculée » —
 * portés par le back (le_bien.toit.verdict/libelle). Le tiroir s'OMET si rien n'est évaluable
 * (couche bâtiments non ingérée → le_bien=null). Auto-suffisant, n'importe que des primitives.
 *
 * FICHE-RANGEMENT-2 Lot 1 (étape 3) — le contenu est découpé en BLOCS FEUILLES exportés, pour que
 * les nouvelles sections par nature les composent : BatiBlock → §3 Bâti, TerrainDuBienBlock → §2
 * Terrain (surface libre + OCS GE), FiliationBlock → §1 Identité. LeBienSection les compose encore
 * (transition non-breaking ; le tiroir « Le bien » sera dissous à l'étape 4).
 */
import type { Fiche } from '../../lib/types'
import { fmtInt, fmtDateNum } from '../../lib/format'
import { IC, RefDrawer, FactRow, FactNote, GroupLabel } from './primitives'
import { Badge } from '../ui/Badge'
// KELFONCIER-FIX-2 (Partie B, Lot F) — les blocs Bâti/Terrain composent désormais les FORMES de la
// maquette v3 (Verdict · Tuiles · Lignes · Repli). Aucune donnée recalculée : les valeurs, hauteurs,
// verdicts « terrain nu » viennent servis par le back et sont réagencés tels quels.
import { Verdict, Tuiles, type Tuile, Lignes, Ligne, Repli } from './formes'

type Etab = NonNullable<Fiche['etablissements']>['liste'][number]
/** Une ligne Établissement (SIRENE) — nom masqué en italique, NAF · effectif · état · régime collectif. */
function EtabLigne({ e }: { e: Etab }) {
  return (
    <Ligne
      label={<span className={e.nom_masque ? 'italic opacity-70' : ''}>{e.nom}</span>}
      valeur={<>{e.naf_label ?? e.naf ?? '—'}
        {e.tranche_effectif ? <> <small>· {e.tranche_effectif}</small></> : null}
        {!e.actif ? <> <small className="text-txt-dim">· fermé</small></> : null}
        {e.regime_collectif ? <> <small className="text-st-ecartee">· {e.regime_collectif.libelle}</small></> : null}</>} />
  )
}

// verdicts de forme réellement SERVIS (les autres = états « non déterminée » / « non calculée »).
const TOIT_SERVI = new Set(['plat', 'monopente', 'double_pente', 'croupe_complexe'])

/** hauteur MESURÉE (LiDAR HD) en phrase courte pour le résumé replié (RECETTE-12 C2). */
export function hauteurBienMesuree(b: NonNullable<Fiche['le_bien']>): string | null {
  return b.hauteur_nature === 'sourcé' && b.hauteur_faitage_m != null
    ? `faîtage ${b.hauteur_faitage_m} m mesuré (LiDAR HD${b.hauteur_survol ? `, survol ${b.hauteur_survol}` : ''})`
    : null
}

/** §3 Bâti — le bâti existant : emprise, CoSIA, nb, hauteur, DPE, toit, RNB, établissements.
 *  KELFONCIER-FIX-2 (Lot F) — mis en formes maquette v3 : Verdict + Tuiles d'en-tête, puis Lignes de
 *  détail (aucune donnée perdue), Repli au-delà de 3 établissements. Terrain nu = Verdict + ligne
 *  « aucun établissement ». Les valeurs et le verdict « terrain nu » sont servis par le back. */
export function BatiBlock({ f }: { f: Fiche }) {
  const b = f.le_bien
  if (!b || !b.disponible) return null
  const dpe = f.dpe_connu
  const emprise = b.emprise_batie_m2
  const nb = b.nb_batiments
  const toit = b.toit
  const toitServi = !!toit && TOIT_SERVI.has(toit.verdict)
  const bati = (nb != null && nb > 0) || emprise > 0
  const faitageSourced = b.hauteur_nature === 'sourcé' && b.hauteur_faitage_m != null
  const etab = f.etablissements
  const etabList = etab?.liste ?? []

  // ── Tuiles d'en-tête (bâti présent) : emprise · hauteur · nb · toit. ──
  const tuiles: Tuile[] = []
  if (bati) {
    tuiles.push({ label: 'Emprise bâtie au sol',
      valeur: emprise > 0 ? <>{fmtInt(emprise)} <small>m²</small></> : '—',
      ton: emprise > 0 ? undefined : 'gris', sous: b.emprise_source })
    tuiles.push(faitageSourced
      ? { label: 'Faîtage (LiDAR)', valeur: <>{b.hauteur_faitage_m} <small>m</small></>, sous: 'haut de toit',
          ton: b.hauteur_discordante && b.hauteur_discordance_motif === 'faîtage aberrant' ? 'ambre' : undefined }
      : { label: 'Hauteur du bâti',
          valeur: b.hauteur_bati_m != null ? <>{b.hauteur_bati_m} <small>m</small></> : 'non déterminée',
          ton: b.hauteur_bati_m != null ? undefined : 'gris', sous: b.hauteur_bati_m != null ? 'BD TOPO' : undefined })
    tuiles.push({ label: 'Nombre de bâtiments', valeur: nb != null ? String(nb) : 'non déterminé', ton: nb != null ? undefined : 'gris' })
    tuiles.push({ label: 'Nature du toit', valeur: toit ? toit.libelle : 'non disponible',
      ton: toitServi ? undefined : 'gris', sous: toit?.pente_mediane_deg != null ? `${Math.round(toit.pente_mediane_deg)}° de pente` : undefined })
  }

  return (
    <div className="flex flex-col gap-3" data-le-bien>
      {/* Verdict — restitution de faits servis (occupation, emprise, hauteur), aucun recalcul. */}
      {bati ? (
        <Verdict ton="vert" reponse={b.occupation_label || `${nb ?? ''} bâtiment${(nb ?? 0) > 1 ? 's' : ''}`}
          contexte={[emprise > 0 ? `emprise ${fmtInt(emprise)} m²` : null,
            faitageSourced ? `faîtage ${b.hauteur_faitage_m} m mesuré (LiDAR)` : null].filter(Boolean).join(' · ') || undefined} />
      ) : (
        <Verdict ton="vert" reponse="Terrain nu"
          contexte={`aucun bâtiment BD TOPO, aucune hauteur LiDAR${etabList.length ? '' : ', aucun établissement rattaché'}`} />
      )}

      {bati && <Tuiles items={tuiles} />}

      {/* DONNEES-FIX-1 lot A — égout LiDAR + hauteur BD TOPO : la même grandeur que le badge de
          discordance (jamais le faîtage, plus haut par construction sur un toit en pente / R+n). */}
      {faitageSourced && (b.hauteur_egout_m != null || b.hauteur_bdtopo_m != null) && (
        <Lignes>
          {b.hauteur_egout_m != null && (
            <Ligne label="Égout mesuré (LiDAR)" valeur={<>{b.hauteur_egout_m} <small>m — bord de toit</small></>}
              ton={b.hauteur_discordante && b.hauteur_discordance_motif === 'égout ↔ BD TOPO' ? 'ambre' : undefined} />
          )}
          {b.hauteur_bdtopo_m != null && (
            <Ligne label="Hauteur BD TOPO (≈ égout)" valeur={<>{b.hauteur_bdtopo_m} <small>m</small></>}
              ton={b.hauteur_discordante && b.hauteur_discordance_motif === 'égout ↔ BD TOPO' ? 'ambre' : undefined} />
          )}
        </Lignes>
      )}

      {b.hauteur_discordante && (
        <div data-hauteur-discordante>
          <Badge ton="ambre">Sources discordantes</Badge>
          <p className="mt-0.5 text-[11px] leading-snug text-amber">
            {b.hauteur_discordance_motif === 'faîtage aberrant'
              ? <>Faîtage mesuré {b.hauteur_faitage_m} m — valeur physiquement impossible, mesure à écarter.</>
              : <>Égout LiDAR {b.hauteur_egout_m} m · BD TOPO {b.hauteur_bdtopo_m} m — écart{b.ecart_egout_bdtopo_m != null ? ` de ${Math.abs(b.ecart_egout_bdtopo_m)} m` : ''} sur la même grandeur, à vérifier sur photo aérienne.</>}
          </p>
        </div>
      )}

      {/* Faits complémentaires (aucune donnée perdue) : CoSIA détecté · DPE · pente toit · BAN PLUS. */}
      {(b.cosia_detecte_m2 != null || dpe || (toitServi && toit?.pente_mediane_deg != null)
        || (b.adresses_bati && (b.adresses_bati.adresses > 0 || b.adresses_bati.batiments > 0))) && (
        <Lignes>
          {b.cosia_detecte_m2 != null && (
            <Ligne label="Bâti détecté (CoSIA)" ton="gris"
              valeur={<>~{fmtInt(b.cosia_detecte_m2)} <small>m² — non cartographié BD TOPO, à vérifier</small></>} />
          )}
          {dpe && (
            <Ligne label="DPE du bâtiment"
              valeur={<>{dpe.etiquette}{dpe.etiquette_ges ? <> / GES {dpe.etiquette_ges}</> : null}
                {dpe.annee ? <> <small>({dpe.annee})</small></> : null}</>} />
          )}
          {toitServi && toit?.pente_mediane_deg != null && (
            <Ligne label="Pente du toit" valeur={<>{Math.round(toit.pente_mediane_deg)}<small>°</small></>} />
          )}
          {b.adresses_bati && (b.adresses_bati.adresses > 0 || b.adresses_bati.batiments > 0) && (
            <Ligne label="Adresses BAN PLUS"
              valeur={<>{b.adresses_bati.adresses} <small>adresse{b.adresses_bati.adresses > 1 ? 's' : ''} · {b.adresses_bati.batiments} bâtiment{b.adresses_bati.batiments > 1 ? 's' : ''}</small></>} />
          )}
        </Lignes>
      )}

      {toitServi && toit?.methode && <FactNote>{toit.methode}</FactNote>}

      {/* REPARATIONS-1 lot 4 — RNB ID (Référentiel National des Bâtiments) de chaque bâtiment. */}
      {(b.rnb?.length ?? 0) > 0 && (
        <div data-le-bien-rnb>
          <GroupLabel>Identifiant national du bâtiment (RNB)</GroupLabel>
          <Lignes>
            {b.rnb!.map((r) => (
              <Ligne key={r.rnb_id} label="RNB"
                valeur={<a href={r.lien} target="_blank" rel="noreferrer"
                  className="font-mono text-[12px] hover:underline">{r.rnb_id} ↗</a>} />
            ))}
          </Lignes>
        </div>
      )}

      {/* KELFONCIER-FIX-1 (Lot H) — ÉTABLISSEMENTS (SIRENE, rattachés par l'adresse BAN). Les 3
          premiers visibles, le reste derrière un Repli (aucune donnée cachée). */}
      {etab && etab.n > 0 ? (
        <div data-etablissements>
          <GroupLabel>Établissements sur la parcelle{etab.n > etab.affiches
            ? ` (${etab.affiches} sur ${etab.n})` : ` (${etab.n})`}</GroupLabel>
          <Lignes>{etabList.slice(0, 3).map((e) => <EtabLigne key={e.siret} e={e} />)}</Lignes>
          {etabList.length > 3 && (
            <Repli compteur={etabList.length - 3} label="autres établissements">
              <Lignes>{etabList.slice(3).map((e) => <EtabLigne key={e.siret} e={e} />)}</Lignes>
            </Repli>
          )}
          <FactNote>{etab.note}</FactNote>
        </div>
      ) : (!bati && (
        <Lignes><Ligne label="Établissements sur la parcelle" valeur={<>aucun <small>SIRENE, adresse exacte</small></>} ton="gris" /></Lignes>
      ))}

      <FactNote>Bâti existant — {b.source_bati}. Information de fiche, jamais un signal de classement.</FactNote>
    </div>
  )
}

/** §2 Terrain — ce qui touche le sol : surface au sol libre + artificialisation (OCS GE). */
export function TerrainDuBienBlock({ f }: { f: Fiche }) {
  const b = f.le_bien
  if (!b || !b.disponible) return null
  return (
    <div data-le-bien-terrain>
      <FactRow label="Surface au sol libre"
        value={b.surface_libre_m2 != null ? <>{fmtInt(b.surface_libre_m2)} <small>m²</small></> : 'non déterminée'}
        tone={b.surface_libre_m2 != null ? undefined : 'mute'} />
      {/* REPARATIONS-1 lot 5 — artificialisation OFFICIELLE (OCS GE, donnée d'îlot), aucun effet score. */}
      {b.ocsge?.part_artif_pct != null && (
        <FactRow label="Sol artificialisé" value={<>{b.ocsge.part_artif_pct.toLocaleString('fr-FR')}<small> % — d'après OCS GE {b.ocsge.millesime}</small></>}
          src={b.ocsge.source} />
      )}
      {/* DONNEES-2 — CoSIA COMPLÈTE OCS GE : couverture du sol de la parcelle à 20 cm, 3 parts en
          complément (ni doublon ni remplacement : imperméabilisé ≠ artificialisé, maille = parcelle). */}
      {b.cosia_couverture && (
        <>
          {b.cosia_couverture.part_impermeabilisee_pct != null && (
            <FactRow label="Part imperméabilisée" value={<>{b.cosia_couverture.part_impermeabilisee_pct.toLocaleString('fr-FR')}<small> %</small></>}
              src={b.cosia_couverture.source} />
          )}
          {b.cosia_couverture.part_vegetalisee_boisee_pct != null && (
            <FactRow label="Part végétalisée / boisée" value={<>{b.cosia_couverture.part_vegetalisee_boisee_pct.toLocaleString('fr-FR')}<small> %</small></>}
              src={b.cosia_couverture.source} />
          )}
          {b.cosia_couverture.part_sol_nu_pct != null && (
            <FactRow label="Part sol nu" value={<>{b.cosia_couverture.part_sol_nu_pct.toLocaleString('fr-FR')}<small> %</small></>}
              src={b.cosia_couverture.source} />
          )}
        </>
      )}
    </div>
  )
}

/** §1 Identité — historique cadastral officiel (filiation DFI).
 *  FICHE-FIX-4 (Lot C) — chaque filiation en une Ligne (« Issue de » / « A donné », valeur qui passe
 *  à la ligne proprement), le paragraphe de méthode passe en source (FactNote). */
export function FiliationBlock({ f }: { f: Fiche }) {
  if (!f.filiation) return null
  const fi = f.filiation
  return (
    <div data-le-bien-filiation>
      <GroupLabel>Filiation cadastrale</GroupLabel>
      <Lignes>
        {fi.meres?.map((m) => (
          <Ligne key={`m-${m.idu}-${m.date}`} label="Issue de"
            valeur={<>{m.idu}{m.date ? <small> · {fmtDateNum(m.date)}</small> : null}{m.nature ? <small> · {m.nature}</small> : null}</>} />
        ))}
        {fi.filles?.map((x) => (
          <Ligne key={`f-${x.idu}-${x.date}`} label="A donné"
            valeur={<>{x.idu}{x.date ? <small> · {fmtDateNum(x.date)}</small> : null}{x.nature ? <small> · {x.nature}</small> : null}</>} />
        ))}
      </Lignes>
      <FactNote>{fi.division_recente ? 'Division récente (événement ≥ 2023) — signal de mouvement foncier. ' : ''}{fi.source}. Contrôle croisé avec le cadastre d'époque (géométrie) — deux canaux, jamais un conflit.</FactNote>
    </div>
  )
}

export function LeBienSection({ f }: { f: Fiche; idu: string }) {
  const b = f.le_bien
  if (!b || !b.disponible) return null   // rien d'évaluable → pas de bloc creux
  const nb = b.nb_batiments
  const hauteurMesuree = hauteurBienMesuree(b)
  const contexteBien = hauteurMesuree
    ? `${b.occupation_label || 'bâti existant'} · ${hauteurMesuree}`
    : (b.occupation_label || 'bâti existant')
  return (
    <RefDrawer id="le_bien" icon={IC.faisa} name="Le bien"
      context={contexteBien}
      value={nb != null && nb > 0
        ? <Badge ton="vert">{nb} bâtiment{nb > 1 ? 's' : ''}</Badge>
        : <Badge ton="vert">terrain nu</Badge>}>
      <div className="flex flex-col gap-3">
        <BatiBlock f={f} />
        <TerrainDuBienBlock f={f} />
        <FiliationBlock f={f} />
      </div>
    </RefDrawer>
  )
}
