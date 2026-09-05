/** BLOC B · Partie 2 — les outils O sans écran (verdict Vic sur maquettes docs/mockups/).
 *  Chaque module vit dans le shell violet du registre ; tokens seulement, wording boussole
 *  (Sourcé/Estimé, « non couvert » dit — jamais un faux RAS). */
import { useQuery } from '@tanstack/react-query'
import { useEffect, useMemo, useState } from 'react'
import { useApp } from '../../store/useApp'
import { ParcelInput } from '../ParcelInput'
import { Loading } from '../Loading'
import { ErrorState } from '../States'
import { Tip } from '../Tip'

const jfetch = async <T,>(url: string): Promise<T> => {
  const r = await fetch(url)
  if (!r.ok) throw new Error(`${url} → ${r.status}`)
  return r.json() as Promise<T>
}

function Banner({ children }: { children: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-mint/40 bg-mint/[0.07] px-3 py-2 text-[10.5px] leading-relaxed text-txt-mut">
      {children}
    </div>
  )
}

/* ───────────── O5 — SERVITUDES INVISIBLES (S46) ───────────── */

type Servitudes = {
  idu: string; n: number; synthese: string
  servitudes: { categorie: string; effet: string; source: string; date: string | null }[]
  non_couvert: string[]
}

export function O5Servitudes() {
  const { selectedIdu, select } = useApp()
  const [idu, setIdu] = useState(selectedIdu ?? '')
  useEffect(() => { if (selectedIdu) setIdu(selectedIdu) }, [selectedIdu])
  const q = useQuery({
    queryKey: ['o5', idu],
    queryFn: () => jfetch<Servitudes>(`/servitudes-invisibles/${idu.trim()}`),
    enabled: idu.trim().length === 14,
  })
  const d = q.data
  return (
    <>
      {/* RETOURS-12 O3 — intro DESCRIPTIVE : ce que l'outil montre. L'aveu « ce que nos données ne
          couvrent pas » quitte l'accueil client ; la limite vit désormais dans « Méthode & limites »
          (replié, plus bas). */}
      <Banner>Ce qui peut bloquer un projet sans se voir sur la carte : servitudes, sols, bruit,
        assainissement. Chaque servitude est nommée, datée et sourcée.</Banner>
      {/* PATRON OMNIBOX (M137) — adresse OU IDU dans le même champ (ParcelInput partagé). Le clic
          carte est déjà capté par l'effet selectedIdu ci-dessus → withCarte inutile ici. */}
      <ParcelInput dataAttr="o5-idu" withCarte={false} placeholder="Adresse ou IDU (ou clic carte)" onPick={(id) => setIdu(id)} />
      {q.isLoading && <Loading accent="mint" label="Recherche des servitudes…" />}
      {q.isError && <ErrorState className="py-6" message="Servitudes indisponibles." retry={() => q.refetch()} />}
      {d && (
        <div className="flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto">
          <div className="rounded-lg border border-line-2 bg-surface-2 px-3 py-2 text-[11px]">
            <span className="num-key text-base text-mint">{d.n}</span>{' '}
            <span className="text-txt-mut">servitude(s)/contrainte(s) sur</span>{' '}
            <button onClick={() => select(d.idu)} className="font-mono text-txt-hi hover:text-mint hover:underline">
              {d.idu.slice(8, 10)} {d.idu.slice(10)}</button>
          </div>
          {d.servitudes.map((s, i) => (
            <div key={i} className="rounded-lg bg-surface-3 px-3 py-2 shadow-elev-1">
              <div className="flex flex-wrap items-baseline gap-1.5">
                <b className="text-[11.5px] text-txt-hi">{s.categorie}</b>
                <span className="rounded-full border border-mint/40 bg-mint/10 px-1.5 text-[8.5px] font-medium text-mint">Sourcé</span>
                <span className="text-[9.5px] text-txt-dim">{s.source}{s.date ? ` · ${s.date}` : ''}</span>
              </div>
              <p className="mt-1 text-[11px] leading-snug text-txt">{s.effet}</p>
            </div>
          ))}
          {d.servitudes.length === 0 && (
            <p className="rounded-lg bg-surface-2/60 px-3 py-2 text-[11px] text-txt-mut">
              Aucune servitude détectée dans les couches ingérées à cette parcelle.</p>
          )}
          {/* RETOURS-12 O3 — l'encadré « NON COUVERT PAR LA BASE — À VÉRIFIER AILLEURS » quitte la vue
              client : plus d'aveu d'ignorance en évidence. Ce qui reste (les limites de couverture)
              vit ICI, dans une MÉTHODE repliée. Les procédures PLU renvoient discrètement à l'outil
              PLU ; les 417 SUP décodées sont rappelées comme une réserve courte, pas une alarme. */}
          {d.non_couvert?.length > 0 && (
            <details data-o5-methode className="rounded-lg border border-line-2 bg-surface-2 px-3 py-2">
              <summary className="cursor-pointer list-none text-[10.5px] text-txt-dim hover:text-txt">
                Méthode &amp; limites — ce que la base ne voit pas <span className="text-txt-mut">(déplier)</span>
              </summary>
              <div className="mt-1.5 space-y-0.5 border-t border-line pt-1.5">
                {d.non_couvert.map((n, i) => <p key={i} className="text-[10.5px] leading-snug text-txt-mut">· {n}</p>)}
                <p className="mt-1 text-[9.5px] leading-snug text-txt-dim">Une servitude non publiée au Géoportail de l'urbanisme n'est pas vue — le certificat d'urbanisme reste la référence. Les procédures PLU en cours sont servies par l'outil « PLU ».</p>
              </div>
            </details>
          )}
        </div>
      )}
      {!d && !q.isLoading && !q.isError && (
        <p className="text-[11px] text-txt-dim">Saisissez un IDU complet (14 caractères) ou cliquez une parcelle.</p>
      )}
    </>
  )
}

