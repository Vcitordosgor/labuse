import { useQuery } from '@tanstack/react-query'
import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { getSources } from '../../lib/api'
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

// M87 P4 — DÉRIVÉS de la donnée servie (jamais recalculés : la fraîcheur vient de fraicheur.py via /sources,
// le radar amont de radar.py). Ces prédicats nourrissent la barre d'état, les filtres ET les badges — un
// seul jeu de règles, pas de chiffre en dur.
const sondable = (s: SourceInfo) => s.radar?.statut === 'a_jour' || s.radar?.statut === 'nouvelle_publication'
// M123 — état HONNÊTE d'une source sans sonde auto fiable : suivie À LA MAIN (cadence dite), ni
// « à jour » automatique ni « cassé ». Distinct de `sondable` (radar auto).
const suiviManuel = (s: SourceInfo) => s.radar?.statut === 'verification_manuelle'
// CRON-2 — le statut vient désormais du job `sources-fraicheur` (calculé sur les 59/64 affichées, même
// prédicat que /sources, persisté). « en_panne » = au-delà de 2× la cadence : surfacé comme un retard fort.
const enRetard = (s: SourceInfo) => s.fraicheur_statut === 'en_retard' || s.fraicheur_statut === 'en_panne'
// CONNEXIONS-2 Lot 6.2 (KO-14) — échec d'ingestion : distinct de l'ancienneté, badge rouge.
const enErreur = (s: SourceInfo) => s.fraicheur_statut === 'en_erreur' || !!s.fraicheur_erreur_at
// M105 P2 — le verdict AMONT EN AVANCE (M96) : le radar a vu une publication plus récente que
// ce que nous avons intégré. Distinct de « publication ancienne » (là, c'est le producteur).
// NUANCE mesurée : `nouvelle_publication` = « changé depuis le DERNIER PASSAGE radar », pas
// « non intégré » — les sources à cron auto (SITADEL/DPE) sont souvent déjà ingérées APRÈS la
// publication détectée. Le verdict compare donc la date AMONT sondée à notre dernière
// intégration (tolérance 1 jour) — faux positifs mesurés et écartés (17/08).
const amontEnAvance = (s: SourceInfo) => {
  if (s.radar?.statut !== 'nouvelle_publication' || !s.radar?.valeur) return false
  const amont = Date.parse(s.radar.valeur)
  const integreStr = majReelle(s)
  const integre = integreStr ? Date.parse(integreStr) : NaN
  return Number.isFinite(amont) && (!Number.isFinite(integre) || amont > integre + 86_400_000)
}
/** La cadence en mots (dérivée du seuil servi = 2× la cadence — jamais un chiffre en dur ici). */
function cadenceMot(seuil?: number | null): string {
  const j = seuil != null ? Math.round(seuil / 2) : null
  if (j === 7) return 'chaque semaine'
  if (j === 30) return 'chaque mois'
  if (j === 91) return 'chaque trimestre'
  return j != null ? `tous les ${j} jours` : 'à cadence connue'
}
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
const nonTrace = (s: SourceInfo) => versionMeta(s).untracked
// M105 P1 — « à jour » = ni retard de publication (producteur), ni version plus récente non
// intégrée (nous). Une source SANS date exposée par le producteur n'est PAS « pas à jour » —
// c'est une propriété du producteur, dite dans la petite ligne de l'encart, pas un défaut LABUSE.
const aJour = (s: SourceInfo) => !enRetard(s) && !amontEnAvance(s)

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
  const late = enRetard(s)
  const lic = licence(s)
  const fiab = fiabiliteBadge(s)
  const prod = [s.provider, lic].filter(Boolean)
  const erreur = enErreur(s)

  return (
    <div ref={ref} data-source-row
      className={`grid grid-cols-[14px_1fr_20px] items-center gap-x-3.5 gap-y-1.5 border-b border-line px-4 py-3 last:border-b-0 hover:bg-white/[0.018] md:grid-cols-[14px_1fr_190px_150px_20px] ${focused ? 'bg-mint/[0.06]' : ''}`}>
      {/* pastille — rouge (en erreur) > warn (en retard) > mint (à jour), avec halo */}
      <span className="h-[7px] w-[7px] shrink-0 rounded-full"
        style={erreur
          ? { background: '#E05252', boxShadow: '0 0 0 3px rgba(224,82,82,.12)' }
          : late
            ? { background: TOKENS.warn, boxShadow: `0 0 0 3px ${TOKENS.warnBg}` }
            : { background: TOKENS.mint, boxShadow: '0 0 0 3px rgba(74,222,128,.10)' }}
        title={erreur ? 'Dernière ingestion en erreur' : late ? 'En retard sur sa cadence de publication' : 'À jour selon la cadence du producteur'} />

      {/* nom + badges d'état */}
      <span className="flex flex-wrap items-center gap-2 text-[13.5px] text-txt">
        {s.name}
        {erreur && (
          <Badge kind="error" title={s.fraicheur_erreur_message
            ? `${s.fraicheur_erreur_message}${s.fraicheur_erreur_at ? ` — ${s.fraicheur_erreur_at.slice(0, 10)}` : ''}`
            : "La dernière ingestion de cette source a échoué."}>
            <span data-source-erreur>en erreur</span>
          </Badge>
        )}
        {sondable(s) && <Badge kind="auto" title="Le producteur expose une date interrogeable : notre radar vérifie automatiquement que c'est la dernière version publiée.">version vérifiée</Badge>}
        {suiviManuel(s) && <Badge kind="dashed" title={`Pas de sonde automatique fiable : version vérifiée à la main. Cadence : ${s.radar?.cadence ?? 'grande passe'}.`}>suivi manuel</Badge>}
        {late && (
          <Badge kind="late" title="Le producteur n'a rien publié depuis plus longtemps que sa cadence habituelle — nous servons bien la dernière version publiée.">
            <span data-source-decroche>publication ancienne</span>
          </Badge>
        )}
        {amontEnAvance(s) && (
          <Badge kind="late" title="Le radar amont a détecté une publication plus récente chez le producteur, pas encore intégrée chez nous.">
            <span data-source-amont>version plus récente disponible</span>
          </Badge>
        )}
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

      {/* ligne dépliée : le retard chiffré, ou la nature (proxy/curée) dite en clair */}
      {/* M105 P2 — état 1 : c'est le PRODUCTEUR qui n'a rien publié (nous servons la dernière
          version publiée) — formulation côté producteur, jamais « LABUSE en retard ». */}
      {late && (
        <p data-source-retard-producteur className="col-[2/-1] text-[12px] leading-snug text-txt-dim">
          Dernière publication : {s.derniere_donnee ? new Date(s.derniere_donnee).toLocaleDateString('fr-FR') : 'date inconnue'}.
          {' '}Le producteur publie habituellement {cadenceMot(s.fraicheur_seuil_jours)}.
        </p>
      )}
      {/* M105 P2 — état 2 (verdict AMONT EN AVANCE de M96, côté NOUS) : devrait rester vide en
          permanence une fois les crons VPS actifs — sinon c'est un vrai signal. */}
      {amontEnAvance(s) && (
        <p data-source-amont-detail className="col-[2/-1] text-[12px] leading-snug text-txt-dim">
          Une version plus récente est disponible et n'est pas encore intégrée.
        </p>
      )}
      {s.nature?.detail && (
        <p data-source-nature-detail className="col-[2/-1] text-[12px] leading-snug text-txt-dim">{s.nature.detail}</p>
      )}
    </div>
  )
}

