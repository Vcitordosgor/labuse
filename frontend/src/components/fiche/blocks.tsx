/**
 * fiche/blocks.tsx — FICHE-RANGEMENT-2 Lot 1 (étape 2).
 *
 * Blocs de contenu EXTRAITS de Fiche.tsx pour casser le cycle d'import : les futures sections
 * (`sections/*.tsx`) doivent pouvoir composer ces blocs SANS importer Fiche.tsx (qui les importe
 * en retour). Aucun changement de comportement — pur déplacement (mêmes composants, mêmes rendus).
 * N'importe QUE des primitives + blocs feuilles (cycle-free, comme les autres sous-composants).
 */
import { useState } from 'react'
import { Trace } from '../../lib/trace'
import { fmtInt } from '../../lib/format'
import type { FicheZoneDestinations, ReglementPlu, PluException } from '../../lib/types'
import { BlocIndisponible } from './BlocIndisponible'
import { DestinationBadge } from '../outils/DestinationSelect'   // DESTINATIONS-1 (X4.2) — pastille contour partagée
import { GroupLabel, FactNote } from './primitives'
import { Chevron } from '../ui/Chevron'
// KELFONCIER-FIX-2 (Lot G) — les règles-valeurs de la zone passent en Tuiles de la maquette v3.
import { Tuiles, type Tuile, InfoI } from './formes'
// PLU-EXCEPTIONS-1 — l'exception au règlement, affichée sous le « i » de la tuile de règle.
import { ExceptionTip } from './PluExceptionTip'

// FICHE-FIX-4 (Lot F) — les 6 dimensions de règle, en gris « non calibré », pour les zones dont le
// règlement n'est pas indexé à la lettre dans LABUSE (même gabarit que les zones calibrées).
const REGLES_NON_CALIBRE: Tuile[] = [
  { label: 'Hauteur', valeur: '—', sous: 'non calibré', ton: 'gris' },
  { label: 'Emprise', valeur: '—', sous: 'non calibré', ton: 'gris' },
  { label: 'Recul voie', valeur: '—', sous: 'non calibré', ton: 'gris' },
  { label: 'Recul limites', valeur: '—', sous: 'non calibré', ton: 'gris' },
  { label: 'Pleine terre', valeur: '—', sous: 'non calibré', ton: 'gris' },
  { label: 'Stationnement', valeur: '—', sous: 'non calibré', ton: 'gris' },
]