/* ───────────── O6 — COMPARATEUR DE COMMUNES (S47) ───────────── */

type Comparateur = {
  communes: Record<string, string | number | null>[]
  indicateurs: Record<string, { libelle: string; direction: string; poids: number; source: string; nature: string }>
  methode: string; avertissement: string
}
// communes-tableau — UN SEUL tableau, toutes les colonnes visibles d'un coup (rendu en GRAND, overlay
// plein écran), chacune triable par clic sur son en-tête. Plus de composite ni de pondérations.
//  • `head` = intitulé LISIBLE (fini « Vélo »/« SRU » cryptiques : le mandat COMMUNES renomme).
//  • `title`/`tip` = « i » d'en-tête (les deux prix DOIVENT se distinguer : ancien ≠ neuf).
//  • `best` = sens de la « meilleure » valeur, mis en VERT pour guider l'œil — seulement là où « mieux »
//    est NON ambigu pour l'investisseur : plus de foncier (max) et instruction plus rapide (min). Les
//    prix et le déficit SRU restent neutres (pas de faux signal « bon/mauvais »).
// PERMIS : la donnée servie est un CUMUL SUR 5 ANS (comparateur.py : INTERVAL '5 years'), PAS un
// glissant 12 mois — la maquette disait « Permis 12 m », c'était illustratif et faux. On étiquette vrai.
const O6_COLS: { k: string; head: string; title: string; tip?: string; best?: 'max' | 'min' }[] = [
  // RETOURS-11 O14b (décision Vic) — « Stock foncier » renommé « Parcelles à potentiel »
  // (= Priorité + À suivre), définition au survol.
  { k: 'stock', head: 'Parcelles à potentiel', best: 'max',
    title: 'Parcelles à potentiel — parcelles promues par LABUSE sur la commune (Priorité + À suivre, run servi)' },
  { k: 'velocite', head: 'Instruction (mois)', best: 'min',
    title: 'Instruction — délai médian dépôt→autorisation, en mois (plus bas = plus rapide)' },
  { k: 'permis', head: 'Permis (5 ans)',
    title: 'Dynamisme permis — permis SITADEL cumulés sur 5 ans (glissants)' },
  { k: 'deficit_sru', head: 'Déficit SRU (pts)',
    title: 'Déficit SRU — objectif légal − taux de logement social, en points' },
  { k: 'prix_ancien', head: '€/m² ancien',
    title: '€/m² ANCIEN — médiane DVF de la commune entière (tous types bâti, ventes strictes, n ≥ 100). Vue MACRO : la même série que le Baromètre.',
    tip: '€/m² ANCIEN — médiane DVF COMMUNE ENTIÈRE (tous types bâti, ventes strictes, n ≥ 100). Vue macro, série du Baromètre. ⚠ La FICHE d’une commune affiche un prix LOCAL (secteur autour de la parcelle centrale, appartements priorisés) — plus fin, souvent inférieur : c’est normal qu’il diffère de cette colonne.' },
  { k: 'prix_neuf', head: '€/m² neuf',
    title: '€/m² NEUF — prix de sortie du neuf (DVF), €/m² habitable. À NE PAS confondre avec l’ancien : marché et niveau différents.',
    tip: '€/m² NEUF — prix de sortie du neuf (DVF), €/m² habitable. À NE PAS confondre avec l’ancien : marché et niveau différents.' },
  // RETOURS-11F O14/M13 — €/m² TERRAIN NU DVF : « le chiffre du promoteur », absent jusqu'ici. MÊME
  // moteur que la fiche (Marché) — médiane DVF terrain nu par zone PLU calibrée (U de préférence, sinon
  // AU). Sous le seuil de cellule → « — ». 23/24 communes servables (mesuré base réelle).
  { k: 'prix_terrain_nu', head: '€/m² terrain nu',
    title: '€/m² TERRAIN NU — médiane DVF des ventes de terrain nu de la commune, par zone PLU calibrée (U de préférence, sinon AU). C’est la valeur foncière brute que vise un promoteur — le chiffre le plus direct pour arbitrer un achat.',
    tip: '€/m² TERRAIN NU — médiane DVF terrain nu par zone PLU (U sinon AU). La valeur foncière brute (« le chiffre du promoteur »). Absente si la commune n’a pas assez de ventes de terrain (→ « — »).' },
]
// Rendu en GRAND (overlay ≤ 1100 px) : colonnes larges, tout lisible, zéro scroll horizontal. Dernière
// piste = affordance de clic (chevron › / « Ouvrir la fiche → » au survol).
const O6_GRID = 'grid-cols-[minmax(140px,1.5fr)_repeat(7,minmax(72px,1fr))_minmax(96px,0.7fr)] gap-x-2'
const fmtFr = (v: unknown) => (v == null ? '—' : Number(v).toLocaleString('fr-FR'))

