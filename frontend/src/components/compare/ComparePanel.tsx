// M54-EXPO-3 A8 / COMPARAISON (refonte 13 outils) — comparateur 2 à 3 parcelles côte à côte.
// L'outil est ANCRÉ dans Outils : `CompareModule` = le panneau gauche (stepper ① clic-carte ②
// tableau ③ retour, chips de sélection, note SOCLE) ; `ComparePanel` = le TABLEAU en surimpression
// (contenu/colonnes INCHANGÉS, mandat point 4). La carte reste active à droite pendant le picking.
import { Fragment, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getCompare, type CompareRow } from '../../lib/api'
import { fmtInt, fmtTauxEmprise, iduCourt } from '../../lib/format'
import { useApp } from '../../store/useApp'
import { EntreeParcelle } from '../outils/EntreeParcelle'   // RECETTE-OUTILS-1 (point 17) — bloc de saisie unique
import { useOuvrirDocument } from '../../lib/ouvrirDocument'   // RECETTE-OUTILS-1 (point 21) — export PDF = Docs
import { docComparatifUrl } from '../../lib/api'
import { Squelette } from '../Loading'
import { EmptyState } from '../States'
import { Bouton } from '../ui/Bouton'
import { Tip } from '../Tip'   // RETOURS-29 — détail d'une contrainte au clic

// OUTILS-FIX-3 C1 — le verdict de scoring (verdictMeta) n'est plus affiché dans Comparer (badge « Faible »
// retiré : on n'impose pas l'Analyse LABUSE sur cet écran). Import + helper `verdict` supprimés.

// lignes du tableau (libellé, valeur) — resserrées : les doublons fiche (Capacité, CA estimé) retirés ;
// ajoutés : prix terrain nu/zone (M79) + contrainte majeure explicite.
// O9(d) — `num` + `best` permettent de surligner en vert la meilleure valeur de la ligne (front-side,
// comme la table Communes) : `best:'hi'` = la plus grande gagne (surface, capacité), `best:'lo'` = la
// plus basse gagne (charge foncière = moins cher). Les lignes booléennes/texte n'ont pas de gagnant.
// `title` (O9-c) = infobulle définissant la ligne au survol du libellé.
type Row = {
  label: string
  val: (r: CompareRow) => string
  num?: (r: CompareRow) => number | null
  best?: 'hi' | 'lo'
  title?: string
  // provenance : « source » = donnée publique observée · « estime » = calcul de LABUSE.
  prov: 'source' | 'estime'
  // RETOURS-29 — barre proportionnelle sous la valeur (lignes chiffrées).
  bar?: boolean
  // rendu personnalisé (puces de contraintes).
  render?: (r: CompareRow) => JSX.Element
}
// RECETTE-PROD-1 (12) — tag COURT de la cause (le code servi par /compare) pour la cellule SDP
// résiduelle. La phrase longue (engine.cause_libelle) vit dans l'infobulle de la ligne.
const CAUSE_COURT: Record<string, string> = {
  terrain_exigu: 'terrain exigu',
  hors_plu: 'hors PLU',
  redhibitoire: 'rédhibitoire',
  capacite_nulle: 'capacité nulle',
  bati_non_ingere: 'bâti non estimé',
}
const causeCourt = (c?: string | null): string | null => {
  if (!c) return null
  if (c.startsWith('zone_non_constructible') || c.startsWith('zone_non_resolue')) return 'zone non constructible'
  return CAUSE_COURT[c] ?? c.replace(/_/g, ' ')
}

