import { useQuery } from '@tanstack/react-query'
import { useEffect, useRef, useState } from 'react'
import { getCommuneAcquisitions, getCommunes, getRadarMarche } from '../../lib/api'
import { useApp } from '../../store/useApp'
import { Squelette } from '../Loading'
import { EmptyState, ErrorState } from '../States'
import { CommunesLegende, O6Comparateur } from './blocB'
import { M18 } from './moteurs'
import { RadarMarche } from './RadarMarche'
import { Bouton } from '../ui/Bouton'
import { SousAccordion } from '../panel/FiltreLabuse'   // RETOURS-23 (pt 4) — accordéon partagé (DA)

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

// DA-FIX-4 verif (task 3) — l'ancien AcqChevron local passe sur le Chevron partagé (fermé ▶ / ouvert ▼).

// RETOURS-23 (pt 4) — SÉLECTEUR de commune à la DA de l'app (plus de <select> natif dont la liste
// déroulante est rendue par l'OS, hors charte) : déclencheur + volet `.floating`, lignes au survol
// vert (hover-fill), fermeture au clic-dehors / Échap. Même grammaire que le menu « Déplacer » du CRM.
function CommuneMenu({ communes, value, onChange }: {
  communes: { insee: string; commune: string }[]
  value: string | null
  onChange: (commune: string) => void
}) {
  const [open, setOpen] = useState(false)
  const wrap = useRef<HTMLDivElement>(null)
  useEffect(() => {
    if (!open) return
    const onDown = (e: MouseEvent) => { if (wrap.current && !wrap.current.contains(e.target as Node)) setOpen(false) }
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') setOpen(false) }
    document.addEventListener('mousedown', onDown); document.addEventListener('keydown', onKey)
    return () => { document.removeEventListener('mousedown', onDown); document.removeEventListener('keydown', onKey) }
  }, [open])
  return (
    <div ref={wrap} className="relative mt-1 w-full">
      <button data-acq-commune type="button" aria-haspopup="menu" aria-expanded={open} onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center justify-between gap-1.5 rounded-md border border-line-2 bg-surface-3 px-2 py-1.5 text-[12px] transition-colors duration-quick hover:border-mint/50">
        <span className={value ? 'text-txt' : 'text-txt-dim'}>{value ?? 'Choisir une commune…'}</span>
        <svg aria-hidden viewBox="0 0 12 12" className="ml-1 h-2.5 w-2.5 shrink-0 text-txt-mut"><path d="M2.5 4.5 L6 8 L9.5 4.5" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" /></svg>
      </button>
      {open && (
        <div role="menu" className="floating absolute left-0 top-full z-30 mt-1 max-h-64 w-full overflow-y-auto p-1 text-[12px]">
          {communes.map((c) => (
            <button key={c.insee} role="menuitem" data-acq-commune-opt={c.insee}
              onClick={() => { onChange(c.commune); setOpen(false) }}
              className={`hover-fill flex w-full items-center whitespace-nowrap rounded-md px-2.5 py-1.5 text-left transition-colors duration-quick ${value === c.commune ? 'text-mint' : 'text-txt'}`}>
              {c.commune}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

// ── Vue « Acquisitions récentes » (R3.3) — sélecteur de commune + listing, clic → parcelle ──
// RETOURS-11 O16 (Vic) : (c) le clic ouvre la fiche parcelle EN SUPERPOSITION (on ne quitte plus
// l'outil) ; (b) filtre par millésime d'arrivée (2023/2024/2025) sur les lignes chargées ; (d)
// mention « personnes morales uniquement » ; (e) regroupement par acquéreur (SIREN) avec renvoi vers
// son Scan patrimoine. NB : le backend ne sert au plus 50 lignes (limit=50) depuis 2022 — le total
// (« sur N ») n'est donc PAS paginable côté front (O16-a reste à faire côté serveur).
function AcquisitionsRecentes() {
  const communes = useQuery({ queryKey: ['communes'], queryFn: getCommunes })
  const [commune, setCommune] = useState<string | null>(null)
  // RETOURS-13 R14 — filtre par année MULTI-SÉLECTION (chips des années présentes) + pagination
  // « Voir plus — N / M chargés » par 200 (le plafond de 50 en dur est levé côté serveur).
  const [millesimes, setMillesimes] = useState<number[]>([])
  const [limite, setLimite] = useState(200)
  // RETOURS-23 (pt 4) — l'état d'ouverture par acquéreur est désormais LOCAL à chaque SousAccordion
  // (accordéon partagé de l'app) ; plus de Set `ouverts` ici.
  const q = useQuery({
    queryKey: ['commune-acquisitions', commune, limite],
    queryFn: () => getCommuneAcquisitions(commune!, limite),
    enabled: !!commune,
    placeholderData: (prev) => prev,   // « Voir plus » n'efface pas la liste pendant le rechargement
  })
  const d = q.data
  // RETOURS-15 B4 (P7) — clic sur une parcelle de la liste → focusParcelle(idu, {fiche}) : ZOOM +
  // CONTOUR surligné + fiche (le geste unique du socle S3). L'outil Communes reste monté à gauche
  // (module='communes'), la fiche s'ouvre en superposition à droite.
  const ouvrirParcelle = (idu: string) => useApp.getState().focusParcelle(idu, { fiche: true })
  // O16(e) — Scan patrimoine d'un acquéreur : même idiome que « Voir le patrimoine » (m02Prefill + module).
  // CHASSE-NAV-FIX-1 (N-4) — pose le FIL DE RETOUR « ← Communes » (comme Blocs/Permis/Remonter le temps),
  // APRÈS setModule (qui vide la pile via CLOSE_OVERLAYS) : l'utilisateur peut revenir à Communes.
  const ouvrirScanPatrimoine = (siren: string) => {
    const s = useApp.getState()
    s.setM02Prefill(siren)
    s.setModule('patrimoine')
    s.pushOutilRetour({ module: 'communes', label: 'Communes' })
  }
  // millésimes d'arrivée réellement présents dans les lignes chargées (jamais une année inventée)
  const anneesDispo = d
    ? [...new Set(d.acquisitions.map((a) => a.a_millesime))].sort((x, y) => y - x)
    : []
  const toggleMillesime = (an: number) => setMillesimes((ms) => ms.includes(an) ? ms.filter((x) => x !== an) : [...ms, an])
  const lignes = (d?.acquisitions ?? []).filter((a) => millesimes.length === 0 || millesimes.includes(a.a_millesime))
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
        <CommuneMenu communes={communes.data ?? []} value={commune}
          onChange={(c) => { setCommune(c); setMillesimes([]); setLimite(200) }} />
      </div>
      {/* O16(d) — le champ DGFiP ne publie QUE les personnes morales : dit une fois, franchement. */}
      {commune && (
        <p className="shrink-0 text-[10px] leading-snug text-txt-dim">
          Personnes morales uniquement — fichier DGFiP ; les acquisitions par des particuliers ne
          sont pas publiées.
        </p>
      )}
      {/* O16(b) — filtre par millésime d'arrivée (seulement les années effectivement présentes).
          COMMUNE-124 Lot C1 — même grammaire de puces que l'outil Permis (bloc « Filtrer par état ») :
          actif = aplat vert opaque (`bg-mint text-mint-ink`), survol = aplat vert opaque
          (`hover:bg-mint hover:text-mint-ink`), et la puce « Toutes » (le neutre) TOUJOURS en DERNIER
          (règle d'ordre RETOURS-15 U3, comme « Tout » dans Permis). */}
      {commune && anneesDispo.length > 1 && (
        <div data-acq-millesimes className="flex shrink-0 flex-wrap items-center gap-1.5 text-[11px]">
          {anneesDispo.map((an) => {
            const actif = millesimes.includes(an)
            return (
              <button key={an} data-acq-millesime={an} onClick={() => toggleMillesime(an)} aria-pressed={actif}
                className={`rounded-md px-2 py-0.5 font-mono transition-colors duration-quick ${
                  actif ? 'bg-mint text-mint-ink' : 'border border-line-2 text-txt hover:bg-mint hover:text-mint-ink'}`}>
                {an - 1}→{an}
              </button>
            )
          })}
          <button data-acq-millesime="" onClick={() => setMillesimes([])} aria-pressed={millesimes.length === 0}
            className={`rounded-md px-2 py-0.5 transition-colors duration-quick ${
              millesimes.length === 0 ? 'bg-mint text-mint-ink' : 'border border-line-2 text-txt hover:bg-mint hover:text-mint-ink'}`}>
            Toutes
          </button>
        </div>
      )}
      {!commune ? (
        <p className="text-[11px] leading-snug text-txt-dim">Choisissez une commune pour lister les
          changements récents de propriétaire moral (constat DGFiP par millésime).</p>
      ) : q.isLoading ? (
        <Squelette lignes={6} />
      ) : q.isError || !d ? (
        <ErrorState message="Constat indisponible — réessayez." retry={() => q.refetch()} />
      ) : d.n_total === 0 ? (
        <EmptyState title="Aucun changement de propriétaire moral constaté"
          hint={`depuis ${d.depuis_millesime} à ${commune}.`} />
      ) : (
        <div className="flex min-h-0 flex-1 flex-col gap-1.5 overflow-y-auto">
          {/* RETOURS-23 (pt 12) — la ligne « N changements · M acquéreurs — N / M chargés depuis 2022 »
              est RETIRÉE (demande Vic) : les accordéons par acquéreur et le bouton « Voir plus » portent
              déjà le décompte. */}
          {/* RETOURS-23 (pt 4) — une LIGNE par personne morale via l'accordéon PARTAGÉ de l'app
              (SousAccordion) : libellé = acquéreur, compte = N parcelles ; déplié → scan + parcelles. */}
          {groupes.map((g) => (
            <SousAccordion key={g.siren ?? '∅'} dataAttr="data-acq-groupe-tete"
              label={g.denomination ?? 'Acquéreur non identifié'}
              count={`${g.items.length} parcelle${g.items.length > 1 ? 's' : ''}`}>
              {g.siren && (
                /* RETOURS-23 (pt 3) — lien d'action VERT (plus d'ambre). */
                <button data-acq-scan={g.siren} onClick={() => ouvrirScanPatrimoine(g.siren!)}
                  className="self-start px-1.5 py-0.5 text-[11px] text-mint hover:underline">Scan patrimoine →</button>
              )}
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
            </SousAccordion>
          ))}
          {/* R14 — « Voir plus — N / M chargés », par 200 (règle des listes longues). */}
          {d.tronquee && (
            <Bouton niveau="lien" data-acq-voir-plus onClick={() => setLimite((l) => l + 200)}
              className="shrink-0 self-start">
              Voir plus — {d.n} / {d.n_total} chargés
            </Bouton>
          )}
          <p className="shrink-0 pb-1 text-[10px] leading-snug text-txt-dim italic">{d.note}</p>
        </div>
      )}
    </div>
  )
}

// COMMUNE-124 Lot A1 — l'encart « Marché des annonces (Radar) — N biens collectés à ce jour » qui
// s'affichait sous la table comparative est RETIRÉ : le Radar a déjà SA porte dédiée sur l'écran
// d'entrée (« Marché des annonces (Radar) »), ce renvoi doublonnait et alourdissait le bas du panneau.

// ── Porte de l'écran d'entrée (gabarit door-hot du tiroir Outils) ──
function Porte({ dataAttr, titre, sous, onClick }: { dataAttr: string; titre: string; sous: string; onClick: () => void }) {
  return (
    <button data-communes-porte={dataAttr} onClick={onClick}
      className="door hover-fill mb-0 w-full text-left transition-colors duration-quick">
      {/* RETOURS-23 (pt 8) — titre et description sur UNE ligne chacun (truncate = garde-fou). */}
      <div className="truncate text-xs font-medium text-txt">{titre}</div>
      <div className="mt-0.5 truncate text-[10.5px] leading-snug text-txt-dim">{sous}</div>
    </button>
  )
}

export function Communes() {
  const setCommunesTableOpen = useApp((s) => s.setCommunesTableOpen)
  const setEvolutionTableOpen = useApp((s) => s.setEvolutionTableOpen)
  const setRadarTableOpen = useApp((s) => s.setRadarTableOpen)
  // RECETTE-OUTILS-1 (point 8) — rouvrir une table FERME la fiche commune ouverte (la table, masquée
  // derrière la fiche, réapparaît au lieu de rester cachée).
  const setContexteCommune = useApp((s) => s.setContexteCommune)
  const communePrefill = useApp((s) => s.communePrefill)
  const setCommunePrefill = useApp((s) => s.setCommunePrefill)
  const [vue, setVue] = useState<'accueil' | 'acquisitions'>('accueil')
  // COPILOTE-2 lot 1 — le chemin FICHE commune : le Copilote pose `communePrefill` puis ouvre l'outil ;
  // on ouvre directement le tableau comparatif des 24 communes (la surface commune), puis on consomme.
  useEffect(() => {
    if (communePrefill) { setCommunesTableOpen(true); setCommunePrefill(null) }
  }, [communePrefill, setCommunesTableOpen, setCommunePrefill])
  // RETOURS-23 (pt 1) — le « ← Retour » interne est retiré : dans « Acquisitions récentes », le bouton
  // unique du haut ramène à la liste des chemins (sinon au menu Outils).
  const setOutilSousRetour = useApp((s) => s.setOutilSousRetour)
  useEffect(() => {
    setOutilSousRetour(vue === 'acquisitions' ? () => setVue('accueil') : null)
    return () => setOutilSousRetour(null)
  }, [vue, setOutilSousRetour])
  if (vue === 'accueil') {
    return (
      <div className="flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto">
        {/* RETOURS-23 (pt 8) — chaque chemin : titre ET description sur UNE ligne (descriptions raccourcies). */}
        <Porte dataAttr="comparaison" titre="Comparaison communes"
          sous="Les 24 communes comparées, triées par colonne."
          onClick={() => { setContexteCommune(null); setCommunesTableOpen(true) }} />
        <Porte dataAttr="evolution" titre="Évolution du marché : ventes et permis"
          sous="Ventes DVF et permis, par trimestre."
          onClick={() => setEvolutionTableOpen(true)} />
        <Porte dataAttr="radar-marche" titre="Marché des annonces (Radar)"
          sous="Les biens en vente repérés, par commune."
          onClick={() => setRadarTableOpen(true)} />
        <Porte dataAttr="acquisitions" titre="Acquisitions récentes"
          sous="Changements de propriétaire moral (DGFiP)."
          onClick={() => setVue('acquisitions')} />
      </div>
    )
  }
  return (
    <div className="flex min-h-0 flex-1 flex-col gap-2 overflow-hidden">
      <AcquisitionsRecentes />
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
  // COMMUNE-124 Lot A2 — la légende (ex-pied permanent) est repliée sous le bouton « Légende » du
  // coin haut-droit du panneau ; cliquer l'ouvre/le referme (défaut : replié).
  const [legendeOuverte, setLegendeOuverte] = useState(false)
  if (module !== 'communes' || !communesTableOpen) return null
  // RECETTE-OUTILS-2 (R5 / point 8) — fiche ouverte : le tableau RESTE MONTÉ ET VISIBLE derrière (plus
  // de `hidden`), simplement rendu PASSIF (`pointer-events-none`) pour que le clic aille à la fiche
  // (z-50, au-dessus) ; sa croix ferme la fiche et rend le tableau interactif, intact (tri/défilement).
  return (
    <div data-communes-table-panel
      className={`absolute inset-0 z-40 flex items-center justify-center bg-black/50 p-6${contexteCommune ? ' pointer-events-none' : ''}`}
      onClick={() => setCommunesTableOpen(false)}>
      <div className="floating flex max-h-full w-full max-w-[1240px] flex-col overflow-hidden" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between border-b border-line px-4 py-2.5">
          <div>
            <h2 className="text-sm font-medium text-txt-hi">Les 24 communes</h2>
            {/* COMMUNE-124 Lot A3 — accroche UNIQUE (ex-sous-titre + ex-Banner d'O6Comparateur fusionnés). */}
            <p className="text-[10.5px] text-txt-dim">Comparez les communes, ouvrez leur fiche, triez en cliquant sur leur en-tête.</p>
          </div>
          {/* COMMUNE-124 Lot A2 — « Légende » (haut à droite) : ouvre/referme le bloc légende replié. */}
          <div className="flex shrink-0 items-center gap-3">
            <button data-communes-legende-toggle onClick={() => setLegendeOuverte((v) => !v)} aria-expanded={legendeOuverte}
              className={`rounded-md border px-2 py-1 text-[11px] transition-colors duration-quick ${
                legendeOuverte ? 'border-mint bg-mint-bg text-mint' : 'border-line-2 text-txt-mut hover:border-mint hover:text-txt'}`}>
              Légende {legendeOuverte ? '▾' : '▸'}
            </button>
            <button onClick={() => setCommunesTableOpen(false)} className="text-txt-mut hover:text-txt" aria-label="Fermer">✕</button>
          </div>
        </div>
        {/* Légende repliable : rendue sous l'en-tête quand ouverte (plus de bloc légende permanent en bas). */}
        {legendeOuverte && (
          <div data-communes-legende className="shrink-0 border-b border-line-2 bg-surface-2 px-6 py-2">
            <CommunesLegende />
          </div>
        )}
        {/* flex column bornée : O6Comparateur gère son propre scroll interne (rangs).
            Pas d'overflow ICI (sinon double scroll). */}
        {/* RETOURS-13 R11 — marges internes gauche/droite élargies (la ligne survolée ne colle
            plus aux bords de la modale) ; largeur portée à 1240 px. */}
        <div className="flex min-h-0 flex-1 flex-col px-6 py-3">
          {/* RETOURS-11 O14(c) — cliquer une commune OUVRE sa fiche (ContextePanel, panneau droit)
              en SUPERPOSITION : la table reste montée dessous (on ne la referme plus). Fermer la
              fiche fait donc RÉAPPARAÎTRE le tableau comparatif, sans le reconstruire ni perdre le tri. */}
          <O6Comparateur onSelect={(c) => setContexteCommune(c)} />
        </div>
      </div>
    </div>
  )
}


/** RETOURS-14 S1 — « Marché des annonces (Radar) » EN GRAND : le tableau par commune du Radar,
 *  sous SON nom, avec SON compteur (101 biens collectés à la main — la minceur vient de la
 *  source, elle est dite, pas subie). Même coquille plein écran que « Les 24 communes ». */
export function RadarTablePanel() {
  const module = useApp((s) => s.module)
  const radarTableOpen = useApp((s) => s.radarTableOpen)
  const setRadarTableOpen = useApp((s) => s.setRadarTableOpen)
  useQuery({ queryKey: ['radar-marche'], queryFn: getRadarMarche, staleTime: 60_000, enabled: radarTableOpen })
  if (module !== 'communes' || !radarTableOpen) return null
  return (
    <div data-radar-table-panel
      className="absolute inset-0 z-40 flex items-center justify-center bg-black/50 p-6"
      onClick={() => setRadarTableOpen(false)}>
      <div className="floating flex max-h-full w-full max-w-[1240px] flex-col overflow-hidden" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between border-b border-line px-4 py-2.5">
          <div>
            <h2 className="text-sm font-medium text-txt-hi">
              Marché des annonces (Radar)
            </h2>
            <p className="text-[10.5px] text-txt-dim">Les biens en vente repérés par le Radar (collecte humaine), agrégés par commune. Une médiane ou un taux n'est servi qu'à partir de 5 biens — jamais de fausse précision.</p>
          </div>
          <button onClick={() => setRadarTableOpen(false)} className="text-txt-mut hover:text-txt" aria-label="Fermer">✕</button>
        </div>
        <div className="flex min-h-0 flex-1 flex-col overflow-y-auto px-6 py-3">
          <RadarMarche />
        </div>
      </div>
    </div>
  )
}

/** RETOURS-13 R13 — « Évolution du marché » EN GRAND : la MÊME coquille plein écran que la table
 *  des 24 communes (overlay noir, carte `floating`, en-tête + croix), le MÊME moteur M18 dedans
 *  (tableau trimestriel, en-tête collant, légende sous le tableau). Aucune donnée nouvelle. */
export function EvolutionTablePanel() {
  const module = useApp((s) => s.module)
  const evolutionTableOpen = useApp((s) => s.evolutionTableOpen)
  const setEvolutionTableOpen = useApp((s) => s.setEvolutionTableOpen)
  if (module !== 'communes' || !evolutionTableOpen) return null
  return (
    <div data-evolution-table-panel
      className="absolute inset-0 z-40 flex items-center justify-center bg-black/50 p-6"
      onClick={() => setEvolutionTableOpen(false)}>
      <div className="floating flex max-h-full w-full max-w-[1240px] flex-col overflow-hidden" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between border-b border-line px-4 py-2.5">
          <div>
            {/* COMMUNE-124 Lot B1 — titre resserré ; la source (DVF + Sitadel) est dite dans le sous-titre. */}
            <h2 className="text-sm font-medium text-txt-hi">Évolution du marché : ventes et permis</h2>
            <p className="text-[10.5px] text-txt-dim">DVF ancien bâti · DVF terrain nu · permis Sitadel — une ligne par trimestre sur 8 trimestres. Un trimestre sans vente reste « — ».</p>
          </div>
          <button onClick={() => setEvolutionTableOpen(false)} className="text-txt-mut hover:text-txt" aria-label="Fermer">✕</button>
        </div>
        <div className="flex min-h-0 flex-1 flex-col overflow-y-auto px-6 py-3">
          <M18 />
        </div>
      </div>
    </div>
  )
}