// `onSelect` : dans l'outil Communes, cliquer une ligne ouvre la fiche commune.
export function O6Comparateur({ onSelect }: { onSelect?: (commune: string) => void } = {}) {
  // Tri par CLIC sur l'en-tête ; défaut = stock foncier décroissant (l'entrée la plus parlante :
  // où il y a le plus de foncier à travailler). Re-clic sur la même colonne inverse le sens.
  const [tri, setTri] = useState<{ k: string; dir: 'desc' | 'asc' }>({ k: 'stock', dir: 'desc' })
  const q = useQuery({ queryKey: ['o6'], queryFn: () => jfetch<Comparateur>('/comparateur-communes') })
  const clicTri = (k: string) => setTri((t) => (t.k === k ? { k, dir: t.dir === 'desc' ? 'asc' : 'desc' } : { k, dir: 'desc' }))
  const rows = [...(q.data?.communes ?? [])].sort((a, b) => {
    const av = a[tri.k], bv = b[tri.k]                    // NULL toujours en bas, quel que soit le sens
    if (av == null && bv == null) return 0
    if (av == null) return 1
    if (bv == null) return -1
    return tri.dir === 'desc' ? Number(bv) - Number(av) : Number(av) - Number(bv)
  })
  // « meilleure valeur » par colonne (invariante au tri) — seulement pour les colonnes à sens clair.
  const best = useMemo(() => {
    const m: Record<string, number> = {}
    for (const col of O6_COLS) {
      if (!col.best) continue
      const vals = (q.data?.communes ?? []).map((c) => c[col.k]).filter((v) => v != null).map(Number)
      if (vals.length) m[col.k] = col.best === 'max' ? Math.max(...vals) : Math.min(...vals)
    }
    return m
  }, [q.data])
  const arrow = (k: string) => (tri.k === k ? (tri.dir === 'desc' ? ' ↓' : ' ↑') : '')
  // Colonne FLEX : bannière (haut) + rangs qui défilent (milieu, scroll unique) + légende PERMANENTE
  // (bas, jamais poussée hors écran). Le parent (CommunesTablePanel) donne la hauteur bornée.
  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <Banner>Où investir : les <b>24 communes</b>, tous les indicateurs sourcés d’un coup. Cliquez un
        <b> en-tête</b> pour trier, une <b>ligne</b> pour ouvrir sa fiche.</Banner>
      {q.isLoading && <Loading accent="mint" label="Chargement des communes…" />}
      {q.isError && <ErrorState className="py-6" message="Comparateur indisponible." retry={() => q.refetch()} />}
      <div className="min-h-0 flex-1 overflow-y-auto">
        {/* RETOURS-12 T4 — thead-sticky (z-20, fond opaque) : l'en-tête « 24 communes » ne glisse plus sur les lignes. */}
        <div className={`thead-sticky grid ${O6_GRID} items-end border-b border-line-2 px-2 py-1.5`}>
          <span className="label-caps text-[10px] text-txt-mut">Commune</span>
          {O6_COLS.map((c) => (
            <span key={c.k} className="flex items-center justify-end gap-1">
              <button data-o6-tri={c.k} onClick={() => clicTri(c.k)} title={c.tip ?? c.title}
                className={`text-right text-[10px] font-medium uppercase leading-tight tracking-tight ${
                  tri.k === c.k ? 'text-mint' : 'text-txt-dim hover:text-txt-mut'}`}>
                {c.head}{arrow(c.k)}</button>
              <Tip side="top" tip={c.tip ?? c.title}>
                <span role="button" tabIndex={0} aria-label={c.title}
                  className="flex h-[13px] w-[13px] shrink-0 items-center justify-center rounded-full border border-line-2 text-[8px] font-bold leading-none text-txt-dim hover:border-mint hover:text-mint">i</span>
              </Tip>
            </span>
          ))}
          {/* consigne d'affordance dans l'en-tête (dernière piste = « ouvrir ») */}
          <span className="text-right text-[9px] normal-case text-txt-dim">cliquez une ligne →</span>
        </div>
        {/* RETOURS-13 R11 — l'infobulle qui répétait le nom (title) est RETIRÉE ; la ligne
            survolée s'arrondit et respecte les marges (px-2 header + rangs, mêmes colonnes). */}
        {rows.map((c) => {
          const Cell = onSelect ? 'button' : 'div'
          return (
            <Cell key={String(c['insee'])} data-o6-row
              {...(onSelect ? { onClick: () => onSelect(String(c['commune'])) } : {})}
              className={`group grid w-full ${O6_GRID} items-baseline rounded-md border-b border-line px-2 py-2 text-left ${onSelect ? 'hover-fill transition-colors duration-quick' : ''}`}>
              <span className="min-w-0 truncate text-[12px] font-medium text-txt group-hover:text-txt-hi">{String(c['commune'])}</span>
              {O6_COLS.map((col) => {
                const isBest = best[col.k] != null && Number(c[col.k]) === best[col.k]
                return (
                  <span key={col.k} data-o6-cell={col.k}
                    className={`tnum text-right font-mono text-[11px] ${
                      isBest ? 'font-semibold text-mint' : tri.k === col.k ? 'font-semibold text-txt-hi' : 'text-txt-mut'}`}>
                    {fmtFr(c[col.k])}</span>
                )
              })}
              {/* OUTILS-1 B4 — « Fiche → » PERMANENT sur chaque ligne. RETOURS-13 R11 — action
                  SECONDAIRE : jaune opaque au survol (distinct du survol vert de la ligne). */}
              {onSelect && (
                <span className="hover-jaune -my-0.5 justify-self-end whitespace-nowrap px-1.5 py-0.5 text-right text-[11px] font-medium text-mint">Fiche →</span>
              )}
            </Cell>
          )
        })}
      </div>
      {/* LÉGENDE PERMANENTE en pied — plus d'en-tête à deviner. */}
      <div data-o6-legende className="shrink-0 border-t border-line-2 pt-2 text-[10px] leading-relaxed text-txt-dim">
        <b className="text-txt-mut">Légende :</b>{' '}
        <b>Parcelles à potentiel</b> = parcelles promues par LABUSE (Priorité + À suivre) ·{' '}
        <b>Instruction</b> = délai médian dépôt→autorisation (mois) ·{' '}
        <b>Permis 5 ans</b> = permis SITADEL cumulés sur 5 ans ·{' '}
        <b>Déficit SRU</b> = objectif légal − taux de logement social (points) ·{' '}
        <b>€/m² ancien</b> = médiane DVF commune entière (ventes strictes) ·{' '}
        <b>€/m² neuf</b> = prix de sortie du neuf ·{' '}
        <b>€/m² terrain nu</b> = médiane DVF terrain nu par zone PLU (U sinon AU) — le chiffre du promoteur.
        <span className="mt-0.5 block">Meilleure valeur en <span className="font-semibold text-mint">vert</span> (foncier / rapidité d’instruction).
          Une donnée absente reste « — », jamais un zéro inventé.</span>
      </div>
    </div>
  )
}

