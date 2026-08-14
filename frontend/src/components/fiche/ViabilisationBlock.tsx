/**
 * M-VIA lot 2 — Bloc « Viabilisation » (indicateur par FAISCEAU DE PREUVES).
 *
 * INDICATEUR de probabilité, JAMAIS une certitude ni un verrou de constructibilité.
 * Aucun tracé de réseau (donnée sensible). Contributions tracées « comme le bloc P v2 » :
 * la fiche dit POURQUOI (permis < 100 m, façade voie urbanisée, bâti mitoyen, zone).
 * Coût de raccordement QUALITATIF (Lot 3). Note PV S3REnR au niveau île (Lot 2.5).
 * Additif : rendu depuis la charge utile de la fiche (aucun fetch).
 */
import { TOKENS } from '../../lib/tokens'
import type { AncStatut, Viabilisation } from '../../lib/types'
import { Tip } from '../Tip'

// M88 — badge d'état ANC : Sourcé (mint, réglementaire) · Sourcé secteur (mint clair, taux INSEE de
// secteur, JAMAIS un verdict parcellaire ni un seuil) · Absent (dim). L'« Estimé » proba_anc est retiré.
const ANC_BADGE: Record<AncStatut['statut'], { label: string; cls: string }> = {
  source: { label: 'Sourcé', cls: 'bg-mint/15 text-mint' },
  source_secteur: { label: 'Sourcé · secteur', cls: 'bg-mint/10 text-mint' },
  absent: { label: 'Absent', cls: 'bg-surface-2 text-txt-dim' },
}

const BAND_META: Record<Viabilisation['band'], { color: string; bg: string }> = {
  confirmee:  { color: TOKENS.viabConfirmee, bg: TOKENS.viabConfirmeeBg },
  probable:   { color: TOKENS.viabProbable, bg: TOKENS.viabProbableBg },
  incertaine: { color: TOKENS.viabIncertaine, bg: TOKENS.viabIncertaineBg },
  lourde:     { color: TOKENS.viabLourde, bg: TOKENS.viabLourdeBg },
}

export function ViabilisationBlock({ via, anc }: { via: Viabilisation; anc?: AncStatut | null }) {
  const m = BAND_META[via.band] ?? BAND_META.incertaine
  const ab = anc ? ANC_BADGE[anc.statut] : null
  return (
    <div data-viabilisation className="card-elev px-3 py-2.5">
      {/* M70 point 6a : en-tête sur UNE ligne à 400px — libellé tronquable, verdict à droite,
          pastille raccourcie (le « Viabilisation » redondant est retiré, le sens reste). */}
      <div className="flex flex-nowrap items-center gap-2">
        <span className="min-w-0 flex-1 truncate text-xs font-medium text-txt-hi">Viabilisation (eau · assainissement · élec)</span>
        <span className="shrink-0 whitespace-nowrap rounded-full px-2 py-0.5 text-[10.5px] font-semibold"
          style={{ backgroundColor: m.bg, color: m.color }}>{via.libelle.replace(/^Viabilisation\s+/i, '')}</span>
      </div>

      {/* M70 décision 5 — plus de score /100 ni de jauge (une seule jauge dans la fiche = ICD, et
          elle-même n'est plus chiffrée). Le verdict qualitatif (pastille en-tête) porte l'info ;
          les preuves restent listées sous « Pourquoi cet indicateur », sans pondération affichée. */}
      <p className="mt-2 text-[11px] leading-snug text-txt-dim">
        Probabilité de viabilisation par faisceau de preuves (jamais une certitude).
      </p>

      <p className="label-caps mt-2">Pourquoi cet indicateur</p>
      <ul className="mt-1 flex flex-col gap-0.5">
        {via.contributions.map((c, i) => (
          <li key={i} className="flex items-baseline gap-1.5 text-[11.5px]">
            <span aria-hidden className={`shrink-0 ${
              c.points > 0 ? 'text-st-chaude' : c.signe === '−' ? 'text-st-ecartee' : 'text-txt-mut'}`}>
              {c.points > 0 ? '▲' : c.signe === '−' ? '▽' : '·'}
            </span>
            <span className="text-txt">
              <b className="font-medium text-txt-hi">{c.libelle}</b>
              <span className="text-txt-dim"> — {c.detail}</span>
            </span>
          </li>
        ))}
      </ul>

      {/* Lot 3 — coût de raccordement qualitatif */}
      <div className="mt-2.5 rounded-lg bg-surface-3 px-2.5 py-2">
        <p className="label-caps">Raccordement (qualitatif)</p>
        <p className="mt-1 text-[11.5px] leading-snug text-txt">{via.cout_raccordement.niveau}</p>
        <p className="mt-1 text-[11px] leading-snug text-txt-dim">{via.cout_raccordement.assainissement}</p>
      </div>

      {/* M88 — état d'ASSAINISSEMENT (ANC / tout-à-l'égout) : contrainte de constructibilité.
          Trois états jamais quatre — Sourcé (réglementaire) / Sourcé secteur (taux INSEE, maille +
          millésime DITS dans la phrase) / Absent. Le libellé du secteur est un TAUX, pas un verdict. */}
      {anc && ab && (
        <div data-anc className="mt-2 rounded-lg bg-surface-3 px-2.5 py-2">
          <div className="flex items-center justify-between gap-2">
            <p className="label-caps">Assainissement (zonage)</p>
            <span data-anc-statut={anc.statut} className={`shrink-0 rounded-full px-1.5 py-0.5 text-[9px] font-semibold uppercase ${ab.cls}`}>{ab.label}</span>
          </div>
          <p className={`mt-1 text-[11.5px] font-medium leading-snug ${anc.statut === 'source' && anc.anc ? 'text-amber' : 'text-txt-hi'}`}>{anc.libelle}</p>
          <p className="mt-0.5 text-[11px] leading-snug text-txt-dim">{anc.phrase}</p>
          {anc.statut === 'absent' && anc.couverture && (
            <p className="mt-1 text-[10.5px] leading-snug text-txt-mut">
              Zonage réglementaire disponible sur {anc.couverture.communes_avec_zonage} communes sur {anc.couverture.communes_total} — état documenté, pas un trou de données.
            </p>
          )}
        </div>
      )}

      {/* Lot 2.5 — note PV S3REnR (niveau île, volet photovoltaïque) */}
      {via.elec_pv && (
        <p className="mt-2 flex items-start gap-1.5 text-[11px] leading-snug text-txt-dim">
          <span aria-hidden className="text-st-creuser">↯</span>
          {via.elec_pv.source
            ? <Tip tip={via.elec_pv.source}><span>{via.elec_pv.note}</span></Tip>
            : <span>{via.elec_pv.note}</span>}
        </p>
      )}

      {/* M75 — gisement solaire PVGIS : INFORMATION seule, à côté du S3REnR (soleil vs réseau).
          Le libellé `note` vient du backend (point de calcul unique = mêmes mots que les exports).
          Productible SOURCÉ PVGIS → état Estimé affiché ; jamais de score /100. */}
      {via.solaire && (
        <p data-solaire className="mt-2 flex items-start gap-1.5 text-[11px] leading-snug text-txt-dim">
          <span aria-hidden className="text-amber">☀</span>
          <span>{via.solaire.note} <span className="text-txt-mut">{via.solaire.etat}.</span></span>
        </p>
      )}

      <p className="mt-2 text-[10.5px] leading-snug text-txt-dim">{via.disclaimer}</p>
    </div>
  )
}
