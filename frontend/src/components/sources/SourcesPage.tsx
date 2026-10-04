import { useQuery } from '@tanstack/react-query'
import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { getSources, getSourcesCouverture } from '../../lib/api'
import type { SourceInfo } from '../../lib/types'
import { useApp } from '../../store/useApp'
import { Squelette } from '../Loading'
import { EmptyState, ErrorState } from '../States'
import { Badge as UiBadge, type BadgeTon } from '../ui/Badge'

// PAGE-SOURCES-1 (lot 2) — la LICENCE (« licence ouverte »…) est retirée de la vitrine cliente : le
// client voit la source et son producteur, pas la mention de licence (elle reste en base, lue ailleurs).

// PAGES-RANGEMENT-1 (lot 1) — L'EXPLOITATION SORT DE L'APP CLIENTE. Le client voit QUELLES sources
// alimentent LABUSE et leur MILLÉSIME, rien d'autre. Tout ce qui relève de l'exploitation — fraîcheur,
// états (« à jour » / « mise à jour en cours »), compteur « X à jour », fiabilité (reliability_level) —
// est retiré ici : ce détail vit au dashboard admin (Données / le Circuit). Les pastilles de couches
// par source (COUCHES-REGISTRE-2 lot 3) ont elles aussi migré vers la fiche du réservoir (Données).

// ── Badge — DA-034 : délègue au Badge partagé (3 tons). `auto` = producteur interrogeable (→ vert),
// `late` = en retard sur sa cadence (→ ambre), `error` = échec d'ingestion VISIBLE (→ ambre), `dashed`
// = proxy / curée manuellement — donnée approchée (→ neutre).
const BADGE_TON: Record<'auto' | 'late' | 'dashed' | 'error', BadgeTon> = {
  auto: 'vert', late: 'ambre', error: 'ambre', dashed: 'neutre',
}
function Badge({ kind, children, title }: { kind: 'auto' | 'late' | 'dashed' | 'error'; children: ReactNode; title?: string }) {
  return <UiBadge aria-label={title} ton={BADGE_TON[kind]}>{children}</UiBadge>
}

function Row({ s, focused }: { s: SourceInfo; focused: boolean }) {
  const ref = useRef<HTMLElement | null>(null)
  useEffect(() => { if (focused) ref.current?.scrollIntoView({ block: 'center' }) }, [focused])
  const setRef = (el: HTMLElement | null) => { ref.current = el }

  // PAGE-SOURCES-1 (lot 2) — la ligne est ALIGNÉE À GAUCHE (plus de colonne-espaceur fantôme qui la
  // décalait) et TOUTE la ligne est CLIQUABLE vers la page du producteur (plus seulement la flèche).
  // Retiré : la licence (« licence ouverte »…) et le millésime (« Publié le … »). Restent le nom, le
  // producteur, la cadence habituelle du producteur et la couverture réelle.
  const contenu = (
    <>
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
          <span className="flex flex-wrap items-center gap-2 text-[13.5px] text-txt">
            {s.name}
            {/* nature (« proxy — donnée approchée ») : honnêteté sur la donnée, pas un état d'exploitation. */}
            {s.nature?.dashed && (
              <Badge kind="dashed" title={s.nature.detail}><span data-source-nature>{s.nature.label}</span></Badge>
            )}
            {/* RETOUCHES-1 D.16 — servie en direct d'un producteur externe (overlay WMTS), sans réservoir
                ni sonde amont : « En direct », jamais « à jour »/vide (le flux EST le producteur). */}
            {s.statut === 'live' && (
              <Badge kind="auto" title="Servie en direct depuis le producteur externe (overlay), sans réservoir en base."><span data-source-live>En direct</span></Badge>
            )}
          </span>
          {s.provider && <span data-source-provider className="shrink-0 text-[12px] text-txt-dim">{s.provider}</span>}
        </div>
        {/* cadence habituelle du producteur (à titre d'information ; jamais un jugement, jamais « retard »). */}
        {s.cadence_mention && (
          <p data-source-publication className="mt-1 text-[12px] leading-snug text-txt-dim">
            Le producteur publie habituellement {s.cadence_mention}.
          </p>
        )}
        {/* REPARATIONS-1 lot 3 — la COUVERTURE RÉELLE : où la source arrive et où elle s'arrête. */}
        {s.couverture_note && (
          <p data-source-couverture className="mt-1 text-[12px] leading-snug text-txt-dim">{s.couverture_note}</p>
        )}
      </div>
      {s.documentation_url && (
        <span aria-hidden className="ml-3 shrink-0 self-center text-[13px] text-txt-dim group-hover:text-mint">↗</span>
      )}
    </>
  )

  // RECETTE-1 R31 — survol vert opaque (hover-fill). PAGE-SOURCES-1 : toute la ligne = un lien.
  const cls = `group flex items-start justify-between gap-3 border-b border-line px-4 py-3 text-left last:border-b-0 hover-fill ${focused ? 'bg-mint/[0.06]' : ''}`
  return s.documentation_url
    ? <a ref={setRef} data-source-row href={s.documentation_url} target="_blank" rel="noreferrer"
        className={cls}>{contenu}</a>
    : <div ref={setRef} data-source-row className={cls}>{contenu}</div>
}

