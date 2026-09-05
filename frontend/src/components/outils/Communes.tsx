import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { getCommuneAcquisitions, getCommunes, getRadarMarche } from '../../lib/api'
import { fmtInt } from '../../lib/format'
import { useApp } from '../../store/useApp'
import { O6Comparateur } from './blocB'
import { M18 } from './moteurs'

// RETOURS-1 R3/R4 (Vic) — OUTIL « COMMUNES » RESTRUCTURÉ : un écran d'entrée à TROIS portes :
//   1. Comparaison communes — le tableau comparatif (overlay plein écran, patron §4) ;
//   2. Évolution du marché — l'ex-Baromètre (M18, île entière) ;
//   3. Acquisitions récentes — NOUVEAU : sélecteur de commune + listing des changements de
//      propriétaire PM récents (le contenu de l'ex-bloc « Acquisitions PM récentes » de la fiche
//      commune, qui vit désormais ICI, uniquement). Clic sur une ligne → fiche parcelle.
//      Constat brut (« changement de millésime, n'affirme pas une vente »), hors scoring.
// R4 — la fiche commune de l'OUTIL (CommuneFiche) a DISPARU : une seule fiche commune dans
// l'app, celle du CONTEXTE (ContextePanel). Le tableau de comparaison l'ouvre en panneau à
// droite (setContexteCommune) ; les blocs propres à l'ex-fiche-outil (Marché local, Rareté &
// ZAN, Vélocité) sont TRANSFÉRÉS dans ContextePanel — aucune donnée perdue, aucun doublon.

