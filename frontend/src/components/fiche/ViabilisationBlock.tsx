/**
 * M-VIA lot 2 — Bloc « Viabilisation » (indicateur par FAISCEAU DE PREUVES).
 *
 * INDICATEUR de probabilité, JAMAIS une certitude ni un verrou de constructibilité.
 * Aucun tracé de réseau (donnée sensible). Contributions tracées « comme le bloc P v2 » :
 * la fiche dit POURQUOI (permis < 100 m, façade voie urbanisée, bâti mitoyen, zone).
 * Coût de raccordement QUALITATIF (Lot 3). Note PV S3REnR au niveau île (Lot 2.5).
 * Additif : rendu depuis la charge utile de la fiche (aucun fetch).
 */
import type { AncStatut, Viabilisation } from '../../lib/types'
// FICHE-FIX-5 (Lot G) — la viabilisation, le raccordement, le solaire et l'assainissement passent en
// Lignes ; le faisceau de preuves (indices) va dans un Repli. Plus de kickers ni de paragraphes.
import { Lignes, Ligne, InfoI, Repli } from './formes'
import { Badge } from '../ui/Badge'

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

export function ViabilisationBlock({ via, anc }: { via: Viabilisation; anc?: AncStatut | null }) {
  const assain = assainissementResume(anc)
  return (
    <div data-viabilisation>
      <Lignes>
        <Ligne ton={via.band === 'confirmee' ? 'vert' : (via.band === 'probable' || via.band === 'lourde') ? 'ambre' : undefined}
          label={<>Viabilisation eau · élec<InfoI aria="Sur la viabilisation" tip={`Probabilité par faisceau de preuves, jamais une certitude. ${via.disclaimer}`} /></>}
          valeur={via.libelle.replace(/^Viabilisation\s+/i, '')} />
        <Ligne title={via.cout_raccordement.niveau}
          label={<>Raccordement eau · élec<InfoI aria="Sur le raccordement" tip={via.cout_raccordement.niveau} /></>}
          valeur={via.cout_raccordement.niveau} />
        {via.solaire && (
          <Ligne title={`${via.solaire.note} ${via.solaire.etat}`}
            label={<>Solaire<InfoI aria="Sur le solaire" tip={`${via.solaire.note} ${via.solaire.etat}.`} /></>}
            valeur={<>{via.solaire.note} <Badge ton="ambre">Estimé</Badge></>} />
        )}
        {anc && (
          <Ligne ton={assain.ton === 'vert' ? 'vert' : assain.ton === 'ambre' ? 'ambre' : 'gris'}
            title={`${anc.libelle} — ${anc.phrase}`}
            label={<>Assainissement<InfoI aria="Sur l'assainissement" tip={`${anc.libelle}. ${anc.phrase} ${via.cout_raccordement.assainissement}`} /></>}
            valeur={assain.plein} />
        )}
      </Lignes>
      {via.contributions.length > 0 && (
        <Repli compteur={via.contributions.length} label="indices (faisceau de preuves)">
          <Lignes>
            {via.contributions.map((c, i) => (
              <Ligne key={i} title={c.detail} label={c.libelle} valeur={c.detail} />
            ))}
          </Lignes>
        </Repli>
      )}
    </div>
  )
}

