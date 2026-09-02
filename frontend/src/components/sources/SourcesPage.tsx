import { useQuery } from '@tanstack/react-query'
import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { getSources, getSourcesCouverture } from '../../lib/api'
import { CLIENT } from '../../lib/strings'
import { TOKENS } from '../../lib/tokens'
import type { SourceInfo } from '../../lib/types'
import { useApp } from '../../store/useApp'
import { Loading } from '../Loading'

// M86 (correction factuelle) — le millésime amont est LU depuis l'API (`data_sources.source_millesime`,
// magasin centralisé) : plus AUCUNE date en dur au front. Repli sur l'année présente dans le nom (dérivé,
// pas inventé). L'ancienne carte `MILLESIME_VERIFIE` (7 dates codées) a été supprimée.
function millesimeNote(s: SourceInfo): string | null {
  if (s.source_millesime) return s.source_millesime
  const y = s.name.match(/\b(19|20)\d{2}\b/)
  return y ? `millésime ${y[0]}` : null
}

// ── FIX-SOURCES S6 (corrige M6 Phase 2a) : la licence est DÉRIVÉE de legal_notes CÔTÉ SERVEUR
// (`app._source_licence`) et servie dans `license_label` / `license_url`. Le front ne code PLUS aucune
// licence ni aucune carte par nom : corriger la mention en base suffit, la vitrine suit. Défaut sûr
// si un vieux cache n'a pas encore le champ : « Licence à confirmer » (jamais un libellé inventé).
function licence(s: SourceInfo): string { return s.license_label || 'Licence à confirmer' }

/** Date de mise à jour AFFICHÉE : la plus récente entre last_sync_at et la dernière ingestion tracée. */
function majReelle(s: SourceInfo): string | null {
  const a = s.last_sync_at, b = s.derniere_ingestion
  if (a && b) return b > a ? b : a
  return b ?? a
}

// RETOURS-9 (Q11.3) — les prédicats de MÉTHODE DE VEILLE (sondable/suiviManuel) ne servent plus côté
// client : la « dernière colonne » (collecte manuelle/automatique) disparaît. Le client lit source ·
// producteur · publié le · à jour. Ces distinctions restent dans Données (admin).
// RETOURS-8 (R2) — le client ne voit que DEUX états, et le mot « retard » n'apparaît JAMAIS. L'arbitre
// unique du serveur (etats_sources → `etat_client`) tranche : « pas à jour » = une version plus récente
// existe chez le producteur et n'est pas encore intégrée (« mise à jour en cours », jamais rouge) ; tout
// le reste = « à jour ». Les anciens prédicats fraîcheur (en_retard / en_panne / en_erreur / amont en
// avance) NE SONT PLUS surfacés côté client : leur détail vit au dashboard admin (R1).
const pasAJour = (s: SourceInfo) => s.etat_client === 'pas_a_jour'
const aJour = (s: SourceInfo) => !pasAJour(s)
/** FIX-SOURCES S7 — la version DISTINGUE les deux dates, comme les « i » des couches (Legend.fmtFraich :
 *  « millésime X (ingéré le Y) ») : `label` = la fraîcheur AMONT (jusqu'au / millésime), `ingere` = la
 *  date d'INGESTION en mention secondaire « ingéré le … ». Jamais fondues, jamais une date inventée.
 *  Quand seule l'ingestion existe (pas d'amont), elle EST la primaire — pas de « ingéré le » redondant. */
function versionMeta(s: SourceInfo): { label: string; untracked: boolean; ingere: string | null } {
  const ing = majReelle(s)
  const ingLabel = ing ? `ingéré le ${new Date(ing).toLocaleDateString('fr-FR')}` : null
  if (s.derniere_donnee) return { label: `jusqu'au ${new Date(s.derniere_donnee).toLocaleDateString('fr-FR')}`, untracked: false, ingere: ingLabel }
  const mil = millesimeNote(s)
  if (mil) return { label: mil, untracked: false, ingere: ingLabel }
  if (ing) return { label: `donnée du ${new Date(ing).toLocaleDateString('fr-FR')}`, untracked: false, ingere: null }
  return { label: 'millésime non tracé', untracked: true, ingere: null }
}