// ── Vue « Acquisitions récentes » (R3.3) — sélecteur de commune + listing, clic → parcelle ──
// RETOURS-11 O16 (Vic) : (c) le clic ouvre la fiche parcelle EN SUPERPOSITION (on ne quitte plus
// l'outil) ; (b) filtre par millésime d'arrivée (2023/2024/2025) sur les lignes chargées ; (d)
// mention « personnes morales uniquement » ; (e) regroupement par acquéreur (SIREN) avec renvoi vers
// son Scan patrimoine. NB : le backend ne sert au plus 50 lignes (limit=50) depuis 2022 — le total
// (« sur N ») n'est donc PAS paginable côté front (O16-a reste à faire côté serveur).
function AcquisitionsRecentes() {
  const communes = useQuery({ queryKey: ['communes'], queryFn: getCommunes })
  const [commune, setCommune] = useState<string | null>(null)
  const [millesime, setMillesime] = useState<number | null>(null)   // O16(b) — filtre année d'arrivée
  const q = useQuery({
    queryKey: ['commune-acquisitions', commune],
    queryFn: () => getCommuneAcquisitions(commune!),
    enabled: !!commune,
  })
  const d = q.data
  // O16(c) — la fiche parcelle s'ouvre en SUPERPOSITION (carte-overlay via `select`) : on ne touche
  // NI à `view` NI à `module`, l'outil Communes reste monté dessous et se retrouve à la fermeture.
  const ouvrirParcelle = (idu: string) => useApp.getState().select(idu)
  // O16(e) — Scan patrimoine d'un acquéreur : même idiome que « Voir le patrimoine » (m02Prefill + module).
  const ouvrirScanPatrimoine = (siren: string) => {
    const s = useApp.getState()
    s.setM02Prefill(siren)
    s.setModule('patrimoine')
  }
  // millésimes d'arrivée réellement présents dans les lignes chargées (jamais une année inventée)
  const anneesDispo = d
    ? [...new Set(d.acquisitions.map((a) => a.a_millesime))].sort((x, y) => y - x)
    : []
  const lignes = (d?.acquisitions ?? []).filter((a) => millesime == null || a.a_millesime === millesime)
  // O16(e) — regroupement par acquéreur (SIREN d'arrivée). Sans SIREN → seau « acquéreur non identifié ».
  const parAcquereur = new Map<string, { siren: string | null; denomination: string | null; items: typeof lignes }>()
  for (const a of lignes) {
    const cle = a.siren_apres ?? '∅'
    const g = parAcquereur.get(cle)
    if (g) g.items.push(a)
    else parAcquereur.set(cle, { siren: a.siren_apres, denomination: a.denomination_apres, items: [a] })
  }
  const groupes = [...parAcquereur.values()].sort((x, y) => y.items.length - x.items.length)
  return (
    <div className="flex min-h-0 flex-1 flex-col gap-2">
      <div className="shrink-0">
        <p className="label-caps text-[9.5px]">Commune</p>
        <select data-acq-commune value={commune ?? ''} onChange={(e) => { setCommune(e.target.value || null); setMillesime(null) }}
          className="mt-1 w-full rounded-md border border-line-2 bg-surface-3 px-2 py-1.5 text-[12px] text-txt focus:border-mint focus:outline-none">
          <option value="">Choisir une commune…</option>
          {(communes.data ?? []).map((c) => <option key={c.insee} value={c.commune}>{c.commune}</option>)}
        </select>
      </div>
      {/* O16(d) — le champ DGFiP ne publie QUE les personnes morales : dit une fois, franchement. */}
      {commune && (
        <p className="shrink-0 text-[10px] leading-snug text-txt-dim">
          Personnes morales uniquement — fichier DGFiP ; les acquisitions par des particuliers ne
          sont pas publiées.
        </p>
      )}
      {/* O16(b) — filtre par millésime d'arrivée (seulement les années effectivement présentes). */}
      {commune && anneesDispo.length > 1 && (
        <div data-acq-millesimes className="flex shrink-0 flex-wrap items-center gap-1.5 text-[11px]">
          <button data-acq-millesime="" onClick={() => setMillesime(null)}
            className={`rounded-full px-2 py-0.5 ${millesime == null ? 'bg-mint-bg text-mint' : 'text-txt-mut hover:text-txt'}`}>
            Tous
          </button>
          {anneesDispo.map((an) => (
            <button key={an} data-acq-millesime={an} onClick={() => setMillesime(an)}
              className={`rounded-full px-2 py-0.5 font-mono ${millesime === an ? 'bg-mint-bg text-mint' : 'text-txt-mut hover:text-txt'}`}>
              {an - 1}→{an}
            </button>
          ))}
        </div>
      )}
      {!commune ? (
        <p className="text-[11px] leading-snug text-txt-dim">Choisissez une commune pour lister les
          changements récents de propriétaire moral (constat DGFiP par millésime).</p>
      ) : q.isLoading ? (
        <p className="text-[11px] text-txt-dim">Chargement…</p>
      ) : q.isError || !d ? (
        <p className="text-[11px] text-st-ecartee">Constat indisponible — réessayez.</p>
      ) : d.n_total === 0 ? (
        <p className="text-[11px] leading-snug text-txt-dim">Aucun changement de propriétaire moral
          constaté depuis {d.depuis_millesime} à {commune}.</p>
      ) : (
        <div className="flex min-h-0 flex-1 flex-col gap-1.5 overflow-y-auto">
          <p className="shrink-0 text-[11px] text-txt-mut">
            {lignes.length} changement{lignes.length > 1 ? 's' : ''}
            {millesime != null ? ` en ${millesime - 1}→${millesime}` : ''} · {groupes.length} acquéreur{groupes.length > 1 ? 's' : ''}
            {d.tronquee ? ` (${d.n} servis sur ${d.n_total} depuis ${d.depuis_millesime})` : ` depuis ${d.depuis_millesime}`}.
          </p>
          {groupes.map((g) => (
            <div key={g.siren ?? '∅'} data-acq-groupe={g.siren ?? ''}
              className="rounded-md border border-line-2 bg-surface-2 px-2.5 py-1.5">
              <div className="flex items-baseline justify-between gap-2">
                <span className="min-w-0 truncate text-[11px] font-medium text-txt-hi">
                  {g.denomination ?? 'Acquéreur non identifié'}
                  <span className="ml-1 text-[10px] font-normal text-txt-dim">· {g.items.length} parcelle{g.items.length > 1 ? 's' : ''}</span>
                </span>
                {g.siren && (
                  <button data-acq-scan={g.siren} onClick={() => ouvrirScanPatrimoine(g.siren!)}
                    title={`Scan patrimoine de ${g.denomination ?? g.siren}`}
                    className="shrink-0 text-[11px] text-mint hover:underline">Scan patrimoine →</button>
                )}
              </div>
              <div className="mt-1 flex flex-col gap-1">
                {g.items.map((a) => (
                  <button key={`${a.idu}-${a.a_millesime}`} data-acq-ligne
                    onClick={() => ouvrirParcelle(a.idu)}
                    /* RETOURS-12 T5/O11 — infobulle « Ouvrir la parcelle {idu} » RETIRÉE : le lien
                       « parcelle {idu} → » est déjà affiché sous la ligne (rien de non-affiché à ajouter). */
                    className="hover-fill rounded border border-line-2 bg-surface-3 px-2 py-1 text-left text-[11px] leading-snug text-txt transition-colors duration-quick">
                    {/* RETOURS-12 T6 — .chip chip-mint : le millésime reste lisible (fond sombre, texte mint) quand la ligne passe en vert plein au survol. */}
                    <span className="chip chip-mint mr-1.5 bg-mint-bg px-1.5 py-0.5 font-mono text-[10px] text-mint">{a.de_millesime}→{a.a_millesime}</span>
                    <span className="text-txt-mut">{a.denomination_avant ?? '—'}</span>
                    <span className="mx-1 text-txt-dim">→</span>
                    <span className="font-medium text-txt-hi">{a.denomination_apres ?? '—'}</span>
                    <span className="mt-0.5 block font-mono text-[9.5px] text-txt-dim">parcelle {a.idu} →</span>
                  </button>
                ))}
              </div>
            </div>
          ))}
          <p className="shrink-0 pb-1 text-[10px] leading-snug text-txt-dim italic">{d.note}</p>
        </div>
      )}
    </div>
  )
}

