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
function AcquisitionsRecentes() {
  const communes = useQuery({ queryKey: ['communes'], queryFn: getCommunes })
  const [commune, setCommune] = useState<string | null>(null)
  const q = useQuery({
    queryKey: ['commune-acquisitions', commune],
    queryFn: () => getCommuneAcquisitions(commune!),
    enabled: !!commune,
  })
  const d = q.data
  const ouvrirParcelle = (idu: string) => {
    // même patron que les listes d'événements (blocB O10) : retour carte + fiche parcelle
    const s = useApp.getState()
    s.setView('cartes')
    s.select(idu)
  }
  return (
    <div className="flex min-h-0 flex-1 flex-col gap-2">
      <div className="shrink-0">
        <p className="label-caps text-[9.5px]">Commune</p>
        <select data-acq-commune value={commune ?? ''} onChange={(e) => setCommune(e.target.value || null)}
          className="mt-1 w-full rounded-md border border-line-2 bg-surface-3 px-2 py-1.5 text-[12px] text-txt focus:border-mint focus:outline-none">
          <option value="">Choisir une commune…</option>
          {(communes.data ?? []).map((c) => <option key={c.insee} value={c.commune}>{c.commune}</option>)}
        </select>
      </div>
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
            {d.n} affichée{d.n > 1 ? 's' : ''} sur {d.n_total} changement{d.n_total > 1 ? 's' : ''} de
            propriétaire moral depuis {d.depuis_millesime}.
          </p>
          {d.acquisitions.map((a) => (
            <button key={`${a.idu}-${a.a_millesime}`} data-acq-ligne
              onClick={() => ouvrirParcelle(a.idu)}
              title={`Ouvrir la parcelle ${a.idu}`}
              className="rounded-md border border-line-2 bg-surface-2 px-2.5 py-1.5 text-left text-[11px] leading-snug text-txt transition-colors duration-quick hover:border-mint/50 hover:bg-surface-3">
              <span className="mr-1.5 rounded bg-mint-bg px-1.5 py-0.5 font-mono text-[10px] text-mint">{a.de_millesime}→{a.a_millesime}</span>
              <span className="text-txt-mut">{a.denomination_avant ?? '—'}</span>
              <span className="mx-1 text-txt-dim">→</span>
              <span className="font-medium text-txt-hi">{a.denomination_apres ?? '—'}</span>
              <span className="mt-0.5 block font-mono text-[9.5px] text-txt-dim">parcelle {a.idu} →</span>
            </button>
          ))}
          <p className="shrink-0 pb-1 text-[10px] leading-snug text-txt-dim italic">{d.note}</p>
        </div>
      )}
    </div>
  )
}

// ── O2-3 (OUTILS-2) — Bloc « Marché des annonces (Radar) » sous la table comparative ──
// Règle : tant qu'AUCUNE commune n'atteint SEUIL_N biens en vente, le bloc se replie en UNE ligne
// « en constitution · N biens collectés · à partir de 5 biens » — 24 lignes de zéros dilueraient les
// vrais chiffres et donneraient l'impression d'un produit vide. Au-delà, SEULES les communes au seuil
// s'affichent (les autres restent absentes, jamais un zéro). SEUIL_N vient du backend (pige/marche.py),
// jamais écrit en dur ici.
function MarcheAnnoncesRadar() {
  const setView = useApp((s) => s.setView)
  const { data: d } = useQuery({ queryKey: ['radar-marche'], queryFn: getRadarMarche, staleTime: 60_000 })
  if (!d) return null   // bloc non critique : silencieux si la donnée n'est pas là
  const auSeuil = d.communes
    .filter((c) => (c.actives ?? 0) >= d.seuil_n)
    .sort((a, b) => (b.actives ?? 0) - (a.actives ?? 0))
  return (
    <div data-communes-marche-radar className="mt-2 shrink-0 rounded-lg border border-line-2 bg-surface-2 px-3 py-2 text-[12px]">
      <div className="flex items-center justify-between gap-2">
        <b className="label-caps text-[10px] tracking-[0.14em] text-txt-dim">Marché des annonces (Radar)</b>
        <button data-marche-radar-lien onClick={() => setView('radar')} className="shrink-0 text-[11px] text-mint hover:underline">
          {auSeuil.length ? 'Ouvrir le Radar →' : 'Suivre la collecte →'}
        </button>
      </div>
      {auSeuil.length === 0 ? (
        <p className="mt-1 leading-snug text-txt-mut">
          <span className="text-txt-dim">en constitution</span> · <b className="text-txt">{fmtInt(d.corpus_actif)} biens collectés</b> ·
          affichage par commune à partir de {d.seuil_n} biens.
        </p>
      ) : (
        <div className="mt-1.5 flex flex-col gap-1">
          {auSeuil.map((c) => (
            <div key={c.commune} className="flex items-baseline justify-between gap-2">
              <span className="text-txt">{c.commune}</span>
              <span className="flex items-baseline gap-2 font-mono text-[11px]">
                <span className="text-txt-hi">{c.actives} en vente</span>
                {!c.prix_m2_bati.insuffisant && c.prix_m2_bati.valeur != null && (
                  <span className="text-txt-mut">{fmtInt(c.prix_m2_bati.valeur)} €/m² bâti</span>
                )}
              </span>
            </div>
          ))}
          <p className="mt-0.5 text-[9.5px] leading-snug text-txt-dim">
            Seules les communes atteignant {d.seuil_n} biens en vente s'affichent ({fmtInt(d.corpus_actif)} collectés en tout) ; prix médian quand n ≥ {d.seuil_n}.
          </p>
        </div>
      )}
    </div>
  )
}

// ── Porte de l'écran d'entrée (gabarit door-hot du tiroir Outils) ──
function Porte({ dataAttr, titre, sous, onClick }: { dataAttr: string; titre: string; sous: string; onClick: () => void }) {
  return (
    <button data-communes-porte={dataAttr} onClick={onClick}
      className="door door-hot mb-0 w-full text-left transition-colors duration-quick hover:border-line-3">
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
 *  fiche commune de CONTEXTE en panneau à droite (setContexteCommune) — l'ex-fiche-outil a disparu,
 *  la table se referme pour laisser voir le panneau. */
export function CommunesTablePanel() {
  const module = useApp((s) => s.module)
  const communesTableOpen = useApp((s) => s.communesTableOpen)
  const setCommunesTableOpen = useApp((s) => s.setCommunesTableOpen)
  const setContexteCommune = useApp((s) => s.setContexteCommune)
  if (module !== 'communes' || !communesTableOpen) return null
  return (
    <div data-communes-table-panel className="absolute inset-0 z-40 flex items-center justify-center bg-black/50 p-6"
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
          <O6Comparateur onSelect={(c) => { setContexteCommune(c); setCommunesTableOpen(false) }} />
          {/* O2-3 — le marché des annonces (Radar) sous la table, seuil géré côté backend. */}
          <MarcheAnnoncesRadar />
        </div>
      </div>
    </div>
  )
}
