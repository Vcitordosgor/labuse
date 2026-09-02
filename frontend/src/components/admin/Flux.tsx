// FLUX-1 — la page « Flux » du dashboard admin : la donnée, de la source à l'écran.
// Construite depuis les VRAIES métadonnées (data_sources, source_veille, registre des outils,
// matrice source→consommateurs rendue exécutable côté backend `labuse.flux`) — jamais un dessin
// statique. En haut : les trois gestes (injecter · calculer · basculer). Au milieu : la fourmilière
// (cliquer une source surligne ce qu'elle alimente). En bas : la donnée qui s'accumule (Radar) et
// la garde qui vérifie que tout le monde lit le même run. Réf. docs/audit-2026-09/maquette-dashboard-flux.html.
import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  getAdminFlux, getAdminFluxRuns, postAdminFluxLancerRun, postAdminFluxBascule, postAdminSourceVeilleInjecter,
  type AdminFlux, type FluxDot, type FluxSourceNode, type FluxRadarEcart,
} from '../../lib/api'
import { Chip } from './AdminView'

const fmtReu = (iso?: string | null, avecHeure = false) => {
  if (!iso) return '—'
  try {
    return new Intl.DateTimeFormat('fr-FR', {
      timeZone: 'Indian/Reunion', day: '2-digit', month: '2-digit',
      ...(avecHeure ? { hour: '2-digit', minute: '2-digit' } : {}),
    }).format(new Date(iso))
  } catch { return '—' }
}
const DOT: Record<FluxDot, string> = {
  ok: 'bg-mint', warn: 'bg-amber', err: 'bg-coral', off: 'bg-line-3',
}

// ── un nœud (source / moteur / surface) cliquable, avec son état (dot) et son millésime/run ──
function Node({ dot, nom, mv, hi, dim, onClick }: {
  dot: FluxDot; nom: string; mv?: string | null; hi?: boolean; dim?: boolean; onClick?: () => void
}) {
  return (
    <div onClick={onClick}
      className={`mb-1.5 flex cursor-pointer items-center gap-2.5 rounded-lg border px-2.5 py-2 transition-colors
        ${hi ? 'border-mint bg-mint/[0.07]' : 'border-line bg-surface-2 hover:border-line-3'}
        ${dim ? 'opacity-35' : ''}`}>
      <span className={`h-2 w-2 shrink-0 rounded-full ${DOT[dot]}`} />
      <span className="min-w-0 flex-1 truncate text-[13px] text-txt">{nom}</span>
      {mv && <span className="shrink-0 font-mono text-[11px] text-txt-dim">{mv}</span>}
    </div>
  )
}