// RETOURS-29 (Comparatif v2, maquette 15-comparatif-v2) — SEULES les lignes que l'API sert, dans l'ordre
// de la maquette. AUCUN classement LABUSE, AUCUNE puce de vente, AUCUN prix de marché (hors maquette).
const PROPRIO: Record<string, string> = { morale: 'personne morale', public: 'public', particulier: 'particulier', succession: 'succession', indivision: 'indivision' }
const ROWS: Row[] = [
  // TERRAIN
  { label: 'Surface', prov: 'source', bar: true, best: 'hi', num: (r) => r.surface_m2 ?? null,
    val: (r) => r.surface_m2 != null ? `${fmtInt(r.surface_m2)} m²` : '—' },
  { label: 'Bâti existant', prov: 'source', best: 'lo', num: (r) => r.bati_existant_pct ?? null,
    val: (r) => r.bati_existant_pct == null ? '—' : r.bati_existant_pct <= 0 ? 'aucun' : `${fmtInt(r.bati_existant_pct)} % du terrain`,
    title: 'Part du terrain déjà couverte par le bâti (emprise au sol / surface) — plus bas = plus de place à bâtir.' },
  { label: 'Propriétaire', prov: 'source', val: (r) => PROPRIO[r.proprietaire as string] ?? '—',
    title: 'Public / personne morale / succession / indivision / particulier — issu du fichier DGFiP.' },
  // URBANISME
  { label: 'Hauteur autorisée', prov: 'source', best: 'hi', num: (r) => r.gabarit_niveaux_max ?? null,
    val: (r) => r.gabarit_niveaux_max != null ? `R+${Math.max(0, r.gabarit_niveaux_max - 1)}${r.gabarit_combles ? ' + combles' : ''}` : '—',
    title: '« + combles » = niveau de combles aménageables sous un toit dont le faîtage domine l\'égout d\'au moins 1,80 m.' },
  { label: 'Emprise au sol maximale', prov: 'source', best: 'hi', num: (r) => r.emprise_ces_pct ?? null,
    val: (r) => r.emprise_ces_pct != null ? `${fmtInt(r.emprise_ces_pct)} %` : 'non réglementée',
    title: 'Emprise au sol maximale fixée par le règlement de la zone (CES) — « non réglementée » si le PLU n\'en fixe pas.' },
  // POTENTIEL CONSTRUCTIBLE
  { label: 'Plancher possible · bâti conservé', prov: 'estime', bar: true, best: 'hi', num: (r) => r.sdp_residuelle_m2 ?? null,
    val: (r) => {
      if (r.sdp_residuelle_m2 != null && r.sdp_residuelle_m2 > 0) return `${fmtInt(r.sdp_residuelle_m2)} m²`
      const base = r.sdp_residuelle_m2 === 0 ? '0 m²' : '—'
      const sc = causeCourt(r.cause)
      return sc ? `${base} · ${sc}` : base
    },
    title: 'Surface de plancher qui reste à bâtir en gardant le bâti existant.' },
  { label: 'Plancher possible · reconstruction', prov: 'estime', bar: true, best: 'hi', num: (r) => r.sdp_max_m2 ?? null,
    val: (r) => r.sdp_max_m2 != null ? `${fmtInt(r.sdp_max_m2)} m²` : '—',
    title: 'Surface de plancher maximale réglementaire, terrain libéré (après démolition du bâti existant).' },
  { label: 'Part du gabarit déjà occupée', prov: 'estime', best: 'lo', num: (r) => r.taux_emprise_pct ?? null,
    val: (r) => fmtTauxEmprise(r.taux_emprise_pct),
    title: 'Bâti existant ÷ emprise constructible (plus bas = plus de marge à bâtir). Au-delà de 100 % : « Saturé ».' },
  { label: 'Charge foncière', prov: 'estime', bar: true, best: 'hi', num: (r) => r.charge_fonciere_m2 ?? null,
    val: (r) => r.charge_fonciere_m2 != null ? `${fmtInt(r.charge_fonciere_m2)} €/m²` : '—',
    title: 'Charge foncière supportable ramenée au m² de terrain — plus haut = plus intéressant (négatif = l\'opération ne dégage rien pour le foncier).' },
  // RISQUES ET CONTRAINTES
  { label: 'Assainissement', prov: 'source', val: (r) => r.assainissement ?? '—',
    title: 'Desserte d\'assainissement — souvent un constat de secteur (statistique), pas un raccordement vérifié à la parcelle.' },
  { label: 'Contraintes relevées', prov: 'source',
    val: (r) => (r.contraintes ?? []).length ? `${(r.contraintes ?? []).length} relevée${(r.contraintes ?? []).length > 1 ? 's' : ''}` : 'aucune relevée',
    render: (r) => {
      const cs = r.contraintes ?? []
      if (!cs.length) return <span className="text-txt-dim">aucune relevée</span>
      return (
        <div className="flex flex-wrap gap-1">
          {cs.map((c, i) => (
            <Tip key={i} garder side="top" tip={c}>
              <span data-compare-contrainte role="button" tabIndex={0}
                className="cursor-help rounded-full border border-line-2 px-2 py-0.5 text-[10px] text-txt-mut hover:border-mint hover:text-txt">{contrainteCourt(c)}</span>
            </Tip>
          ))}
        </div>
      )
    } },
]

