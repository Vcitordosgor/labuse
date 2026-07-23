import { useMutation, useQuery } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { addProfile, getProfiles, matchCompatibilite, motAssemblage, motBarometre, motSimulPlu, motSimulPluZones, motZan, promoteursActifs, runMatch, zanParcelle } from '../../lib/api'
import { fmtInt } from '../../lib/format'
import { TOKENS } from '../../lib/tokens'
import { useApp } from '../../store/useApp'
import { Loading } from '../Loading'
import { TierBadge } from './TierBadge'

const fmt = fmtInt

function Banner({ children }: { children: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-violet/40 bg-violet/[0.07] px-3 py-2 text-[10.5px] leading-relaxed text-txt-mut">
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
  const { setModuleMap, select } = useApp()   // fix : la liste était inerte (select non branché)
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
            className={`rounded-full border px-2.5 py-1 text-[11px] ${zone === z.zone ? 'border-violet text-violet' : 'border-line-2 text-txt-mut'}`}>
            {z.zone} → U
          </button>
        ))}
      </div>
      {sim.isLoading && <div className="flex flex-1 items-center justify-center py-8"><Loading accent="violet" label="Recalcul à blanc en cours…" big /></div>}
      {d && (
        <>
          <div className="rounded-lg border border-line-2 bg-surface-2 px-3 py-2 text-[11px] text-txt-mut">
            <div><b className="text-txt">{fmt(d.n_parcelles)}</b> parcelles en {d.zone} · ratio analogie <b className="text-txt">{d.ratio_analogie}</b></div>
            <div className="mt-1">SDP estimée totale <b className="tnum text-violet">{fmt(d.sdp_totale_estimee_m2)} m²</b> ·{' '}
              <b className="tnum text-violet">{fmt(d.bascules_potentielles)}</b> bascules potentielles (surlignées)</div>
          </div>
          <div className="flex min-h-0 flex-1 flex-col gap-1 overflow-y-auto">
            {(d.items as Record<string, any>[]).slice(0, 120).map((i) => (
              <button key={i.idu} data-m15-item onClick={() => select(i.idu)}
                title="Ouvrir la parcelle"
                className="flex items-center gap-2 rounded-lg border border-line-2 bg-surface-3 px-3 py-1.5 text-left text-[11px] transition-colors duration-quick hover:border-violet/60">
                <span className="font-mono text-txt-hi">{i.idu.slice(8)}</span>
                <span className="text-txt-dim">{fmt(i.surface_m2)} m²</span>
                <span className={`ml-auto tnum ${i.bascule_potentielle ? 'text-violet' : 'text-txt-dim'}`}>
                  SDP est. {fmt(i.sdp_estimee_m2)} m²{i.bascule_potentielle ? ' ▲' : ''}
                </span>
              </button>
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
            className="min-h-7 rounded-full border border-violet/60 px-2 py-0.5 font-mono text-[11px] text-violet transition-colors duration-quick hover:bg-violet/10"
            title="Retirer de la sélection">
            {i.slice(8)} ×
          </button>
        ))}
        {msel.length === 0 && <span className="text-[11px] text-txt-dim">aucune parcelle sélectionnée</span>}
      </div>
      <div className="flex gap-2">
        <button onClick={() => msel.length >= 2 && run.mutate()} disabled={msel.length < 2 || run.isPending}
          className="flex-1 rounded-lg bg-violet py-1.5 text-xs font-medium text-bg transition-[filter] duration-quick hover:brightness-110 disabled:opacity-40">
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
              <span className="num-key text-lg text-violet">{d.score_assemblage}</span>
              <span className="text-txt-mut">score d'assemblage</span>
              <span className={`ml-auto rounded-full px-2 py-0.5 text-[11px] ${d.contigu ? 'bg-mint/10 text-mint' : 'bg-st-ecartee/10 text-st-ecartee'}`}>
                {d.contigu ? "d'un seul tenant" : 'NON contiguë'}
              </span>
            </div>
            {/* A — GAIN d'assemblage : combinée vs meilleure parcelle seule */}
            <div data-asm-gain className="mt-1.5 rounded-md bg-mint/[0.06] px-2 py-1.5">
              <div className="text-txt">Ensemble : <b className="tnum text-mint">{fmt(d.sdp_combinee_m2)} m²</b> SDP · ~{fmt(d.logements_combine)} logements
                {d.gain_ratio && <span className="text-mint"> (×{d.gain_ratio} vs la meilleure parcelle seule)</span>}
              </div>
              <div className="mt-0.5 text-txt-dim">Séparément, la meilleure parcelle = {fmt(d.sdp_max_seule_m2)} m² (~{fmt(d.logements_max_seule)} logements) — l'assemblage débloque la taille de programme.</div>
            </div>
            <div className="mt-1 text-[11px] text-txt-dim">{d.note_sdp}</div>
          </div>

          {/* B — approche propriétaire (privacy : PM nommée / particulier masqué) */}
          <div data-asm-proprio className={`rounded-lg border px-3 py-1.5 text-[11px] ${d.tous_personnes_morales ? 'border-mint/40 bg-mint/[0.06]' : 'border-line-2 bg-surface-2'}`}>
            {d.tous_personnes_morales ? (
              <span className="text-mint">✓ Approche simplifiée — {d.n_personnes_morales} propriétaire(s) <b>personne(s) morale(s)</b>, aucun particulier</span>
            ) : (
              <span className="text-txt-mut">{d.n_personnes_morales} personne(s) morale(s) · <b className="text-st-creuser">{d.n_particuliers} particulier(s)</b> (approche plus lourde)</span>
            )}
            {(d.proprietaires_pm as string[]).length > 0 && (
              <div className="mt-0.5 truncate text-txt-dim" title={(d.proprietaires_pm as string[]).join(' · ')}>PM : {(d.proprietaires_pm as string[]).join(' · ')}</div>
            )}
          </div>

          <div className="flex min-h-0 flex-1 flex-col gap-1 overflow-y-auto">
            {(d.items as Record<string, any>[]).map((i) => {
              const pr = i.proprio as Record<string, any>
              return (
              <div key={i.idu} className="rounded-lg border border-line-2 bg-surface-3 px-3 py-1.5 text-[11px]">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-txt-hi">{i.idu.slice(8)}</span>
                  <span className="text-txt-dim">{fmt(i.surface_m2)} m² · SDP {fmt(i.sdp_residuelle_m2)}</span>
                  <span className="ml-auto">
                    <TierBadge tier={i.tier_v2 as string | null} etage0={i.etage0 as boolean | null} statut={i.statut as string | null} />
                  </span>
                </div>
                {/* PRIVACY : PM = dénomination + SIREN (public) ; particulier = jamais nommé */}
                <div className="truncate text-[11px] text-txt-dim" title={pr.type === 'personne_morale' ? `SIREN ${pr.siren ?? '—'}${pr.groupe ? ' · ' + pr.groupe : ''}` : 'personne physique — non communiqué'}>
                  {pr.type === 'personne_morale'
                    ? <><span className="text-txt">{pr.denomination}</span>{pr.siren ? <span> · SIREN {pr.siren}</span> : null}</>
                    : <span className="italic">propriétaire particulier — non communiqué</span>}
                </div>
              </div>
            )})}
          </div>
          {/* C — indivision non détectable en base (honnête, pas fabriqué) */}
          <p className="shrink-0 text-[10px] leading-snug text-txt-dim">Indivision : non détectable en open data (aucune structure de propriété physique publiée) — signal non affiché plutôt qu'inventé.</p>
        </>
      )}
    </>
  )
}