export function FluxSection() {
  const qc = useQueryClient()
  const q = useQuery({ queryKey: ['admin-flux'], queryFn: getAdminFlux, refetchInterval: 60_000 })
  // RETOURS-9 (Q1) — RENDU PROGRESSIF : les runs terminés + écarts au servi (calcul ~50 s en base
  // réelle) sont sortis de /admin/flux et chargés à part. Le Circuit rend tout de suite (q ci-dessus,
  // ~6 s) ; ce panneau se remplit ensuite. Il alimente la liste « Runs terminés · écart au servi ».
  const qRuns = useQuery({ queryKey: ['admin-flux-runs'], queryFn: getAdminFluxRuns, refetchInterval: 60_000 })
  const [sel, setSel] = useState<{ kind: 'source' | 'moteur' | 'surface'; id: string } | null>(null)
  const [recherche, setRecherche] = useState('')
  const [replie, setReplie] = useState<Record<string, boolean>>({})
  const [glossaire, setGlossaire] = useState(false)

  const lancer = useMutation({
    mutationFn: postAdminFluxLancerRun,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin-flux'] }),
  })
  const bascule = useMutation({
    mutationFn: (run: string) => postAdminFluxBascule(run),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin-flux'] }),
  })
  const injecter = useMutation({
    mutationFn: (id: number) => postAdminSourceVeilleInjecter(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin-flux'] }),
  })

  const d: AdminFlux | undefined = q.data
  // ── surlignage : cliquer une source surligne ses moteurs + les surfaces qui les lisent (et vice-versa) ──
  const hi = useMemo(() => {
    const s = { sources: new Set<number>(), moteurs: new Set<string>(), surfaces: new Set<string>() }
    if (!d || !sel) return s
    const { sources, moteurs, surfaces } = d.flux
    if (sel.kind === 'source') {
      const src = sources.find((x) => String(x.id) === sel.id)
      if (src) { s.sources.add(src.id); src.moteurs.forEach((m) => s.moteurs.add(m)) }
    } else if (sel.kind === 'moteur') {
      s.moteurs.add(sel.id)
      sources.forEach((x) => { if (x.moteurs.includes(sel.id)) s.sources.add(x.id) })
    } else {
      const su = surfaces.find((x) => x.key === sel.id)
      if (su) su.moteurs.forEach((m) => s.moteurs.add(m))
      s.surfaces.add(sel.id)
    }
    // moteurs → surfaces + moteurs → sources (fermeture)
    surfaces.forEach((su) => { if (su.moteurs.some((m) => s.moteurs.has(m))) s.surfaces.add(su.key) })
    if (sel.kind !== 'source') sources.forEach((x) => { if (x.moteurs.some((m) => s.moteurs.has(m))) s.sources.add(x.id) })
    void moteurs
    return s
  }, [d, sel])

  if (q.isError) return <div className="p-6 text-sm text-coral">Chargement impossible.</div>
  if (!d) return <div className="p-6 text-sm text-txt-dim">Chargement…</div>

  const { flux, radar, coherence } = d
  const { run, comptes } = flux
  const nouvelleVersion = comptes.nouvelle_version
  const plusRecentes = comptes.plus_recentes_que_run
  const actif = !!sel
  const dim = (on: boolean) => actif && !on

  // sources groupées par fournisseur (F1.5), filtrées par la recherche
  const filtre = recherche.trim().toLowerCase()
  const srcVisibles = flux.sources.filter((x) =>
    !filtre || x.name.toLowerCase().includes(filtre) || (x.fournisseur || '').toLowerCase().includes(filtre))
  const groupes: Array<[string, FluxSourceNode[]]> = []
  for (const x of srcVisibles) {
    const f = x.fournisseur || 'Autres'
    const last = groupes[groupes.length - 1]
    if (last && last[0] === f) last[1].push(x)
    else groupes.push([f, [x]])
  }
  const surfacesParGroupe: Record<string, typeof flux.surfaces> = {}
  for (const s of flux.surfaces) (surfacesParGroupe[s.groupe] ||= []).push(s)

  const coherenceKo = coherence.ok === false
  // Q1 — runs servis via la 2e requête (rendu progressif). Tant qu'elle charge, on l'indique.
  const runsBasculables = (qRuns.data?.runs ?? []).filter((r) => !r.servi)

  // Q4 — UN SEUL chiffre de surfaces, la même phrase partout. Le total (comptes.n_surfaces) inclut
  // la surface VIVANTE hors run (« Remonter le temps ») ; le run n'en scoré que coherence.n_surfaces.
  const surfTotal = comptes.n_surfaces
  const surfRun = coherence.n_surfaces ?? surfTotal
  const surfVivantes = Math.max(0, surfTotal - surfRun)
  const phraseSurfaces = surfVivantes > 0
    ? `${surfTotal} surfaces · ${surfRun} sur ${run.label} · ${surfVivantes} vivante${surfVivantes > 1 ? 's' : ''} (hors run)`
    : `${surfTotal} surfaces · toutes sur ${run.label}`

  return (
    <div className="pb-10">
      {/* en-tête */}
      <div className="font-mono text-[10.5px] uppercase tracking-[0.26em] text-txt-dim">Dashboard · Flux</div>
      <h1 className="mt-1.5 font-display text-[22px] font-semibold text-txt-hi">La donnée, de la source à l'écran.</h1>
      <div className="mt-1 text-[13px] text-txt-dim">
        Run courant <span className="font-mono text-mint">{run.label}</span>
        {run.calcule_le && <> · calculé le {fmtReu(run.calcule_le)}</>}
        {/* Q4 — une seule phrase exacte, identique à la colonne Surfaces (test d'égalité). */}
        <> · <span data-flux-surfaces-phrase>{phraseSurfaces}</span></>
      </div>

      {/* alerte cohérence en tête (F1.4) — ne doit jamais arriver depuis CONNEXIONS-2 */}
      {coherenceKo && (
        <div className="mt-4 rounded-xl border border-coral/40 bg-coral/5 px-4 py-3 text-[13px] text-coral">
          ⚠ Une surface ne lit pas le run courant :{' '}
          {coherence.checks.filter((c) => !c.ok).map((c) => c.libelle).join(' · ')}
        </div>
      )}

      {/* ── bandeau 3 étapes (F2) ── */}
      <div className="mt-5 grid grid-cols-1 gap-3 md:grid-cols-3">
        {/* 1 · Injecter */}
        <div className="rounded-xl border border-line bg-surface-2 p-4">
          <div className="font-mono text-[10.5px] uppercase tracking-[0.22em] text-txt-dim">1 · Sources</div>
          <div className="mt-1 text-[15px] font-semibold text-txt-hi">Injecter</div>
          <div className="mt-2 text-[13px] leading-relaxed text-txt-dim">
            <b className="text-txt">{comptes.surveillees}</b> surveillées sur {comptes.total} ·{' '}
            <b className="text-txt">{nouvelleVersion}</b> {nouvelleVersion > 1 ? 'ont' : 'a'} une nouvelle version
          </div>
          {plusRecentes > 0
            ? <div className="mt-2"><Chip tone="warn">● {plusRecentes} plus récente(s) que le run</Chip></div>
            : <div className="mt-2"><Chip tone="ok">● tout est au niveau du run</Chip></div>}
          <div className="mt-3 flex flex-wrap gap-1.5">
            {flux.sources.filter((s) => s.dot === 'warn' && s.injectable).map((s) => (
              <button key={s.id} onClick={() => injecter.mutate(s.id)} disabled={injecter.isPending}
                className="rounded-lg border border-mint/40 bg-mint/10 px-2.5 py-1 text-[11.5px] font-medium text-mint disabled:opacity-40">
                Injecter {s.name.split(' ')[0]} →
              </button>
            ))}
            {flux.sources.filter((s) => s.dot === 'warn' && s.injectable).length === 0 && (
              <span className="text-[12px] text-txt-mut">Rien à injecter automatiquement (ingestion manuelle).</span>
            )}
          </div>
        </div>

        {/* 2 · Calculer */}
        <div className="rounded-xl border border-line bg-surface-2 p-4">
          <div className="font-mono text-[10.5px] uppercase tracking-[0.22em] text-txt-dim">2 · Run</div>
          <div className="mt-1 text-[15px] font-semibold text-txt-hi">Calculer</div>
          <div className="mt-2 text-[13px] leading-relaxed text-txt-dim">
            {run.enregistre_sources
              ? <>Le run courant a enregistré <b className="text-txt">{run.source_millesimes.length}</b> millésimes de sources.</>
              : <>Ce run est antérieur à Flux : il n'a pas enregistré ses millésimes (les prochains runs le feront).</>}
          </div>
          {plusRecentes > 0 && <div className="mt-2"><Chip tone="warn">● {plusRecentes} source(s) plus récentes que ce run</Chip></div>}
          <div className="mt-3 flex items-center gap-2">
            <button onClick={() => lancer.mutate()} disabled={lancer.isPending}
              className="rounded-lg bg-mint px-3.5 py-2 text-[13px] font-semibold text-[#071009] disabled:opacity-40">
              {lancer.isPending ? 'Lancement…' : 'Lancer un run →'}
            </button>
            {lancer.data?.estimation && <span className="text-[12px] text-txt-mut">{lancer.data.estimation}</span>}
          </div>
          {lancer.data?.label && (
            <div className="mt-2 font-mono text-[11px] text-mint">→ {lancer.data.label} lancé (non servi)</div>
          )}
        </div>

        {/* 3 · Basculer */}
        <div className="rounded-xl border border-line bg-surface-2 p-4">
          <div className="font-mono text-[10.5px] uppercase tracking-[0.22em] text-txt-dim">3 · Bascule</div>
          <div className="mt-1 text-[15px] font-semibold text-txt-hi">Basculer</div>
          <div className="mt-2 text-[13px] leading-relaxed text-txt-dim">
            {d.bascule.derniere
              ? <>Dernière bascule : <b className="text-txt">{fmtReu(d.bascule.derniere.ts)}</b>, {d.bascule.derniere.ancien} → {d.bascule.derniere.nouveau}.</>
              : <>Aucune bascule journalisée pour l'instant.</>}
          </div>
          <div className="mt-2"><Chip tone={coherenceKo ? 'warn' : 'ok'}>● tous les écrans sur {run.label}</Chip></div>
          {bascule.data && (
            <div className={`mt-2 text-[11.5px] ${bascule.data.ok ? 'text-mint' : 'text-coral'}`}>
              {bascule.data.ok
                ? `Bascule ${bascule.data.ancien} → ${bascule.data.nouveau} · ${bascule.data.caches_purges?.length ?? 0} caches purgés`
                : bascule.data.motif}
            </div>
          )}
        </div>
      </div>

      {/* recherche */}
      <div className="mt-5 flex items-center gap-2">
        <input value={recherche} onChange={(e) => setRecherche(e.target.value)}
          placeholder="Rechercher une source…"
          className="w-64 rounded-lg border border-line bg-surface-1 px-3 py-1.5 text-[13px] text-txt placeholder:text-txt-mut focus:border-mint/40 focus:outline-none" />
        {sel && <button onClick={() => setSel(null)} className="text-[12px] text-txt-mut hover:text-txt">✕ désélectionner</button>}
      </div>

      {/* ── fourmilière : 3 colonnes ── */}
      <div className="mt-3 grid grid-cols-1 gap-5 lg:grid-cols-[1.15fr_1fr_1.15fr]">
        {/* SOURCES */}
        <div>
          <ColHead titre="Sources" note={`${comptes.total} · ${comptes.surveillees} surveillées`}
            replie={!!replie.sources} onToggle={() => setReplie((r) => ({ ...r, sources: !r.sources }))} />
          {!replie.sources && groupes.map(([f, items]) => (
            <div key={f}>
              <div className="mb-1 mt-2.5 text-[11px] tracking-wide text-txt-mut">{f}</div>
              {items.map((s) => (
                <div key={s.id} className="group relative">
                  <Node dot={s.dot} nom={s.name} mv={s.millesime || s.etat}
                    hi={hi.sources.has(s.id)} dim={dim(hi.sources.has(s.id))}
                    onClick={() => setSel(sel?.kind === 'source' && sel.id === String(s.id) ? null : { kind: 'source', id: String(s.id) })} />
                </div>
              ))}
            </div>
          ))}
          {!replie.sources && groupes.length === 0 && <div className="mt-3 text-[12px] text-txt-mut">Aucune source.</div>}
        </div>

        {/* MOTEURS */}
        <div>
          <ColHead titre="Moteurs" note={`run ${run.label}`}
            replie={!!replie.moteurs} onToggle={() => setReplie((r) => ({ ...r, moteurs: !r.moteurs }))} />
          {!replie.moteurs && flux.moteurs.map((m) => {
            const on = hi.moteurs.has(m.key)
            return (
              <div key={m.key} onClick={() => setSel(sel?.kind === 'moteur' && sel.id === m.key ? null : { kind: 'moteur', id: m.key })}
                className={`mb-2 cursor-pointer rounded-xl border p-3 transition-colors
                  ${on ? 'border-mint bg-mint/[0.06]' : 'border-line bg-surface-1 hover:border-line-3'}
                  ${dim(on) ? 'opacity-35' : ''}`}>
                <div className="flex items-center justify-between">
                  <span className="flex items-center gap-2 text-[13px] font-semibold text-txt">
                    <span className={`h-2 w-2 rounded-full ${DOT[m.dot]}`} />{m.label}
                  </span>
                  <span className="font-mono text-[11px] text-mint">{m.run}</span>
                </div>
                <div className="mt-1 text-[11.5px] text-txt-dim">{m.detail}</div>
              </div>
            )
          })}
          {/* légende */}
          <div className="mt-3 flex flex-wrap gap-4 text-[11.5px] text-txt-dim">
            <span className="flex items-center gap-1.5"><i className="h-2 w-2 rounded-full bg-mint" /> à jour</span>
            <span className="flex items-center gap-1.5"><i className="h-2 w-2 rounded-full bg-amber" /> plus récent que le run</span>
            <span className="flex items-center gap-1.5"><i className="h-2 w-2 rounded-full bg-coral" /> erreur</span>
            <span className="flex items-center gap-1.5"><i className="h-2 w-2 rounded-full bg-line-3" /> non surveillé</span>
          </div>
        </div>

        {/* SURFACES */}
        <div>
          <ColHead titre="Surfaces" note={phraseSurfaces}
            replie={!!replie.surfaces} onToggle={() => setReplie((r) => ({ ...r, surfaces: !r.surfaces }))} />
          {!replie.surfaces && Object.entries(surfacesParGroupe).map(([g, items]) => (
            <div key={g}>
              <div className="mb-1 mt-2.5 text-[11px] tracking-wide text-txt-mut">{g}</div>
              {items.map((s) => (
                <Node key={s.key} dot={s.dot} nom={s.label} mv={s.run === 'vivant' ? 'vivant' : run.label.split('_')[0] + '_' + (run.label.split('_')[1] || '')}
                  hi={hi.surfaces.has(s.key)} dim={dim(hi.surfaces.has(s.key))}
                  onClick={() => setSel(sel?.kind === 'surface' && sel.id === s.key ? null : { kind: 'surface', id: s.key })} />
              ))}
            </div>
          ))}
        </div>
      </div>

      {/* Q5 — dire ce que le clic montre + un moyen de tout éteindre */}
      <div className="mt-3 flex flex-wrap items-center justify-between gap-2 rounded-lg border border-line bg-surface-1 px-3.5 py-2.5">
        <span className="text-[12.5px] leading-relaxed text-txt-dim">
          Cliquez une source, un moteur ou une surface : tout ce qui est relié s'allume — en amont ce qui l'alimente, en aval ce qui s'en sert.
        </span>
        <button onClick={() => setSel(null)} disabled={!sel}
          className="shrink-0 rounded-lg border border-line px-2.5 py-1 text-[12px] text-txt-mut hover:text-txt disabled:opacity-30">
          Tout désélectionner
        </button>
      </div>

      {/* ── bas : radar + cohérence ── */}
      <div className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-[1.5fr_1fr]">
        <RadarBox radar={radar} />
        <div className="rounded-xl border border-line bg-surface-2 p-4">
          <div className="mb-3 font-mono text-[10.5px] uppercase tracking-[0.24em] text-txt-dim">
            Garde de cohérence{coherence.verifie_le ? ` · ${fmtReu(coherence.verifie_le, true)}` : ''}
          </div>
          {coherence.checks.length === 0 && <div className="text-[12px] text-txt-mut">{coherence.erreur || 'Non exécutée.'}</div>}
          {coherence.checks.map((c) => (
            <div key={c.libelle} className="flex items-center justify-between gap-3 border-b border-line py-2 text-[12.5px] last:border-b-0">
              <span className="text-txt-dim">{c.libelle}{c.detail && !c.ok ? <span className="text-coral"> — {c.detail}</span> : ''}</span>
              <span className={c.ok ? 'text-mint' : 'text-coral'}>{c.ok ? '✓' : '✕'}</span>
            </div>
          ))}
          {d.bascule.derniere && (
            <div className="flex items-center justify-between gap-3 py-2 text-[12.5px]">
              <span className="text-txt-dim">Caches purgés à la dernière bascule</span>
              <span className="text-mint">✓ {fmtReu(d.bascule.derniere.ts)}</span>
            </div>
          )}

          {/* runs basculables (F2.3) — Q1 : rendu progressif (le calcul d'écart est lent en base réelle) */}
          {qRuns.isLoading && (
            <div className="mt-4 text-[12px] text-txt-mut">Calcul des écarts au run servi en cours…</div>
          )}
          {runsBasculables.length > 0 && (
            <div className="mt-4">
              <div className="mb-2 font-mono text-[10px] uppercase tracking-[0.16em] text-txt-dim">Runs terminés · écart au servi</div>
              {runsBasculables.slice(0, 4).map((r) => (
                <div key={r.label} className="mb-1.5 flex items-center justify-between gap-2 rounded-lg border border-line bg-surface-1 px-3 py-2 text-[12px]">
                  <span className="min-w-0">
                    <span className="font-mono text-txt">{r.label}</span>
                    {r.ecart && <span className="text-txt-dim"> · {r.ecart.tiers_changes} tiers changent · dérive {r.ecart.derive_promues_pct > 0 ? '+' : ''}{r.ecart.derive_promues_pct}%</span>}
                  </span>
                  <button onClick={() => bascule.mutate(r.label)} disabled={!r.complet || bascule.isPending}
                    title={r.complet ? 'Basculer vers ce run' : r.motif}
                    className="shrink-0 rounded-lg border border-mint/40 bg-mint/10 px-2.5 py-1 text-[11.5px] font-medium text-mint disabled:opacity-30">
                    Basculer
                  </button>
                </div>
              ))}
            </div>
          )}

          {/* F5 — comment ça marche (replié) */}
          <div className="mt-4 rounded-lg border border-line px-3.5 py-2.5">
            <button onClick={() => setGlossaire((g) => !g)} className="text-[13px] font-semibold text-txt">
              Comment ça marche {glossaire ? '▴' : '▾'}
            </button>
            {glossaire && (
              <p className="mt-2 text-[12.5px] leading-relaxed text-txt-dim">
                <b className="text-txt">Source</b> : une donnée brute, avec son <b className="text-txt">millésime</b> (la version chargée).{' '}
                <b className="text-txt">Run</b> : le calcul global qui produit scores et cascade pour toutes les parcelles ; il est figé une fois terminé.{' '}
                <b className="text-txt">Bascule</b> : l'interrupteur qui désigne le run que tout le monde lit. Mettre à jour = injecter, calculer, basculer.{' '}
                Rien n'est automatique — la sentinelle prévient, vous injectez, vous lancez, vous basculez.
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

function ColHead({ titre, note, replie, onToggle }: { titre: string; note: string; replie: boolean; onToggle: () => void }) {
  return (
    <div className="flex items-center justify-between">
      <h3 className="font-mono text-[10.5px] uppercase tracking-[0.24em] text-txt-dim">{titre}</h3>
      <button onClick={onToggle} className="font-mono text-[11px] text-txt-mut hover:text-txt">
        {replie ? '▸' : '▾'} <span className="tracking-normal">{note}</span>
      </button>
    </div>
  )
}

function RadarBox({ radar }: { radar: AdminFlux['radar'] }) {
  const c = radar.compteurs as AdminFlux['radar']['compteurs'] & { biens?: number }
  // S5 — dénominateur M = total des biens (annonces distinctes) ; le KPI dit « rattachées N / M ».
  const totalBiens = c.biens ?? c.annonces
  const pts = radar.courbe.points
  const max = Math.max(1, ...pts.map((p) => p.paires))
  const line = pts.length >= 2
    ? pts.map((p, i) => `${i ? 'L' : 'M'}${(i * (600 / (pts.length - 1))).toFixed(1)},${(96 - (p.paires / max) * 84).toFixed(1)}`).join(' ')
    : ''
  return (
    <div className="rounded-xl border border-line bg-surface-2 p-4">
      <div className="mb-3 font-mono text-[10.5px] uppercase tracking-[0.24em] text-txt-dim">La donnée qui s'accumule · Radar</div>
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-5">
        <Kpi n={c.annonces} l="annonces collectées" d={c.annonces_semaine ? `+${c.annonces_semaine} cette semaine` : undefined} />
        <Kpi n={c.rattachees} l={`annonces rattachées / ${totalBiens.toLocaleString('fr-FR')}`} d={c.rattachees_pct != null ? `${c.rattachees_pct} %` : undefined} />
        <Kpi n={c.paires} l="paires annonce ↔ vente DVF" d={c.paires_semaine ? `+${c.paires_semaine} cette semaine` : undefined} key_ />
        <Kpi n={c.communes} l="communes couvertes" d={`sur ${c.communes_total}`} />
        <Kpi n={c.types} l="types couverts" />
      </div>
      <div className="relative mt-3 h-24 overflow-hidden rounded-lg border border-line bg-surface-1">
        <span className="absolute left-2.5 top-2 text-[10.5px] text-txt-dim">
          paires annonce ↔ vente, cumul {radar.courbe.depuis_le ? `depuis le ${fmtReu(radar.courbe.depuis_le)}` : '(relevés à venir)'}
        </span>
        {line && (
          <svg viewBox="0 0 600 96" preserveAspectRatio="none" className="h-full w-full">
            <path d={`${line} L600,96 L0,96Z`} fill="rgba(74,222,128,.08)" />
            <path d={line} fill="none" stroke="#4ADE80" strokeWidth="2" />
          </svg>
        )}
      </div>
      <div className="mt-2.5 flex flex-wrap gap-2">
        {radar.ecart.length === 0 && <span className="text-[12px] text-txt-mut">Aucune paire encore — l'écart demandé/acté apparaîtra ici.</span>}
        {radar.ecart.map((e: FluxRadarEcart) => (
          <div key={e.type} className="flex-1 rounded-lg border border-line bg-surface-1 px-3 py-2 text-[12px] text-txt-dim">
            <b className="block text-[14px] text-txt">{e.ecart_pct != null ? `${e.ecart_pct > 0 ? '+' : ''}${e.ecart_pct} %` : '—'}</b>
            écart demandé / acté · {e.type}
            <i className="block text-[10.5px] not-italic text-txt-mut">· {e.n} paire{e.n > 1 ? 's' : ''}{e.fragile ? ' · encore fragile' : ''}</i>
          </div>
        ))}
      </div>
    </div>
  )
}

function Kpi({ n, l, d, key_ }: { n: number; l: string; d?: string; key_?: boolean }) {
  return (
    <div className={`min-w-0 rounded-lg border bg-surface-1 px-3 py-2.5 ${key_ ? 'border-mint/45' : 'border-line'}`}>
      <div className="font-display text-[19px] font-bold tabular-nums text-mint">{n.toLocaleString('fr-FR')}</div>
      <div className="mt-0.5 text-[10.5px] leading-tight text-txt-dim">{l}</div>
      {d && <div className="mt-0.5 text-[10.5px] text-mint">{d}</div>}
    </div>
  )
}