/* ───────────── O7 — CARNET DE SECTEUR (S48) ───────────── */

type CarnetListe = { secteurs: { secteur: string; commune: string; opportunites: number; brulantes: number }[]; note: string }
type CarnetSecteur = {
  secteur: string; commune: string; section: string
  stock: { total: number; opportunites: number; par_tier: Record<string, number> }
  prix: { dvf: Record<string, { mediane_prix_m2: number | null; n: number }> } | null
  signaux: { type: string; n: number }[] | null
  permis_24_mois: number | null
  note: string; avertissement: string | null
}

// DORMANT — outil « Suivi de secteur » retiré du produit le 21/08/2026 (plus câblé au menu : registry +
// ModulePanel COMPONENTS). Mesuré : nom qui promettait un suivi non fait (le vrai suivi = la Veille),
// 0 état, 0 usage, plafond muet 30/478. Vue en partie ailleurs (prix→fiche, ZAN→Communes, permis→radar) ;
// seul le compte d'opportunités agrégé PAR SECTION reste sans autre foyer. Composant conservé au dépôt
// (exporté) ; endpoints /carnet-secteur vivants. Concept-route Copilote retirée.
export function O7Carnet() {
  const [secteur, setSecteur] = useState<string | null>(null)
  const liste = useQuery({ queryKey: ['o7-liste'], queryFn: () => jfetch<CarnetListe>('/carnet-secteur') })
  const page = useQuery({
    queryKey: ['o7', secteur], queryFn: () => jfetch<CarnetSecteur>(`/carnet-secteur/${secteur}`),
    enabled: !!secteur,
  })
  const d = page.data
  if (secteur && d) {
    const dvf = Object.entries(d.prix?.dvf ?? {}).filter(([, v]) => v.mediane_prix_m2 != null)
    return (
      <>
        <button onClick={() => setSecteur(null)}
          className="min-h-7 self-start text-[11px] text-txt-mut transition-colors duration-quick hover:text-txt-hi">← Secteurs</button>
        <div className="rounded-lg border border-line-2 bg-surface-2 px-3 py-2">
          <span className="font-mono text-txt-hi">{d.secteur.slice(8)}</span>
          <span className="ml-2 text-[11px] text-txt-mut">{d.commune} · section {d.section}</span>
        </div>
        <div className="grid grid-cols-2 gap-2">
          <div className="rounded-lg bg-surface-3 px-3 py-2 shadow-elev-1">
            <p className="label-caps text-[9px]">Opportunités</p>
            <p className="num-key text-lg text-mint">{d.stock.opportunites}</p>
            <p className="text-[9.5px] text-txt-dim">{d.stock.par_tier['brulante'] ?? 0} brûlantes · {d.stock.total} parcelles</p>
          </div>
          <div className="rounded-lg bg-surface-3 px-3 py-2 shadow-elev-1">
            <p className="label-caps text-[9px]">Permis 24 mois</p>
            <p className="num-key text-lg">{d.permis_24_mois ?? '—'}</p>
          </div>
        </div>
        {dvf.length > 0 && (
          <div className="rounded-lg bg-surface-3 px-3 py-2 shadow-elev-1">
            <p className="label-caps text-[9px]">Prix médians DVF <span className="normal-case text-mint">Sourcé</span></p>
            {dvf.map(([k, v]) => (
              <div key={k} className="flex items-baseline justify-between text-[11px]">
                <span className="text-txt-mut">{k}</span>
                <span className="tnum font-mono text-txt">{Number(v.mediane_prix_m2).toLocaleString('fr-FR')} €/m² <span className="text-txt-dim">({v.n})</span></span>
              </div>
            ))}
          </div>
        )}
        {(d.signaux?.length ?? 0) > 0 && (
          <div className="rounded-lg bg-surface-3 px-3 py-2 shadow-elev-1">
            <p className="label-caps text-[9px]">Signaux du secteur</p>
            {d.signaux!.map((sg) => (
              <div key={sg.type} className="flex items-baseline justify-between text-[11px]">
                <span className="min-w-0 truncate text-txt-mut">{sg.type}</span>
                <span className="tnum font-mono text-txt">{sg.n}</span>
              </div>
            ))}
          </div>
        )}
        <p className="shrink-0 text-[9.5px] leading-snug text-txt-dim">{d.note}</p>
      </>
    )
  }
  return (
    <>
      <Banner>Votre <b>secteur</b> (section cadastrale) suivi comme un portefeuille — stock
        d'opportunités, prix, permis, signaux, tout sourcé. L'abonnement digest arrivera avec
        les comptes utilisateurs ; le carnet se consulte à la demande.</Banner>
      {liste.isLoading && <Loading accent="mint" label="Secteurs les plus actifs…" />}
      {liste.isError && <ErrorState className="py-6" message="Carnet indisponible." retry={() => liste.refetch()} />}
      {secteur && page.isLoading && <Loading accent="mint" label="Ouverture du secteur…" />}
      <div className="flex min-h-0 flex-1 flex-col gap-1.5 overflow-y-auto">
        {(liste.data?.secteurs ?? []).map((s) => (
          <button key={s.secteur} data-o7-secteur={s.secteur} onClick={() => setSecteur(s.secteur)}
            className="flex items-center gap-2 rounded-lg border border-line-2 bg-surface-3 px-3 py-2 text-left transition-colors duration-quick hover:border-mint/50">
            <span className="font-mono text-[11px] text-txt-hi">{s.secteur.slice(8)}</span>
            <span className="min-w-0 flex-1 truncate text-[10.5px] text-txt-mut">{s.commune}</span>
            <span className="tnum text-[11px] text-mint">{s.opportunites} opp.</span>
            {s.brulantes > 0 && <span className="tnum text-[10px] text-st-ecartee">{s.brulantes} brûl.</span>}
          </button>
        ))}
      </div>
    </>
  )
}