/* ───────────── M17 — ZAN ───────────── */

// Étiquette Sourcé (observé, vert) / Estimé (dérivé, ambre) — la boussole d'honnêteté (comme DVF).
const SrcTag = ({ src }: { src: boolean }) => (
  <span className={`ml-1 rounded px-1 py-0.5 align-middle text-[8.5px] font-medium ${src ? 'bg-mint/10 text-mint' : 'bg-st-creuser/10 text-st-creuser'}`}>{src ? 'Sourcé' : 'Estimé'}</span>
)

/** Indicateur ZAN d'une commune : consommé (Sourcé) + budget/reste (Estimé) + caveat loi TRACE. */
function IndicateurCommune({ ind, caveat }: { ind: Record<string, any>; caveat: string }) {
  return (
    <div className="rounded-lg border border-line-2 bg-surface-2 px-3 py-2 text-[11px]">
      <div className="flex items-center justify-between">
        <span className="font-medium text-txt">{ind.commune} — enveloppe ZAN (estimée)</span>
      </div>
      <div className="mt-1 grid grid-cols-2 gap-x-3 gap-y-0.5 text-txt-mut">
        <span>Consommé 2011-21 : <b className="text-txt">{ind.conso_2011_2021_ha}</b> ha<SrcTag src /></span>
        <span>Consommé 2021-24 : <b className="text-txt">{ind.conso_2021_2024_ha}</b> ha<SrcTag src /></span>
        <span>Budget 2021-31 : <b className="tnum text-st-creuser">{ind.budget_2021_2031_ha}</b> ha<SrcTag src={false} /></span>
        <span>Reste théorique : <b className={`tnum ${ind.depasse ? 'text-st-ecartee' : 'text-st-creuser'}`}>{ind.reste_theorique_ha}</b> ha<SrcTag src={false} /></span>
      </div>
      {ind.depasse && <p className="mt-1 text-[10.5px] text-st-ecartee">▲ Rythme déjà « dépassé » sur la période estimée (reste négatif).</p>}
      <p className="mt-1 text-[10px] italic leading-snug text-st-creuser">{caveat}</p>
      <p className="mt-0.5 text-[9px] text-txt-dim">Observé : {ind.source} · {ind.millesime}</p>
    </div>
  )
}