// FICHE-FIX-5 (Lot E) — libellé de règle en forme COURTE (la tuile ne tronque plus).
function shortReglLabel(l: string): string {
  const s = l.toLowerCase()
  if (/hauteur/.test(s)) return 'Hauteur'
  if (/emprise/.test(s)) return 'Emprise'
  if (/recul/.test(s) && /voie/.test(s)) return 'Recul voie'
  if (/recul/.test(s) && /(limite|s[ée]par)/.test(s)) return 'Recul limites'
  if (/pleine.?terre|espace.?vert|v[ée]g[ée]tal/.test(s)) return 'Pleine terre'
  if (/stationnement|parking/.test(s)) return 'Stationnement'
  return l
}
// Valeur COURTE : « 18 m au faîtage » → « 18 m » ; « 1 place / logement » → « 1 / logt ».
function shortReglValeur(v: string): string {
  // « 18 m au faîtage » → « 18 m » (l'unité est déjà là) ; « R+2 au faîtage » → « R+2 ».
  const s = v.trim().replace(/\s+au\s+fa[iî]t\w*.*/i, '').replace(/\s+à\s+l['’]égout.*/i, '')
  const place = s.match(/(\d[\d.,]*)\s*place/i)
  if (place && /logement|logt|lgt/i.test(s)) return `${place[1].replace('.', ',')} / logt`
  return s.replace(/\.(\d)/, ',$1')
}

// ── M9 lot 4 — ligne « Destinations » de la zone (résumé + dépliable) ──
export function ZoneDestinationsLigne({ d }: { d: FicheZoneDestinations }) {
  const [open, setOpen] = useState(false)
  // phrase seule (non calibrée / zone non lue) — dite telle quelle, rien à déplier
  if (d.phrase && !d.lignes?.length) {
    return <p data-fiche-destinations className="mt-1 text-[10.5px] text-txt-mut">Destinations · {d.phrase}</p>
  }
  const resume = [
    d.autorisees?.length ? `${d.autorisees.length} autorisée${d.autorisees.length > 1 ? 's' : ''} (${d.autorisees.slice(0, 3).join(', ')}${d.autorisees.length > 3 ? '…' : ''})` : null,
    d.interdites?.length ? `${d.interdites.length} interdite${d.interdites.length > 1 ? 's' : ''}` : null,
    d.sous_conditions?.length ? `${d.sous_conditions.length} sous condition` : null,
    d.seuil_commerce_m2 != null
      ? `commerce ≤ ${fmtInt(d.seuil_commerce_m2)} m²${d.seuil_commerce_type === 'emprise_sol' ? ' (emprise au sol)' : ''}` : null,
  ].filter(Boolean).join(' · ')
  return (
    <div data-fiche-destinations className="mt-1">
      <button onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center gap-1.5 rounded px-1 py-0.5 text-left text-[10.5px] text-txt-mut transition-colors duration-quick hover:bg-surface-3 hover:text-txt">
        <Chevron open={open} />
        <span className="min-w-0 flex-1 truncate"><b className="text-txt">Destinations</b>{resume ? ` · ${resume}` : ''}</span>
      </button>
      {open && (
        <div className="mt-1 flex flex-col gap-1 border-l border-line-2 pl-2.5">
          {d.lignes!.map((l) => (
            <div key={l.sous_destination} className="flex items-start gap-2">
              <DestinationBadge etat={l.statut_effectif} />
              {/* la phrase SERVIE, telle quelle (libellé + verdict + article/page/millésime + CDAC) */}
              <span className="min-w-0 flex-1 text-[10.5px] leading-snug text-txt-mut">{l.phrase}</span>
            </div>
          ))}
          {(d.millesime || d.referentiel) && (
            <p className="text-[9.5px] leading-snug text-txt-dim">
              {d.millesime ? `PLU millésime ${d.millesime}` : ''}
              {d.millesime && d.referentiel ? ' · ' : ''}
              {d.referentiel ? `référentiel : ${d.referentiel}` : ''}
            </p>
          )}
        </div>
      )}
    </div>
  )
}

// ── M9 lot 2 — Règlement PLU par zone (règles + valeurs, destinations, à-cheval) ──
export function ReglementPluBlock({ rp }: { rp: ReglementPlu }) {
  if (rp.indisponible) return <BlocIndisponible titre="Règlement PLU" />   // M125 — panne ≠ absence
  // M62-P1 (j) : la phrase d'explication (`note`) était répétée par zone alors qu'elle est
  // identique pour les deux → une seule fois, en gris, sous les lignes. Si les notes diffèrent,
  // on reste par zone (repli honnête).
  const notes = rp.zones.map((z) => z.note).filter(Boolean) as string[]
  const noteCommune = notes.length === rp.zones.length && notes.every((n) => n === notes[0]) ? notes[0] : null
  // COUCHES-1 lot 3 (item 12 / B4) — parcelle À CHEVAL sur plusieurs zones du PLU : la fiche dit la
  // vérité (toutes les zones et leur SURFACE respective), là où la couche « par parcelle » ne montre
  // que la zone dominante.
  const partsConnues = rp.zones.filter((z) => typeof z.part === 'number')
  // FRONT-CHIFFRES-2 (F21) — « à cheval » servi par la cascade (seuil SEUIL_A_CHEVAL_PCT au back) ;
  // le front ne recalcule plus `part[0] < 0,9`. Repli sur l'ancien calcul si le drapeau n'est pas servi.
  const aCheval = rp.a_cheval ?? (partsConnues.length >= 2 && (partsConnues[0].part ?? 1) < 0.9)
  const pct = (p?: number | null) => (typeof p === 'number' ? `${Math.round(p * 100)} %` : null)
  return (
    <div data-reglement-plu>
      {aCheval && (
        <div data-plu-a-cheval className="mb-2 rounded-md border border-amber/40 bg-amber/10 px-2.5 py-1.5 text-[11px] text-txt">
          <b>Parcelle à cheval sur {partsConnues.length} zones du PLU.</b> La colorisation « par parcelle »
          n’affiche que la zone dominante — voici la surface réelle de chacune :
          <span className="mt-1 flex flex-wrap gap-x-3 gap-y-0.5">
            {partsConnues.map((z, i) => (
              <span key={i} className="tabular-nums">{z.zone} <span className="text-txt-hi">{pct(z.part)}</span></span>
            ))}
          </span>
          <span className="mt-1 block text-txt-dim">Tracé officiel : couche « Limites officielles du PLU » (sous-option du zonage sur la carte).</span>
        </div>
      )}
      {rp.zones.map((z, i) => (
        <div key={i}>
          <GroupLabel right={z.url
            ? <a data-plu-link className="f-ref" href={z.url} target="_blank" rel="noreferrer">{z.calibree ? 'voir l’article' : 'voir le règlement'}</a>
            : undefined}>
            Règlement — zone <Trace id="zone_plu_famille"><span>{z.zone}</span></Trace>{aCheval && pct(z.part) ? <span className="text-txt-dim"> · {pct(z.part)} de la parcelle</span> : null}
          </GroupLabel>
          {z.regles_valeurs && z.regles_valeurs.length > 0 ? (
            // FICHE-FIX-5 (Lot E) — tuiles SANS troncature : libellé court (Hauteur · Emprise · Recul
            // voie · Recul limites · Pleine terre · Stationnement), valeur courte (« 10 m », « 50 % »,
            // « 1 / logt »), l'article en sous-ligne. Aucune donnée perdue (valeur pleine en `title`).
            <Tuiles cols={z.regles_valeurs.length >= 5 ? 3 : 2}
              items={z.regles_valeurs.map((rv): Tuile => {
                const exc = (rv.exceptions ?? []) as PluException[]
                return {
                  label: shortReglLabel(rv.libelle),
                  valeur: (rv.etat === 'chiffre' || rv.etat === 'texte') && rv.valeur ? shortReglValeur(rv.valeur) : '—',
                  sous: rv.reference ? (rv.reference.split(',')[0].replace(/^Zone \S+ /, '').trim() || undefined) : undefined,
                  ton: rv.etat === 'chiffre' || rv.etat === 'texte' ? undefined : 'gris',
                  // PLU-EXCEPTIONS-1 — la tuile porte un point d'exception + un « i » qui ouvre le
                  // texte (verbatim), l'article et la page. Une règle sans exception n'affiche rien.
                  marque: exc.length > 0 || undefined,
                  info: exc.length > 0
                    ? <InfoI aria={`Exception au règlement — ${rv.libelle}`} tip={<ExceptionTip regle={rv.libelle} exceptions={exc} />} />
                    : undefined,
                }
              })} />
          ) : (
            // FICHE-FIX-4 (Lot F) — MÊME GABARIT pour les zones non indexées : les 6 tuiles de règles
            // en gris « non calibré » (au lieu d'un paragraphe gris), le règlement écrit reste lié
            // (en-tête « voir le règlement ») et les articles éventuels listés sous les tuiles.
            <>
              <Tuiles cols={3} items={REGLES_NON_CALIBRE} />
              {z.articles.length > 0 && (
                <ul className="mt-1 flex flex-col gap-0.5">
                  {z.articles.slice(0, 6).map((a, j) => (
                    <li key={j} className="text-[11.5px]">
                      <a className="f-ref" href={a.url ?? z.url ?? '#'} target="_blank" rel="noreferrer">{a.reference}</a>
                    </li>
                  ))}
                </ul>
              )}
            </>
          )}
          {/* DESTINATIONS-1 (X4.2) — la ligne « Destinations » de la zone (résumé + dépliable). */}
          {z.destinations && <ZoneDestinationsLigne d={z.destinations} />}
          {/* note par zone UNIQUEMENT si elles diffèrent (sinon rendue une fois plus bas) */}
          {z.note && !noteCommune && <FactNote>{z.note}</FactNote>}
        </div>
      ))}
      {noteCommune && <FactNote>{noteCommune}</FactNote>}
      <FactNote>{rp.disclaimer}</FactNote>
    </div>
  )
}

// FINITIONS-1 (P13) — le bloc « Demander à l'IA de traduire le PLU » (composant TraducteurBloc) est
// SUPPRIMÉ. La règle de zone reste servie par ReglementPluBlock (règlement écrit opposable).