type Filtre = 'toutes' | 'ajour' | 'retard' | 'nontrace'

export function SourcesPage() {
  const { data, isLoading, isError } = useQuery({ queryKey: ['sources'], queryFn: getSources })
  const sourcesFocus = useApp((s) => s.sourcesFocus)
  const [q, setQ] = useState('')
  const [filtre, setFiltre] = useState<Filtre>('toutes')

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

  // M87 P4 — les 4 compteurs de la barre d'état sont DÉRIVÉS des sources servies (jamais en dur).
  // L'API ne sert déjà que connecte-hors-doublons-hors-masquées ; le filtre reste défensif.
  const comptees = useMemo(() => (data ?? []).filter((s) => !s.doublon), [data])
  const nTotal = comptees.length
  const nVerif = comptees.filter(sondable).length
  const nRetard = comptees.filter(enRetard).length
  const nNonTrace = comptees.filter(nonTrace).length
  const nAJour = comptees.filter(aJour).length
  // M105 P3.2 — la DATE du dernier passage radar (max des derniere_verif servis) : un état
  // « à jour » mesuré il y a un mois doit dire son âge.
  const radarPassage = useMemo(() => comptees.reduce<string | null>((acc, s) => {
    const d = s.radar?.derniere_verif ?? null
    return d && (!acc || d > acc) ? d : acc
  }, null), [comptees])
  // FIX-SOURCES S3 — la réserve DVF ne code plus « 2025–2026 » en dur : la borne RÉCENTE est LUE dans
  // la base (dernière donnée servie de la source DVF, dvf_mutations_parcelle). Sans donnée → phrase
  // sans chiffre. Jamais une année inventée.
  const dvfMaxAnnee = useMemo(() => {
    const d = (data ?? []).find((s) => s.name === 'DVF / valeurs foncières')?.derniere_donnee
    const y = d ? new Date(d).getFullYear() : NaN
    return Number.isFinite(y) ? y : null
  }, [data])

  const CHIPS: { key: Filtre; label: string; n: number }[] = [
    { key: 'toutes', label: 'Toutes', n: nTotal },
    { key: 'ajour', label: 'À jour', n: nAJour },
    { key: 'retard', label: 'En retard', n: nRetard },
    { key: 'nontrace', label: 'Millésime non tracé', n: nNonTrace },
  ]

  // Recherche (nom / producteur / licence / catégorie) + filtre actif. Groupé par catégorie.
  const cats = useMemo(() => {
    const ql = q.trim().toLowerCase()
    const passeFiltre = (s: SourceInfo) =>
      filtre === 'toutes' ? true : filtre === 'ajour' ? aJour(s) : filtre === 'retard' ? enRetard(s) : nonTrace(s)
    const passeSearch = (s: SourceInfo) =>
      !ql || [s.name, s.provider, s.category, licence(s)].some((v) => (v ?? '').toLowerCase().includes(ql))
    const m = new Map<string, SourceInfo[]>()
    for (const s of comptees) {
      if (!passeFiltre(s) || !passeSearch(s)) continue
      const k = s.category || 'Autres'
      m.set(k, [...(m.get(k) ?? []), s])
    }
    return [...m.entries()]
  }, [comptees, q, filtre])

  const nVisibles = cats.reduce((acc, [, l]) => acc + l.length, 0)

  return (
    <div data-sources-page className="sources-print flex min-w-0 flex-1 flex-col overflow-y-auto">
      <div className="mx-auto w-full max-w-[1060px] px-7 py-10">
        {/* en-tête */}
        <p className="mb-3.5 font-mono text-[10.5px] uppercase tracking-[.16em] text-txt-dim">Données et méthode</p>
        <h1 className="mb-2 text-[26px] font-semibold tracking-[-.02em] text-txt-hi">Sources &amp; fraîcheur</h1>
        <p data-sources-positionnement className="mb-7 max-w-[62ch] text-[13px] leading-relaxed text-txt-mut">
          Chaque réponse LABUSE est traçable jusqu'à sa source publique. Ce tableau dit d'où vient le
          chiffre, à quelle date il a été publié par son producteur, et si nous savons vérifier cette
          date automatiquement.
        </p>

        {/* M105 P1 — l'encart HIÉRARCHISÉ : en grand l'essentiel (sources · à jour), en petit la
            méthode (vérifiées auto · sans date exposée PAR LE PRODUCTEUR — ce n'est pas LABUSE qui
            ne trace pas). Le compteur « en retard » a QUITTÉ l'encart : l'information vit sur la
            ligne de chaque source concernée (badge + formulation, jamais masquée). Tous les
            compteurs restent CALCULÉS (nAJour dérivé), aucun chiffre en dur. */}
        {data && (
          <div data-sources-bandeau className="mb-3.5 overflow-hidden rounded-[10px] border border-line bg-surface-2">
            <div className="flex flex-wrap">
              <div className="min-w-[150px] flex-1 border-r border-line px-[18px] py-3.5 last:border-r-0">
                <b className="block text-[26px] font-semibold leading-tight text-txt-hi">{nTotal}</b>
                <span className="font-mono text-[10px] uppercase tracking-[.13em] text-txt-dim">sources</span>
              </div>
              <div className="min-w-[150px] flex-1 px-[18px] py-3.5">
                <b className="block text-[26px] font-semibold leading-tight text-mint">{nAJour}</b>
                <span className="font-mono text-[10px] uppercase tracking-[.13em] text-txt-dim">à jour</span>
              </div>
            </div>
            <p data-sources-sousligne className="border-t border-line px-[18px] py-2 text-[11.5px] text-txt-dim">
              {nVerif} vérifiées automatiquement · {nNonTrace} sans date exposée par le producteur
              {radarPassage && <> · radar amont : dernier passage le {new Date(radarPassage).toLocaleDateString('fr-FR')}</>}
            </p>
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

        {/* barre d'outils : recherche + 4 filtres (comptes calculés) */}
        <div className="sticky top-0 z-[5] mb-5 flex flex-wrap items-center gap-2.5 border-b border-line bg-bg py-3">
          <input data-sources-search value={q} onChange={(e) => setQ(e.target.value)}
            placeholder="Chercher une source, un producteur…"
            className="min-w-[200px] flex-[1_1_240px] rounded-lg border border-line bg-surface-2 px-3 py-2 text-[13px] text-txt placeholder:text-txt-dim focus:border-line-2 focus:outline-none" />
          {CHIPS.map((c) => (
            <button key={c.key} data-sources-chip={c.key} aria-pressed={filtre === c.key} onClick={() => setFiltre(c.key)}
              className={`rounded-full border px-3 py-1.5 text-[12.5px] transition-colors duration-quick ${
                filtre === c.key ? 'border-mint/40 bg-mint/10 text-mint' : 'border-line text-txt-mut hover:border-line-2 hover:text-txt'}`}>
              {c.label} <span className="ml-1.5 font-mono text-[11px] opacity-70">{c.n}</span>
            </button>
          ))}
        </div>

        {isLoading && <div className="mt-6"><Loading label="Chargement des sources" className="text-xs" /></div>}
        {isError && <p className="mt-6 text-xs text-st-ecartee">Sources inaccessibles — vérifiez votre réseau ou réessayez.</p>}
        {data && nVisibles === 0 && (
          <p className="mt-8 text-[13px] text-txt-dim">Aucune source ne correspond{q ? <> à « {q} »</> : null}{filtre !== 'toutes' ? ' pour ce filtre' : ''}.</p>
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

        {/* légende (reprise de la maquette) */}
        {data && (
          <div className="mt-9 flex flex-wrap gap-x-6 gap-y-2.5 border-t border-line pt-4 text-[12px] text-txt-dim">
            <span className="flex items-center gap-2"><i className="inline-block h-[7px] w-[7px] rounded-full" style={{ background: TOKENS.mint }} /> à jour selon la cadence du producteur</span>
            <span className="flex items-center gap-2"><i className="inline-block h-[7px] w-[7px] rounded-full" style={{ background: TOKENS.warn }} /> en retard sur sa cadence</span>
            <span className="flex items-center gap-2"><Badge kind="auto">version vérifiée</Badge> le producteur expose une date interrogeable</span>
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
