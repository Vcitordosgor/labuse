import { useMutation, useQuery } from '@tanstack/react-query'
import { useEffect, useMemo, useState } from 'react'
import {
  getPipeline, modBailleur, modCourriers, modDivision, modDueDiligence, modFantome,
  modPatrimoine, modPatrimoineSearch, modPermis, modPromesses, modVelocite,
} from '../../lib/api'
import { pointInPolygon } from '../../lib/geo'
import { STATUT_META } from '../../lib/status'
import { useApp } from '../../store/useApp'
import { M22 } from './M22Programme'
import { M15, M16, M17, M18, M19 } from './moteurs'
import { MODULES, VIOLET } from './registry'

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
  const q = useQuery({ queryKey: ['m01', minScore], queryFn: () => modDivision(minScore) })
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
      <p className="text-[11px] text-txt-dim">{fmt(q.data?.total)} candidats (SQL)</p>
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
  const [q, setQ] = useState('')
  const [siren, setSiren] = useState<string | null>(null)
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
          <span className="truncate">{s.nom}</span><span className="font-mono text-[10px] text-txt-dim">{s.n} parc.</span>
        </button>
      ))}
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
                right={i['statut'] ? <span className="text-[10px]" style={{ color: STATUT_META[i['statut'] as keyof typeof STATUT_META]?.color }}>{STATUT_META[i['statut'] as keyof typeof STATUT_META]?.label}</span> : <span className="text-[10px] text-txt-dim">hors run</span>}
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

function M03() {
  const [months, setMonths] = useState(24)
  const zone = useApp((s) => s.zone)
  const q = useQuery({ queryKey: ['m03', months], queryFn: () => modPermis(months) })
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
        Données jusqu'au <b>{String(d?.['donnees_jusqu_au'] ?? '…')}</b> (flux Sitadel régional).</Banner>
      <div className="flex gap-1.5">
        {[12, 24, 48, 72].map((m) => (
          <button key={m} onClick={() => setMonths(m)}
            className={`rounded-full border px-2.5 py-1 text-[11px] ${months === m ? 'border-[#B497F0] text-[#B497F0]' : 'border-line-2 text-txt-mut'}`}>
            {m} mois
          </button>
        ))}
      </div>
      <p className="text-[11px] text-txt-dim">
        {zone ? `${items.length} permis dans la zone dessinée` : `${fmt(d?.['total'] as never)} permis`} · {geo.length} sur la carte
        {zone && <span className="text-[#8b76c0]"> · outil Zone actif</span>}
      </p>
      <div className="flex min-h-0 flex-1 flex-col gap-1 overflow-y-auto">
        {items.slice(0, 150).map((i, k) => (
          <div key={k} className={`flex items-center gap-2 rounded-lg border border-line-2 px-3 py-1.5 text-[11px] ${i['geom'] ? 'bg-surface-3' : 'bg-[#141019]'}`}>
            <span className="font-mono text-txt">{i['type'] as string}</span>
            <span className="text-txt-mut">{i['date'] as string}</span>
            <span className="text-txt-dim">état {i['etat'] as string}</span>
            {i['nb_lgt'] != null && <span className="text-txt-dim">{String(i['nb_lgt'])} lgt</span>}
            {!i['geom'] && <span className="ml-auto text-[9.5px] text-[#8b76c0]">non géocodé</span>}
          </div>
        ))}
      </div>
    </>
  )
}

/* ───────────────────────────── M04 — PROMESSES MORTES ───────────────────────────── */

function M04() {
  const [months, setMonths] = useState(24)
  const q = useQuery({ queryKey: ['m04', months], queryFn: () => modPromesses(months) })
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
      <p className="text-[11px] text-txt-dim">{fmt(d?.['total'] as never)} promesses mortes</p>
      <div className="flex min-h-0 flex-1 flex-col gap-1.5 overflow-y-auto">
        {items.map((i, k) => (
          <Row key={k} idu={i['idu'] as string}
            sub={`PC ${i['date']} · ${fmt(i['surface_m2'] as number)} m² · état ${i['etat']}`}
            right={<span className="text-[10px]" style={{ color: STATUT_META[i['statut'] as keyof typeof STATUT_META]?.color }}>{STATUT_META[i['statut'] as keyof typeof STATUT_META]?.label}</span>}
            fiche={[['Permis', `${i['permit_id']} (${i['date']})`], ['État source', `code ${i['etat']} — sans achèvement déclaré`],
              ['Lecture', 'PC ancien jamais réalisé — réalisation à vérifier']]} />
        ))}
      </div>
    </>
  )
}

/* ───────────────────────────── M05 — VÉLOCITÉ ADMIN ───────────────────────────── */