// ── Renvoi « Marché des annonces (Radar) » sous la table comparative ──
// RETOURS-11 O15(b) (Vic) : le détail PAR COMMUNE (actives / nouveautés / retirées, prix demandé)
// appartient au RADAR, pas à Communes. Ce bloc ne re-rend donc PLUS les lignes par commune : c'est
// un simple RENVOI vers le Radar (avec, pour contexte honnête, le volume total du corpus collecté).
function MarcheAnnoncesRadar() {
  const setView = useApp((s) => s.setView)
  const { data: d } = useQuery({ queryKey: ['radar-marche'], queryFn: getRadarMarche, staleTime: 60_000 })
  if (!d) return null   // bloc non critique : silencieux si la donnée n'est pas là
  return (
    <div data-communes-marche-radar className="mt-2 shrink-0 rounded-lg border border-line-2 bg-surface-2 px-3 py-2 text-[12px]">
      <div className="flex items-center justify-between gap-2">
        <b className="label-caps text-[10px] tracking-[0.14em] text-txt-dim">Marché des annonces</b>
        <button data-marche-radar-lien onClick={() => setView('radar')} className="shrink-0 text-[11px] text-mint hover:underline">
          Ouvrir le Radar →
        </button>
      </div>
      <p className="mt-1 leading-snug text-txt-mut">
        Le détail par commune (biens en vente, nouveautés, retraits, prix demandés) vit dans le
        <b className="text-txt"> Radar</b> — <b className="text-txt">{fmtInt(d.corpus_actif)} bien{d.corpus_actif > 1 ? 's' : ''} collecté{d.corpus_actif > 1 ? 's' : ''}</b> à ce jour.
      </p>
    </div>
  )
}

// ── Porte de l'écran d'entrée (gabarit door-hot du tiroir Outils) ──
function Porte({ dataAttr, titre, sous, onClick }: { dataAttr: string; titre: string; sous: string; onClick: () => void }) {
  return (
    <button data-communes-porte={dataAttr} onClick={onClick}
      className="door door-hot hover-fill mb-0 w-full text-left transition-colors duration-quick">
      <div className="text-xs font-medium text-txt">{titre}</div>
      <div className="mt-0.5 text-[10.5px] leading-snug text-txt-dim">{sous}</div>
    </button>
  )
}