export function M17() {
  const q = useQuery({ queryKey: ['m17'], queryFn: motZan })
  const { setModuleMap, select, selectedIdu } = useApp()
  const d = q.data
  const [idu, setIdu] = useState(selectedIdu ?? '')
  useEffect(() => { if (selectedIdu) setIdu(selectedIdu) }, [selectedIdu])
  const sig = useQuery({ queryKey: ['zan-parc', idu], queryFn: () => zanParcelle(idu.trim()), enabled: idu.trim().length >= 10 })
  const s = sig.data
  useEffect(() => {
    const items = (d?.zan_compatibles ?? []) as Record<string, any>[]
    setModuleMap({ idus: items.map((i) => i.idu), extra: null })
    return () => setModuleMap({ idus: [], extra: null })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [q.dataUpdatedAt])
  const sigColor = s?.signal === 'aligne' ? TOKENS.mint : s?.signal === 'contrainte' ? TOKENS.stEcartee : TOKENS.txtMut
  const sigLabel = s?.signal === 'aligne' ? 'Aligné ZAN' : s?.signal === 'contrainte' ? 'Sous contrainte ZAN' : 'À instruire'
  return (
    <>
      <Banner>{d?.bandeau ?? '…'}</Banner>
      {q.isLoading && <div className="flex flex-1 items-center justify-center py-8"><Loading accent="violet" label="Analyse en cours…" big /></div>}

      {/* SIGNAL PAR PARCELLE (mène — robuste, sourcé, indépendant des quotas) */}
      <p className="label-caps">Signal ZAN par parcelle</p>
      <input data-zan-idu value={idu} onChange={(e) => setIdu(e.target.value.trim())}
        placeholder="IDU (ou sélectionnez une parcelle sur la carte)"
        className="rounded-lg border border-line-2 bg-surface-3 px-2 py-1.5 font-mono text-[11px] text-txt focus:border-violet focus:outline-none" />
      {s && (
        <div data-zan-signal className="flex flex-col gap-1.5 rounded-lg border px-3 py-2" style={{ borderColor: `${sigColor}55` }}>
          <div className="flex items-center gap-2">
            <span className="rounded-full px-2 py-0.5 text-[11px] font-medium" style={{ background: `${sigColor}22`, color: sigColor }}>{sigLabel}</span>
            <span className="text-[10.5px] text-txt-dim">{s.commune}</span>
          </div>
          {(s.raisons as string[]).map((r, i) => (
            <div key={i} className="flex gap-1.5 text-[10.5px] text-txt-mut"><span style={{ color: sigColor }}>•</span><span>{r}<SrcTag src /></span></div>
          ))}
          {s.exemption_sru && (
            <div className="rounded border border-mint/40 bg-mint/[0.06] px-2 py-1 text-[10.5px] text-mint">★ {s.exemption_sru}<SrcTag src /></div>
          )}
        </div>
      )}
      {/* CONTEXTE COMMUNE : indicateur estimé + caveat */}
      {s?.indicateur && <IndicateurCommune ind={s.indicateur} caveat={s.caveat as string} />}

      {/* Communes les plus consommatrices (contexte île, observé) */}
      <p className="label-caps mt-1">Consommation ENAF par commune (observé)<SrcTag src /></p>
      <div className="flex max-h-32 shrink-0 flex-col overflow-y-auto">
        {((d?.indicateurs ?? []) as Record<string, any>[]).slice(0, 8).map((c) => (
          <button key={c.commune} onClick={() => setIdu('')}
            className="flex items-center gap-2 border-b border-line py-1 text-left text-[11px]" title={`${c.commune} : reste théorique estimé ${c.reste_theorique_ha} ha`}>
            <span className="min-w-0 flex-1 truncate text-txt">{c.commune}</span>
            <span className="font-mono text-txt-dim">{c.conso_2011_2021_ha} ha (11-21)</span>
            <span className={`font-mono tnum ${c.depasse ? 'text-st-ecartee' : 'text-st-creuser'}`}>{c.reste_theorique_ha} ha</span>
          </button>
        ))}
      </div>
      <p className="text-[11px] text-txt-dim">{fmt((d?.zan_compatibles ?? []).length)} parcelles déjà artificialisées promues (surlignées) — <b className="text-mint">alignées ZAN</b></p>
      <div className="flex min-h-0 flex-1 flex-col gap-1 overflow-y-auto">
        {((d?.zan_compatibles ?? []) as Record<string, any>[]).slice(0, 60).map((i) => (
          <button key={i.idu} onClick={() => { setIdu(i.idu); select(i.idu) }}
            className="flex items-center gap-2 rounded-lg border border-line-2 bg-surface-3 px-3 py-1.5 text-left text-[11px] transition-colors duration-quick hover:border-violet/50">
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
        className="self-start rounded-lg bg-violet px-3 py-1.5 text-xs font-medium text-bg transition-[filter] duration-quick hover:brightness-110">
        ⬇ Rapport PDF
      </a>
      <p className="label-caps">DVF par trimestre</p>
      <div className="flex shrink-0 flex-col gap-1">
        {((d?.dvf_trimestres ?? []) as Record<string, any>[]).map((r) => (
          <div key={r.trimestre} className="flex items-center gap-2 text-[11px]">
            <span className="w-14 font-mono text-txt-dim">{r.trimestre}</span>
            <span className="relative h-2.5 min-w-0 flex-1 overflow-hidden rounded-full bg-line">
              <span className="absolute left-0 top-0 h-full rounded-full bg-violet" style={{ width: `${(100 * r.mutations) / max}%` }} />
            </span>
            <span className="w-12 text-right font-mono text-txt-mut">{fmt(r.mutations)}</span>
            <span className="w-20 text-right font-mono text-txt-dim">{fmt(r.median_eur_m2_bati)} €/m²</span>
          </div>
        ))}
      </div>
      <p className="label-caps mt-1">Prix par commune (top)</p>
      <div className="flex min-h-0 flex-1 flex-col overflow-y-auto">
        {((d?.top_communes_prix ?? []) as Record<string, any>[]).map((r) => (
          <div key={r.commune} className="flex items-center gap-2 border-b border-line py-1 text-[11px]">
            <span className="min-w-0 flex-1 truncate text-txt">{r.commune}</span>
            <span className="font-mono text-txt-dim">{fmt(r.mutations)} mut.</span>
            <span className="tnum font-mono text-violet">{fmt(r.median_eur_m2)} €/m²</span>
          </div>
        ))}
      </div>
    </>
  )
}


/* ───────────── M19 — MATCHING TERRAIN ↔ PROMOTEUR ───────────── */

const DemoTag = () => <span className="ml-1 rounded bg-violet/15 px-1 py-0.5 text-[8px] font-medium text-violet">DÉMO · ILLUSTRATIF</span>
const RealTag = () => <span className="ml-1 rounded bg-mint/10 px-1 py-0.5 text-[8px] font-medium text-mint">RÉEL · SITADEL</span>

export function M19() {
  const profiles = useQuery({ queryKey: ['m19'], queryFn: getProfiles })
  const { selectedIdu, commune } = useApp()
  const [idu, setIdu] = useState(selectedIdu ?? '')
  useEffect(() => { if (selectedIdu) setIdu(selectedIdu) }, [selectedIdu])
  const compat = useQuery({ queryKey: ['m19-compat', idu], queryFn: () => matchCompatibilite(idu.trim()), enabled: idu.trim().length >= 10 })
  const secteur = commune ?? (compat.data?.commune as string | undefined)
  const actifs = useQuery({ queryKey: ['m19-actifs', secteur], queryFn: () => promoteursActifs(secteur!), enabled: !!secteur })
  const [nom, setNom] = useState('')
  const [smin, setSmin] = useState('')
  const add = useMutation({ mutationFn: () => addProfile({ nom, surface_min: smin ? Number(smin) : null }),
    onSuccess: () => { setNom(''); profiles.refetch() } })
  const match = useMutation({ mutationFn: runMatch })
  return (
    <>
      <Banner>Deux volets : la <b>compatibilité</b> avec des profils <b>démo</b> (illustratif) et les
        <b>promoteurs réellement actifs</b> du secteur via <b>SITADEL</b> (donnée réelle).</Banner>

      {/* A + B — compatibilité parcelle × profil (DÉMO), score décomposé */}
      <p className="label-caps">Compatibilité parcelle × profil<DemoTag /></p>
      <input data-m19-idu value={idu} onChange={(e) => setIdu(e.target.value.trim())}
        placeholder="IDU (ou sélectionnez une parcelle sur la carte)"
        className="rounded-lg border border-line-2 bg-surface-3 px-2 py-1.5 font-mono text-[11px] text-txt focus:border-violet focus:outline-none" />
      {compat.data && (compat.data.profils as Record<string, any>[]).map((pr, k) => (
        <div key={k} data-m19-compat className="rounded-lg border border-line-2 bg-surface-3 px-3 py-2 text-[11px]">
          <div className="flex items-center gap-2">
            <span className={`num-key text-base ${pr.score >= 70 ? 'text-mint' : pr.score >= 40 ? 'text-st-creuser' : 'text-txt-mut'}`}>{pr.score}</span>
            <span className="text-txt-dim">/100 · {pr.profil}</span>
            {pr.demo && <DemoTag />}
          </div>
          <div className="mt-1 flex flex-col gap-0.5">
            {(pr.facteurs as Record<string, any>[]).map((f, i) => (
              <div key={i} className="flex gap-1.5 text-[10.5px]">
                <span className={f.ok ? 'text-mint' : 'text-txt-dim'}>{f.ok ? '✓' : '○'}</span>
                <span className={f.ok ? 'text-txt-mut' : 'text-txt-dim'}>{f.critere} <span className="text-txt-dim">— {f.valeur}</span></span>
              </div>
            ))}
          </div>
        </div>
      ))}

      {/* C — promoteurs réellement actifs (SITADEL, réel, PM only) */}
      <p className="label-caps mt-1">Promoteurs actifs du secteur<RealTag /></p>
      {actifs.data ? (
        <div data-m19-actifs className="flex max-h-48 flex-col gap-1 overflow-y-auto">
          <p className="text-[9.5px] leading-snug text-txt-dim">{actifs.data.source}</p>
          {(actifs.data.promoteurs as Record<string, any>[]).map((p, k) => (
            <div key={k} className="rounded-lg border border-line-2 bg-surface-2 px-3 py-1.5 text-[11px]">
              <div className="truncate text-txt" title={`SIREN ${p.siren}`}>{p.nom}</div>
              <div className="text-[10.5px] text-txt-dim">SIREN {p.siren} · <b className="text-txt-mut">{p.n_permis}</b> permis (5 ans){p.logements ? ` · ${p.logements} logements` : ''}</div>
            </div>
          ))}
          {(actifs.data.promoteurs as unknown[]).length === 0 && <p className="text-[10.5px] text-txt-dim">Aucun promoteur (personne morale) avec ≥ 2 permis récents ici.</p>}
        </div>
      ) : <p className="text-[10.5px] text-txt-dim">Choisissez une commune ou une parcelle pour voir les promoteurs actifs réels.</p>}

      <p className="label-caps mt-1">Profils de recherche (alertes cloche)<DemoTag /></p>
      <div className="flex min-h-0 flex-col gap-1.5 overflow-y-auto">
        {((profiles.data ?? []) as Record<string, any>[]).map((p) => (
          <div key={p.id} className="rounded-lg border border-line-2 bg-surface-3 px-3 py-2 text-[11px]">
            <div className="flex items-center gap-2">
              <span className="text-txt">{p.nom}</span>
              {p.demo && <span className="rounded-full bg-violet/15 px-1.5 py-0.5 text-[8.5px] text-violet">DÉMO</span>}
            </div>
            <div className="mt-0.5 text-[11px] text-txt-dim">
              {p.commune ?? 'toute commune'} · surface {p.surface_min ?? '—'}–{p.surface_max ?? '—'} m² · SDP ≥ {p.sdp_min ?? '—'}
            </div>
          </div>
        ))}
      </div>
      <div className="flex gap-1.5">
        <input value={nom} onChange={(e) => setNom(e.target.value)} placeholder="Nom du profil…"
          className="min-w-0 flex-1 rounded border border-line-2 bg-surface-3 px-2 py-1 text-[11px] text-txt focus:border-violet focus:outline-none" />
        <input value={smin} onChange={(e) => setSmin(e.target.value)} placeholder="surf. min" type="number"
          className="w-20 rounded border border-line-2 bg-surface-3 px-2 py-1 text-[11px] text-txt focus:border-violet focus:outline-none" />
        <button onClick={() => nom.trim() && add.mutate()} disabled={!nom.trim()}
          title="Ajouter le profil" aria-label="Ajouter le profil"
          className="rounded bg-violet px-2 text-[11px] font-medium text-bg transition-[filter] duration-quick hover:brightness-110 disabled:opacity-40">+</button>
      </div>
      <button onClick={() => match.mutate()} disabled={match.isPending}
        className="rounded-lg border border-line-2 py-1.5 text-[11px] text-txt transition-colors duration-quick hover:text-txt-hi">
        {match.isPending ? '…' : 'Tester le matching maintenant'}
      </button>
      {match.data && <p className="text-[11px] text-violet">✓ {match.data.matches} match(s) émis → voir la cloche</p>}
    </>
  )
}