const SECTIONS = ['Terrain', 'Urbanisme', 'Potentiel constructible', 'Risques et contraintes'] as const
type Section = typeof SECTIONS[number]
const SECTION_OF: Record<string, Section> = {
  'Surface': 'Terrain', 'Bâti existant': 'Terrain', 'Propriétaire': 'Terrain',
  'Hauteur autorisée': 'Urbanisme', 'Emprise au sol maximale': 'Urbanisme',
  'Plancher possible · bâti conservé': 'Potentiel constructible', 'Plancher possible · reconstruction': 'Potentiel constructible',
  'Part du gabarit déjà occupée': 'Potentiel constructible', 'Charge foncière': 'Potentiel constructible',
  'Assainissement': 'Risques et contraintes', 'Contraintes relevées': 'Risques et contraintes',
}

// RETOURS-29 — puce COURTE d'une contrainte ; son détail complet s'ouvre au clic (Tip).
function contrainteCourt(c: string): string {
  const court = c.split(/\s[—·:(]/)[0].trim()
  return court.length > 34 ? `${court.slice(0, 32)}…` : court
}

// RETOURS-29 (maquette 15) — badge de provenance en OUTLINE : « sourcé » (vert) / « estimé » (ambre).
function ProvBadge({ prov }: { prov: 'source' | 'estime' }) {
  return prov === 'source'
    ? <span className="rounded-full border border-mint/50 px-1.5 py-0.5 text-[9px] font-medium text-mint">sourcé</span>
    : <span className="rounded-full border border-amber-500/50 px-1.5 py-0.5 text-[9px] font-medium text-amber-500">estimé</span>
}

// indice de la cellule gagnante. RETOURS-28/29 : AUCUN vert en cas d'égalité (gagnant UNIQUE) ni sur une
// valeur ABSENTE (null) ou NÉGATIVE. Un 0 RÉEL reste un gagnant valable pour une ligne « lo » (ex. « aucun »
// bâti, « 0 % » de gabarit occupé — cf. maquette).
function bestIdx(row: Row, parcels: CompareRow[]): Set<number> {
  const out = new Set<number>()
  if (!row.num || !row.best) return out
  const nums = parcels.map((p) => row.num!(p))
  const present = nums.filter((v): v is number => v != null)
  if (present.length < 2) return out
  const target = row.best === 'hi' ? Math.max(...present) : Math.min(...present)
  if (target < 0) return out                                    // pas de vert sur une valeur négative
  if (present.filter((v) => v === target).length !== 1) return out   // pas d'égalité
  nums.forEach((v, i) => { if (v != null && v === target) out.add(i) })
  return out
}

// RETOURS-29 — valeur MAX (> 0) d'une ligne à barre, pour la largeur proportionnelle des barres.
function barMax(row: Row, parcels: CompareRow[]): number {
  if (!row.num || !row.bar) return 0
  const pos = parcels.map((p) => row.num!(p)).filter((v): v is number => v != null && v > 0)
  return pos.length ? Math.max(...pos) : 0
}

// ── LE PANNEAU GAUCHE (outil « comparer », hôte ModulePanel) — ancré dans Outils, carte active à droite.
export function CompareModule() {
  const compareIdus = useApp((s) => s.compareIdus)
  const selectedIdu = useApp((s) => s.selectedIdu)   // O9(e) — parcelle courante (fiche ouverte)
  const addToCompare = useApp((s) => s.addToCompare)
  const removeFromCompare = useApp((s) => s.removeFromCompare)
  const clearCompare = useApp((s) => s.clearCompare)
  const setCompareOpen = useApp((s) => s.setCompareOpen)
  const setComparePicking = useApp((s) => s.setComparePicking)
  const setModuleMap = useApp((s) => s.setModuleMap)
  const n = compareIdus.length
  // panneau monté = picking ON (le clic-carte AJOUTE) + surlignage de la sélection ; nettoyage au démontage.
  useEffect(() => {
    setComparePicking(true)
    return () => { setComparePicking(false); setModuleMap({ idus: [], extra: null }) }
  }, [setComparePicking, setModuleMap])
  useEffect(() => { setModuleMap({ idus: compareIdus, extra: null }) }, [compareIdus, setModuleMap])
  // RECETTE-OUTILS-1 (point 23 / T1) — quitter l'outil VIDE la sélection (plus de persistance 15 min).
  useEffect(() => () => { clearCompare() }, [])   // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto">
      {/* RECETTE-OUTILS-1 (point 17 / T5) — bloc de saisie UNIQUE, comme les autres outils (barre
          « Adresse, IDU ou référence » + « — ou — cliquez une parcelle sur la carte »). Jusqu'à 3
          parcelles en puces retirables. Plus de « + 1 libre », plus d'étape numérotée, plus de
          « Réinitialiser » en tête. */}
      <p className="text-[11px] font-medium text-txt">Jusqu'à 3 parcelles — barre ou clic carte.</p>
      {n < 3 && (
        <EntreeParcelle source={null} viderApresPick
          onPick={(idu) => { if (!compareIdus.includes(idu)) addToCompare(idu) }} />
      )}
      {n > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {compareIdus.map((i, k) => (
            <span key={i} data-compare-chip className="flex items-center gap-1.5 rounded-lg border border-mint/50 bg-surface-2 px-2 py-1 font-mono text-[11px] text-txt">
              <b className="text-mint">{k + 1}</b>{iduCourt(i)}
              <button onClick={() => removeFromCompare(i)} className="text-txt-dim hover:text-st-ecartee" aria-label="Retirer">✕</button>
            </span>
          ))}
        </div>
      )}
      {/* ajouter la parcelle courante (fiche ouverte) sans la re-cliquer sur la carte */}
      {selectedIdu && !compareIdus.includes(selectedIdu) && n < 3 && (
        <Bouton niveau="secondaire" ton="vert" data-compare-ajouter-courante onClick={() => addToCompare(selectedIdu)} className="w-full">
          + Ajouter la parcelle courante ({iduCourt(selectedIdu)})
        </Bouton>
      )}
      <Bouton niveau="primaire" ton="vert" data-compare-ouvrir onClick={() => setCompareOpen(true)} disabled={n < 1} className="w-full">
        Comparer ({n}/3)
      </Bouton>
    </div>
  )
}

