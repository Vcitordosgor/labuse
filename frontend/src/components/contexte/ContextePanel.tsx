import { useQuery } from '@tanstack/react-query'
import { useEffect } from 'react'
import { getContexteCommune } from '../../lib/api'
import { useApp } from '../../store/useApp'
import { Loading } from '../Loading'

const fmt = (n: number | null | undefined) => (n == null ? '—' : Math.round(Number(n)).toLocaleString('fr-FR'))

//: statut SRU → couleur + lecture métier (une phrase sobre — le ciblage de la promotrice)
const SRU_META: Record<string, { color: string; bg: string; label: string; lecture: string }> = {
  carencee: { color: '#E8695A', bg: '#2a1210', label: 'CARENCÉE',
    lecture: 'Commune en carence SRU : forte pression de production de logement social — les programmes avec part LLS y sont attendus (et souvent facilités).' },
  deficitaire: { color: '#E8B44C', bg: '#211a10', label: 'DÉFICITAIRE',
    lecture: 'Sous l’objectif légal : la commune doit produire du logement social — un programme mixte y répond à une obligation réelle.' },
  exemptee: { color: '#8FA69A', bg: '#141a17', label: 'EXEMPTÉE 2023-2025',
    lecture: 'Soumise SRU mais exemptée d’obligations sur la période (décret) — pression de production sociale suspendue.' },
  conforme: { color: '#5CE6A1', bg: '#0F1A14', label: 'CONFORME',
    lecture: 'Objectif SRU atteint — pas de pression réglementaire de rattrapage social.' },
}

function Source({ nom, url }: { nom?: string | null; url?: string | null }) {
  if (!nom) return null
  return (
    <p className="mt-1.5 text-[11px] leading-snug text-txt-dim">
      Source :{' '}
      {url ? <a href={url} target="_blank" rel="noreferrer" className="text-[#7DE8E0] hover:underline">{nom} ↗</a> : nom}
    </p>
  )
}

function Bar({ parts }: { parts: { label: string; pct: number; color: string }[] }) {
  return (
    <div>
      <div className="flex h-1.5 overflow-hidden rounded-full bg-line">
        {parts.map((p) => <span key={p.label} style={{ width: `${p.pct}%`, background: p.color }} />)}
      </div>
      <div className="mt-1 flex flex-wrap gap-x-3 gap-y-0.5">
        {parts.map((p) => (
          <span key={p.label} className="flex items-center gap-1 text-[11px] text-txt-mut">
            <span className="h-1.5 w-1.5 rounded-full" style={{ background: p.color }} />{p.label} {p.pct.toLocaleString('fr-FR')} %
          </span>
        ))}
      </div>
    </div>
  )
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="border-b border-line px-5 py-4">
      <p className="mb-2 font-mono text-[10px] tracking-widest text-txt-dim">{title}</p>
      {children}
    </section>
  )
}

/** VOLET CONTEXTE COMMUNE (mandat promotrice) — SRU · ANRU · PLH · marché INSEE · QPV.
 *  Contexte SOURCÉ (échelle commune) — aucune de ces données n'entre dans le scoring. */
