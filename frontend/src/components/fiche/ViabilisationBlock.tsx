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

export function ViabilisationBlock({ via, anc }: { via: Viabilisation; anc?: AncStatut | null }) {
  const m = BAND_META[via.band] ?? BAND_META.incertaine
  const ab = anc ? ANC_BADGE[anc.statut] : null
  return (
    // RETOURS-20 Z3 — plus de card-elev : la viabilisation vit à plat sous ses kickers.
    <div data-viabilisation>
      {/* Z1·02 — en-tête = KICKER « Viabilisation… » + verdict à droite (pastille de bande, tokens
          viab*). M70 6a : le libellé raccourci reste, le sens aussi. */}
      <GroupLabel right={
        <span data-viab-band={via.band} className="shrink-0 whitespace-nowrap rounded-full px-2 py-0.5 text-[10.5px] font-semibold"
          style={{ backgroundColor: m.bg, color: m.color }}>{via.libelle.replace(/^Viabilisation\s+/i, '')}</span>
      }>Viabilisation (eau · assainissement · élec)</GroupLabel>

      {/* M70 décision 5 — plus de score /100 ni de jauge. La phrase de méthode passe en NOTE 11,5 px. */}
      <FactNote>Probabilité de viabilisation par faisceau de preuves (jamais une certitude).</FactNote>

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

      {/* Lot 3 — coût de raccordement qualitatif : Z3 la boîte (rounded bg) devient un kicker + texte. */}
      <GroupLabel>Raccordement (qualitatif)</GroupLabel>
      <p className="mt-1 text-[11.5px] leading-snug text-txt">{via.cout_raccordement.niveau}</p>
      <FactNote>{via.cout_raccordement.assainissement}</FactNote>

      {/* M88 — état d'ASSAINISSEMENT (ANC / tout-à-l'égout). Z3 la boîte devient un kicker + badge à
          droite (Sourcé/…); libellé et phrase inchangés. Trois états jamais quatre. */}
      {anc && ab && (
        <div data-anc>
          <GroupLabel right={
            <span data-anc-statut={anc.statut} className={`rounded-full px-1.5 py-0.5 text-[9px] font-semibold uppercase ${ab.cls}`}>{ab.label}</span>
          }>Assainissement (zonage)</GroupLabel>
          <p className={`mt-1 text-[11.5px] font-medium leading-snug ${anc.statut === 'source' && anc.anc ? 'text-amber' : 'text-txt-hi'}`}>{anc.libelle}</p>
          <p className="mt-0.5 text-[11px] leading-snug text-txt-dim">{anc.phrase}</p>
          {anc.statut === 'absent' && anc.couverture && (
            <FactNote>
              Zonage réglementaire disponible sur {anc.couverture.communes_avec_zonage} communes sur {anc.couverture.communes_total} — état documenté, pas un trou de données.
            </FactNote>
          )}
        </div>
      )}

      {/* Lot 2.5 — note PV S3REnR (niveau île, volet photovoltaïque) */}
      {via.elec_pv && (
        <p className="mt-2 flex items-start gap-1.5 text-[11px] leading-snug text-txt-mut">
          <span aria-hidden className="text-st-creuser">↯</span>
          {via.elec_pv.source
            ? <Tip tip={via.elec_pv.source}><span>{via.elec_pv.note}</span></Tip>
            : <span>{via.elec_pv.note}</span>}
        </p>
      )}

      {/* M75 — gisement solaire PVGIS : INFORMATION seule, à côté du S3REnR (soleil vs réseau). */}
      {via.solaire && (
        <p data-solaire className="mt-2 flex items-start gap-1.5 text-[11px] leading-snug text-txt-mut">
          <span aria-hidden className="text-amber">☀</span>
          <span>{via.solaire.note} <span className="text-txt-dim">{via.solaire.etat}.</span></span>
        </p>
      )}

      <FactNote>{via.disclaimer}</FactNote>
    </div>
  )
}