export function SourcesPage() {
  // FINITIONS-1 (P5) — le temps de chargement vient de l'endpoint /sources, qui recalcule côté serveur
  // la fraîcheur/radar LIVE de chaque source (1–5 s) ; cette page ne l'affiche plus (seule l'année DVF,
  // via derniere_donnee, en est lue) mais on ne peut pas retirer ce calcul sans risque (derniere_donnee
  // en dépend, endpoint partagé). Correctif sans risque : on CACHE le résultat (staleTime) → la page se
  // recharge instantanément aux visites suivantes au lieu de re-tourner le calcul à chaque ouverture.
  const { data, isLoading, isError, refetch } = useQuery({ queryKey: ['sources'], queryFn: getSources, staleTime: 5 * 60_000 })
  // RETOURS-9 (Q11.5) — les chiffres de couverture qui parlent au client, lus des données réelles.
  const couverture = useQuery({ queryKey: ['sources-couverture'], queryFn: getSourcesCouverture, staleTime: 5 * 60_000 }).data
  const sourcesFocus = useApp((s) => s.sourcesFocus)
  const [q, setQ] = useState('')
  // RETOURS-9 (Q11.1) — plus de chips de tri : « Toutes » ou un thème (accordéon replié « Filtrer par thème »).
  const [theme, setTheme] = useState<string | null>(null)
  const [themeOuvert, setThemeOuvert] = useState(false)

  // PAGE-SOURCES-1 (lot 2) — le bloc « détail technique » (modèle de scoring, hash, recalage d'intercept,
  // avertissement de recalibration) est RETIRÉ de la page cliente ; l'appel /v2/modele l'est aussi.

  // Les sources servies (hors doublons). L'API ne sert déjà que connecte-hors-masquées ; filtre défensif.
  const comptees = useMemo(() => (data ?? []).filter((s) => !s.doublon), [data])
  const nTotal = comptees.length
  // RETOURS-9 (Q11.1) — les THÈMES existants (catégorie du catalogue), pour l'accordéon « Filtrer par thème ».
  const themes = useMemo(() => {
    const set = new Map<string, number>()
    for (const s of comptees) { const k = s.category || 'Autres'; set.set(k, (set.get(k) ?? 0) + 1) }
    return [...set.entries()].sort((a, b) => a[0].localeCompare(b[0], 'fr'))
  }, [comptees])

  // Recherche (nom / producteur / catégorie) + thème actif. Groupé par catégorie.
  const cats = useMemo(() => {
    const ql = q.trim().toLowerCase()
    const passeTheme = (s: SourceInfo) => theme == null || (s.category || 'Autres') === theme
    const passeSearch = (s: SourceInfo) =>
      !ql || [s.name, s.provider, s.category].some((v) => (v ?? '').toLowerCase().includes(ql))
    const m = new Map<string, SourceInfo[]>()
    for (const s of comptees) {
      if (!passeTheme(s) || !passeSearch(s)) continue
      const k = s.category || 'Autres'
      m.set(k, [...(m.get(k) ?? []), s])
    }
    return [...m.entries()]
  }, [comptees, q, theme])

  const nVisibles = cats.reduce((acc, [, l]) => acc + l.length, 0)

  return (
    <div data-sources-page className="sources-print flex min-w-0 flex-1 flex-col overflow-y-auto">
      <div className="mx-auto w-full max-w-[1060px] px-7 py-10">
        {/* en-tête — PAGE-SOURCES-1 (lot 2) : le sur-titre « Données et méthode » est retiré. */}
        <h1 className="mb-2 text-[26px] font-semibold tracking-[-.02em] text-txt-hi">Sources</h1>
        {/* PAGE-SOURCES-1 (lot 2) — phrase sur la VÉRIFICATION des sources. Formulation vérifiée sur la
            couverture RÉELLE de la sentinelle : 78 des 94 sources sont sondées chaque jour (cadence 24 h) ;
            16 ne le sont pas (source manuelle sans amont public, ou hors de portée de la sonde). On écrit
            donc « la plupart », jamais « toutes » (l'affirmation quotidienne globale serait fausse). */}
        <p data-sources-positionnement className="mb-7 text-[13px] leading-relaxed text-txt-mut">
          La plupart de nos sources sont vérifiées automatiquement chaque jour : une sentinelle repère
          quand leur producteur publie une nouvelle version.
        </p>

        {/* PAGES-RANGEMENT-1 (lot 1) — l'encart ne porte plus que des chiffres CLIENTS : le nombre de
            sources et la couverture réelle (parcelles · communes), LUS des données. La tuile « à jour »
            (compteur d'exploitation) est retirée — la fraîcheur vit au dashboard admin. */}
        {data && (
          <div data-sources-bandeau className="mb-3.5 overflow-hidden rounded-[10px] border border-line bg-surface-2">
            <div className="flex flex-wrap">
              {([
                { v: String(nTotal), l: 'sources', mint: false },
                // PAGES-RANGEMENT-1 (lot 1) — la tuile « à jour » (compteur d'exploitation) est retirée.
                { v: couverture?.parcelles != null ? couverture.parcelles.toLocaleString('fr-FR') : '—', l: 'parcelles couvertes', mint: false },
                { v: couverture?.communes != null ? `${couverture.communes}/${couverture.communes_total}` : '—', l: 'communes', mint: false },
                // RETOURS-10 (T7) — la tuile « dernière analyse » est retirée : la date de l'analyse
                // vit déjà sur les fiches et dans Projets. Les quatre tuiles restantes se répartissent la ligne.
              ] as const).map((t, i) => (
                <div key={i} className="min-w-[130px] flex-1 border-r border-line px-[18px] py-3.5 last:border-r-0">
                  <b className={`block font-semibold leading-tight text-[26px] ${t.mint ? 'text-mint' : 'text-txt-hi'}`}>{t.v}</b>
                  <span className="font-mono text-[10px] uppercase tracking-[.13em] text-txt-dim">{t.l}</span>
                </div>
              ))}
            </div>
          </div>
        )}
        {/* RETOURS-14 P6 — RÉCONCILIATION des deux comptes de parcelles. « parcelles couvertes » = total
            ingéré (431 663) ; le bouton « Voir les N parcelles » du panneau Filtre affiche 430 813 =
            parcelles explorables (le filtre masque les micro-parcelles « sliver » < 2 m²). L'écart est
            légitime et volontaire : on l'ÉCRIT ici, là où le grand nombre apparaît, plutôt que de laisser
            deux totaux muets se contredire. */}
        {couverture?.parcelles != null && couverture?.parcelles_filtrables != null
          && couverture.parcelles !== couverture.parcelles_filtrables && (
          <p data-sources-parcelles-note className="mb-3.5 -mt-1.5 text-[11.5px] leading-snug text-txt-dim">
            {couverture.parcelles.toLocaleString('fr-FR')} parcelles couvertes, dont{' '}
            <b className="text-txt-mut">{couverture.parcelles_filtrables.toLocaleString('fr-FR')}</b> d’au moins 2 m²
            explorables au filtre — les {(couverture.parcelles - couverture.parcelles_filtrables).toLocaleString('fr-FR')} micro-parcelles
            (moins de 2 m²) sont écartées de l’exploration.
          </p>
        )}

        {/* RECETTE-1 (D7, Vic 04/10) — toute la section « Réserve » (retard de publication DVF) est
            RETIRÉE de la page Sources côté client. Les données ne bougent pas, seul l'affichage. */}

        {/* RETOURS-9 (Q11.1) — barre d'outils : recherche + « Toutes » + accordéon replié « Filtrer par thème »
            (les thèmes existent déjà dans le catalogue : Énergie, Urbanisme, Risques, Marché, Cadastre…). */}
        <div className="sticky top-0 z-[5] mb-5 flex flex-wrap items-center gap-2.5 border-b border-line bg-bg py-3">
          <input data-sources-search value={q} onChange={(e) => setQ(e.target.value)}
            placeholder="Chercher une source, un producteur…"
            className="min-w-[200px] flex-[1_1_240px] rounded-lg border border-line bg-surface-2 px-3 py-2 text-[13px] text-txt placeholder:text-txt-dim focus:border-line-2 focus:outline-none" />
          {/* RECETTE-1 R37 — arrondi aligné sur la DA (rounded-lg, comme la barre de recherche et les
              cartes), au lieu du rounded-full qu'on ne retrouvait nulle part ailleurs. */}
          <button data-sources-chip="toutes" aria-pressed={theme == null} onClick={() => { setTheme(null); setThemeOuvert(false) }}
            className={`rounded-lg border px-3 py-1.5 text-[12.5px] transition-colors duration-quick ${
              theme == null ? 'border-mint bg-mint text-mint-ink' : 'border-line text-txt-mut hover:border-line-2 hover:text-txt'}`}>
            Toutes <span className="ml-1.5 font-mono text-[11px] opacity-70">{nTotal}</span>
          </button>
          <div className="relative">
            {/* RECETTE-2 (S25) — liseré VERT autour du bouton (border-mint) + animation VERTE au survol
                (hover-fill) + flèche vers le BAS quand la liste est ouverte (▾), vers la droite fermée (▸). */}
            <button data-sources-theme-toggle aria-expanded={themeOuvert} onClick={() => setThemeOuvert((o) => !o)}
              className={`rounded-lg border px-3 py-1.5 text-[12.5px] ${
                theme != null ? 'border-mint bg-mint text-mint-ink' : 'border-mint/60 text-txt hover-fill'}`}>
              {theme != null ? `Thème : ${theme}` : 'Filtrer par thème'} {themeOuvert ? '▾' : '▸'}
            </button>
            {themeOuvert && (
              <div data-sources-themes className="absolute left-0 top-10 z-10 max-h-[60vh] w-64 overflow-y-auto rounded-lg border border-line bg-surface-1 p-1.5 shadow-lg">
                {themes.map(([t, n]) => (
                  <button key={t} data-sources-theme={t} onClick={() => { setTheme(t); setThemeOuvert(false) }}
                    className={`flex w-full items-center justify-between rounded px-2.5 py-1.5 text-left text-[12.5px] hover:bg-surface-3 ${theme === t ? 'text-mint' : 'text-txt-mut'}`}>
                    <span>{t}</span><span className="font-mono text-[11px] text-txt-dim">{n}</span>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        {isLoading && <div className="mt-6"><Squelette lignes={5} /></div>}
        {isError && <ErrorState className="mt-6" message="Sources inaccessibles — vérifiez votre réseau ou réessayez." retry={() => refetch()} />}
        {data && nVisibles === 0 && (
          <EmptyState className="mt-8" title="Aucune source ne correspond"
            hint={(q || theme != null) ? <>{q ? <>à « {q} »</> : null}{theme != null ? <> au thème « {theme} »</> : null}.</> : undefined} />
        )}

        {/* groupes par catégorie */}
        {cats.map(([cat, list]) => (
          <div key={cat} className="mt-7">
            <div className="mb-0.5 flex items-baseline gap-2.5 pb-2">
              <h2 className="m-0 font-mono text-[10.5px] font-normal uppercase tracking-[.16em] text-txt-dim">{cat}</h2>
              <span className="font-mono text-[10.5px] text-txt-dim opacity-60">{list.length}</span>
            </div>
            <div className="overflow-hidden rounded-[10px] border border-line bg-surface-1">
              {list.map((s) => <Row key={s.id} s={s} focused={s.name === sourcesFocus} />)}
            </div>
          </div>
        ))}

        {/* FINITIONS-1 (P6) — l'encart de bas de page « proxy — donnée approchée, jamais servie comme
            source » est RETIRÉ. */}

      </div>
    </div>
  )
}
