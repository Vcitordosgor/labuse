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
import { GroupLabel, FactNote } from './primitives'

// M88 — badge d'état ANC : Sourcé (mint, réglementaire) · Sourcé secteur (mint clair, taux INSEE de
// secteur, JAMAIS un verdict parcellaire ni un seuil) · Absent (dim). L'« Estimé » proba_anc est retiré.
const ANC_BADGE: Record<AncStatut['statut'], { label: string; cls: string }> = {
  source: { label: 'Sourcé', cls: 'bg-mint/15 text-mint' },
  source_secteur: { label: 'Sourcé · secteur', cls: 'bg-mint/10 text-mint' },
  // M95 — commune classée intégralement en ANC (Office de l'eau) : Sourcé d'échelle COMMUNE.
  source_commune: { label: 'Sourcé · commune', cls: 'bg-mint/15 text-mint' },
  absent: { label: 'Absent', cls: 'bg-surface-2 text-txt-dim' },
}

const BAND_META: Record<Viabilisation['band'], { color: string; bg: string }> = {
  confirmee:  { color: TOKENS.viabConfirmee, bg: TOKENS.viabConfirmeeBg },
  probable:   { color: TOKENS.viabProbable, bg: TOKENS.viabProbableBg },
  incertaine: { color: TOKENS.viabIncertaine, bg: TOKENS.viabIncertaineBg },
  lourde:     { color: TOKENS.viabLourde, bg: TOKENS.viabLourdeBg },
}

// FICHE-FIX-2 P1 — résumé d'assainissement dérivé du zonage SIG (anc), source unique partagée avec
// l'en-tête (reseaux.tsx). `court` = en-tête, `plein` = tiroir. L'assainissement N'ENTRE PAS dans le
// score de viabilisation (eau/élec) : c'est un fait distinct, sourcé du zonage. source_secteur = taux
// INSEE indicatif → pas un verdict parcellaire. Doctrine : un fait, une section.
export function assainissementResume(anc?: AncStatut | null): { court: string; plein: string; ton: 'vert' | 'ambre' | 'neutre' } {
  if (!anc || anc.statut === 'absent') return { court: 'non renseigné', plein: 'non renseigné', ton: 'neutre' }
  if (anc.statut === 'source' || anc.statut === 'source_commune') {
    return anc.anc
      ? { court: 'non collectif', plein: 'non collectif — filière autonome à prévoir', ton: 'ambre' }
      : { court: 'collectif', plein: 'collectif', ton: 'vert' }
  }
  return { court: 'non renseigné', plein: 'non renseigné (secteur indicatif)', ton: 'neutre' }
}

const ASSAIN_TON: Record<'vert' | 'ambre' | 'neutre', string> = {
  vert: 'text-mint', ambre: 'text-amber', neutre: 'text-txt-hi',
}

export function ViabilisationBlock({ via, anc }: { via: Viabilisation; anc?: AncStatut | null }) {
  const m = BAND_META[via.band] ?? BAND_META.incertaine
  const ab = anc ? ANC_BADGE[anc.statut] : null
  // FICHE-FIX-2 P1 — verdict d'assainissement explicite (« collectif » / « non collectif — filière
  // autonome à prévoir » / « non renseigné »), dérivé du zonage SIG, source unique (en-tête + tiroir).
  const assain = assainissementResume(anc)
  return (
    // RETOURS-20 Z3 — plus de card-elev : la viabilisation vit à plat sous ses kickers.
    <div data-viabilisation>
      {/* FICHE-FIX-2 P1 — le score de viabilisation ne teste QUE eau/élec (permis, voie, bâti, zone) :
          le titre ne dit plus « assainissement » (il vit dans son propre bloc plus bas). */}
      <GroupLabel right={
        <span data-viab-band={via.band} className="shrink-0 whitespace-nowrap rounded-full px-2 py-0.5 text-[10.5px] font-semibold"
          style={{ backgroundColor: m.bg, color: m.color }}>{via.libelle.replace(/^Viabilisation\s+/i, '')}</span>
      }>Viabilisation (eau · élec)</GroupLabel>

      {/* M70 décision 5 — plus de score /100 ni de jauge. La phrase de méthode passe en NOTE 11,5 px. */}
      <FactNote>Probabilité de viabilisation eau/élec par faisceau de preuves (jamais une certitude). L'assainissement est traité à part (zonage SIG, ci-dessous).</FactNote>

      {/* Z1·02 — sous-titre encadré (label-caps) → kicker. La liste « pourquoi » (faisceau) inchangée. */}
      <GroupLabel>Pourquoi cet indicateur</GroupLabel>
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

      {/* Lot 3 — coût de raccordement qualitatif (eau/élec) : la note d'assainissement du raccordement
          descend dans le bloc Assainissement (un fait, une section). */}
      <GroupLabel>Raccordement eau/élec (qualitatif)</GroupLabel>
      <p className="mt-1 text-[11.5px] leading-snug text-txt">{via.cout_raccordement.niveau}</p>

      {/* FICHE-FIX-2 P1 — ÉLECTRICITÉ (réseau S3REnR + solaire PVGIS) sous LEUR PROPRE titre, AVANT le
          bloc Assainissement : l'ensoleillement ne se lit plus comme une suite de l'assainissement. */}
      {(via.elec_pv || via.solaire) && (
        <div data-elec-solaire>
          <GroupLabel>Électricité — réseau et solaire</GroupLabel>
          {via.elec_pv && (
            <p className="mt-1 flex items-start gap-1.5 text-[11px] leading-snug text-txt-mut">
              <span aria-hidden className="text-st-creuser">↯</span>
              {via.elec_pv.source
                ? <Tip tip={via.elec_pv.source}><span>{via.elec_pv.note}</span></Tip>
                : <span>{via.elec_pv.note}</span>}
            </p>
          )}
          {via.solaire && (
            <p data-solaire className="mt-1 flex items-start gap-1.5 text-[11px] leading-snug text-txt-mut">
              <span aria-hidden className="text-amber">☀</span>
              <span>{via.solaire.note} <span className="text-txt-dim">{via.solaire.etat}.</span></span>
            </p>
          )}
        </div>
      )}

      {/* FICHE-FIX-2 P1 — ASSAINISSEMENT : bloc distinct, sourcé du zonage SIG (hors score eau/élec).
          Verdict explicite en tête (collectif / non collectif — filière autonome à prévoir / non
          renseigné), puis le libellé de zonage brut, la phrase, et la note de raccordement. */}
      {anc && ab && (
        <div data-anc>
          <GroupLabel right={
            <span data-anc-statut={anc.statut} className={`rounded-full px-1.5 py-0.5 text-[9px] font-semibold uppercase ${ab.cls}`}>{ab.label}</span>
          }>Assainissement (zonage)</GroupLabel>
          <p data-assain-verdict className={`mt-1 text-[11.5px] font-semibold leading-snug ${ASSAIN_TON[assain.ton]}`}>{assain.plein}</p>
          <p className="mt-0.5 text-[11px] leading-snug text-txt-dim">{anc.libelle}</p>
          <p className="mt-0.5 text-[11px] leading-snug text-txt-dim">{anc.phrase}</p>
          <FactNote>{via.cout_raccordement.assainissement}</FactNote>
          {anc.statut === 'absent' && anc.couverture && (
            <FactNote>
              Zonage réglementaire disponible sur {anc.couverture.communes_avec_zonage} communes sur {anc.couverture.communes_total} — état documenté, pas un trou de données.
            </FactNote>
          )}
        </div>
      )}

      <FactNote>{via.disclaimer}</FactNote>
    </div>
  )
}