export function ContextePanel() {
  const { contexteCommune, setContexteCommune } = useApp()
  const q = useQuery({
    queryKey: ['contexte', contexteCommune],
    queryFn: () => getContexteCommune(contexteCommune!),
    enabled: !!contexteCommune,
  })
  useEffect(() => {
    const h = (e: KeyboardEvent) => e.key === 'Escape' && setContexteCommune(null)
    window.addEventListener('keydown', h)
    return () => window.removeEventListener('keydown', h)
  }, [setContexteCommune])
  if (!contexteCommune) return null
  const d = q.data

  return (
    <aside data-contexte-panel className="absolute right-0 top-0 z-30 flex h-full w-[420px] flex-col border-l border-line bg-surface-1 shadow-2xl">
      <div className="flex shrink-0 items-center justify-between border-b border-line px-5 py-3">
        <div>
          <p className="font-mono text-[10px] tracking-widest text-[#B497F0]">CONTEXTE COMMUNE</p>
          <h2 className="font-display text-lg font-bold text-txt-hi">{contexteCommune}</h2>
          {d?.epci && <p className="text-[10.5px] text-txt-mut">{d.epci} — {d.epci_nom}</p>}
        </div>
        <button onClick={() => setContexteCommune(null)} className="text-txt-dim hover:text-txt-hi" title="Fermer (Échap)">✕</button>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto">
        {q.isLoading && <div className="p-5"><Loading label="Chargement du contexte commune" className="text-xs" /></div>}
        {q.isError && <p className="p-5 text-xs text-st-ecartee">Erreur de chargement — réessayez.</p>}
        {d && (
          <>
            <Section title="SRU — LOGEMENT SOCIAL">
              {d.sru ? (() => {
                const m = SRU_META[d.sru.statut] ?? SRU_META.conforme
                return (
                  <>
                    <div className="rounded-lg border px-3 py-2" style={{ borderColor: `${m.color}55`, background: m.bg }}>
                      <span className="font-display text-[15px] font-bold" style={{ color: m.color }}>
                        SRU {Number(d.sru.taux_lls).toLocaleString('fr-FR')} %
                      </span>
                      <span className="ml-2 text-xs text-txt-mut">objectif {Number(d.sru.objectif_pct).toLocaleString('fr-FR')} %</span>
                      <span className="ml-2 rounded-full px-2 py-0.5 text-[11px] font-semibold" style={{ color: m.color, background: `${m.color}22` }}>{m.label}</span>
                      {Number(d.sru.prelevement_eur) > 0 && (
                        <p className="mt-1 text-[10.5px] text-txt-mut">Prélèvement 2025 : {fmt(d.sru.prelevement_eur)} €</p>
                      )}
                    </div>
                    <p className="mt-2 text-[11px] leading-relaxed text-txt">{m.lecture}</p>
                    <p className="mt-1 text-[11px] text-txt-dim">{fmt(d.sru.detail?.nb_lls)} LLS à l’inventaire · {d.sru.millesime}</p>
                    <Source nom={d.sru.source_nom} url={d.sru.source_url} />
                  </>
                )
              })() : <p className="text-xs text-txt-mut">Non disponible pour cette commune (source SRU DHUP).</p>}
            </Section>

            <Section title="RENOUVELLEMENT URBAIN — NPNRU">
              {d.anru.length > 0 ? (
                <>
                  {d.anru.map((a) => (
                    <div key={a.nom} className="mb-1.5 rounded-lg border border-line-2 bg-surface-3 px-3 py-2">
                      <span className="text-xs font-medium text-txt-hi">{a.nom}</span>
                      <span className="ml-2 rounded-full bg-[#1a2340] px-2 py-0.5 text-[11px] font-medium text-[#8FB4F0]">intérêt {a.interet}</span>
                      <p className="mt-0.5 text-[11px] text-txt-dim">{a.code_qpv} · activer la couche « ANRU » sur la carte</p>
                    </div>
                  ))}
                  <Source nom={d.anru[0].source_nom} url={d.anru[0].source_url} />
                </>
              ) : <p className="text-xs text-txt-mut">Aucun périmètre NPNRU sur cette commune (8 quartiers d’intérêt national à La Réunion, aucun régional).</p>}
              <p className="mt-2 text-[11px] leading-snug text-txt-dim">{d.notes[0]}</p>
            </Section>

            <Section title={`PLH ${d.epci ?? ''} — PROGRAMME LOCAL DE L'HABITAT`}>
              {d.plh ? (
                <>
                  <div className="flex gap-4">
                    {d.plh.obj_logements_an != null && (
                      <div><p className="font-display text-lg font-bold text-txt-hi">{fmt(d.plh.obj_logements_an)}</p>
                        <p className="text-[11px] text-txt-dim">logements / an (objectif)</p></div>
                    )}
                    {d.plh.part_sociale_pct != null && (
                      <div><p className="font-display text-lg font-bold text-txt-hi">{Number(d.plh.part_sociale_pct).toLocaleString('fr-FR')} %</p>
                        <p className="text-[11px] text-txt-dim">part sociale visée</p></div>
                    )}
                  </div>
                  <p className="mt-1 text-[10.5px] text-txt-mut">{d.plh.periode} · {d.plh.statut}</p>
                  {(d.plh.refs ?? []).map((r: { doc: string; url?: string; page?: string | number }, i: number) => (
                    <p key={i} className="mt-0.5 text-[11px] text-txt-dim">
                      Réf. : {r.url ? <a className="text-[#7DE8E0] hover:underline" href={r.url} target="_blank" rel="noreferrer">{r.doc} ↗</a> : r.doc}{r.page ? ` — p. ${r.page}` : ''}
                    </p>
                  ))}
                </>
              ) : (
                <p className="text-xs text-txt-mut">
                  Non disponible — PLH {d.epci ?? ''} non retrouvé en source publique vérifiable
                  (extraction documentaire : aucun chiffre n’est affiché sans sa référence).
                </p>
              )}
            </Section>

            <Section title="MARCHÉ LOGEMENT — INSEE RP 2023">
              {d.marche ? (
                <>
                  <div className="mb-2 flex gap-4">
                    <div><p className="font-display text-lg font-bold text-txt-hi">{fmt(d.marche.logements)}</p><p className="text-[11px] text-txt-dim">logements</p></div>
                    <div><p className="font-display text-lg font-bold text-txt-hi">{fmt(d.marche.vacants)}</p><p className="text-[11px] text-txt-dim">vacants ({d.marche.typologie?.vacance_pct?.toLocaleString?.('fr-FR') ?? d.marche.typologie?.vacance_pct} %)</p></div>
                  </div>
                  <div className="flex flex-col gap-2.5">
                    <Bar parts={[
                      { label: 'locataires', pct: Number(d.marche.locataires_pct), color: '#B497F0' },
                      { label: 'propriétaires', pct: Number(d.marche.proprietaires_pct), color: '#5CE6A1' },
                    ]} />
                    <Bar parts={[
                      { label: 'maisons', pct: Number(d.marche.maisons_pct), color: '#4ADE96' },
                      { label: 'appartements', pct: Number(d.marche.apparts_pct), color: '#7DE8E0' },
                    ]} />
                  </div>
                  {d.marche.typologie && (
                    <div className="mt-3">
                      <p className="mb-1 text-[11px] text-txt-dim" title={d.marche.typologie.libelle}>
                        Résidences principales par nombre de pièces (proxy T1…T5+)
                      </p>
                      <Bar parts={(['p1', 'p2', 'p3', 'p4', 'p5p'] as const).map((k, i) => {
                        const total = ['p1', 'p2', 'p3', 'p4', 'p5p'].reduce((s, kk) => s + (d.marche!.typologie[kk] ?? 0), 0) || 1
                        return { label: k === 'p5p' ? '5p+' : k.replace('p', '') + 'p',
                                 pct: Math.round(1000 * (d.marche!.typologie[k] ?? 0) / total) / 10,
                                 color: ['#2E6B4F', '#4ADE96', '#5CE6A1', '#7DE8E0', '#B497F0'][i] }
                      })} />
                    </div>
                  )}
                  <Source nom={d.marche.source_nom} url={d.marche.source_url} />
                </>
              ) : <p className="text-xs text-txt-mut">Non disponible (INSEE RP).</p>}
            </Section>

            <Section title="QUARTIERS PRIORITAIRES — QPV (rappel)">
              {d.qpv.length > 0 ? (
                <p className="text-xs text-txt">{d.qpv.length} QPV (génération 2024) : {d.qpv.map((x) => x.nom).join(' · ')}</p>
              ) : <p className="text-xs text-txt-mut">Aucun QPV sur cette commune.</p>}
              <p className="mt-2 text-[11px] leading-snug text-txt-dim">{d.notes[1]}</p>
            </Section>
          </>
        )}
      </div>
    </aside>
  )
}