/* ───────────── O9 — PIPELINE RARETÉ (S49) ───────────── */

type Rarete = { communes: { insee: string; commune: string; rythme_conso_ha_an: number | null
  budget_zan_ha: number | null; reste_zan_ha: number | null; horizon_epuisement_ans: number | null
  statut: string; stock_opportunites_ha: number | null; source: string }[] }

export function O9Rarete() {
  const q = useQuery({ queryKey: ['o9'], queryFn: () => jfetch<Rarete>('/pipeline-rarete') })
  const rows = q.data?.communes ?? []
  return (
    <>
      <Banner>La <b>rareté</b> comme argument : au rythme de consommation observé
        (<b>Sourcé</b> Cerema), combien d'années de budget ZAN reste-t-il ? Horizon court =
        foncier qui s'apprécie. <b>Estimé</b> : budget −50 % loi Climat, enveloppes Schéma d'Aménagement Régional (SAR)/SCOT
        non publiées (caveat loi TRACE).</Banner>
      {q.isLoading && <Loading accent="mint" label="Calcul des horizons…" />}
      {q.isError && <ErrorState className="py-6" message="Pipeline rareté indisponible." retry={() => q.refetch()} />}
      <div className="flex min-h-0 flex-1 flex-col overflow-y-auto">
        <p className="label-caps sticky top-0 bg-surface-1 py-1 text-[9.5px]">Horizon d'épuisement du budget ZAN (estimé)</p>
        {rows.map((c) => {
          const depasse = c.statut === 'budget dépassé'
          const pct = depasse ? 100 : c.budget_zan_ha && c.reste_zan_ha != null
            ? Math.max(4, Math.min(100, (c.reste_zan_ha / c.budget_zan_ha) * 100)) : 0
          // classes LITTÉRALES (le JIT Tailwind ne voit pas les interpolations)
          const TONES = {
            ecartee: { bar: 'bg-st-ecartee', txt: 'text-st-ecartee' },
            creuser: { bar: 'bg-st-creuser', txt: 'text-st-creuser' },
            mint: { bar: 'bg-mint', txt: 'text-mint' },
          } as const
          const tone = TONES[depasse ? 'ecartee' : (c.horizon_epuisement_ans ?? 99) < 5 ? 'creuser' : 'mint']
          return (
            <div key={c.insee} data-o9-commune={c.insee} className="flex items-center gap-2 overflow-hidden border-b border-line py-1.5 text-[11px]">
              <span className="min-w-0 flex-1 truncate text-txt">{c.commune}</span>
              <span className="relative h-2 w-12 shrink-0 overflow-hidden rounded-full bg-surface-3">
                <span className={`absolute inset-y-0 left-0 rounded-full ${tone.bar}`} style={{ width: `${pct}%` }} />
              </span>
              <span className={`tnum w-14 shrink-0 text-right font-mono ${tone.txt}`}>
                {depasse ? 'dépassé' : c.horizon_epuisement_ans != null ? `${Math.round(c.horizon_epuisement_ans)} ans` : '—'}</span>
              <span className="tnum hidden w-[62px] shrink-0 text-right font-mono text-txt-dim sm:block">
                {c.stock_opportunites_ha != null ? `${c.stock_opportunites_ha} ha opp.` : '—'}</span>
            </div>
          )
        })}
      </div>
      {rows[0] && <p className="shrink-0 text-[9px] leading-snug text-txt-dim">Source : {rows[0].source}.</p>}
    </>
  )
}

