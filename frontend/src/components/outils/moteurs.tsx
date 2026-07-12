import { useMutation, useQuery } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { addProfile, getProfiles, motAssemblage, motBarometre, motSimulPlu, motSimulPluZones, motZan, runMatch } from '../../lib/api'
import { useApp } from '../../store/useApp'
import { VIOLET } from './registry'
import { TierBadge } from './TierBadge'

const fmt = (n: number | null | undefined) => (n == null ? '—' : Math.round(Number(n)).toLocaleString('fr-FR'))

function Banner({ children }: { children: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-[#4a3d6b] bg-[#1a1526] px-3 py-2 text-[10.5px] leading-relaxed text-[#b8a8de]">
      {children}
    </div>
  )
}

/* ───────────── M15 — SIMULATEUR PLU ───────────── */

export function M15() {
  const commune = useApp((s) => s.commune)
  const zones = useQuery({ queryKey: ['m15z', commune], queryFn: motSimulPluZones })
  const [zone, setZone] = useState<string | null>(null)
  const sim = useQuery({ queryKey: ['m15', zone, commune], queryFn: () => motSimulPlu(zone!), enabled: !!zone })
  const { setModuleMap } = useApp()
  const d = sim.data
  useEffect(() => {
    const items = (d?.items ?? []) as Record<string, any>[]
    setModuleMap({ idus: items.filter((i) => i.bascule_potentielle).map((i) => i.idu), extra: null })
    return () => setModuleMap({ idus: [], extra: null })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sim.dataUpdatedAt])
  return (
    <>
      <Banner>Recalcul <b>à blanc</b> — rien n'est persisté. SDP estimée par <b>analogie</b> aux
        parcelles U de la commune (méthode affichée). Le vrai recalcul règlementaire = prochain cycle.</Banner>
      <div className="flex flex-wrap gap-1.5">
        {(zones.data ?? []).map((z) => (
          <button key={z.zone} onClick={() => setZone(z.zone)}
            className={`rounded-full border px-2.5 py-1 text-[11px] ${zone === z.zone ? 'border-[#B497F0] text-[#B497F0]' : 'border-line-2 text-txt-mut'}`}>
            {z.zone} → U
          </button>
        ))}
      </div>
      {d && (
        <>
          <div className="rounded-lg border border-line-2 bg-surface-2 px-3 py-2 text-[11px] text-txt-mut">
            <div><b className="text-txt">{fmt(d.n_parcelles)}</b> parcelles en {d.zone} · ratio analogie <b className="text-txt">{d.ratio_analogie}</b></div>
            <div className="mt-1">SDP estimée totale <b style={{ color: VIOLET }}>{fmt(d.sdp_totale_estimee_m2)} m²</b> ·{' '}
              <b style={{ color: VIOLET }}>{fmt(d.bascules_potentielles)}</b> bascules potentielles (surlignées)</div>
          </div>
          <div className="flex min-h-0 flex-1 flex-col gap-1 overflow-y-auto">
            {(d.items as Record<string, any>[]).slice(0, 120).map((i) => (
              <div key={i.idu} className="flex items-center gap-2 rounded-lg border border-line-2 bg-surface-3 px-3 py-1.5 text-[11px]">
                <span className="font-mono text-txt-hi">{i.idu.slice(8)}</span>
                <span className="text-txt-dim">{fmt(i.surface_m2)} m²</span>
                <span className="ml-auto" style={{ color: i.bascule_potentielle ? VIOLET : '#5C7268' }}>
                  SDP est. {fmt(i.sdp_estimee_m2)} m²{i.bascule_potentielle ? ' ▲' : ''}
                </span>
              </div>
            ))}
          </div>
        </>
      )}
    </>
  )
}

/* ───────────── M16 — ASSEMBLAGE ───────────── */

export function M16() {
  const { msel, setMsel, setModuleMap } = useApp()
  const run = useMutation({ mutationFn: () => motAssemblage(msel) })
  useEffect(() => {
    setModuleMap({ idus: msel, extra: null })
    return () => setModuleMap({ idus: [], extra: null })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [msel])
  const d = run.data
  return (
    <>
      <Banner><b>Cliquez les parcelles sur la carte</b> pour composer l'assiette (re-cliquer retire).
        SDP cumulée = somme des résiduels — le <b>règlement d'ensemble reste à instruire</b>.</Banner>
      <div className="flex flex-wrap gap-1">
        {msel.map((i) => (
          <button key={i} onClick={() => setMsel(msel.filter((x) => x !== i))}
            className="rounded-full border border-[#6b5a96] px-2 py-0.5 font-mono text-[11px] text-[#B497F0]"
            title="Retirer de la sélection">
            {i.slice(8)} ×
          </button>
        ))}
        {msel.length === 0 && <span className="text-[11px] text-txt-dim">aucune parcelle sélectionnée</span>}
      </div>
      <div className="flex gap-2">
        <button onClick={() => msel.length >= 2 && run.mutate()} disabled={msel.length < 2 || run.isPending}
          className="flex-1 rounded-lg py-1.5 text-xs font-medium text-[#120d1d] disabled:opacity-40" style={{ background: VIOLET }}>
          Analyser l'assiette ({msel.length})
        </button>
        {msel.length > 0 && (
          <button onClick={() => setMsel([])} className="rounded-lg border border-line-2 px-2 text-[11px] text-txt-dim hover:text-txt">vider</button>
        )}
      </div>
      {run.isError && <p className="text-[11px] text-st-ecartee">Erreur — au moins 2 parcelles valides ?</p>}
      {d && (
        <>
          <div className="rounded-lg border border-line-2 bg-surface-2 px-3 py-2 text-[11px]">
            <div className="flex items-center gap-2">
              <span className="font-display text-lg font-bold" style={{ color: VIOLET }}>{d.score_assemblage}</span>
              <span className="text-txt-mut">score d'assemblage</span>
              <span className={`ml-auto rounded-full px-2 py-0.5 text-[11px] ${d.contigu ? 'bg-[#0F1A14] text-mint' : 'bg-[#3a1614] text-st-ecartee'}`}>
                {d.contigu ? "d'un seul tenant" : 'NON contiguë'}
              </span>
            </div>
            <div className="mt-1.5 text-txt-mut">
              {fmt(d.surface_totale_m2)} m² cumulés · SDP <b style={{ color: VIOLET }}>{fmt(d.sdp_cumulee_m2)} m²</b> ·{' '}
              {d.n_proprietaires} propriétaire{d.n_proprietaires > 1 ? 's' : ''}
            </div>
            <div className="mt-1 text-[11px] text-txt-dim">{d.note_sdp}</div>
          </div>
          <div className="flex min-h-0 flex-1 flex-col gap-1 overflow-y-auto">
            {(d.items as Record<string, any>[]).map((i) => (
              <div key={i.idu} className="rounded-lg border border-line-2 bg-surface-3 px-3 py-1.5 text-[11px]">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-txt-hi">{i.idu.slice(8)}</span>
                  <span className="text-txt-dim">{fmt(i.surface_m2)} m² · SDP {fmt(i.sdp_residuelle_m2)}</span>
                  <span className="ml-auto">
                    <TierBadge tier={i.tier_v2 as string | null} etage0={i.etage0 as boolean | null} statut={i.statut as string | null} />
                  </span>
                </div>
                <div className="truncate text-[11px] text-txt-dim">{i.proprietaire}</div>
              </div>
            ))}
          </div>
        </>
      )}
    </>
  )
}

/* ───────────── M17 — ZAN ───────────── */

export function M17() {
  const q = useQuery({ queryKey: ['m17'], queryFn: motZan })
  const { setModuleMap, select } = useApp()
  const d = q.data
  useEffect(() => {
    const items = (d?.zan_compatibles ?? []) as Record<string, any>[]
    setModuleMap({ idus: items.map((i) => i.idu), extra: null })
    return () => setModuleMap({ idus: [], extra: null })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [q.dataUpdatedAt])
  return (
    <>
      <Banner>{d?.bandeau ?? '…'}</Banner>
      <p className="font-mono text-[10px] tracking-widest text-txt-dim">ARTIFICIALISATION (OCS GE, île)</p>
      <div className="flex max-h-40 shrink-0 flex-col overflow-y-auto">
        {((d?.communes ?? []) as Record<string, any>[]).slice(0, 12).map((c) => (
          <div key={c.commune} className="flex items-center gap-2 border-b border-[#141d17] py-1 text-[11px]">
            <span className="min-w-0 flex-1 truncate text-txt">{c.commune}</span>
            <span className="font-mono text-txt-dim">{fmt(c.ilots_artif)} îlots artif.</span>
            <span className="font-mono" style={{ color: VIOLET }}>
              {c.ha_couverts ? Math.round((100 * (c.ha_artif ?? 0)) / c.ha_couverts) : '—'} %
            </span>
          </div>
        ))}
      </div>
      <p className="text-[11px] text-txt-dim">{fmt((d?.zan_compatibles ?? []).length)} parcelles ZAN-compatibles promues (surlignées)</p>
      <div className="flex min-h-0 flex-1 flex-col gap-1 overflow-y-auto">
        {((d?.zan_compatibles ?? []) as Record<string, any>[]).map((i) => (
          <button key={i.idu} onClick={() => select(i.idu)}
            className="flex items-center gap-2 rounded-lg border border-line-2 bg-surface-3 px-3 py-1.5 text-left text-[11px] hover:border-[#6b5a96]">
            <span className="font-mono text-txt-hi">{i.idu.slice(8)}</span>
            <span className="text-txt-dim">{fmt(i.surface_m2)} m²</span>
            <span className="ml-auto">
              <TierBadge tier={i.tier_v2 as string | null} etage0={i.etage0 as boolean | null} statut={i.statut as string | null} />
            </span>
          </button>
        ))}
      </div>
    </>
  )
}

/* ───────────── M18 — BAROMÈTRE ───────────── */

export function M18() {
  const q = useQuery({ queryKey: ['m18'], queryFn: motBarometre })
  const d = q.data
  const max = Math.max(1, ...((d?.dvf_trimestres ?? []) as Record<string, any>[]).map((r) => Number(r.mutations)))
  return (
    <>
      <Banner>Île entière (DVF 24 communes, Sitadel régional). Le PDF est le rapport
        distribuable — canal marketing.</Banner>
      <a href="/moteurs/barometre.pdf" target="_blank" rel="noreferrer"
        className="self-start rounded-lg px-3 py-1.5 text-xs font-medium text-[#120d1d]" style={{ background: VIOLET }}>
        ⬇ Rapport PDF
      </a>
      <p className="font-mono text-[10px] tracking-widest text-txt-dim">DVF PAR TRIMESTRE</p>
      <div className="flex shrink-0 flex-col gap-1">
        {((d?.dvf_trimestres ?? []) as Record<string, any>[]).map((r) => (
          <div key={r.trimestre} className="flex items-center gap-2 text-[11px]">
            <span className="w-14 font-mono text-txt-dim">{r.trimestre}</span>
            <span className="relative h-2.5 min-w-0 flex-1 overflow-hidden rounded-full bg-line">
              <span className="absolute left-0 top-0 h-full rounded-full" style={{ width: `${(100 * r.mutations) / max}%`, background: VIOLET }} />
            </span>
            <span className="w-12 text-right font-mono text-txt-mut">{fmt(r.mutations)}</span>
            <span className="w-20 text-right font-mono text-txt-dim">{fmt(r.median_eur_m2_bati)} €/m²</span>
          </div>
        ))}
      </div>
      <p className="mt-1 font-mono text-[10px] tracking-widest text-txt-dim">PRIX PAR COMMUNE (TOP)</p>
      <div className="flex min-h-0 flex-1 flex-col overflow-y-auto">
        {((d?.top_communes_prix ?? []) as Record<string, any>[]).map((r) => (
          <div key={r.commune} className="flex items-center gap-2 border-b border-[#141d17] py-1 text-[11px]">
            <span className="min-w-0 flex-1 truncate text-txt">{r.commune}</span>
            <span className="font-mono text-txt-dim">{fmt(r.mutations)} mut.</span>
            <span className="font-mono" style={{ color: VIOLET }}>{fmt(r.median_eur_m2)} €/m²</span>
          </div>
        ))}
      </div>
    </>
  )
}


/* ───────────── M19 — MATCHING TERRAIN ↔ PROMOTEUR ───────────── */

export function M19() {
  const profiles = useQuery({ queryKey: ['m19'], queryFn: getProfiles })
  const [nom, setNom] = useState('')
  const [smin, setSmin] = useState('')
  const add = useMutation({ mutationFn: () => addProfile({ nom, surface_min: smin ? Number(smin) : null }),
    onSuccess: () => { setNom(''); profiles.refetch() } })
  const match = useMutation({ mutationFn: runMatch })
  return (
    <>
      <Banner>Profils de recherche enregistrés — quand une parcelle <b>bascule chaude</b> et matche,
        l'alerte apparaît dans la cloche (M11). Les deux profils fournis sont des <b>démos étiquetées</b>.</Banner>
      <div className="flex min-h-0 flex-col gap-1.5 overflow-y-auto">
        {((profiles.data ?? []) as Record<string, any>[]).map((p) => (
          <div key={p.id} className="rounded-lg border border-line-2 bg-surface-3 px-3 py-2 text-[11px]">
            <div className="flex items-center gap-2">
              <span className="text-txt">{p.nom}</span>
              {p.demo && <span className="rounded-full bg-[#2a2138] px-1.5 py-0.5 text-[8.5px] text-[#B497F0]">DÉMO</span>}
            </div>
            <div className="mt-0.5 text-[11px] text-txt-dim">
              {p.commune ?? 'toute commune'} · surface {p.surface_min ?? '—'}–{p.surface_max ?? '—'} m² · SDP ≥ {p.sdp_min ?? '—'}
            </div>
          </div>
        ))}
      </div>
      <div className="flex gap-1.5">
        <input value={nom} onChange={(e) => setNom(e.target.value)} placeholder="Nom du profil…"
          className="min-w-0 flex-1 rounded border border-line-2 bg-surface-3 px-2 py-1 text-[11px] text-txt focus:border-[#B497F0] focus:outline-none" />
        <input value={smin} onChange={(e) => setSmin(e.target.value)} placeholder="surf. min" type="number"
          className="w-20 rounded border border-line-2 bg-surface-3 px-2 py-1 text-[11px] text-txt focus:border-[#B497F0] focus:outline-none" />
        <button onClick={() => nom.trim() && add.mutate()} disabled={!nom.trim()}
          className="rounded px-2 text-[11px] font-medium text-[#120d1d] disabled:opacity-40" style={{ background: VIOLET }}>+</button>
      </div>
      <button onClick={() => match.mutate()} disabled={match.isPending}
        className="rounded-lg border border-line-2 py-1.5 text-[11px] text-txt hover:text-txt-hi">
        {match.isPending ? '…' : 'Tester le matching maintenant'}
      </button>
      {match.data && <p className="text-[11px]" style={{ color: VIOLET }}>✓ {match.data.matches} match(s) émis → voir la cloche</p>}
    </>
  )
}
