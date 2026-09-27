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
import { fmtInt } from '../../lib/format'
import { IC, RefDrawer, FactRow, FactNote } from './primitives'
import { Badge } from '../ui/Badge'

// verdicts de forme réellement SERVIS (les autres = états « non déterminée » / « non calculée »).
const TOIT_SERVI = new Set(['plat', 'monopente', 'double_pente', 'croupe_complexe'])

/** hauteur MESURÉE (LiDAR HD) en phrase courte pour le résumé replié (RECETTE-12 C2). */
export function hauteurBienMesuree(b: NonNullable<Fiche['le_bien']>): string | null {
  return b.hauteur_nature === 'sourcé' && b.hauteur_faitage_m != null
    ? `faîtage ${b.hauteur_faitage_m} m mesuré (LiDAR HD${b.hauteur_survol ? `, survol ${b.hauteur_survol}` : ''})`
    : null
}

/** §3 Bâti — le bâti existant : emprise, CoSIA, nb, hauteur, DPE, toit, RNB. */
export function BatiBlock({ f }: { f: Fiche }) {
  const b = f.le_bien
  if (!b || !b.disponible) return null
  const dpe = f.dpe_connu
  const emprise = b.emprise_batie_m2
  const nb = b.nb_batiments
  const toit = b.toit
  const toitServi = !!toit && TOIT_SERVI.has(toit.verdict)
  return (
    <div className="flex flex-col gap-3" data-le-bien>
      <div>
        <FactRow label="Emprise bâtie au sol"
          value={emprise > 0 ? <>{fmtInt(emprise)} <small>m²</small></> : '—'}
          tone={emprise > 0 ? undefined : 'mute'}
          src={<>{b.emprise_source}</>} />
        {b.cosia_detecte_m2 != null && (
          <FactRow label="Bâti détecté (imagerie CoSIA)" tone="mute"
            value={<>~{fmtInt(b.cosia_detecte_m2)} <small>m² — non cartographié en BD TOPO, à vérifier</small></>}
            src="CoSIA 2025" />
        )}
        <FactRow label="Nombre de bâtiments"
          value={nb != null ? nb : 'non déterminé'} tone={nb != null ? undefined : 'mute'} />
        {/* RECETTE-9 T9 — quand le LiDAR HD a mesuré la parcelle : faîtage ET égout MESURÉS
            (sourcé), l'égout étant ce que BD TOPO ne donne pas. Sinon la hauteur BD TOPO (estimé).
            DONNEES-FIX-1 lot A — trois lignes libellées SANS ambiguïté de grandeur : le faîtage
            (haut de toit, LiDAR), l'égout (bord de toit, LiDAR), et la hauteur BD TOPO qui vaut
            ≈ l'égout — c'est CES DEUX-LÀ qu'on compare pour le badge (même grandeur), jamais le
            faîtage, toujours plus haut par construction sur un toit en pente ou un R+n. */}
        {b.hauteur_nature === 'sourcé' && b.hauteur_faitage_m != null ? (
          <>
            <FactRow label="Faîtage mesuré (LiDAR)"
              value={<>{b.hauteur_faitage_m} <small>m — haut de toit</small></>}
              tone={b.hauteur_discordante && b.hauteur_discordance_motif === 'faîtage aberrant' ? 'warn' : undefined}
              src={`LiDAR HD (mesuré${b.hauteur_survol ? `, survol de ${b.hauteur_survol}` : ''})`} />
            {b.hauteur_egout_m != null && (
              <FactRow label="Égout mesuré (LiDAR)"
                value={<>{b.hauteur_egout_m} <small>m — bord de toit</small></>}
                tone={b.hauteur_discordante && b.hauteur_discordance_motif === 'égout ↔ BD TOPO' ? 'warn' : undefined}
                src="LiDAR HD (mesuré)" />
            )}
            {b.hauteur_bdtopo_m != null && (
              <FactRow label="Hauteur BD TOPO (≈ égout)"
                value={<>{b.hauteur_bdtopo_m} <small>m</small></>}
                tone={b.hauteur_discordante && b.hauteur_discordance_motif === 'égout ↔ BD TOPO' ? 'warn' : undefined}
                src="BD TOPO® (hauteur déclarée)" />
            )}
          </>
        ) : (
          <FactRow label="Hauteur du bâti"
            value={b.hauteur_bati_m != null ? <>{b.hauteur_bati_m} <small>m</small></> : 'non déterminée'}
            tone={b.hauteur_bati_m != null ? undefined : 'mute'}
            src={b.hauteur_bati_m != null ? 'BD TOPO' : undefined} />
        )}
        {b.hauteur_discordante && (
          <div data-hauteur-discordante className="mt-0.5">
            <Badge ton="ambre">Sources discordantes</Badge>
            <p className="mt-0.5 text-[11px] leading-snug text-amber">
              {b.hauteur_discordance_motif === 'faîtage aberrant'
                ? <>Faîtage mesuré {b.hauteur_faitage_m} m — valeur physiquement impossible, mesure à écarter.</>
                : <>Égout LiDAR {b.hauteur_egout_m} m · BD TOPO {b.hauteur_bdtopo_m} m — écart{b.ecart_egout_bdtopo_m != null ? ` de ${Math.abs(b.ecart_egout_bdtopo_m)} m` : ''} sur la même grandeur, à vérifier sur photo aérienne.</>}
            </p>
          </div>
        )}
        {/* FICHE-1 lot 2 — DPE du BÂTIMENT (pas de la parcelle). DONNEES-1 lot 2 — la ligne ne
            s'affiche QUE si un DPE existe : aucune ligne « non déterminé » (DPE non obligatoire
            en DROM, ~0,3 % de couverture ; il ne sert aucun outil ni ciblage). */}
        {dpe && (
          <FactRow label="DPE du bâtiment"
            value={<>{dpe.etiquette}{dpe.etiquette_ges ? <> / GES {dpe.etiquette_ges}</> : null}
              {dpe.annee ? <> <small>({dpe.annee})</small></> : null}</>}
            src={<>{dpe.source}{dpe.n > 1 ? ` · ${dpe.n} DPE connus, le plus récent` : ''}</>} />
        )}
      </div>
      {/* Toit — LiDAR HD (cache). null = non encore relevé (relevé à l'ouverture de la fiche soleil). */}
      <div data-le-bien-toit>
        {toit ? (
          <>
            <FactRow label="Nature du toit" value={toit.libelle}
              tone={toitServi ? undefined : 'mute'}
              src={toitServi ? 'LiDAR HD IGN' : undefined} />
            {toit.pente_mediane_deg != null && (
              <FactRow label="Pente du toit"
                value={<>{Math.round(toit.pente_mediane_deg)}<small>°</small></>}
                src="LiDAR HD IGN — mesure directe" />
            )}
            <FactNote>{toit.methode}</FactNote>
          </>
        ) : (
          /* FICHE-RANGEMENT-3 Lot 4 — la fiche AFFICHE, elle ne demande pas d'action : « non
             disponible » plutôt que « ouvrez la fiche soleil pour la calculer ». */
          <FactRow label="Nature du toit" tone="mute" value="non disponible" />
        )}
      </div>
      {/* REPARATIONS-1 lot 4 — RNB ID (Référentiel National des Bâtiments) de chaque bâtiment. */}
      {(b.rnb?.length ?? 0) > 0 && (
        <div data-le-bien-rnb>
          <div className="mt-2 mb-1 text-[11px] uppercase tracking-wide opacity-60">
            Identifiant national du bâtiment (RNB)
          </div>
          {b.rnb!.map((r) => (
            <FactRow key={r.rnb_id} label="RNB"
              value={<a href={r.lien} target="_blank" rel="noreferrer"
                className="font-mono text-[12px] hover:underline"
                >{r.rnb_id} ↗</a>}
              src="RNB — Référentiel National des Bâtiments" />
          ))}
        </div>
      )}
      {/* FICHE-RANGEMENT-3 Lot 5 — adresses BAN PLUS (IGN) : lien adresse ↔ bâtiment de la parcelle. */}
      {b.adresses_bati && (b.adresses_bati.adresses > 0 || b.adresses_bati.batiments > 0) && (
        <div data-le-bien-ban>
          <FactRow label="Adresses BAN PLUS"
            value={<>{b.adresses_bati.adresses} <small>adresse{b.adresses_bati.adresses > 1 ? 's' : ''} · {b.adresses_bati.batiments} bâtiment{b.adresses_bati.batiments > 1 ? 's' : ''}</small></>}
            src={b.adresses_bati.source} />
        </div>
      )}
      {/* KELFONCIER-FIX-1 (Lot H) — ÉTABLISSEMENTS sur la parcelle (SIRENE, rattachés par l'adresse BAN).
          Nom · NAF fin · tranche d'effectif · état + régime collectif BODACC. Nom masqué si non diffusible. */}
      {f.etablissements && f.etablissements.n > 0 && (
        <div data-etablissements>
          <div className="mt-2 mb-1 text-[11px] uppercase tracking-wide opacity-60">
            Établissements sur la parcelle{f.etablissements.n > f.etablissements.affiches
              ? ` (${f.etablissements.affiches} affichés sur ${f.etablissements.n})` : ` (${f.etablissements.n})`}
          </div>
          {f.etablissements.liste.map((e) => (
            <FactRow key={e.siret}
              label={<span className={e.nom_masque ? 'italic opacity-70' : ''}>{e.nom}</span>}
              value={<>{e.naf_label ?? e.naf ?? '—'}
                {e.tranche_effectif ? <> <small>· {e.tranche_effectif}</small></> : null}
                {!e.actif ? <> <small className="text-txt-dim">· fermé</small></> : null}
                {e.regime_collectif ? <> <small className="text-st-ecartee">· {e.regime_collectif.libelle}</small></> : null}</>}
              src={e.naf ? `SIRENE${e.precision ? ` · position ${e.precision}` : ''}` : undefined} />
          ))}
          <FactNote>{f.etablissements.note}</FactNote>
        </div>
      )}
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

/** §1 Identité — historique cadastral officiel (filiation DFI). */
export function FiliationBlock({ f }: { f: Fiche }) {
  if (!f.filiation) return null
  const fi = f.filiation
  return (
    <div data-le-bien-filiation>
      <div className="mt-2 mb-1 text-[11px] uppercase tracking-wide opacity-60">
        Historique cadastral (filiation officielle)
      </div>
      {fi.meres?.map((m) => (
        <FactRow key={`m-${m.idu}-${m.date}`} label="Issue de"
          value={<>{m.idu}{m.date ? <small> · {m.date}</small> : null}
            {m.nature ? <small> · {m.nature}</small> : null}</>} />
      ))}
      {fi.filles?.map((x) => (
        <FactRow key={`f-${x.idu}-${x.date}`} label="A donné"
          value={<>{x.idu}{x.date ? <small> · {x.date}</small> : null}
            {x.nature ? <small> · {x.nature}</small> : null}</>} />
      ))}
      {fi.division_recente && (
        <FactNote>Division récente (événement ≥ 2023) — signal de mouvement foncier.</FactNote>
      )}
      <FactNote>{fi.source}. Contrôle croisé avec le cadastre d'époque
        (géométrie) — deux canaux, jamais un conflit.</FactNote>
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