export function Communes() {
  const setCommunesTableOpen = useApp((s) => s.setCommunesTableOpen)
  const [vue, setVue] = useState<'accueil' | 'evolution' | 'acquisitions'>('accueil')
  if (vue === 'accueil') {
    return (
      <div className="flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto">
        <Porte dataAttr="comparaison" titre="Comparaison communes"
          sous="Le tableau comparatif des 24 communes, en grand — indicateurs sourcés, tri par colonne."
          onClick={() => setCommunesTableOpen(true)} />
        <Porte dataAttr="evolution" titre="Évolution du marché"
          sous="Ancien bâti, terrain nu et permis sur 8 trimestres (île entière)."
          onClick={() => setVue('evolution')} />
        <Porte dataAttr="acquisitions" titre="Acquisitions récentes"
          sous="Changements de propriétaire moral par commune (constat DGFiP, hors scoring)."
          onClick={() => setVue('acquisitions')} />
      </div>
    )
  }
  return (
    <div className="flex min-h-0 flex-1 flex-col gap-2 overflow-hidden">
      <button data-communes-retour onClick={() => setVue('accueil')}
        className="shrink-0 self-start text-[11px] text-mint hover:underline">‹ Communes</button>
      {vue === 'evolution' ? <M18 /> : <AcquisitionsRecentes />}
    </div>
  )
}

/** §4 — SECTION FLOTTANTE plein écran de la table des 24 communes (patron ex-Comparateur : overlay
 *  `absolute inset-0 z-40 bg-black/50` + carte `floating`). Ouverte par la porte « Comparaison
 *  communes » (drapeau `communesTableOpen`). RETOURS-1 R4 (Vic) : cliquer une commune ouvre la
 *  fiche commune de CONTEXTE en panneau à droite (setContexteCommune).
 *  RETOURS-11 O14(c) (Vic) — la table NE se referme PLUS à la sélection : la fiche commune
 *  (ContextePanel, panneau droit z-30) s'ouvre EN SUPERPOSITION par-dessus la carte. La table
 *  (overlay z-40) est simplement MASQUÉE tant qu'une fiche est ouverte — mais reste MONTÉE, donc
 *  fermer la fiche (setContexteCommune(null)) la fait RÉAPPARAÎTRE telle quelle (tri conservé). */
export function CommunesTablePanel() {
  const module = useApp((s) => s.module)
  const communesTableOpen = useApp((s) => s.communesTableOpen)
  const setCommunesTableOpen = useApp((s) => s.setCommunesTableOpen)
  const setContexteCommune = useApp((s) => s.setContexteCommune)
  const contexteCommune = useApp((s) => s.contexteCommune)
  if (module !== 'communes' || !communesTableOpen) return null
  // Fiche ouverte : on MASQUE l'overlay (sans démonter O6Comparateur, pour garder son tri) afin que
  // la fiche z-30 soit visible par-dessus la carte. Fermer la fiche la ramène intacte.
  return (
    <div data-communes-table-panel
      className={`absolute inset-0 z-40 flex items-center justify-center bg-black/50 p-6${contexteCommune ? ' hidden' : ''}`}
      onClick={() => setCommunesTableOpen(false)}>
      <div className="floating flex max-h-full w-full max-w-[1100px] flex-col overflow-hidden" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between border-b border-line px-4 py-2.5">
          <div>
            <h2 className="text-sm font-medium text-txt-hi">Les 24 communes</h2>
            <p className="text-[10.5px] text-txt-dim">Comparez-les, puis cliquez pour ouvrir la fiche commune.</p>
          </div>
          <button onClick={() => setCommunesTableOpen(false)} className="text-txt-mut hover:text-txt" aria-label="Fermer">✕</button>
        </div>
        {/* flex column bornée : O6Comparateur gère son propre scroll interne (rangs) + légende permanente.
            Pas d'overflow ICI (sinon double scroll + légende poussée hors écran). */}
        <div className="flex min-h-0 flex-1 flex-col p-3">
          {/* RETOURS-11 O14(c) — cliquer une commune OUVRE sa fiche (ContextePanel, panneau droit)
              en SUPERPOSITION : la table reste montée dessous (on ne la referme plus). Fermer la
              fiche fait donc RÉAPPARAÎTRE le tableau comparatif, sans le reconstruire ni perdre le tri. */}
          <O6Comparateur onSelect={(c) => setContexteCommune(c)} />
          {/* O2-3 — le marché des annonces (Radar) sous la table, seuil géré côté backend. */}
          <MarcheAnnoncesRadar />
        </div>
      </div>
    </div>
  )
}
