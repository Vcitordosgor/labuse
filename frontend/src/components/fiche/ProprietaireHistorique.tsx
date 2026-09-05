/**
 * L1 (rattrapage KelFoncier 2) — Historique du propriétaire PERSONNE MORALE par millésime.
 * Millésimes DGFiP 2019→2025 (Licence Ouverte 2.0, situation au 1ᵉʳ janvier). Le changement de
 * propriétaire moral d'une année à l'autre est un CONSTAT sourcé — jamais une vente affirmée, jamais
 * un signal de scoring. RGPD : personnes morales uniquement. Aucun fetch (charge utile de la fiche).
 */
import { useState } from 'react'
import { Siren } from '../shared/Siren'   // RETOURS-12 T2 — SIREN cliquable Pappers
import type { Fiche } from '../../lib/types'

type Histo = NonNullable<Fiche['proprietaire_historique']>

export function ProprietaireHistorique({ h, pm }: { h: Histo | null | undefined; pm: boolean }) {
  const [ouvert, setOuvert] = useState(false)
  // RETOURS-1 R6 (Vic) — enquête : le composant était monté et fonctionnel, mais MUET hors
  // couverture (fichier PM = ~19 % des parcelles ; < 2 millésimes = rien) → sur la plupart des
  // parcelles testées, aucune trace, aucune explication. Désormais : parcelle PM sans timeline =
  // une ligne d'absence honnête ; parcelle PP = rien (le bloc au-dessus explique déjà le workflow
  // SPF, le fichier DGFiP ne couvre que les personnes morales).
  if (!h || h.n_millesimes < 2) {
    if (!pm) return null
    return (
      <p data-proprietaire-historique-absent className="text-[10.5px] leading-snug text-txt-dim">
        Anciens propriétaires : historique par millésime non disponible pour cette parcelle
        (millésimes DGFiP 2019–2025, personnes morales).
      </p>
    )
  }
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
                  SIREN <Siren value={c.siren_avant} className="font-mono text-txt-dim" /> → <Siren value={c.siren_apres} className="font-mono text-txt-dim" />
                </div>
              )}
            </div>
          ))}
        </div>
      ) : (
        <div data-proprietaire-sans-changement className="mt-1.5 text-[11px] text-txt-mut">
          {/* RETOURS-11 F11 — sans changement, un TEXTE honnête (« même propriétaire 2019 → 2025 »),
              plus le bouton trompeur « voir les anciens propriétaires » (il n'y en a aucun). */}
          Même propriétaire moral {premier.millesime} → {dernier.millesime} (aucun changement constaté).
        </div>
      )}

      {/* R6 — un VRAI bouton (l'ex-lien gris 10,5 px souligné pointillé passait inaperçu — cause
          n° 2 de l'invisibilité). RETOURS-11 F11 : le bouton n'apparaît QUE s'il y a un changement
          constaté — sinon il laissait croire à d'anciens propriétaires inexistants. */}
      {h.n_changements > 0 && (
        <button type="button" data-histo-toggle onClick={() => setOuvert((o) => !o)}
          className="mt-2 w-full rounded-md border border-line-2 bg-mint/[0.05] px-2.5 py-1.5 text-left text-[11px] font-medium text-mint transition-colors duration-quick hover:bg-mint/15">
          {ouvert
            ? 'Masquer les anciens propriétaires'
            : `Voir les anciens propriétaires — ${h.n_millesimes} millésimes (${premier.millesime}–${dernier.millesime})`}
        </button>
      )}
      {ouvert && h.n_changements > 0 && (
        <div className="mt-1.5 flex flex-col gap-0.5 border-t border-bd/60 pt-1.5">
          {h.millesimes.map((m) => (
            <div key={m.millesime} className="flex items-baseline gap-2 text-[10.5px] leading-snug">
              <span className="w-8 shrink-0 font-mono text-txt-dim">{m.millesime}</span>
              <span className="text-txt">{m.denomination ?? '—'}</span>
              {m.siren && <span className="font-mono text-[9.5px] text-txt-dim">· <Siren value={m.siren} className="font-mono text-txt-dim" /></span>}
            </div>
          ))}
        </div>
      )}

      <p className="mt-2 text-[10px] leading-snug text-txt-dim italic">{h.note}</p>
    </div>
  )
}
