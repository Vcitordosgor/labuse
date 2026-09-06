/**
 * fiche/leBien.tsx — FICHE-1 lot 1, tiroir « Le bien ».
 * Le bâtiment EXISTANT de la parcelle : emprise bâtie au sol (BD TOPO), nombre de bâtiments,
 * hauteur du bâti, surface au sol libre restante, et nature/pente du toit (LiDAR HD, cache seul).
 * Trois états jamais confondus (RETOURS-15 U5) : servie · « non déterminée » · « non calculée » —
 * portés par le back (le_bien.toit.verdict/libelle). Le tiroir s'OMET si rien n'est évaluable
 * (couche bâtiments non ingérée → le_bien=null). Auto-suffisant, n'importe que des primitives.
 */
import type { Fiche } from '../../lib/types'
import { fmtInt } from '../../lib/format'
import { IC, RefDrawer, FactRow, FactNote } from './primitives'

// verdicts de forme réellement SERVIS (les autres = états « non déterminée » / « non calculée »).
const TOIT_SERVI = new Set(['plat', 'monopente', 'double_pente', 'croupe_complexe'])

export function LeBienSection({ f }: { f: Fiche; idu: string }) {
  const b = f.le_bien
  if (!b || !b.disponible) return null   // rien d'évaluable → pas de bloc creux
  const dpe = f.dpe_connu
  const emprise = b.emprise_batie_m2
  const nb = b.nb_batiments
  const toit = b.toit
  const toitServi = !!toit && TOIT_SERVI.has(toit.verdict)
  return (
    <RefDrawer id="le_bien" icon={IC.faisa} name="Le bien"
      context={b.occupation_label || 'bâti existant'}
      value={nb != null && nb > 0
        ? <span className="pill-mint">{nb} bâtiment{nb > 1 ? 's' : ''}</span>
        : <span className="pill-mint">terrain nu</span>}>
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
          <FactRow label="Hauteur du bâti"
            value={b.hauteur_bati_m != null ? <>{b.hauteur_bati_m} <small>m</small></> : 'non déterminée'}
            tone={b.hauteur_bati_m != null ? undefined : 'mute'}
            src={b.hauteur_bati_m != null ? 'BD TOPO' : undefined} />
          <FactRow label="Surface au sol libre"
            value={b.surface_libre_m2 != null ? <>{fmtInt(b.surface_libre_m2)} <small>m²</small></> : 'non déterminée'}
            tone={b.surface_libre_m2 != null ? undefined : 'mute'} />
          {/* FICHE-1 lot 2 — DPE du BÂTIMENT (pas de la parcelle). Affiché quand il y a du bâti :
              le plus récent + nombre ; « non déterminée » si aucun DPE ne se rattache. */}
          {nb != null && nb > 0 && (
            dpe ? (
              <FactRow label="DPE du bâtiment"
                value={<>{dpe.etiquette}{dpe.etiquette_ges ? <> / GES {dpe.etiquette_ges}</> : null}
                  {dpe.annee ? <> <small>({dpe.annee})</small></> : null}</>}
                src={<>{dpe.source}{dpe.n > 1 ? ` · ${dpe.n} DPE connus, le plus récent` : ''}</>} />
            ) : (
              <FactRow label="DPE du bâtiment" tone="mute"
                value="non déterminée — aucun DPE rattaché" />
            )
          )}
        </div>
        {/* Toit — LiDAR HD (cache). Les 3 états U5 voyagent dans toit.libelle/verdict ; null = non
            encore relevé (le relevé se fait à l'ouverture de la fiche soleil). */}
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
            <FactRow label="Nature du toit" tone="mute"
              value="non encore relevée — ouvrez la fiche soleil pour la calculer" />
          )}
        </div>
        <FactNote>Bâti existant — {b.source_bati}. Information de fiche, jamais un signal de classement.</FactNote>
      </div>
    </RefDrawer>
  )
}