function M05() {
  const q = useQuery({ queryKey: ['m05'], queryFn: modVelocite })
  const [sort, setSort] = useState<'permis' | 'delai_median_mois' | 'pct_acheves'>('permis')
  const rows = useMemo(() => ([...(q.data?.communes ?? [])] as Record<string, any>[]).sort((a, b) => Number(b[sort] ?? 0) - Number(a[sort] ?? 0)), [q.data, sort])
  return (
    <>
      <Banner>{q.data?.note ?? '…'} — la source ne porte pas les dates de dépôt/décision.</Banner>
      <a href="/modules/velocite?fmt=csv" className="self-start rounded-lg border border-line-2 px-2.5 py-1 text-[11px] text-txt hover:text-txt-hi">
        ⬇ Export CSV
      </a>
      <div className="flex min-h-0 flex-1 flex-col overflow-y-auto">
        <div className="sticky top-0 grid grid-cols-[1fr_54px_58px_54px] gap-1 bg-surface-1 py-1 text-[9.5px] tracking-wide text-txt-dim">
          <span>COMMUNE (ÎLE)</span>
          {([['permis', 'PERMIS'], ['delai_median_mois', 'DÉLAI*'], ['pct_acheves', 'ACHEV.']] as const).map(([k, l]) => (
            <button key={k} onClick={() => setSort(k)} className={`text-right ${sort === k ? 'text-[#B497F0]' : ''}`}>{l} ↓</button>
          ))}
        </div>
        {rows.map((c) => (
          <div key={c['commune'] as string} className="grid grid-cols-[1fr_54px_58px_54px] gap-1 border-b border-[#141d17] py-1.5 text-[11px]">
            <span className="truncate text-txt">{c['commune'] as string}</span>
            <span className="text-right font-mono text-txt-mut">{fmt(c['permis'] as number)}</span>
            <span className="text-right font-mono" style={{ color: VIOLET }}>{c['delai_median_mois'] == null ? '—' : `${c['delai_median_mois']} m`}</span>
            <span className="text-right font-mono text-txt-mut">{String(c['pct_acheves'])}%</span>
          </div>
        ))}
        <p className="py-2 text-[9.5px] text-txt-dim">* médiane permis → déclaration d'achèvement (DAACT)</p>
      </div>
    </>
  )
}

/* ───────────────────────────── M06 — MODE BAILLEUR ───────────────────────────── */

function M06() {
  const q = useQuery({ queryKey: ['m06'], queryFn: modBailleur })
  const d = q.data as Record<string, any> | undefined
  const items = ((d?.['items'] ?? []) as Record<string, any>[])
  useModuleMap(items.map((i) => i['idu'] as string), null, [q.dataUpdatedAt])
  return (
    <>
      <Banner>{String(d?.['lecture_lls'] ?? '…')}</Banner>
      <p className="text-[11px] text-txt-dim">{fmt(d?.['total'] as never)} parcelles promues en QPV</p>
      <div className="flex min-h-0 flex-1 flex-col gap-1.5 overflow-y-auto">
        {items.map((i) => (
          <Row key={i['idu'] as string} idu={i['idu'] as string}
            sub={`${fmt(i['surface_m2'] as number)} m² · SDP ${fmt(i['sdp'] as number)} m²`}
            right={<span className="text-[10px]" style={{ color: STATUT_META[i['statut'] as keyof typeof STATUT_META]?.color }}>{STATUT_META[i['statut'] as keyof typeof STATUT_META]?.label}</span>}
            fiche={[['Mode bailleur', 'Parcelle en QPV'], ['Leviers LLS', 'TVA 2,1 % · abattement TFPB 30 %'],
              ['SDP résiduelle', `${fmt(i['sdp'] as number)} m²`]]} />
        ))}
      </div>
    </>
  )
}

/* ───────────────────────────── M07 — FONCIER FANTÔME ───────────────────────────── */

function M07() {
  const q = useQuery({ queryKey: ['m07'], queryFn: modFantome })
  const d = q.data as Record<string, any> | undefined
  const items = ((d?.['items'] ?? []) as Record<string, any>[])
  useModuleMap(items.map((i) => i['idu'] as string), null, [q.dataUpdatedAt])
  return (
    <>
      <Banner>Constructible (Q ≥ 50) mais <b>verrouillé</b> : personne morale introuvable au RNE ou
        dirigeant inactif. Levier indiqué par cas — vérification notariale indispensable.</Banner>
      <p className="text-[11px] text-txt-dim">{fmt(d?.['total'] as never)} parcelles gelées</p>
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
                <div className="mt-1 line-clamp-3 whitespace-pre-wrap text-[10px] leading-snug text-txt-mut">{c.texte ?? c.erreur}</div>
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
                    right={<span className="text-[10px]" style={{ color: STATUT_META[i['statut'] as keyof typeof STATUT_META]?.color ?? '#5C7268' }}>{STATUT_META[i['statut'] as keyof typeof STATUT_META]?.label ?? 'hors run'}</span>} />
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

/* ───────────────────────────── shell ───────────────────────────── */

const COMPONENTS: Record<string, () => JSX.Element> = {
  division: M01, patrimoine: M02, permis: M03, promesses: M04, velocite: M05,
  bailleur: M06, fantome: M07, temps: M08, courriers: M09, duediligence: M10,
  simulplu: M15, assemblage: M16, zan: M17, barometre: M18, matching: M19, programme: M22,
}

export function ModulePanel() {
  const { module, setModule } = useApp()
  const def = MODULES.find((m) => m.key === module)
  if (!def) return null
  const Body = COMPONENTS[def.key]
  return (
    <aside className="flex h-full w-[320px] shrink-0 flex-col border-r border-line bg-surface-1">
      <div className="flex shrink-0 items-start justify-between border-b border-[#2a2138] bg-[#171221] px-4 py-3">
        <div>
          <span className="font-mono text-[10px] tracking-widest" style={{ color: VIOLET }}>{def.num} · MODULE</span>
          <h2 className="text-sm font-medium text-txt-hi">{def.label}</h2>
        </div>
        <button onClick={() => setModule(null)} className="text-txt-mut hover:text-txt-hi" title="Fermer le module">✕</button>
      </div>
      <div className="flex min-h-0 flex-1 flex-col gap-2 overflow-hidden p-4">
        <Body />
      </div>
    </aside>
  )
}