// FIX-SOURCES S4 — la FIABILITÉ (data_sources.reliability_level) était STOCKÉE mais jamais rendue
// (champ mort). On la montre quand elle appelle une réserve honnête (« à confirmer » / convention /
// légal) ; « vérifié » = l'état par défaut d'une source servie, pas un badge (ce serait du bruit).
function fiabiliteBadge(s: SourceInfo): { label: string; title: string } | null {
  switch (s.reliability_level) {
    case 'a_confirmer': return { label: 'fiabilité à confirmer', title: 'Donnée servie, mais sa fiabilité (ou sa licence) reste à confirmer avec le producteur.' }
    case 'sous_convention': return { label: 'accès sous convention', title: 'Accès encadré par une convention avec le producteur.' }
    case 'legal': return { label: 'accès légal restreint', title: 'Réutilisation juridiquement encadrée.' }
    default: return null
  }
}

// ── Badge (classe .badge de la maquette) : mono, majuscule, 3 variantes. `auto` = mint (le producteur
// expose une date interrogeable), `late` = warn (#D9873D, en retard sur sa cadence), `dashed` = pointillé
// (proxy / servi par proxys / curée manuellement — donnée approchée, jamais servie comme source).
// CONNEXIONS-2 Lot 6.2 (KO-14) — variante `error` (rouge) : un échec d'ingestion est VISIBLE.
function Badge({ kind, children, title }: { kind: 'auto' | 'late' | 'dashed' | 'error'; children: ReactNode; title?: string }) {
  const base = 'shrink-0 rounded-[3px] px-1.5 py-px font-mono text-[9.5px] uppercase tracking-[.09em]'
  if (kind === 'auto') return <span title={title} className={`${base} border border-mint/40 bg-mint/10 text-mint`}>{children}</span>
  if (kind === 'late') return <span title={title} className={base} style={{ border: `1px solid ${TOKENS.warn}`, color: TOKENS.warn, background: TOKENS.warnBg }}>{children}</span>
  if (kind === 'error') return <span title={title} className={base} style={{ border: '1px solid #E05252', color: '#E05252', background: 'rgba(224,82,82,.10)' }}>{children}</span>
  return <span title={title} className={`${base} border border-dashed border-line-2 text-txt-dim`}>{children}</span>
}

function Row({ s, focused }: { s: SourceInfo; focused: boolean }) {
  const ref = useRef<HTMLDivElement>(null)
  useEffect(() => { if (focused) ref.current?.scrollIntoView({ block: 'center' }) }, [focused])

  const meta = versionMeta(s)
  const majEnCours = pasAJour(s)
  const lic = licence(s)
  const fiab = fiabiliteBadge(s)
  const prod = [s.provider, lic].filter(Boolean)

  return (
    <div ref={ref} data-source-row
      className={`grid grid-cols-[14px_1fr_20px] items-center gap-x-3.5 gap-y-1.5 border-b border-line px-4 py-3 last:border-b-0 hover:bg-white/[0.018] md:grid-cols-[14px_1fr_190px_150px_20px] ${focused ? 'bg-mint/[0.06]' : ''}`}>
      {/* RETOURS-8 (R2) — pastille JAMAIS rouge : mint (à jour) ou mint atténué (mise à jour en cours).
          Le client ne doit jamais croire que LABUSE est en retard. */}
      <span className="h-[7px] w-[7px] shrink-0 rounded-full"
        style={majEnCours
          ? { background: TOKENS.mint, opacity: 0.5, boxShadow: '0 0 0 3px rgba(74,222,128,.08)' }
          : { background: TOKENS.mint, boxShadow: '0 0 0 3px rgba(74,222,128,.10)' }}
        title={majEnCours ? 'Mise à jour en cours (une version plus récente arrive)' : 'À jour : la dernière version publiée par le producteur est dans l\'app'} />

      {/* nom + badges d'état */}
      <span className="flex flex-wrap items-center gap-2 text-[13.5px] text-txt">
        {s.name}
        {/* RETOURS-8 (R2) — le seul état « non à jour » possible côté client : « mise à jour en cours »
            (une version plus récente existe chez le producteur). Neutre, jamais rouge, jamais « retard ». */}
        {majEnCours && (
          <Badge kind="auto" title="Une version plus récente existe chez le producteur ; son intégration est en cours.">
            <span data-source-maj>mise à jour en cours</span>
          </Badge>
        )}
        {/* RETOURS-9 (Q11.3) — badges « version vérifiée » / « suivi manuel » (méthode de veille) retirés côté client. */}
        {s.nature?.dashed && (
          <Badge kind="dashed" title={s.nature.detail}><span data-source-nature>{s.nature.label}</span></Badge>
        )}
        {fiab && <Badge kind="dashed" title={fiab.title}><span data-source-fiabilite>{fiab.label}</span></Badge>}
      </span>

      {/* lien source officielle — col 3 sur mobile (1re ligne), col 5 en large */}
      {s.documentation_url
        ? <a className="col-[3/4] row-start-1 text-right text-[13px] text-txt-dim hover:text-mint md:col-[5/6] md:row-auto" href={s.documentation_url} target="_blank" rel="noreferrer" title="Source officielle">↗</a>
        : <span className="col-[3/4] row-start-1 md:col-[5/6] md:row-auto" />}

      {/* producteur · licence (lien vers le texte de licence — audit §1.11) */}
      <span className="col-[2/-1] min-w-0 truncate text-[12px] text-txt-dim md:col-[3/4]">
        {s.provider}{s.provider && prod.length > 1 ? ' · ' : ''}
        {s.license_url
          ? <a data-source-licence href={s.license_url} target="_blank" rel="noreferrer" className="hover:text-mint hover:underline" title="Texte de la licence">{lic}</a>
          : <span data-source-licence>{lic}</span>}
      </span>

      {/* FIX-SOURCES S7 — deux dates DISTINCTES (comme les « i » des couches) : la fraîcheur AMONT en
          service (mono), puis « ingéré le … » en mention secondaire — plus jamais fondues en une seule. */}
      <span data-source-version
        className={`col-[2/-1] min-w-0 truncate font-mono text-[11.5px] md:col-[4/5] md:whitespace-nowrap ${meta.untracked ? 'text-txt-dim' : 'text-txt-mut'}`}>
        {meta.label}
        {meta.ingere && <span data-source-ingere className="ml-1 text-txt-dim">· {meta.ingere}</span>}
      </span>

      {/* RETOURS-8 (R2) — chaque ligne dit la DATE de publication par le producteur et sa cadence
          habituelle, À TITRE D'INFORMATION (jamais un jugement, jamais « retard »). */}
      {(s.publie_le || s.cadence_mention) && (
        <p data-source-publication className="col-[2/-1] text-[12px] leading-snug text-txt-dim">
          {s.publie_le && <>Publié le {s.publie_le}.</>}
          {s.publie_le && s.cadence_mention ? ' ' : ''}
          {s.cadence_mention && <>Le producteur publie habituellement {s.cadence_mention}.</>}
        </p>
      )}
      {s.nature?.detail && (
        <p data-source-nature-detail className="col-[2/-1] text-[12px] leading-snug text-txt-dim">{s.nature.detail}</p>
      )}
    </div>
  )
}