// ── LE TABLEAU (surimpression plein écran) — contenu/colonnes INCHANGÉS (mandat point 4).
export function ComparePanel() {
  const { compareIdus, removeFromCompare, select, setCompareOpen } = useApp()
  const { ouvrir, enCours } = useOuvrirDocument()   // RECETTE-OUTILS-1 (point 21) — export = doc Comparatif
  const q = useQuery({ queryKey: ['compare', compareIdus.join(',')], queryFn: () => getCompare(compareIdus), enabled: compareIdus.length > 0 })
  const parcels = q.data?.parcels ?? []

  // OUTILS-FIX-3 Lot E — l'export CSV du tableau (bouton + générateur client `exporterCsv`) est RETIRÉ
  // (décision Vic 06/09 : aucun export CSV dans l'app pour l'instant). Aucune capacité back touchée —
  // le tableau reste consultable à l'écran.

  // Échap ferme LE TABLEAU (retour carte + panneau) — capture, pour passer AVANT le handler « Échap =
  // fermer le module » de ModulePanel (qui, lui, ignore Échap tant que le tableau est ouvert).
  useEffect(() => {
    const h = (e: KeyboardEvent) => { if (e.key === 'Escape') { e.stopImmediatePropagation(); setCompareOpen(false) } }
    window.addEventListener('keydown', h, true)
    return () => window.removeEventListener('keydown', h, true)
  }, [setCompareOpen])

  return (
    // RETOURS-28 (Comparatif) — un clic HORS du tableau (sur le fond) ferme l'overlay (Échap aussi).
    <div data-compare-panel onClick={(e) => { if (e.target === e.currentTarget) setCompareOpen(false) }}
      className="absolute inset-0 z-40 flex items-center justify-center bg-black/50 p-6">
      {/* RETOURS-15 B7 (P13) — le tableau s'élargit à la largeur disponible (880 → 1240 px) pour que
          chaque libellé et chaque valeur tiennent sur UNE ligne à 1440 px (whitespace-nowrap plus bas). */}
      <div className="floating flex max-h-full w-full max-w-[1240px] flex-col overflow-hidden">
        <div className="flex items-center justify-between border-b border-line px-4 py-2.5">
          {/* RETOURS-29 (maquette 15) — titre + sous-titre « ● meilleure valeur de la ligne ». */}
          <div className="min-w-0">
            <p className="text-sm font-medium text-txt-hi">Comparer {compareIdus.length} parcelle{compareIdus.length > 1 ? 's' : ''}</p>
            <p className="flex items-center gap-1 text-[10.5px] text-txt-dim"><span className="text-mint">●</span> meilleure valeur de la ligne</p>
          </div>
          <div className="flex items-center gap-3 text-[11px]">
            {/* RECETTE-OUTILS-1 (point 21 / T6) — « Exporter en PDF » = le document « Comparatif » de Docs
                (même générateur back `/comparatif.pdf`). Requiert ≥ 2 parcelles. */}
            <Bouton niveau="secondaire" ton="vert" data-compare-export
              disabled={enCours != null || compareIdus.length < 2}
              onClick={() => ouvrir(docComparatifUrl(compareIdus), 'comparatif')}>
              Exporter en PDF
            </Bouton>
            {/* RECETTE-OUTILS-1 (point 19) — « Retour à la carte » et « Tout vider » retirés : seule la
                croix ferme le tableau (et ramène à la carte). */}
            <button onClick={() => setCompareOpen(false)} className="text-txt-mut hover:text-txt" aria-label="Fermer">✕</button>
          </div>
        </div>
        <div className="min-h-0 flex-1 overflow-auto p-3">
          {compareIdus.length === 0 && (
            <div data-compare-vide>
              <EmptyState title="Aucune parcelle à comparer."
                hint={<>Cliquez-en sur la carte ou ouvrez une fiche → Comparer.</>}
                action={<Bouton niveau="lien" onClick={() => setCompareOpen(false)}>Cliquez-en sur la carte</Bouton>} />
            </div>
          )}
          {compareIdus.length > 0 && q.isPending && <div className="p-4"><Squelette lignes={4} /></div>}
          {/* RECETTE-2 (D6) — table-fixed : les 3 colonnes de données se partagent la largeur à ÉGALITÉ et
              tiennent dans l'overlay (jamais de défilement horizontal) ; le texte long passe à la ligne
              dans sa cellule (whitespace-nowrap retiré plus bas). */}
          {parcels.length > 0 && (
            <table className="w-full table-fixed border-collapse text-[12px]">
              <thead>
                <tr>
                  {/* RETOURS-29 — en-tête de la colonne libellé : « N parcelles · commune ». */}
                  <th scope="col" className="w-[190px] p-2 align-bottom text-left text-[10px] font-normal text-txt-dim">
                    {compareIdus.length} parcelle{compareIdus.length > 1 ? 's' : ''}{parcels[0]?.commune ? ` · ${parcels[0].commune}` : ''}
                  </th>
                  {/* colonne dédiée aux badges « sourcé »/« estimé », entre le libellé et les valeurs. */}
                  <th scope="col" className="w-[58px] p-2" />
                  {parcels.map((r) => (
                    // RETOURS-29 (maquette 15) — en-tête colonne : IDU · adresse (aperçu) · zone · surface ·
                    // « Ouvrir la fiche → » · croix. Aucun classement/bande.
                    <th scope="col" key={r.idu} data-compare-col className="border-l border-line p-2 align-top">
                      <div className="flex items-start justify-between gap-2">
                        <span className="font-mono text-[11px] font-semibold tracking-tight text-txt-hi">{r.idu}</span>
                        <button onClick={() => removeFromCompare(r.idu)} aria-label="Retirer" className="shrink-0 text-[11px] text-txt-dim hover:text-st-ecartee">✕</button>
                      </div>
                      <p className="mt-0.5 break-words text-[10.5px] font-normal text-txt">{r.adresse ?? r.commune ?? '—'}</p>
                      <p className="mt-0.5 text-[10px] font-normal text-txt-dim">
                        {[r.zone, r.surface_m2 != null ? `${fmtInt(r.surface_m2)} m²` : null].filter(Boolean).join(' · ') || '—'}
                      </p>
                      <button data-compare-fiche onClick={() => select(r.idu)} className="mt-1 text-[10.5px] font-medium text-mint hover:underline">Ouvrir la fiche →</button>
                    </th>
                  ))}
                </tr>
              </thead>
              {/* RETOURS-29 (maquette 15) — lignes regroupées en 4 sections ; badge en 2e colonne ; valeur
                  avec point vert sur le gagnant + fine barre proportionnelle sur les lignes chiffrées. */}
              <tbody>
                {SECTIONS.map((sec) => {
                  const secRows = ROWS.filter((row) => SECTION_OF[row.label] === sec)
                  return (
                    <Fragment key={sec}>
                      <tr data-compare-section={sec}>
                        <td colSpan={2 + parcels.length} className="px-2 pb-1 pt-3 text-[10px] font-semibold uppercase tracking-[.1em] text-mint">{sec}</td>
                      </tr>
                      {secRows.map((row) => {
                        const winners = bestIdx(row, parcels)     // gagnant unique (ou aucun)
                        const bmax = barMax(row, parcels)         // max > 0 pour la largeur des barres
                        return (
                          <tr key={row.label} className="border-t border-line">
                            <td className="break-words p-2 align-top text-[10.5px] text-txt-dim">
                              {row.title
                                ? <span className="cursor-help border-b border-dotted border-line-2">{row.label}</span>
                                : row.label}
                            </td>
                            {/* badge de provenance dans SA colonne (entre libellé et valeurs). */}
                            <td className="p-2 align-top"><ProvBadge prov={row.prov} /></td>
                            {parcels.map((r, i) => {
                              const win = winners.has(i)
                              const v = row.num ? row.num(r) : null
                              const barW = row.bar && bmax > 0 && v != null && v > 0 ? Math.max(4, Math.round((v / bmax) * 100)) : 0
                              return (
                                <td key={r.idu} className="border-l border-line p-2 align-top">
                                  <div className="flex items-baseline gap-1">
                                    {win && <span aria-hidden className="text-[10px] text-mint">●</span>}
                                    <span className={`break-words ${win ? 'font-semibold text-mint' : 'text-txt'}`}>
                                      {row.render ? row.render(r) : row.val(r)}
                                    </span>
                                  </div>
                                  {row.bar && barW > 0 && (
                                    <div className="mt-1.5 h-[2px] w-full max-w-[180px] overflow-hidden rounded-full bg-line-2">
                                      <div className={`h-full rounded-full ${win ? 'bg-mint' : 'bg-txt-ghost'}`} style={{ width: `${barW}%` }} />
                                    </div>
                                  )}
                                </td>
                              )
                            })}
                          </tr>
                        )
                      })}
                    </Fragment>
                  )
                })}
              </tbody>
            </table>
          )}
          {/* RETOURS-29 (maquette 15) — pied : légende des badges + rappel du clic sur une contrainte. */}
          {parcels.length > 0 && (
            <p data-compare-pied className="mt-2 border-t border-line px-1 pt-2 text-[10px] text-txt-dim">
              <span className="text-mint">sourcé</span> : donnée publique · <span className="text-amber-500">estimé</span> : calcul de LABUSE. Un clic sur une contrainte en affiche le détail.
            </p>
          )}
        </div>
      </div>
    </div>
  )
}
