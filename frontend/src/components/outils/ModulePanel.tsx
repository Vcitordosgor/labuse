import { useMutation, useQuery } from '@tanstack/react-query'
import { useEffect, useMemo, useState } from 'react'
import {
  getPipeline, modBailleur, modCourriers, modDivision, modDueDiligence, modFantome,
  modPatrimoine, modPatrimoineSearch, modPermis, modPermisFiche,
  modPromesses, modSolaireParkings, modSolaireTertiaire, modVelocite,
} from '../../lib/api'
import { pointInPolygon } from '../../lib/geo'
import { useApp } from '../../store/useApp'
import { Loading } from '../Loading'
import { M22 } from './M22Programme'
import { M15, M16, M17, M18, M19 } from './moteurs'
import { MODULES, VIOLET } from './registry'
import { ScoringV2Module } from './ScoringV2'
import { TierBadge } from './TierBadge'

/* ───────── primitives partagées (doctrine module : violet, bandeau honnête, liste→fiche) ───────── */

function Banner({ children }: { children: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-[#4a3d6b] bg-[#1a1526] px-3 py-2 text-[10.5px] leading-relaxed text-[#b8a8de]">
      {children}
    </div>
  )
}

function Row({ idu, right, sub, fiche }: { idu: string; right: React.ReactNode; sub?: string; fiche?: [string, string][] }) {
  const { select, moduleFiche, setModuleFiche, module } = useApp()
  return (
    <button
      onClick={() => {
        if (fiche && module) setModuleFiche({ ...moduleFiche, [idu]: { module, lines: fiche } })
        select(idu)
      }}
      className="flex w-full shrink-0 items-center gap-2 rounded-lg border border-line-2 bg-surface-3 px-3 py-2 text-left hover:border-[#6b5a96]"
    >
      <div className="min-w-0 flex-1">
        <div className="font-mono text-xs text-txt-hi">{idu.slice(8, 10)} {idu.slice(10)}</div>
        {sub && <div className="truncate text-[10.5px] text-txt-mut">{sub}</div>}
      </div>
      <div className="shrink-0 text-right">{right}</div>
    </button>
  )
}

const V = ({ children }: { children: React.ReactNode }) => (
  <span className="font-display text-sm font-bold" style={{ color: VIOLET }}>{children}</span>
)

const fmt = (n: number | null | undefined) => (n == null ? '—' : Math.round(Number(n)).toLocaleString('fr-FR'))

/** Pousse résultats sur la carte (surlignage violet + géométries propres) — et nettoie en sortie. */
function useModuleMap(idus: string[], extra: unknown | null, deps: unknown[]) {
  const setModuleMap = useApp((s) => s.setModuleMap)
  useEffect(() => {
    setModuleMap({ idus, extra })
    return () => setModuleMap({ idus: [], extra: null })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)
}

const featureCollection = (features: unknown[]) => ({ type: 'FeatureCollection', features })

/* ───────────────────────────── M01 — DIVISION ───────────────────────────── */

function M01() {
  const [minScore, setMinScore] = useState(70)
  const commune = useApp((s) => s.commune)
  const q = useQuery({ queryKey: ['m01', minScore, commune], queryFn: () => modDivision(minScore) })
  const items = (q.data?.items ?? []) as Record<string, any>[]
  useModuleMap(
    items.map((i) => i['idu'] as string),
    featureCollection(items.filter((i) => i['lot']).map((i) => ({ type: 'Feature', geometry: i['lot'], properties: { kind: 'lot' } }))),
    [q.dataUpdatedAt],
  )
  return (
    <>
      <Banner>Lot candidat = approximation (plus grand cercle inscrit, recul bâti 3 m) — dessiné en
        pointillés, <b>indicatif</b>. Règles de division (PLU, accès, réseaux) à instruire.</Banner>
      <label className="mt-1 flex items-center gap-2 text-[11px] text-txt-mut">
        Score division ≥ <input type="range" min={0} max={95} step={5} value={minScore}
          onChange={(e) => setMinScore(Number(e.target.value))} className="flex-1 accent-[#B497F0]" />
        <span className="font-mono text-txt">{minScore}</span>
      </label>
      <p className="text-[11px] text-txt-dim">
        {q.isFetching ? <Loading label="Calcul des candidats" /> : `${fmt(q.data?.total)} candidats (SQL)`}
      </p>
      <div className="flex min-h-0 flex-1 flex-col gap-1.5 overflow-y-auto">
        {items.map((i) => (
          <Row key={i['idu'] as string} idu={i['idu'] as string}
            sub={`${fmt(i['surface_m2'] as number)} m² · emprise ${i['emprise_pct']}% · lot ~${fmt(i['lot_area_m2'] as number)} m²`}
            right={<V>{i['score'] as number}</V>}
            fiche={[['Score division', String(i['score'])], ['Lot détachable (approx.)', `~${fmt(i['lot_area_m2'] as number)} m²`],
              ['Rayon libre', `${i['mic_radius_m']} m`], ['Emprise bâtie', `${i['emprise_pct']} %`], ['Zone', String(i['zone'])]]} />
        ))}
      </div>
    </>
  )
}

/* ───────────────────────────── M02 — PATRIMOINE ───────────────────────────── */

function M02() {
  const { m02Prefill, setM02Prefill } = useApp()
  const [q, setQ] = useState('')
  const [siren, setSiren] = useState<string | null>(null)
  useEffect(() => {
    if (m02Prefill) { setSiren(m02Prefill); setM02Prefill(null) }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [m02Prefill])
  const sug = useQuery({ queryKey: ['m02s', q], queryFn: () => modPatrimoineSearch(q), enabled: q.length >= 2 && !siren })
  const pat = useQuery({ queryKey: ['m02', siren], queryFn: () => modPatrimoine(siren!), enabled: !!siren })
  const d = pat.data as Record<string, any> | undefined
  const items = ((d?.['items'] ?? []) as Record<string, any>[])
  useModuleMap(items.map((i) => i['idu'] as string), null, [pat.dataUpdatedAt])
  return (
    <>
      <input value={q} onChange={(e) => { setQ(e.target.value); setSiren(null) }}
        placeholder="SIREN ou nom (ex. CBO, SCI…)"
        className="rounded-lg border border-line-2 bg-surface-3 px-2 py-1.5 text-xs text-txt focus:border-[#B497F0] focus:outline-none" />
      {!siren && (sug.data ?? []).map((s) => (
        <button key={s.siren} onClick={() => setSiren(s.siren)}
          className="flex items-center justify-between rounded-lg border border-line-2 bg-surface-3 px-3 py-1.5 text-left text-xs text-txt hover:border-[#6b5a96]">
          <span className="truncate">{s.nom}</span><span className="font-mono text-[11px] text-txt-dim">{s.n} parc.</span>
        </button>
      ))}
      {/* Fix pré-lancement : distinguer un « 0 résultat LÉGITIME » d'une panne — sans ça, une boîte
          absente des fichiers fonciers (ex. VISHOR MATERIAUX) donne un écran muet lu comme « cassé ». */}
      {!siren && q.length >= 2 && !sug.isFetching && (sug.data?.length ?? 0) === 0 && (
        <div data-m02-vide className="rounded-lg border border-line-2 bg-surface-2 px-3 py-2 text-[11px] leading-snug text-txt-mut">
          « <b className="text-txt">{q}</b> » n'a pas de foncier connu dans les fichiers fonciers (DGFiP),
          ou n'y figure pas. Ces fichiers ne recensent que les <b>personnes morales</b> détentrices de
          foncier à La Réunion — une personne physique ou une société sans bien détecté n'apparaît pas.
        </div>
      )}
      {d && (
        <>
          {d['bodacc'] != null && (
            <div className="rounded-lg border border-[#5a2420] bg-[#3a1614] px-3 py-2 text-[11px] text-st-ecartee">
              ● BODACC — {(d['bodacc'] as Record<string, string>)['type_procedure']}
            </div>
          )}
          <div className="rounded-lg border border-line-2 bg-surface-2 px-3 py-2 text-xs">
            <div className="truncate font-medium text-txt-hi">{d['nom'] as string}</div>
            <div className="mt-1 flex gap-4 text-[11px] text-txt-mut">
              <span><V>{d['n_parcelles'] as number}</V> parcelles</span>
              <span>SDP totale <V>{fmt(d['sdp_totale_m2'] as number)}</V> m²</span>
            </div>
          </div>
          <div className="flex min-h-0 flex-1 flex-col gap-1.5 overflow-y-auto">
            {items.map((i) => (
              <Row key={i['idu'] as string} idu={i['idu'] as string}
                sub={`${i['commune']} · ${fmt(i['surface_m2'] as number)} m² · SDP ${fmt(i['sdp'] as number)}`}
                right={<TierBadge tier={i['tier_v2'] as string | null} etage0={i['etage0'] as boolean | null} statut={i['statut'] as string | null} />}
                fiche={[['Propriétaire', String(d['nom'])], ['SIREN', String(d['siren'])],
                  ['Patrimoine', `${d['n_parcelles']} parcelles · SDP ${fmt(d['sdp_totale_m2'] as number)} m²`]]} />
            ))}
          </div>
        </>
      )}
    </>
  )
}

/* ───────────────────────────── M03 — RADAR PERMIS ───────────────────────────── */

const NATURES = [['', 'Tout'], ['PC', 'PC'], ['DP', 'DP'], ['PA', 'PA'], ['PD', 'PD']] as const

/** Tiroir « fiche permis » (M10 lot 1.1) — s'ouvre au clic sur un permis, partagé radar/fiche. */
export function PermitDrawer({ permitId, onClose }: { permitId: string; onClose: () => void }) {
  const q = useQuery({ queryKey: ['permis-fiche', permitId], queryFn: () => modPermisFiche(permitId) })
  const d = q.data as Record<string, any> | undefined
  const F = ({ label, value }: { label: string; value: React.ReactNode }) =>
    value == null || value === '' ? null : (
      <div className="flex justify-between gap-3 border-b border-[#141d17] py-1.5 text-[11px]">
        <span className="text-txt-dim">{label}</span>
        <span className="text-right text-txt">{value}</span>
      </div>
    )
  return (
    <div data-permis-drawer className="fixed inset-0 z-50 flex items-end justify-center bg-black/50 sm:items-center" onClick={onClose}>
      <div className="max-h-[80vh] w-full max-w-md overflow-y-auto rounded-t-2xl border border-[#4a3d6b] bg-surface-1 p-4 sm:rounded-2xl"
        onClick={(e) => e.stopPropagation()}>
        {q.isLoading && <Loading />}
        {d && (
          <>
            <div className="mb-2 flex items-start justify-between gap-2">
              <div>
                <div className="font-display text-sm font-bold text-txt-hi">{d['nature_libelle']}</div>
                <div className="font-mono text-[11px] text-txt-mut">{d['permit_id']} · {d['commune']}</div>
              </div>
              <button onClick={onClose} className="rounded-full border border-line-2 px-2 py-0.5 text-[11px] text-txt-mut">✕</button>
            </div>
            <F label="Statut" value={d['statut']} />
            <F label="Porteur" value={d['porteur'] ?? <span className="text-txt-dim">{d['porteur_note']}</span>} />
            {d['porteur_siren'] && <F label="SIREN" value={<span className="font-mono">{d['porteur_siren']}</span>} />}
            <F label="Nombre de lots" value={d['nb_lots']} />
            <F label="Surface habitable" value={d['surface_hab_m2'] != null ? `${fmt(d['surface_hab_m2'])} m²` : null} />
            <F label="Date de dépôt" value={d['date_depot']} />
            <F label="Date d'autorisation" value={d['date_autorisation']} />
            <F label="Achèvement (DAACT)" value={d['date_achevement']} />
            {d['delai_instruction'] && (
              <F label="Délai d'instruction" value={<span style={{ color: VIOLET }} className="font-semibold">{d['delai_instruction']['libelle']}</span>} />
            )}
            <F label="Parcelle(s)" value={<span className="font-mono text-[10px]">{(d['parcelles'] as string[]).join(', ')}</span>} />
            <p className="mt-2 text-[10px] text-txt-dim">{d['source']}</p>
          </>
        )}
      </div>
    </div>
  )
}

function M03() {
  const [months, setMonths] = useState(24)
  const [nature, setNature] = useState('')
  const [open, setOpen] = useState<string | null>(null)
  const zone = useApp((s) => s.zone)
  const commune = useApp((s) => s.commune)
  const q = useQuery({ queryKey: ['m03', months, nature, commune], queryFn: () => modPermis(months, nature || null) })
  const d = q.data as Record<string, any> | undefined
  // la ZONE DESSINÉE (outil carte) filtre aussi les permis géocodés — les non-géocodés restent listés
  const items = ((d?.['items'] ?? []) as Record<string, any>[]).filter((i) => {
    if (!zone || !i['geom']) return true
    const c = (i['geom'] as { coordinates: [number, number] }).coordinates
    return pointInPolygon(c, zone)
  })
  const geo = items.filter((i) => i['geom'])
  useModuleMap([],
    featureCollection(geo.map((i) => ({ type: 'Feature', geometry: i['geom'], properties: { kind: 'permis', label: `${i['type']} ${i['date']}` } }))),
    [q.dataUpdatedAt])
  return (
    <>
      <Banner>Géocodage {String(d?.['pct_geocode'] ?? '…')} % — les non-géocodés restent listés.
        Données jusqu'au <b>{String(d?.['donnees_jusqu_au'] ?? '…')}</b> (flux Sitadel régional).
        Cliquez un permis pour sa fiche (porteur, lots, surfaces, délai d'instruction).</Banner>
      <div className="flex flex-wrap gap-1.5">
        {[12, 24, 48, 72].map((m) => (
          <button key={m} onClick={() => setMonths(m)}
            className={`rounded-full border px-2.5 py-1 text-[11px] ${months === m ? 'border-[#B497F0] text-[#B497F0]' : 'border-line-2 text-txt-mut'}`}>
            {m} mois
          </button>
        ))}
        <span className="mx-1 self-center text-line-2">|</span>
        {NATURES.map(([v, l]) => (
          <button key={v} onClick={() => setNature(v)}
            className={`rounded-full border px-2.5 py-1 text-[11px] ${nature === v ? 'border-[#B497F0] text-[#B497F0]' : 'border-line-2 text-txt-mut'}`}>
            {l}
          </button>
        ))}
      </div>
      <p className="text-[11px] text-txt-dim">
        {zone ? `${items.length} permis dans la zone dessinée` : `${fmt(d?.['total'] as never)} permis${(d?.['affiches'] as number) < (d?.['total'] as number) ? ` · ${fmt(d?.['affiches'] as never)} affichés` : ''}`} · {geo.length} sur la carte
        {zone && <span className="text-[#8b76c0]"> · outil Zone actif</span>}
      </p>
      <div className="flex min-h-0 flex-1 flex-col gap-1 overflow-y-auto">
        {items.slice(0, 150).map((i, k) => (
          <button key={k} onClick={() => setOpen(i['permit_id'] as string)}
            className={`flex items-center gap-2 rounded-lg border border-line-2 px-3 py-1.5 text-left text-[11px] hover:border-[#6b5a96] ${i['geom'] ? 'bg-surface-3' : 'bg-[#141019]'}`}>
            <span className="font-mono text-txt">{i['type'] as string}</span>
            <span className="text-txt-mut">{i['date'] as string}</span>
            {i['delai_mois'] != null && <span style={{ color: VIOLET }}>{String(i['delai_mois'])} m</span>}
            {i['nb_lgt'] != null && <span className="text-txt-dim">{String(i['nb_lgt'])} lgt</span>}
            {!i['geom'] && <span className="ml-auto text-[11px] text-[#8b76c0]">non géocodé</span>}
          </button>
        ))}
      </div>
      {open && <PermitDrawer permitId={open} onClose={() => setOpen(null)} />}
    </>
  )
}

/* ───────────────────────────── M04 — PROMESSES MORTES ───────────────────────────── */

function M04() {
  const [months, setMonths] = useState(24)
  const commune = useApp((s) => s.commune)
  const q = useQuery({ queryKey: ['m04', months, commune], queryFn: () => modPromesses(months) })
  const d = q.data as Record<string, any> | undefined
  const items = ((d?.['items'] ?? []) as Record<string, any>[])
  useModuleMap(items.map((i) => i['idu'] as string), null, [q.dataUpdatedAt])
  return (
    <>
      <Banner>PC accordé, <b>aucune déclaration d'achèvement</b>, parcelle toujours non bâtie au
        scoring — « réalisation à vérifier » sur place. Codes d'état de la source non documentés
        (affichés bruts).</Banner>
      <label className="flex items-center gap-2 text-[11px] text-txt-mut">
        Permis plus vieux que
        <select value={months} onChange={(e) => setMonths(Number(e.target.value))}
          className="rounded border border-line-2 bg-surface-3 px-1 py-0.5 text-txt">
          {[24, 36, 48, 60].map((m) => <option key={m} value={m}>{m} mois</option>)}
        </select>
      </label>
      <p className="text-[11px] text-txt-dim">{fmt(d?.['total'] as never)} promesses mortes{(d?.['affiches'] as number) < (d?.['total'] as number) ? ` · ${fmt(d?.['affiches'] as never)} affichées` : ''}</p>
      <div className="flex min-h-0 flex-1 flex-col gap-1.5 overflow-y-auto">
        {items.map((i, k) => (
          <Row key={k} idu={i['idu'] as string}
            sub={`PC ${i['date']} · ${fmt(i['surface_m2'] as number)} m² · état ${i['etat']}`}
            right={<TierBadge tier={i['tier_v2'] as string | null} etage0={i['etage0'] as boolean | null} statut={i['statut'] as string | null} />}
            fiche={[['Permis', `${i['permit_id']} (${i['date']})`], ['État source', `code ${i['etat']} — sans achèvement déclaré`],
              ['Lecture', 'PC ancien jamais réalisé — réalisation à vérifier']]} />
        ))}
      </div>
    </>
  )
}

/* ───────────────────────────── M05 — VÉLOCITÉ ADMIN ───────────────────────────── */

function M05() {
  const [nature, setNature] = useState('PC')
  const q = useQuery({ queryKey: ['m05', nature], queryFn: () => modVelocite(nature || null) })
  const d = q.data as Record<string, any> | undefined
  const [sort, setSort] = useState<'n_valide' | 'delai_median_mois'>('delai_median_mois')
  const rows = useMemo(() => ([...((d?.['communes'] ?? []) as Record<string, any>[])])
    .sort((a, b) => Number(b[sort] ?? 0) - Number(a[sort] ?? 0)), [d, sort])
  const natLabel = { PC: 'PC', DP: 'DP', PA: 'PA', PD: 'PD', '': 'toutes natures' }[nature]
  return (
    <>
      <Banner><b>{d?.['indicateur'] ?? 'Délai médian d\'instruction dépôt → autorisation'}</b> ({natLabel},
        cohortes {String(d?.['cohortes'] ?? '…')}). {d?.['note']}
        <div className="mt-1 text-[#8b76c0]">⚠ {d?.['censure']}</div>
        <div className="mt-1 italic">{d?.['disclaimer']}</div>
      </Banner>
      <div className="flex flex-wrap gap-1.5">
        {NATURES.filter(([v]) => v).map(([v, l]) => (
          <button key={v} onClick={() => setNature(v)}
            className={`rounded-full border px-2.5 py-1 text-[11px] ${nature === v ? 'border-[#B497F0] text-[#B497F0]' : 'border-line-2 text-txt-mut'}`}>
            {l}
          </button>
        ))}
        <a href={`/modules/velocite?fmt=csv${nature ? `&nature=${nature}` : ''}`}
          className="ml-auto self-center rounded-lg border border-line-2 px-2.5 py-1 text-[11px] text-txt hover:text-txt-hi">⬇ CSV</a>
      </div>
      <div className="flex min-h-0 flex-1 flex-col overflow-y-auto">
        <div className="sticky top-0 grid grid-cols-[1fr_64px_60px] gap-1 bg-surface-1 py-1 text-[11px] tracking-wide text-txt-dim">
          <span>COMMUNE (ÎLE)</span>
          {([['delai_median_mois', 'MÉDIANE'], ['n_valide', 'N']] as const).map(([k, l]) => (
            <button key={k} onClick={() => setSort(k)} className={`text-right ${sort === k ? 'text-[#B497F0]' : ''}`}>{l} ↓</button>
          ))}
        </div>
        {rows.map((c) => (
          <div key={c['commune'] as string} className="grid grid-cols-[1fr_64px_60px] gap-1 border-b border-[#141d17] py-1.5 text-[11px]"
            title={`${c['commune']} : délai médian d'instruction ${natLabel} = ${c['delai_median_mois']} mois (IQR ${c['delai_p25_mois']}–${c['delai_p75_mois']}), sur ${c['n_mur']} dossiers mûrs. ${c['n_recent_exclu']} dépôts récents exclus (non mûrs), ${c['n_exclus_qualite']} exclus (dépôt>autorisation).`}>
            <span className="truncate text-txt">{c['commune'] as string}</span>
            <span className="text-right font-mono" style={{ color: VIOLET }}>{c['delai_median_mois'] == null ? '—' : `${c['delai_median_mois']} m`}</span>
            <span className="text-right font-mono text-txt-mut">{fmt(c['n_mur'] as number)}</span>
          </div>
        ))}
        <p className="py-2 text-[11px] text-txt-dim">
          Médiane dépôt→autorisation en mois · N = dossiers mûrs (dépôts &lt; {String(d?.['maturite_cutoff'] ?? '…')}).
          Survolez une ligne pour l'IQR et les exclusions.</p>
      </div>
    </>
  )
}

/* ───────────────────────────── M06 — MODE BAILLEUR ───────────────────────────── */

function M06() {
  const commune = useApp((s) => s.commune)
  const q = useQuery({ queryKey: ['m06', commune], queryFn: modBailleur })
  const d = q.data as Record<string, any> | undefined
  const items = ((d?.['items'] ?? []) as Record<string, any>[])
  useModuleMap(items.map((i) => i['idu'] as string), null, [q.dataUpdatedAt])
  return (
    <>
      <Banner>{String(d?.['lecture_lls'] ?? '…')}</Banner>
      <p className="text-[11px] text-txt-dim">{fmt(d?.['total'] as never)} parcelles promues en QPV{(d?.['affiches'] as number) < (d?.['total'] as number) ? ` · ${fmt(d?.['affiches'] as never)} affichées` : ''}</p>
      <div className="flex min-h-0 flex-1 flex-col gap-1.5 overflow-y-auto">
        {items.map((i) => (
          <Row key={i['idu'] as string} idu={i['idu'] as string}
            sub={`${fmt(i['surface_m2'] as number)} m² · SDP ${fmt(i['sdp'] as number)} m²`}
            right={<TierBadge tier={i['tier_v2'] as string | null} etage0={i['etage0'] as boolean | null} statut={i['statut'] as string | null} />}
            fiche={[['Mode bailleur', 'Parcelle en QPV'], ['Leviers LLS', 'TVA 2,1 % · abattement TFPB 30 %'],
              ['SDP résiduelle', `${fmt(i['sdp'] as number)} m²`]]} />
        ))}
      </div>
    </>
  )
}

/* ───────────────────────────── M07 — FONCIER FANTÔME ───────────────────────────── */

function M07() {
  const commune = useApp((s) => s.commune)
  const q = useQuery({ queryKey: ['m07', commune], queryFn: modFantome })
  const d = q.data as Record<string, any> | undefined
  const items = ((d?.['items'] ?? []) as Record<string, any>[])
  useModuleMap(items.map((i) => i['idu'] as string), null, [q.dataUpdatedAt])
  return (
    <>
      <Banner>Constructible (Q ≥ 50) mais <b>verrouillé</b> : personne morale introuvable au RNE ou
        dirigeant inactif. Levier indiqué par cas — vérification notariale indispensable.</Banner>
      <p className="text-[11px] text-txt-dim">{fmt(d?.['total'] as never)} parcelles gelées{(d?.['affiches'] as number) < (d?.['total'] as number) ? ` · ${fmt(d?.['affiches'] as never)} affichées` : ''}</p>
      <div className="flex min-h-0 flex-1 flex-col gap-1.5 overflow-y-auto">
        {items.map((i) => (
          <Row key={i['idu'] as string} idu={i['idu'] as string}
            sub={`${(i['denomination'] as string) ?? ''} · ${i['verrou']}`}
            right={<V>{i['q_score'] as number}</V>}
            fiche={[['⚠ Gelé', String(i['verrou'])], ['Levier', String(i['levier'])],
              ['Propriétaire', `${i['denomination']} (${i['siren']})`]]} />
        ))}
      </div>
    </>
  )
}

/* ───────────────────────────── M08 — REMONTER LE TEMPS ───────────────────────────── */

function M08() {
  return (
    <>
      <Banner>Comparateur <b>1950-1965 ↔ aujourd'hui</b> (orthos IGN libres). Glissez la poignée
        au centre de la carte. Les parcelles promues restent affichées des deux côtés.</Banner>
      <p className="text-[11px] leading-relaxed text-txt-mut">
        Le split est actif sur la carte. Accès direct depuis toute fiche : bouton « 1950 ».
      </p>
    </>
  )
}

/* ───────────────────────────── M09 — COURRIERS ───────────────────────────── */

function M09() {
  const pipeline = useQuery({ queryKey: ['pipeline'], queryFn: getPipeline })
  const [contexte, setContexte] = useState('standard')
  const [manual, setManual] = useState('')
  const gen = useMutation({ mutationFn: (idus: string[]) => modCourriers(idus, contexte) })
  const idus = manual.trim()
    ? manual.split(/[\n,;\s]+/).filter(Boolean)
    : (pipeline.data ?? []).map((e) => e.idu)
  const download = () => {
    const txt = (gen.data?.courriers ?? []).filter((c) => c.texte)
      .map((c) => `── ${c.idu} ${'─'.repeat(40)}\n\n${c.texte}`).join('\n\n\n')
    const a = document.createElement('a')
    a.href = URL.createObjectURL(new Blob([txt], { type: 'text/markdown' }))
    a.download = `courriers_${contexte}.md`
    a.click()
  }
  return (
    <>
      <Banner>Génération de courriers types — <b>aucun envoi</b>. Identité du propriétaire : workflow
        SPF/CERFA existant (fiche → export SPF), aucune donnée nominative automatisée.</Banner>
      <label className="text-[11px] text-txt-mut">Contexte
        <select value={contexte} onChange={(e) => setContexte(e.target.value)}
          className="ml-2 rounded border border-line-2 bg-surface-3 px-1 py-0.5 text-txt">
          <option value="standard">standard</option>
          <option value="indivision">indivision</option>
          <option value="succession">succession</option>
        </select>
      </label>
      <textarea value={manual} onChange={(e) => setManual(e.target.value)} rows={3}
        placeholder={`IDU (un par ligne) — vide = le pipeline CRM (${(pipeline.data ?? []).length} parcelles)`}
        className="rounded-lg border border-line-2 bg-surface-3 px-2 py-1.5 font-mono text-[10.5px] text-txt focus:border-[#B497F0] focus:outline-none" />
      <button onClick={() => idus.length && gen.mutate(idus)} disabled={!idus.length || gen.isPending}
        className="rounded-lg py-1.5 text-xs font-medium text-[#120d1d] disabled:opacity-40" style={{ background: VIOLET }}>
        {gen.isPending ? 'Génération…' : `Générer ${idus.length} courrier${idus.length > 1 ? 's' : ''}`}
      </button>
      {gen.data && (
        <>
          <button onClick={download} className="rounded-lg border border-line-2 py-1 text-[11px] text-txt hover:text-txt-hi">⬇ Télécharger le lot (.md)</button>
          <div className="flex min-h-0 flex-1 flex-col gap-1.5 overflow-y-auto">
            {gen.data.courriers.map((c) => (
              <div key={c.idu} className="rounded-lg border border-line-2 bg-surface-3 p-2">
                <div className="font-mono text-[10.5px] text-txt-hi">{c.idu}</div>
                <div className="mt-1 line-clamp-3 whitespace-pre-wrap text-[11px] leading-snug text-txt-mut">{c.texte ?? c.erreur}</div>
              </div>
            ))}
          </div>
        </>
      )}
    </>
  )
}

/* ───────────────────────────── M10 — DUE DILIGENCE ───────────────────────────── */

function M10() {
  const [refs, setRefs] = useState('')
  const run = useMutation({ mutationFn: () => modDueDiligence(refs) })
  const items = (run.data?.items ?? []) as Record<string, any>[]
  return (
    <>
      <Banner>Collez une liste de références (IDU complet ou SECTION+NUMÉRO, ex. AC0253) — un
        rapport par parcelle, PDF individuel réutilisant l'export fiche.</Banner>
      <textarea value={refs} onChange={(e) => setRefs(e.target.value)} rows={4}
        placeholder={'97415000AC0253\nAC0254\nBK 63…'}
        className="rounded-lg border border-line-2 bg-surface-3 px-2 py-1.5 font-mono text-[10.5px] text-txt focus:border-[#B497F0] focus:outline-none" />
      <button onClick={() => refs.trim() && run.mutate()} disabled={!refs.trim() || run.isPending}
        className="rounded-lg py-1.5 text-xs font-medium text-[#120d1d] disabled:opacity-40" style={{ background: VIOLET }}>
        {run.isPending ? 'Analyse…' : 'Analyser le lot'}
      </button>
      {run.data && (
        <>
          <p className="text-[11px] text-txt-dim">{run.data.n_trouvees}/{run.data.n_demandes} références trouvées</p>
          <div className="flex min-h-0 flex-1 flex-col gap-1.5 overflow-y-auto">
            {items.map((i, k) => 'idu' in i ? (
              <div key={k} className="rounded-lg border border-line-2 bg-surface-3 px-3 py-2">
                <div className="flex items-center gap-2">
                  <Row idu={i['idu'] as string} sub={`${i['commune']} · ${fmt(i['surface_m2'] as number)} m² · ${i['flags']} flags · ${i['exclusions']} exclusion(s)`}
                    right={<TierBadge tier={i['tier_v2'] as string | null} etage0={i['etage0'] as boolean | null} statut={i['statut'] as string | null} />} />
                </div>
                <a href={i['pdf'] as string} target="_blank" rel="noreferrer" className="mt-1 inline-block text-[10.5px] text-[#8b76c0] hover:text-[#B497F0] hover:underline">⬇ PDF</a>
              </div>
            ) : (
              <div key={k} className="rounded-lg border border-[#5a2420] bg-[#2a1210] px-3 py-2 text-[11px] text-st-ecartee">
                {i['ref'] as string} — {i['erreur'] as string}
              </div>
            ))}
          </div>
        </>
      )}
    </>
  )
}

/* ─────────────── M23 — PARKINGS APER (mandat Habitat Solaire, Lot 9.3) ─────────────── */

function M23() {
  const [tranche, setTranche] = useState<string | null>(null)
  const q = useQuery({ queryKey: ['m23', tranche], queryFn: () => modSolaireParkings(tranche) })
  const d = q.data as Record<string, any> | undefined
  const items = ((d?.['items'] ?? []) as Record<string, any>[])
  useModuleMap([], d?.['geojson'] ?? null, [q.dataUpdatedAt])
  return (
    <>
      <Banner>Loi APER art. 40 — seuil <b>Réunion 1 000 m²</b> (décret 2025-802) : ombrières PV sur
        ≥ 50 % de la surface. ≥ 10 000 m² : échéance <b>01/07/2026 DÉPASSÉE</b> (jusqu'à 40 k€/an).
        Détection OSM = plancher, pas un recensement ; exemptions non déduites.</Banner>
      <div className="flex gap-1.5">
        {([[null, 'tous'], ['sup_10000', '≥ 10 000 m²'], ['1000_10000', '1 000-10 000 m²']] as const).map(([k, l]) => (
          <button key={l} onClick={() => setTranche(k)}
            className={`rounded-full border px-2.5 py-1 text-[11px] ${tranche === k ? 'border-[#B497F0] text-[#B497F0]' : 'border-line-2 text-txt-mut'}`}>
            {l}
          </button>
        ))}
      </div>
      <p className="text-[11px] text-txt-dim">
        {q.isFetching ? <Loading label="Chargement" /> : <>{fmt(d?.['total'])} parkings assujettis · <b className="text-st-ecartee">{fmt(d?.['echeances_depassees'])} échéance(s) dépassée(s)</b>{typeof d?.['affiches'] === 'number' && d['affiches'] < d['total'] ? <span className="text-txt-dim"> · {fmt(d['affiches'])} affichés</span> : null}</>}
      </p>
      <a href={`/solaire/parkings?fmt=csv${tranche ? `&tranche=${tranche}` : ''}`}
        className="self-start rounded-lg border border-line-2 px-2.5 py-1 text-[11px] text-txt hover:text-txt-hi">⬇ Export CSV</a>
      <div className="flex min-h-0 flex-1 flex-col gap-1.5 overflow-y-auto">
        {items.map((i) => {
          const idu = ((i['idus'] ?? []) as string[])[0]
          const sub = `${i['proprio_pm'] ?? 'propriétaire non identifié'}${i['proprio_siren'] ? ` (${i['proprio_siren']})` : ''}`
          const right = (
            <div className="text-right">
              <div className="font-mono text-[10.5px]" style={{ color: i['echeance_depassee'] ? '#ff7a68' : VIOLET }}>
                {i['echeance_depassee'] ? 'DÉPASSÉE' : String(i['echeance'] ?? '')}
              </div>
              <div className="text-[11px] text-txt-dim">{fmt(i['surface_m2'])} m²</div>
            </div>
          )
          return idu ? (
            <Row key={i['id']} idu={idu} sub={sub} right={right}
              fiche={[['Parking APER', `${fmt(i['surface_m2'])} m² (${i['tranche']})`],
                ['Échéance', `${i['echeance']}${i['echeance_depassee'] ? ' — DÉPASSÉE' : ''}`],
                ['Propriétaire', sub]]} />
          ) : (
            <div key={i['id']} className="rounded-lg border border-line-2 bg-surface-3 px-3 py-2 text-[11px] text-txt-mut">
              {fmt(i['surface_m2'])} m² · {sub} <span className="float-right">{right}</span>
            </div>
          )
        })}
      </div>
    </>
  )
}

/* ─────────────── M24 — TOITURES TERTIAIRES (mandat Habitat Solaire, Lot 9.4) ─────────────── */

function M24() {
  const q = useQuery({ queryKey: ['m24'], queryFn: modSolaireTertiaire })
  const d = q.data as Record<string, any> | undefined
  const items = ((d?.['items'] ?? []) as Record<string, any>[])
  useModuleMap(items.map((i) => i['idu'] as string).filter(Boolean), null, [q.dataUpdatedAt])
  return (
    <>
      <Banner>Emprises bâties &gt; 500 m² (hors résidentiel) × propriétaire personne morale ×
        dernier bilan INPI × gisement PVGIS — triées par potentiel (surface × score).
        {d?.['note'] ? <> {String(d['note'])}</> : null}</Banner>
      <p className="text-[11px] text-txt-dim">
        {q.isFetching ? <Loading label="Chargement" /> : <>{fmt(d?.['total'])} toitures{typeof d?.['affiches'] === 'number' && d['affiches'] < d['total'] ? <span className="text-txt-dim"> · {fmt(d['affiches'])} affichées</span> : null}</>}
      </p>
      <a href="/solaire/tertiaire?fmt=csv" className="self-start rounded-lg border border-line-2 px-2.5 py-1 text-[11px] text-txt hover:text-txt-hi">⬇ Export CSV</a>
      <div className="flex min-h-0 flex-1 flex-col gap-1.5 overflow-y-auto">
        {items.map((i) => (
          <Row key={i['bat_id']} idu={i['idu'] as string}
            sub={`${i['commune']} · ${fmt(i['emprise_m2'])} m² · ${i['proprio_pm'] ?? 'PM non identifiée'}${i['ca'] != null ? ` · CA ${fmt(i['ca'])} €` : ''}`}
            right={<V>{i['score_solaire'] ?? '—'}</V>}
            fiche={[['Toiture', `${fmt(i['emprise_m2'])} m² (${i['usage'] ?? 'activité'})`],
              ['Propriétaire', `${i['proprio_pm'] ?? '—'}${i['proprio_siren'] ? ` (${i['proprio_siren']})` : ''}`],
              ['Bilan INPI', i['bilan_annee'] ? `${i['bilan_annee']} · CA ${fmt(i['ca'])} € · résultat ${fmt(i['resultat_net'])} €` : 'non disponible'],
              ['Gisement', i['prod_spec_kwh_kwc'] ? `${fmt(i['prod_spec_kwh_kwc'])} kWh/kWc/an (score ${i['score_solaire']})` : 'en cours']]} />
        ))}
      </div>
    </>
  )
}

/* ───────────────────────────── shell ───────────────────────────── */

const COMPONENTS: Record<string, () => JSX.Element> = {
  division: M01, patrimoine: M02, permis: M03, promesses: M04, velocite: M05,
  bailleur: M06, fantome: M07, temps: M08, courriers: M09, duediligence: M10,
  simulplu: M15, assemblage: M16, zan: M17, barometre: M18, matching: M19, programme: M22,
  'parkings-aper': M23, 'toitures-tertiaires': M24,
  'scoring-v2': ScoringV2Module,
}

export function ModulePanel() {
  const { module, setModule, toggleOutils } = useApp()
  const def = MODULES.find((m) => m.key === module)
  // M6.1 item 3 : Échap ferme le panneau (cohérent fiche/contexte). La fiche et les
  // tiroirs gardent la priorité : si l'un d'eux est ouvert, c'est LUI qu'Échap ferme.
  // Phase CAPTURE : il faut lire l'état AVANT que le handler de la fiche (bulle,
  // Fiche.tsx) ne fasse select(null) — sinon, fiche montée avant le panneau = un seul
  // Échap fermerait les deux d'un coup (zustand est synchrone).
  useEffect(() => {
    const h = (e: KeyboardEvent) => {
      if (e.key !== 'Escape') return
      const st = useApp.getState()
      if (st.selectedIdu || st.sourceLine || st.tool) return
      st.setModule(null)
    }
    window.addEventListener('keydown', h, true)
    return () => window.removeEventListener('keydown', h, true)
  }, [])
  if (!def) return null
  const Body = COMPONENTS[def.key]
  return (
    <aside className="flex h-full w-[320px] shrink-0 flex-col border-r border-line bg-surface-1">
      <div className="flex shrink-0 flex-col border-b border-[#2a2138] bg-[#171221] px-4 py-3">
        {/* M6.1 item 3 : retour direct au menu Outils (fil d'Ariane) — plus besoin de
            repasser par le rail pour changer d'outil. */}
        <div className="flex items-center justify-between gap-2">
          <nav data-module-breadcrumb className="flex min-w-0 items-center gap-1.5 font-mono text-[10px] tracking-widest">
            <button data-module-retour onClick={toggleOutils}
              className="shrink-0 rounded px-1 py-0.5 -mx-1 hover:bg-[#241c33]"
              style={{ color: VIOLET }} title="Revenir au menu Outils">
              ← OUTILS
            </button>
            <span className="text-txt-dim">›</span>
            <span className="truncate text-txt-mut">{def.label.toUpperCase()}</span>
          </nav>
          <button onClick={() => setModule(null)} className="shrink-0 text-txt-mut hover:text-txt-hi"
            title="Fermer le module (Échap)">✕</button>
        </div>
        <div className="mt-1">
          {/* P3 (revue Vic n°3) : plus de code M à l'écran — l'intitulé métier + le bénéfice */}
          <h2 className="text-sm font-medium text-txt-hi">{def.label}</h2>
          <p className="mt-0.5 text-[10.5px] leading-snug text-txt-dim">{def.desc}</p>
        </div>
      </div>
      <div className="flex min-h-0 flex-1 flex-col gap-2 overflow-hidden p-4">
        <Body />
      </div>
    </aside>
  )
}