export function SourcesPage() {
  const { data, isLoading, isError } = useQuery({ queryKey: ['sources'], queryFn: getSources })
  // RETOURS-9 (Q11.5) — les chiffres de couverture qui parlent au client, lus des données réelles.
  const couverture = useQuery({ queryKey: ['sources-couverture'], queryFn: getSourcesCouverture, staleTime: 5 * 60_000 }).data
  const sourcesFocus = useApp((s) => s.sourcesFocus)
  const [q, setQ] = useState('')
  // RETOURS-9 (Q11.1) — plus de chips de tri : « Toutes » ou un thème (accordéon replié « Filtrer par thème »).
  const [theme, setTheme] = useState<string | null>(null)
  const [themeOuvert, setThemeOuvert] = useState(false)

  // M5 : version du modèle P v2 (sha + avertissement censure) — RÉSERVE DE MÉTHODE conservée (repliée
  // en bas), jamais supprimée : la maquette ne la montre pas mais la doctrine interdit d'effacer une réserve.
  const modele = useQuery({
    queryKey: ['v2-modele'],
    queryFn: async () => {
      const r = await fetch('/v2/modele')
      if (!r.ok) throw new Error(`v2 ${r.status}`)
      return r.json() as Promise<{ model_version: string; sha256_court: string;
        avertissement_censure: string; politique_recalibration: string }>
    },
    retry: false, staleTime: 5 * 60_000,
  }).data

  // Les sources servies (hors doublons). L'API ne sert déjà que connecte-hors-masquées ; filtre défensif.
  const comptees = useMemo(() => (data ?? []).filter((s) => !s.doublon), [data])
  const nTotal = comptees.length
  const nAJour = comptees.filter(aJour).length
  // FIX-SOURCES S3 — la réserve DVF ne code plus « 2025–2026 » en dur : la borne RÉCENTE est LUE dans
  // la base (dernière donnée servie de la source DVF). Sans donnée → phrase sans chiffre.
  const dvfMaxAnnee = useMemo(() => {
    const d = (data ?? []).find((s) => s.name === 'DVF / valeurs foncières')?.derniere_donnee
    const y = d ? new Date(d).getFullYear() : NaN
    return Number.isFinite(y) ? y : null
  }, [data])
  // RETOURS-9 (Q11.1) — les THÈMES existants (catégorie du catalogue), pour l'accordéon « Filtrer par thème ».
  const themes = useMemo(() => {
    const set = new Map<string, number>()
    for (const s of comptees) { const k = s.category || 'Autres'; set.set(k, (set.get(k) ?? 0) + 1) }
    return [...set.entries()].sort((a, b) => a[0].localeCompare(b[0], 'fr'))
  }, [comptees])

  // Recherche (nom / producteur / licence / catégorie) + thème actif. Groupé par catégorie.
  const cats = useMemo(() => {
    const ql = q.trim().toLowerCase()
    const passeTheme = (s: SourceInfo) => theme == null || (s.category || 'Autres') === theme
    const passeSearch = (s: SourceInfo) =>
      !ql || [s.name, s.provider, s.category, licence(s)].some((v) => (v ?? '').toLowerCase().includes(ql))
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
        {/* en-tête */}
        <p className="mb-3.5 font-mono text-[10.5px] uppercase tracking-[.16em] text-txt-dim">Données et méthode</p>
        <h1 className="mb-2 text-[26px] font-semibold tracking-[-.02em] text-txt-hi">Sources &amp; fraîcheur</h1>
        {/* RETOURS-9 (Q11.4) — intro en PLEINE LARGEUR (plus de marge interne étroite), raccourcie. */}
        <p data-sources-positionnement className="mb-7 text-[13px] leading-relaxed text-txt-mut">
          Chaque chiffre LABUSE est traçable jusqu'à sa source publique : d'où il vient, quand son
          producteur l'a publié, et s'il est à jour dans l'app.
        </p>

        {/* M105 P1 — l'encart HIÉRARCHISÉ : en grand l'essentiel (sources · à jour), en petit la
            méthode (vérifiées auto · sans date exposée PAR LE PRODUCTEUR — ce n'est pas LABUSE qui
            ne trace pas). Le compteur « en retard » a QUITTÉ l'encart : l'information vit sur la
            ligne de chaque source concernée (badge + formulation, jamais masquée). Tous les
            compteurs restent CALCULÉS (nAJour dérivé), aucun chiffre en dur. */}
        {/* RETOURS-9 (Q11.5) — cinq tuiles au plus, une ligne : les deux chiffres cœur (sources · à jour)
            gagnent des voisins qui parlent au client, LUS des données réelles (couverture). Q11.2 : la
            ligne d'exploitation (« vérifiées automatiquement · radar amont… ») est retirée. */}
        {data && (
          <div data-sources-bandeau className="mb-3.5 overflow-hidden rounded-[10px] border border-line bg-surface-2">
            <div className="flex flex-wrap">
              {([
                { v: String(nTotal), l: 'sources', mint: false },
                { v: String(nAJour), l: 'à jour', mint: true },
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

        {/* les DEUX réserves de méthode — conservées, repliées (jamais supprimées) */}
        <details data-sources-reserves className="mb-8 rounded-[10px] border border-line bg-surface-2">
          <summary className="flex cursor-pointer list-none items-center gap-2.5 px-[18px] py-3.5 text-[13px] text-txt-mut [&::-webkit-details-marker]:hidden">
            <span className="rounded-[3px] border px-1.5 py-0.5 font-mono text-[10px] uppercase tracking-[.12em]"
              style={{ borderColor: TOKENS.warn, color: TOKENS.warn }}>Réserves</span>
            Deux limites à connaître avant de lire les scores
          </summary>
          <div className="border-t border-line px-[18px] pb-[18px] pt-4">
            <p className="mb-3 max-w-[78ch] text-[13px] leading-relaxed text-txt-mut">
              <strong className="font-semibold text-txt">Retard de publication des ventes.</strong> Les ventes
              mettent 1 à 3 ans à apparaître dans DVF.{' '}
              {dvfMaxAnnee
                ? <>Les niveaux de prix les plus récents (jusqu’à {dvfMaxAnnee}) sont provisoires</>
                : <>Les niveaux de prix les plus récents sont provisoires</>} ; le
              classement relatif entre parcelles, lui, reste fiable.
            </p>
            <p className="max-w-[78ch] text-[13px] leading-relaxed text-txt-mut">
              <strong className="font-semibold text-txt">Segment « Densifier l’existant ».</strong> Il identifie un
              potentiel physique et réglementaire sur des parcelles déjà bâties. Il ne prédit pas une mise en
              vente et ne constitue pas une opportunité qualifiée.
            </p>
          </div>
        </details>

        {/* RETOURS-9 (Q11.1) — barre d'outils : recherche + « Toutes » + accordéon replié « Filtrer par thème »
            (les thèmes existent déjà dans le catalogue : Énergie, Urbanisme, Risques, Marché, Cadastre…). */}
        <div className="sticky top-0 z-[5] mb-5 flex flex-wrap items-center gap-2.5 border-b border-line bg-bg py-3">
          <input data-sources-search value={q} onChange={(e) => setQ(e.target.value)}
            placeholder="Chercher une source, un producteur…"
            className="min-w-[200px] flex-[1_1_240px] rounded-lg border border-line bg-surface-2 px-3 py-2 text-[13px] text-txt placeholder:text-txt-dim focus:border-line-2 focus:outline-none" />
          <button data-sources-chip="toutes" aria-pressed={theme == null} onClick={() => { setTheme(null); setThemeOuvert(false) }}
            className={`rounded-full border px-3 py-1.5 text-[12.5px] transition-colors duration-quick ${
              theme == null ? 'border-mint bg-mint text-mint-ink' : 'border-line text-txt-mut hover:border-line-2 hover:text-txt'}`}>
            Toutes <span className="ml-1.5 font-mono text-[11px] opacity-70">{nTotal}</span>
          </button>
          <div className="relative">
            <button data-sources-theme-toggle aria-expanded={themeOuvert} onClick={() => setThemeOuvert((o) => !o)}
              className={`rounded-full border px-3 py-1.5 text-[12.5px] transition-colors duration-quick ${
                theme != null ? 'border-mint bg-mint text-mint-ink' : 'border-line text-txt-mut hover:border-line-2 hover:text-txt'}`}>
              {theme != null ? `Thème : ${theme}` : 'Filtrer par thème'} {themeOuvert ? '▴' : '▾'}
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

        {isLoading && <div className="mt-6"><Loading label="Chargement des sources" className="text-xs" /></div>}
        {isError && <p className="mt-6 text-xs text-st-ecartee">Sources inaccessibles — vérifiez votre réseau ou réessayez.</p>}
        {data && nVisibles === 0 && (
          <p className="mt-8 text-[13px] text-txt-dim">Aucune source ne correspond{q ? <> à « {q} »</> : null}{theme != null ? <> au thème « {theme} »</> : null}.</p>
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

        {/* légende — RETOURS-9 (Q11.3) : plus de méthode de veille, le client lit source · producteur · publié le · à jour. */}
        {data && (
          <div className="mt-9 flex flex-wrap gap-x-6 gap-y-2.5 border-t border-line pt-4 text-[12px] text-txt-dim">
            <span className="flex items-center gap-2"><i className="inline-block h-[7px] w-[7px] rounded-full" style={{ background: TOKENS.mint }} /> à jour : la dernière version publiée est dans l'app</span>
            <span className="flex items-center gap-2"><Badge kind="auto">mise à jour en cours</Badge> une version plus récente arrive</span>
            <span className="flex items-center gap-2"><Badge kind="dashed">proxy</Badge> donnée approchée, jamais servie comme source</span>
          </div>
        )}

        {/* RÉSERVE DE MÉTHODE conservée : le modèle de scoring (version + avertissement censure), replié */}
        {modele && (
          <details data-sources-modele className="mt-6 rounded-lg border border-line-2 bg-surface-2 px-4 py-2.5">
            <summary className="cursor-pointer list-none text-[11px] font-medium text-txt-mut hover:text-txt">▸ {CLIENT.modele.detailToggle}</summary>
            <p className="mt-2 text-[11px] leading-snug text-txt">{CLIENT.modele.confiance}</p>
            <p className="mt-2 text-[10.5px] font-medium text-txt">
              Modèle de scoring : <span className="font-mono">{modele.model_version}</span>
              <span className="ml-1.5 font-mono text-[10px] text-txt-dim">sha {modele.sha256_court}</span>
            </p>
            <p className="mt-1 text-[10.5px] leading-snug text-st-creuser">▲ {modele.avertissement_censure}.</p>
            <p className="mt-0.5 text-[10px] leading-snug text-txt-dim">{modele.politique_recalibration}.</p>
          </details>
        )}
      </div>
    </div>
  )
}
