/**
 * PLU-EXCEPTIONS-1 — le contenu du « i » d'exception au règlement.
 *
 * Rend le TEXTE VERBATIM de l'exception (entre guillemets, jamais reformulé), suivi de son
 * article et sa page PDF. Partagé par la fiche §Urbanisme (tuile de règle) et l'outil PLU.
 * Aucune exception n'entre dans un calcul : c'est une aide à la lecture (cf. Lot C).
 */
import type { PluException } from '../../lib/types'

const PORTE_LABEL: Record<string, string> = {
  sous_secteur: 'Sous-secteur',
  bande_limite: 'Bande depuis une limite',
  hauteur_alternative: 'Hauteur alternative',
  majoration_conditionnelle: 'Majoration conditionnelle',
  voie_specifique: 'Voie spécifique (RN/RD)',
  destination: 'Selon la destination',
  operation_ensemble: 'En opération d’ensemble',
  exclusion_generique: 'Cas particuliers',
  autre: 'Cas particulier',
}

export function porteLabel(porte: string | null | undefined): string {
  return (porte && PORTE_LABEL[porte]) || 'Exception'
}

export function ExceptionTip({ regle, exceptions }: { regle?: string; exceptions: PluException[] }) {
  return (
    <div style={{ maxWidth: 320, display: 'flex', flexDirection: 'column', gap: 8 }}>
      <div style={{ fontWeight: 600, color: 'var(--txt-hi)' }}>
        {exceptions.length > 1 ? `${exceptions.length} exceptions au règlement` : 'Exception au règlement'}
        {regle ? <span style={{ color: 'var(--txt-dim)', fontWeight: 400 }}> — {regle}</span> : null}
      </div>
      {exceptions.map((e, i) => (
        <div key={e.id ? `${e.id}-${i}` : i} data-exception-item style={{ borderTop: i > 0 ? '1px solid var(--line)' : undefined, paddingTop: i > 0 ? 6 : 0 }}>
          <div style={{ fontSize: 10, textTransform: 'uppercase', letterSpacing: '.02em', color: 'var(--amber)', marginBottom: 2 }}>{porteLabel(e.porte)}</div>
          <blockquote style={{ margin: 0, fontStyle: 'italic', color: 'var(--txt-hi)', lineHeight: 1.4 }}>« {e.texte} »</blockquote>
          <div style={{ fontSize: 11, color: 'var(--txt-dim)', marginTop: 3 }}>
            {[e.article, e.page_pdf != null ? `p. ${e.page_pdf}` : null].filter(Boolean).join(' · ')}
          </div>
        </div>
      ))}
      <div style={{ fontSize: 10.5, color: 'var(--txt-off)' }}>
        Texte du règlement PLU — n’entre pas dans le calcul de capacité (aide à la lecture).
      </div>
    </div>
  )
}
