import { useMutation, useQuery } from '@tanstack/react-query'
import { useEffect, useMemo, useState } from 'react'
import {
  courrierDemande, modBailleur, modCourriers, modDivision, modDueDiligence, modFantome,
  modPatrimoine, modPatrimoineSearch, modPermis, modPermisFiche,
  modPromesses, modVelocite,
} from '../../lib/api'
import { fmtInt } from '../../lib/format'
import { pointInPolygon } from '../../lib/geo'
import { useApp } from '../../store/useApp'
import { Loading } from '../Loading'
import { M22 } from './M22Programme'
import { O5Servitudes, O6Comparateur, O7Carnet } from './blocB'
import { M15, M16, M17, M18, M19 } from './moteurs'
import { MODULES, VIOLET } from './registry'
import { ScoringV2Module } from './ScoringV2'
import { TierBadge } from './TierBadge'

/* ───────── primitives partagées (doctrine module : violet, bandeau honnête, liste→fiche) ───────── */

function Banner({ children }: { children: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-violet/40 bg-violet/[0.07] px-3 py-2 text-[10.5px] leading-relaxed text-txt-mut">
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
      className="flex w-full shrink-0 items-center gap-2 rounded-lg border border-line-2 bg-surface-3 px-3 py-2 text-left transition-colors duration-quick hover:border-violet/50"
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
  <span className="num-key text-sm text-violet">{children}</span>
)

const fmt = fmtInt

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
          onChange={(e) => setMinScore(Number(e.target.value))} className="flex-1 accent-violet" />
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
        className="rounded-lg border border-line-2 bg-surface-3 px-2 py-1.5 text-xs text-txt focus:border-violet focus:outline-none" />
      {!siren && (sug.data ?? []).map((s) => (
        <button key={s.siren} onClick={() => setSiren(s.siren)}
          className="flex items-center justify-between rounded-lg border border-line-2 bg-surface-3 px-3 py-1.5 text-left text-xs text-txt transition-colors duration-quick hover:border-violet/50">
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
            <div className="rounded-lg border border-st-ecartee/40 bg-st-ecartee/10 px-3 py-2 text-[11px] text-st-ecartee">
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
  const select = useApp((s) => s.select)      // Fix LOT 2 : localiser la parcelle du permis
  const setFlyTo = useApp((s) => s.setFlyTo)
  // géom du permis (centroïde parcelle) : présente ssi géocodé ; sinon on ne peut pas localiser.
  const geom = d?.['geom'] as { coordinates?: [number, number] } | null | undefined
  const parcelle = (d?.['parcelles'] as string[] | undefined)?.[0]
  const localiser = () => {
    if (!geom?.coordinates) return
    setFlyTo({ center: geom.coordinates, zoom: 18 })
    if (parcelle && parcelle.length === 14) select(parcelle)   // halo sur la parcelle rattachée
    onClose()
  }
  const F = ({ label, value }: { label: string; value: React.ReactNode }) =>
    value == null || value === '' ? null : (
      <div className="flex justify-between gap-3 border-b border-line py-1.5 text-[11px]">
        <span className="text-txt-dim">{label}</span>
        <span className="text-right text-txt">{value}</span>
      </div>
    )
  return (
    <div data-permis-drawer className="fixed inset-0 z-50 flex items-end justify-center bg-black/50 sm:items-center" onClick={onClose}>
      <div className="max-h-[80vh] w-full max-w-md overflow-y-auto rounded-t-2xl border border-violet/40 bg-surface-1 p-4 shadow-elev-3 sm:rounded-2xl"
        onClick={(e) => e.stopPropagation()}>
        {q.isLoading && <Loading />}
        {d && (
          <>
            <div className="mb-2 flex items-start justify-between gap-2">
              <div>
                <div className="font-display text-sm font-bold text-txt-hi">{d['nature_libelle']}</div>
                <div className="font-mono text-[11px] text-txt-mut">{d['permit_id']} · {d['commune']}</div>
              </div>
              <button onClick={onClose} aria-label="Fermer" className="flex h-7 w-7 items-center justify-center rounded-full border border-line-2 text-[11px] text-txt-mut transition-colors duration-quick hover:text-txt">✕</button>
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
              <F label="Délai d'instruction" value={<span className="font-semibold text-violet">{d['delai_instruction']['libelle']}</span>} />
            )}
            <F label="Parcelle(s)" value={<span className="font-mono text-[10px]">{(d['parcelles'] as string[]).join(', ')}</span>} />
            {/* Fix LOT 2 : localiser la parcelle sur la carte (géocodé) ou message clair (non géocodé) —
                jamais un clic mort. La géom d'un permis = centroïde de la parcelle rattachée. */}
            {geom?.coordinates ? (
              <button data-permis-localiser onClick={localiser}
                className="mt-3 flex w-full items-center justify-center gap-2 rounded-lg border border-violet/40 bg-violet/[0.08] py-2 text-[12px] font-medium text-violet transition-colors duration-quick hover:bg-violet/15">
                ◎ Voir la parcelle sur la carte
              </button>
            ) : (
              <div data-permis-nongeocode className="mt-3 rounded-lg border border-st-creuser/40 bg-st-creuser/10 px-3 py-2 text-[11px] leading-snug text-st-creuser">
                <b>Permis non géocodé</b> — son adresse n'a pas pu être rattachée à une parcelle du
                cadastre, il ne peut pas être localisé sur la carte.
              </div>
            )}
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
            className={`rounded-full border px-2.5 py-1 text-[11px] ${months === m ? 'border-violet text-violet' : 'border-line-2 text-txt-mut'}`}>
            {m} mois
          </button>
        ))}
        <span className="mx-1 self-center text-line-2">|</span>
        {NATURES.map(([v, l]) => (
          <button key={v} onClick={() => setNature(v)}
            className={`rounded-full border px-2.5 py-1 text-[11px] ${nature === v ? 'border-violet text-violet' : 'border-line-2 text-txt-mut'}`}>
            {l}
          </button>
        ))}
      </div>
      <p className="text-[11px] text-txt-dim">
        {zone ? `${items.length} permis dans la zone dessinée` : `${fmt(d?.['total'] as never)} permis${(d?.['affiches'] as number) < (d?.['total'] as number) ? ` · ${fmt(d?.['affiches'] as never)} affichés` : ''}`} · {geo.length} sur la carte
        {zone && <span className="text-violet/70"> · outil Zone actif</span>}
      </p>
      <div className="flex min-h-0 flex-1 flex-col gap-1 overflow-y-auto">
        {items.slice(0, 150).map((i, k) => (
          <button key={k} data-permis-row data-geocode={i['geom'] ? '1' : '0'} onClick={() => setOpen(i['permit_id'] as string)}
            className={`flex items-center gap-2 rounded-lg border border-line-2 px-3 py-1.5 text-left text-[11px] transition-colors duration-quick hover:border-violet/50 ${i['geom'] ? 'bg-surface-3' : 'bg-surface-1'}`}>
            <span className="font-mono text-txt">{i['type'] as string}</span>
            <span className="text-txt-mut">{i['date'] as string}</span>
            {i['delai_mois'] != null && <span style={{ color: VIOLET }}>{String(i['delai_mois'])} m</span>}
            {i['nb_lgt'] != null && <span className="text-txt-dim">{String(i['nb_lgt'])} lgt</span>}
            {!i['geom'] && <span className="ml-auto text-[11px] text-violet/70"
              title="Permis dont l'adresse n'a pas pu être rattachée à une parcelle du cadastre — non localisable sur la carte.">non géocodé</span>}
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
      {q.isLoading && <div className="flex flex-1 items-center justify-center py-8"><Loading accent="violet" label="Analyse en cours…" big /></div>}
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
        <div className="mt-1 text-violet/70">▲ {d?.['censure']}</div>
        <div className="mt-1 italic">{d?.['disclaimer']}</div>
      </Banner>
      <div className="flex flex-wrap gap-1.5">
        {NATURES.filter(([v]) => v).map(([v, l]) => (
          <button key={v} onClick={() => setNature(v)}
            className={`rounded-full border px-2.5 py-1 text-[11px] ${nature === v ? 'border-violet text-violet' : 'border-line-2 text-txt-mut'}`}>
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
            <button key={k} onClick={() => setSort(k)} className={`text-right transition-colors duration-quick ${sort === k ? 'text-violet' : ''}`}>{l} ↓</button>
          ))}
        </div>
        {rows.map((c) => {
          const rang = c['rang_delai'] as number | null
          // rapides (rang bas) en mint, lentes (rang haut) en rouge — repère visuel
          const rgColor = rang == null ? '#5C7268' : rang <= 5 ? '#5CE6A1' : rang >= 20 ? '#E8695A' : VIOLET
          const tend = c['tendance'] as string | null
          const tIcon = tend === 'accelere' ? '↓' : tend === 'ralentit' ? '↑' : tend === 'stable' ? '→' : ''
          const tColor = tend === 'accelere' ? '#5CE6A1' : tend === 'ralentit' ? '#E8695A' : '#5C7268'
          return (
            <div key={c['commune'] as string} className="grid grid-cols-[1fr_64px_60px] gap-1 border-b border-line py-1.5 text-[11px]"
              title={`${c['commune']} : rang ${rang ?? '—'}/24 par vélocité · délai médian ${natLabel} = ${c['delai_median_mois']} mois (IQR ${c['delai_p25_mois']}–${c['delai_p75_mois']}), sur ${c['n_mur']} dossiers mûrs. Tendance : ${tend ?? 'indéterminée (cohortes insuffisantes)'}.`}>
              <span className="flex min-w-0 items-center gap-1.5 truncate text-txt">
                {rang != null && <span className="shrink-0 font-mono text-[9px]" style={{ color: rgColor }}>#{rang}</span>}
                <span className="truncate">{c['commune'] as string}</span>
                {tIcon && <span className="shrink-0" style={{ color: tColor }} title={`Tendance ${tend}`}>{tIcon}</span>}
              </span>
              <span className="text-right font-mono" style={{ color: rgColor }}>{c['delai_median_mois'] == null ? '—' : `${c['delai_median_mois']} m`}</span>
              <span className="text-right font-mono text-txt-mut">{fmt(c['n_mur'] as number)}</span>
            </div>
          )
        })}
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
      {q.isLoading && <div className="flex flex-1 items-center justify-center py-8"><Loading accent="violet" label="Analyse en cours…" big /></div>}
      {/* Point 33 : contexte SRU (déficit logement social) — commune carencée = forte demande LLS */}
      {(d?.['sru'] as Record<string, any> | undefined) && (
        <div data-bailleur-sru className={`rounded-lg border px-3 py-2 text-[11px] ${d!['sru']['statut'] === 'carencee' ? 'border-st-creuser/50 bg-st-creuser/10' : 'border-line-2 bg-surface-2'}`}>
          <div className="flex items-center gap-2">
            <span className={`font-medium ${d!['sru']['statut'] === 'carencee' ? 'text-st-creuser' : 'text-txt'}`}>
              SRU {String(d!['sru']['statut'])}
            </span>
            <span className="text-txt-dim">· LLS {d!['sru']['taux_lls']}% / objectif {d!['sru']['objectif_pct']}%</span>
          </div>
          {d!['sru']['deficit_logements'] != null && (
            <div className="mt-1 text-txt-mut">Besoin estimé : <b className="tnum text-st-creuser">{fmt(d!['sru']['deficit_logements'] as number)}</b> logements sociaux pour atteindre l'objectif</div>
          )}
        </div>
      )}
      <p className="text-[11px] text-txt-dim">{fmt(d?.['total'] as never)} parcelles promues en QPV{(d?.['affiches'] as number) < (d?.['total'] as number) ? ` · ${fmt(d?.['affiches'] as never)} affichées` : ''}{d?.['n_communes_carencees'] ? ` · ${fmt(d['n_communes_carencees'] as number)} en communes carencées SRU` : ''}</p>
      <div className="flex min-h-0 flex-1 flex-col gap-1.5 overflow-y-auto">
        {items.map((i) => (
          <Row key={i['idu'] as string} idu={i['idu'] as string}
            sub={`${fmt(i['surface_m2'] as number)} m² · SDP ${fmt(i['sdp'] as number)} m²${i['carencee'] ? ' · SRU carencée' : ''}`}
            right={<TierBadge tier={i['tier_v2'] as string | null} etage0={i['etage0'] as boolean | null} statut={i['statut'] as string | null} />}
            fiche={[['Mode bailleur', 'Parcelle en QPV'], ['SRU commune', i['carencee'] ? 'Carencée — forte demande LLS' : '—'],
              ['Leviers LLS', 'TVA 2,1 % · abattement TFPB 30 %'], ['SDP résiduelle', `${fmt(i['sdp'] as number)} m²`]]} />
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
            fiche={[['▲ Gelé', String(i['verrou'])], ['Levier', String(i['levier'])],
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

// M09 — parcours GUIDÉ en 4 étapes (parcelle → motif → rédaction → demande). C'est une DEMANDE
// d'envoi (l'équipe LABUSE la traite), pas un envoi auto. Le brouillon est GROUNDÉ (faits réels de
// la parcelle, gabarit serveur) et ÉDITABLE. Privacy : adressage générique, aucun particulier nommé.
const MOTIFS: { key: string; label: string; desc: string }[] = [
  { key: 'standard', label: 'Approche standard', desc: 'prise de contact foncière' },
  { key: 'indivision', label: 'Indivision', desc: 'plusieurs co-indivisaires' },
  { key: 'succession', label: 'Succession', desc: 'bien en cours de succession' },
]

function M09() {
  const selectedIdu = useApp((s) => s.selectedIdu)
  const [step, setStep] = useState(1)
  const [idu, setIdu] = useState(selectedIdu ?? '')
  const [motif, setMotif] = useState('standard')
  const [texte, setTexte] = useState('')
  const [done, setDone] = useState<string | null>(null)
  const gen = useMutation({
    mutationFn: () => modCourriers([idu.trim()], motif),
    onSuccess: (d) => { setTexte(d.courriers[0]?.texte ?? d.courriers[0]?.erreur ?? ''); setStep(3) },
  })
  const envoi = useMutation({
    mutationFn: () => courrierDemande({ idu: idu.trim() || null, motif, texte }),
    onSuccess: (r) => setDone(r.message),
  })
  const Stepper = () => (
    <div className="flex items-center gap-1 text-[10px]">
      {['Parcelle', 'Motif', 'Rédaction', 'Demande'].map((l, i) => (
        <div key={l} className={`flex items-center gap-1 ${step === i + 1 ? 'text-violet' : step > i + 1 ? 'text-mint' : 'text-txt-dim'}`}>
          <span className={`flex h-4 w-4 items-center justify-center rounded-full border text-[9px] ${step === i + 1 ? 'border-violet' : step > i + 1 ? 'border-mint' : 'border-line-2'}`}>{step > i + 1 ? '✓' : i + 1}</span>
          {l}{i < 3 && <span className="text-txt-dim">›</span>}
        </div>
      ))}
    </div>
  )
  if (done) return (
    <>
      <Banner>Demande enregistrée.</Banner>
      <div data-courrier-done className="rounded-xl border border-mint/40 bg-mint/[0.06] p-4 text-center">
        <p className="font-display text-sm font-bold text-mint">✓ {done}</p>
        <button onClick={() => { setDone(null); setStep(1); setIdu(''); setTexte('') }}
          className="mt-3 text-[11px] text-txt-mut hover:text-txt">Nouvelle demande</button>
      </div>
    </>
  )
  return (
    <>
      <Banner>Demande d'envoi guidée — <b>pas un envoi automatique</b> : notre équipe la traite. Le
        courrier est <b>adressé génériquement</b> (aucune identité de propriétaire particulier utilisée ;
        identification via le workflow SPF/CERFA).</Banner>
      <Stepper />

      {step === 1 && (
        <div className="flex flex-col gap-2">
          <p className="text-[11px] text-txt-mut">Parcelle concernée (IDU) — ou sélectionnez-en une sur la carte.</p>
          <input data-courrier-idu value={idu} onChange={(e) => setIdu(e.target.value.trim())}
            placeholder="97415000CW0658"
            className="rounded-lg border border-line-2 bg-surface-3 px-2 py-1.5 font-mono text-[11px] text-txt focus:border-violet focus:outline-none" />
          {selectedIdu && selectedIdu !== idu && (
            <button onClick={() => setIdu(selectedIdu)} className="self-start text-[10.5px] text-violet hover:underline">utiliser la parcelle sélectionnée ({selectedIdu.slice(8)})</button>
          )}
          <button data-courrier-next onClick={() => idu.trim().length >= 10 && setStep(2)} disabled={idu.trim().length < 10}
            className="rounded-lg bg-violet py-1.5 text-xs font-medium text-bg transition-[filter] duration-quick hover:brightness-110 disabled:opacity-40">Suivant ›</button>
        </div>
      )}

      {step === 2 && (
        <div className="flex flex-col gap-2">
          <p className="text-[11px] text-txt-mut">Motif de l'approche :</p>
          {MOTIFS.map((m) => (
            <button key={m.key} data-courrier-motif={m.key} onClick={() => setMotif(m.key)}
              className={`rounded-lg border px-3 py-2 text-left ${motif === m.key ? 'border-violet bg-violet/[0.08]' : 'border-line-2 bg-surface-3'}`}>
              <div className="text-[11px] font-medium text-txt">{m.label}</div>
              <div className="text-[10.5px] text-txt-dim">{m.desc}</div>
            </button>
          ))}
          <div className="flex gap-2">
            <button onClick={() => setStep(1)} className="rounded-lg border border-line-2 px-3 py-1.5 text-[11px] text-txt-mut">‹ Retour</button>
            <button data-courrier-next onClick={() => gen.mutate()} disabled={gen.isPending}
              className="flex-1 rounded-lg bg-violet py-1.5 text-xs font-medium text-bg transition-[filter] duration-quick hover:brightness-110 disabled:opacity-40">
              {gen.isPending ? 'Rédaction…' : 'Rédiger le brouillon ›'}</button>
          </div>
        </div>
      )}

      {step === 3 && (
        <div className="flex min-h-0 flex-1 flex-col gap-2">
          <p className="text-[11px] text-txt-mut">Brouillon (faits réels de la parcelle) — <b>éditable</b> :</p>
          <textarea data-courrier-texte value={texte} onChange={(e) => setTexte(e.target.value)}
            className="min-h-[180px] flex-1 rounded-lg border border-line-2 bg-surface-3 px-2 py-1.5 text-[11px] leading-snug text-txt focus:border-violet focus:outline-none" />
          <div className="flex gap-2">
            <button onClick={() => setStep(2)} className="rounded-lg border border-line-2 px-3 py-1.5 text-[11px] text-txt-mut">‹ Retour</button>
            <button data-courrier-next onClick={() => setStep(4)} disabled={texte.trim().length < 10}
              className="flex-1 rounded-lg bg-violet py-1.5 text-xs font-medium text-bg transition-[filter] duration-quick hover:brightness-110 disabled:opacity-40">Prévisualiser ›</button>
          </div>
        </div>
      )}

      {step === 4 && (
        <div className="flex min-h-0 flex-1 flex-col gap-2">
          <p className="text-[11px] text-txt-mut">Aperçu — {MOTIFS.find((m) => m.key === motif)?.label} · {idu}</p>
          <div data-courrier-apercu className="min-h-0 flex-1 overflow-y-auto whitespace-pre-wrap rounded-lg border border-line-2 bg-surface-1 p-3 text-[11px] leading-snug text-txt">{texte}</div>
          <div className="flex gap-2">
            <button onClick={() => setStep(3)} className="rounded-lg border border-line-2 px-3 py-1.5 text-[11px] text-txt-mut">‹ Modifier</button>
            <button data-courrier-envoyer onClick={() => envoi.mutate()} disabled={envoi.isPending}
              className="flex-1 rounded-lg bg-violet py-1.5 text-xs font-medium text-bg transition-[filter] duration-quick hover:brightness-110 disabled:opacity-40">
              {envoi.isPending ? 'Envoi…' : 'Demander l\'envoi'}</button>
          </div>
        </div>
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
        className="rounded-lg border border-line-2 bg-surface-3 px-2 py-1.5 font-mono text-[10.5px] text-txt focus:border-violet focus:outline-none" />
      <button onClick={() => refs.trim() && run.mutate()} disabled={!refs.trim() || run.isPending}
        className="rounded-lg bg-violet py-1.5 text-xs font-medium text-bg transition-[filter] duration-quick hover:brightness-110 disabled:opacity-40">
        {run.isPending ? 'Analyse…' : 'Analyser le lot'}
      </button>
      {run.data && (
        <>
          <p className="text-[11px] text-txt-dim">{run.data.n_trouvees}/{run.data.n_demandes} références trouvées</p>
          <div className="flex min-h-0 flex-1 flex-col gap-1.5 overflow-y-auto">
            {items.map((i, k) => 'idu' in i ? (() => {
              const risque = i['risque'] as number
              const rColor = risque >= 100 ? '#E8695A' : risque >= 60 ? '#E8695A' : risque >= 30 ? '#E8B44C' : '#5CE6A1'
              const rLabel = risque >= 100 ? 'bloquant' : risque >= 60 ? 'élevé' : risque >= 30 ? 'modéré' : 'faible'
              const proprio = i['proprio'] as Record<string, any>
              const checklist = (i['checklist'] ?? []) as Record<string, any>[]
              return (
              <div key={k} data-diligence-item className="rounded-lg border border-line-2 bg-surface-3 px-3 py-2">
                <div className="flex items-center gap-2">
                  <Row idu={i['idu'] as string} sub={`${i['commune']} · ${fmt(i['surface_m2'] as number)} m²`}
                    right={<TierBadge tier={i['tier_v2'] as string | null} etage0={i['etage0'] as boolean | null} statut={i['statut'] as string | null} />} />
                </div>
                {/* Point 42 : score de risque consolidé (déterministe) */}
                <div className="mt-1.5 flex items-center gap-2 text-[11px]">
                  <span data-diligence-risque className="rounded-full px-2 py-0.5 font-medium" style={{ background: `${rColor}22`, color: rColor }}>risque {rLabel} · {risque}/100</span>
                  <span className="truncate text-txt-dim" title={proprio['type'] === 'personne_morale' ? `SIREN ${proprio['siren'] ?? '—'}` : 'propriétaire personne physique — non communiqué'}>
                    {proprio['type'] === 'personne_morale' ? proprio['denomination'] : 'propriétaire particulier'}
                  </span>
                </div>
                {/* checklist — points à vérifier avant achat (facteurs cascade existants) */}
                {checklist.length > 0 && (
                  <div className="mt-1.5 flex flex-col gap-0.5">
                    {checklist.slice(0, 5).map((c, ci) => (
                      <div key={ci} className="flex gap-1.5 text-[10.5px] leading-snug">
                        <span style={{ color: c['result'] === 'HARD_EXCLUDE' ? '#E8695A' : c['severity'] === 'fort' ? '#E8B44C' : '#8FA69A' }}>
                          {c['result'] === 'HARD_EXCLUDE' ? '✕' : '☐'}</span>
                        <span className="text-txt-mut"><b className="text-txt">{c['layer']}</b> — {c['detail']}</span>
                      </div>
                    ))}
                    {checklist.length === 0 && <span className="text-[10.5px] text-mint">✓ aucun point de vigilance</span>}
                  </div>
                )}
                {checklist.length === 0 && <p className="mt-1.5 text-[10.5px] text-mint">✓ aucun point de vigilance cascade</p>}
                <a href={i['pdf'] as string} target="_blank" rel="noreferrer" className="mt-1 inline-block text-[10.5px] text-violet/70 transition-colors duration-quick hover:text-violet hover:underline">⬇ PDF</a>
              </div>
              )})() : (
              <div key={k} className="rounded-lg border border-st-ecartee/40 bg-st-ecartee/10 px-3 py-2 text-[11px] text-st-ecartee">
                {i['ref'] as string} — {i['erreur'] as string}
              </div>
            ))}
          </div>
        </>
      )}
    </>
  )
}


const COMPONENTS: Record<string, () => JSX.Element> = {
  division: M01, patrimoine: M02, permis: M03, promesses: M04, velocite: M05,
  bailleur: M06, fantome: M07, temps: M08, courriers: M09, duediligence: M10,
  simulplu: M15, assemblage: M16, zan: M17, barometre: M18, matching: M19, programme: M22,
  'scoring-v2': ScoringV2Module,
  'o5-servitudes': O5Servitudes,
  'o6-comparateur': O6Comparateur,
  'o7-carnet': O7Carnet,
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
      <div className="flex shrink-0 flex-col border-b border-violet/20 bg-violet/[0.07] px-4 py-3">
        {/* M6.1 item 3 : retour direct au menu Outils (fil d'Ariane) — plus besoin de
            repasser par le rail pour changer d'outil. */}
        <div className="flex items-center justify-between gap-2">
          <nav data-module-breadcrumb className="flex min-w-0 items-center gap-2 font-mono text-[10px] tracking-widest">
            {/* Fix cosmétique (point 27) : flèche retour PLUS VISIBLE — pastille bordée mauve, plus
                grosse, zone de clic élargie + libellé « ← Outils » clair (avant : 10 px inline, on la cherchait). */}
            <button data-module-retour onClick={toggleOutils}
              className="flex shrink-0 items-center gap-1 rounded-md border border-violet/40 bg-violet/10 px-2.5 py-1 text-[11px] font-semibold tracking-wide text-violet transition-colors duration-quick hover:border-violet hover:bg-violet/15"
              title="Revenir au menu Outils">
              ← Outils
            </button>
            <span className="text-txt-dim">›</span>
            <span className="truncate text-txt-mut">{def.label.toUpperCase()}</span>
          </nav>
          <button onClick={() => setModule(null)} aria-label="Fermer le module"
            className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md text-txt-mut transition-colors duration-quick hover:bg-violet/10 hover:text-txt-hi"
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
