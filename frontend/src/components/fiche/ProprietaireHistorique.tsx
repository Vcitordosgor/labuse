/**
 * L1 (rattrapage KelFoncier 2) — Historique du propriétaire PERSONNE MORALE par millésime.
 * Millésimes DGFiP 2019→2025 (Licence Ouverte 2.0, situation au 1ᵉʳ janvier). Le changement de
 * propriétaire moral d'une année à l'autre est un CONSTAT sourcé — jamais une vente affirmée, jamais
 * un signal de scoring. RGPD : personnes morales uniquement. Aucun fetch (charge utile de la fiche).
 *
 * FICHE-FIX-4 (Lot C) — mise en Frise (un seul segment « 2019 → 2025 · nom » même sans changement) ;
 * les trois paragraphes gris (constat DGFiP, « n'affirme pas une vente », millésimes) passent derrière
 * le « i » de l'historique ; le détail des millésimes va dans un Repli « anciens propriétaires · N ».
 */
import { Siren } from '../shared/Siren'   // RETOURS-12 T2 — SIREN cliquable Pappers
import type { Fiche } from '../../lib/types'
import { GroupLabel } from './primitives'
import { Frise, type Segment, Repli, InfoI, Lignes, Ligne } from './formes'

type Histo = NonNullable<Fiche['proprietaire_historique']>

/** Nombre de changements identifiés (≥1 → il y a d'anciens propriétaires distincts). */
export function aDesAnciensProprietaires(h: Histo | null | undefined): number {
  if (!h || h.n_millesimes < 2) return 0
  return h.changements.filter((c) => !c.non_identifiable).length
}

export function ProprietaireHistorique({ h, pm }: { h: Histo | null | undefined; pm: boolean }) {
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

  // Segments de la frise : millésimes consécutifs de même dénomination regroupés. Un seul segment
  // (aucun changement) = « premier → dernier · nom ». Le dernier segment est l'ACTUEL (vert).
  type Seg = { annee: number; nom: string }
  const segs: Seg[] = []
  for (const m of h.millesimes) {
    const nom = m.denomination ?? 'PM non identifiable'
    if (segs.length && segs[segs.length - 1].nom === nom) continue
    segs.push({ annee: m.millesime, nom })
  }
  const friseSegments: Segment[] = segs.length <= 1
    ? [{ annee: `${premier.millesime} → ${dernier.millesime}`, label: dernier.denomination ?? 'PM non identifiable', ton: 'actuel' }]
    : segs.map((s, i) => ({ annee: s.annee, label: s.nom, ton: i === segs.length - 1 ? 'actuel' : 'ancien' }))

  // Les 3 explications grises, derrière le « i » (jamais dans le flux).
  const tip = (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
      <span>Constat cadastral : le propriétaire déclaré au fichier des personnes morales, par millésime.</span>
      <span>Un changement de propriétaire moral n'affirme pas une vente — ce n'est pas un signal de classement.</span>
      <span>{h.note}</span>
    </div>
  )

  return (
    <div data-proprietaire-historique>
      <GroupLabel right={<InfoI tip={tip} aria="Sur l'historique du propriétaire" />}>Historique du propriétaire</GroupLabel>
      <Frise segments={friseSegments} />
      {aDesAnciensProprietaires(h) > 0 && (
        <Repli compteur={h.n_millesimes} label={`anciens propriétaires (${premier.millesime}–${dernier.millesime})`}>
          <Lignes>
            {h.millesimes.map((m) => (
              <Ligne key={m.millesime} label={<span className="font-mono text-txt-dim">{m.millesime}</span>}
                valeur={<>{m.denomination ?? 'PM non identifiable'}{m.siren ? <> · <Siren value={m.siren} className="font-mono text-[10px] text-txt-off" /></> : null}</>} />
            ))}
          </Lignes>
        </Repli>
      )}
    </div>
  )
}
