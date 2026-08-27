/**
 * L1 (rattrapage KelFoncier 2) — Historique du propriétaire PERSONNE MORALE par millésime.
 * Millésimes DGFiP 2019→2025 (Licence Ouverte 2.0, situation au 1ᵉʳ janvier). Le changement de
 * propriétaire moral d'une année à l'autre est un CONSTAT sourcé — jamais une vente affirmée, jamais
 * un signal de scoring. RGPD : personnes morales uniquement. Aucun fetch (charge utile de la fiche).
 */
import { useState } from 'react'
import type { Fiche } from '../../lib/types'

type Histo = NonNullable<Fiche['proprietaire_historique']>

export function ProprietaireHistorique({ h }: { h: Histo | null | undefined }) {
  const [ouvert, setOuvert] = useState(false)
  // Rien à montrer si moins de deux millésimes suivis (le propriétaire courant est déjà au-dessus).
  if (!h || h.n_millesimes < 2) return null
  const premier = h.millesimes[0]
  const dernier = h.millesimes[h.millesimes.length - 1]

  return (
    <div data-proprietaire-historique className="card-elev px-3 py-2.5">
      <p className="label-caps">Historique du propriétaire (DGFiP)</p>

      {h.n_changements > 0 ? (
        <div className="mt-1.5 flex flex-col gap-1.5">
          {h.changements.map((c, i) => (
            <div key={i} className="text-[11px] leading-snug text-txt">
              <span className="mr-1.5 rounded bg-mint-bg px-1.5 py-0.5 font-mono text-[10px] text-mint">
                {c.de_millesime} → {c.a_millesime}
              </span>
              <span className="text-txt-mut">{c.denomination_avant ?? '—'}</span>
              <span className="mx-1 text-txt-dim">→</span>
              <span className="font-medium text-txt-hi">{c.denomination_apres ?? '—'}</span>
              {(c.siren_avant || c.siren_apres) && (
                <div className="mt-0.5 font-mono text-[9.5px] text-txt-dim">
                  SIREN {c.siren_avant ?? '—'} → {c.siren_apres ?? '—'}
                </div>
              )}
            </div>
          ))}
        </div>
      ) : (
        <div className="mt-1.5 text-[11px] text-txt-mut">
          Même propriétaire moral sur toute la période suivie (aucun changement constaté).
        </div>
      )}

      <button type="button" onClick={() => setOuvert((o) => !o)}
        className="mt-2 text-[10.5px] text-txt-mut underline decoration-dotted underline-offset-2 hover:text-txt">
        {ouvert ? 'Masquer' : `Voir les ${h.n_millesimes} millésimes suivis (${premier.millesime}–${dernier.millesime})`}
      </button>
      {ouvert && (
        <div className="mt-1.5 flex flex-col gap-0.5 border-t border-bd/60 pt-1.5">
          {h.millesimes.map((m) => (
            <div key={m.millesime} className="flex items-baseline gap-2 text-[10.5px] leading-snug">
              <span className="w-8 shrink-0 font-mono text-txt-dim">{m.millesime}</span>
              <span className="text-txt">{m.denomination ?? '—'}</span>
              {m.siren && <span className="font-mono text-[9.5px] text-txt-dim">· {m.siren}</span>}
            </div>
          ))}
        </div>
      )}

      <p className="mt-2 text-[10px] leading-snug text-txt-dim italic">{h.note}</p>
    </div>
  )
}