/* ───────────── O10 — BASCULES DATÉES (S50) ───────────── */

type Bascules = { unread: number; items: { id: number; date: string; kind: string; idu: string | null
  titre: string; detail: string | null; demo?: boolean }[] }
const O10_FILTRES = [['', 'tout'], ['bascule', 'bascules'], ['match', 'matches'], ['bodacc', 'BODACC']] as const

// DORMANT — outil « Quoi de neuf » retiré du produit le 21/08/2026 (plus câblé au menu : registry +
// ModulePanel COMPONENTS). Composant conservé au dépôt (exporté pour rester compilable) ; son unique
// source, l'endpoint /events, reste VIVANT (consommé par la cloche de notifications + « le point du
// jour »). Concept-route Copilote (« quoi de neuf » / « bascules du mois ») retirée (answering.py).
export function O10Bascules() {
  const { select, setView } = useApp()
  const [kind, setKind] = useState('')
  const q = useQuery({ queryKey: ['o10'], queryFn: () => jfetch<Bascules>('/events?limit=100') })
  const items = (q.data?.items ?? []).filter((e) => !kind || e.kind.includes(kind))
  return (
    <>
      <Banner>Les <b>bascules datées</b> du run — une parcelle qui passe en Priorité, un match de
        profil, un événement BODACC : chaque changement d'état avec sa date. Le « quoi de
        neuf » du lundi matin, en lecture (marquer lu reste dans la cloche).</Banner>
      <div className="flex flex-wrap gap-1.5">
        {O10_FILTRES.map(([v, l]) => (
          <button key={v} data-o10-filtre={v} onClick={() => setKind(v)}
            className={`min-h-7 rounded-full border px-2.5 py-1 text-[11px] transition-colors duration-quick ${
              kind === v ? 'border-mint text-mint' : 'border-line-2 text-txt-mut hover:text-txt'}`}>{l}</button>
        ))}
      </div>
      {q.isLoading && <Loading accent="mint" label="Lecture des événements…" />}
      {q.isError && <ErrorState className="py-6" message="Événements indisponibles." retry={() => q.refetch()} />}
      <div className="flex min-h-0 flex-1 flex-col gap-1 overflow-y-auto">
        {items.map((e) => (
          <button key={e.id} data-o10-item onClick={() => { if (e.idu) { setView('cartes'); select(e.idu) } }}
            className="flex items-center gap-2 rounded-lg border border-line-2 bg-surface-3 px-2.5 py-1.5 text-left transition-colors duration-quick hover:border-mint/50">
            <span className="shrink-0 font-mono text-[10px] text-txt-dim">{e.date}</span>
            <span className={`shrink-0 rounded-full px-1.5 text-[8.5px] font-medium ${
              e.kind === 'match' ? 'bg-mint/15 text-mint' : 'bg-st-creuser/10 text-st-creuser'}`}>{e.kind}</span>
            {e.idu && <span className="shrink-0 font-mono text-[10.5px] text-txt-hi">{e.idu.slice(8)}</span>}
            <span className="min-w-0 flex-1 truncate text-[11px] text-txt">{e.titre.replace(/^🎯 /, '')}</span>
            {e.demo && <span className="shrink-0 rounded-full bg-mint/15 px-1.5 text-[8px] text-mint">DÉMO</span>}
          </button>
        ))}
        {!q.isLoading && items.length === 0 && (
          // M15 A2 : honnêteté — une bascule est un CHANGEMENT entre deux runs de scoring. Avec un
          // seul run servi, le flux est vide tant qu'un nouveau run n'a pas été comparé au précédent
          // (ou que la démo n'a pas été semée). Ce n'est pas un bug : l'outil lit le même journal
          // d'événements que la cloche de notifications.
          <p className="rounded-lg bg-surface-2/60 px-3 py-2 text-[11px] leading-relaxed text-txt-mut">
            Aucune bascule sur ce filtre. Une bascule apparaît quand une <b>mise à jour des données</b>
            change l'état d'une parcelle par rapport à la précédente (ou via un événement BODACC daté).
            Le flux se remplira à la prochaine mise à jour — ce sont les mêmes alertes que la cloche.
          </p>
        )}
      </div>
    </>
  )
}
