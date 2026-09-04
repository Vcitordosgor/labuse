// DONNEES-2 — onglet « Mise à jour » : le cœur de la page Données, reconstruit selon
// docs/audit-2026-09/maquette-admin-donnees-v2.html. TROIS ÉTAPES VERTICALES — Injecter · Calculer ·
// Basculer — chacune porte SES informations et SES boutons : une action = un endroit, un chiffre =
// une liste. Fini le bandeau « 3 gestes » condensé ; fini les commandes éparpillées dans le Circuit.
//
// Partie B (D3 + backend étape 2) : chaque run porte un STATUT (en cours · terminé · servi · retour
// arrière · abandonné · ancien) ; l'étape 2 lit la PROGRESSION RÉELLE d'un run en cours (barre + %,
// commune) et sait l'ARRÊTER proprement ; « Lancer » refuse si un run tourne déjà. La bascule
// reconstruit les tables servies run-scopées pour le nouveau run (détaché) — la garde repasse au vert
// à la fin. Aucune mécanique réécrite : mêmes endpoints que le Circuit/Catalogue.
import { useEffect, useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  getAdminFlux, getAdminFluxRuns, getAdminFluxRunEtat, postAdminFluxLancerRun, postAdminFluxBascule,
  postAdminFluxArreterRun, postAdminSourceVeilleInjecter, postAdminCronRun,
  type AdminFlux, type FluxRunTermine, type FluxRunStatut,
} from '../../lib/api'

const fmtReu = (iso?: string | null, avecHeure = false) => {
  if (!iso) return '—'
  try {
    return new Intl.DateTimeFormat('fr-FR', {
      timeZone: 'Indian/Reunion', day: '2-digit', month: '2-digit',
      ...(avecHeure ? { hour: '2-digit', minute: '2-digit' } : {}),
    }).format(new Date(iso))
  } catch { return '—' }
}
// millésime lisible : un amont peut arriver en ISO complet (SITADEL : « 2026-08-28T16:05:37Z »)
// ou déjà propre (« 2026-07 ») — on ramène à AAAA-MM sans rien inventer, sinon on rend tel quel.
const fmtMil = (v?: string | null) => {
  if (!v) return '—'
  const m = v.match(/^(\d{4})-(\d{2})/)
  return m ? `${m[1]}-${m[2]}` : v
}
// libellé des moteurs qu'une source alimente (« scoring · signaux · rattachement »)
const MOTEUR_LBL: Record<string, string> = {
  scoring: 'scoring', signaux: 'signaux', sector_price: 'marché', cascade: 'cascade',
  capacite: 'capacité', rattachement: 'rattachement',
}
const alimente = (moteurs: string[]) =>
  moteurs.map((m) => MOTEUR_LBL[m] || m).join(' · ') || '—'

// libellé + ton de la pastille de statut d'un run (D3)
const STATUT: Record<FluxRunStatut, { txt: string; cls: string }> = {
  en_cours: { txt: 'en cours', cls: 'bg-amber/10 text-amber' },
  termine: { txt: 'terminé', cls: 'bg-mint/10 text-mint' },
  servi: { txt: 'servi', cls: 'bg-mint/10 text-mint' },
  retour_arriere: { txt: 'ancien run servi', cls: 'bg-white/5 text-txt-mut' },
  abandonne: { txt: 'abandonné', cls: 'bg-coral/10 text-coral' },
  ancien: { txt: 'ancien', cls: 'bg-white/5 text-txt-mut' },
}

type Tone = 'todo' | 'ok' | 'wait'
// une étape : un numéro dans un rail vertical + une carte qui porte tout (titre, sous-titre, actions)
function Etape({ n, tone, titre, sous, dernier, children }: {
  n: number; tone: Tone; titre: string; sous: string; dernier?: boolean; children: React.ReactNode
}) {
  const num = {
    todo: 'bg-amber/15 text-amber border-amber/40',
    ok: 'bg-mint/10 text-mint border-mint/40',
    wait: 'bg-surface-2 text-txt-mut border-line',
  }[tone]
  return (
    <div className="mb-3.5 grid grid-cols-[44px_1fr] gap-3.5">
      <div className="flex flex-col items-center">
        <span className={`flex h-[30px] w-[30px] flex-none items-center justify-center rounded-full border font-mono text-[13px] font-bold ${num}`}>{n}</span>
        {!dernier && <span className="mt-1.5 w-0.5 flex-1 bg-line" />}
      </div>
      <div className="rounded-xl border border-line bg-surface-2 p-4">
        <h2 className="flex flex-wrap items-center justify-between gap-2.5 text-[15px] font-semibold text-txt-hi">
          {titre}<small className="text-[12px] font-normal text-txt-dim">{sous}</small>
        </h2>
        {children}
      </div>
    </div>
  )
}

// une ligne d'action à l'intérieur d'une carte (libellé à gauche, bouton à droite)
function Ligne({ tirets, children, action }: { tirets?: boolean; children: React.ReactNode; action: React.ReactNode }) {
  return (
    <div className={`flex items-center justify-between gap-3 py-2.5 text-[13px] ${tirets ? 'border-t border-dashed border-line' : 'border-t border-line first:mt-2'}`}>
      <div className="min-w-0 flex-1">{children}</div>
      <div className="shrink-0">{action}</div>
    </div>
  )
}

export function MiseAJour() {
  const qc = useQueryClient()
  const q = useQuery({ queryKey: ['admin-flux'], queryFn: getAdminFlux, refetchInterval: 60_000 })
  // RETOURS-9 (Q1) — rendu progressif : les runs terminés + écarts (calcul ~50 s en base réelle) sont
  // servis à part. L'étape 3 se remplit quand cette requête revient ; le reste rend tout de suite.
  const qRuns = useQuery({ queryKey: ['admin-flux-runs'], queryFn: getAdminFluxRuns, refetchInterval: 60_000 })
  // DONNEES-2 (B3) — l'état du run EN COURS (barre + %), poll léger (3 s) pendant un run.
  const qEtat = useQuery({ queryKey: ['admin-flux-run-etat'], queryFn: getAdminFluxRunEtat, refetchInterval: 3_000 })
  const enCours = qEtat.data?.en_cours ?? null

  const [verifMsg, setVerifMsg] = useState<string | null>(null)
  const [voirAnciens, setVoirAnciens] = useState(false)
  const [reconstruire, setReconstruire] = useState<string | null>(null)   // run dont les tables se reconstruisent

  const invalider = () => {
    qc.invalidateQueries({ queryKey: ['admin-flux'] })
    qc.invalidateQueries({ queryKey: ['admin-flux-runs'] })
    qc.invalidateQueries({ queryKey: ['admin-flux-run-etat'] })
  }
  const lancer = useMutation({
    mutationFn: (recette: 'm36' | 'q_v12') => postAdminFluxLancerRun(recette),
    onSuccess: invalider,
  })
  const arreter = useMutation({
    mutationFn: (label: string) => postAdminFluxArreterRun(label),
    onSuccess: invalider,
  })
  const injecter = useMutation({
    mutationFn: (id: number) => postAdminSourceVeilleInjecter(id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['admin-flux'] }) },
  })
  const bascule = useMutation({
    mutationFn: (run: string) => postAdminFluxBascule(run),
    onSuccess: (r) => {
      if (r?.reconstruction?.lancee && r.nouveau) setReconstruire(r.nouveau)
      invalider()
    },
  })
  const verifierToutes = useMutation({
    mutationFn: () => postAdminCronRun('sentinelle-sources'),
    onSuccess: (r) => {
      setVerifMsg(r.ok ? 'Vérification lancée — les états se mettront à jour dans une minute.' : (r.motif ?? 'Lancement refusé.'))
      setTimeout(() => qc.invalidateQueries({ queryKey: ['admin-flux'] }), 4000)
    },
    onError: () => setVerifMsg('Lancement impossible.'),
  })

  const d: AdminFlux | undefined = q.data
  const runs = qRuns.data?.runs ?? []

  // ── étape 3 : trier les runs par STATUT (D3) ──
  const { recommande, rollback, masques } = useMemo(() => {
    const reco = runs.find((r) => r.statut === 'termine') ?? null
    const roll = runs.find((r) => r.statut === 'retour_arriere') ?? null
    // masqués = anciens + abandonnés + tout « terminé » au-delà du recommandé ; jamais le run en cours.
    const mask = runs.filter((r) => r !== reco && r !== roll && r.statut !== 'servi' && r.statut !== 'en_cours')
    return { recommande: reco, rollback: roll, masques: mask }
  }, [runs])

  // DONNEES-2 (B1) — pendant la reconstruction des tables servies, on poll /admin/flux plus vite ; dès
  // que la garde repasse au vert (6/6), la bannière disparaît.
  const cohOk = d?.coherence.ok === true
  useEffect(() => {
    if (!reconstruire) return
    if (cohOk) { setReconstruire(null); return }
    const t = setInterval(invalider, 5000)
    return () => clearInterval(t)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [reconstruire, cohOk])

  if (q.isError) return <div className="p-6 text-sm text-coral">Chargement impossible.</div>
  if (!d) return <div className="p-6 text-sm text-txt-dim">Chargement…</div>

  const { flux, coherence } = d
  const { run, comptes } = flux
  const injectables = flux.sources.filter((s) => s.dot === 'warn' && s.injectable)
  const plusRecentes = comptes.plus_recentes_que_run
  const autresSources = comptes.total - injectables.length

  const t1: Tone = injectables.length > 0 ? 'todo' : 'ok'
  const t2: Tone = enCours ? 'todo' : (plusRecentes > 0 ? 'todo' : 'ok')
  const t3: Tone = recommande ? 'todo' : 'ok'

  const pct = enCours?.pct ?? null
  const phaseLbl = enCours?.phase === 'cascade' ? `cascade${enCours.commune ? ` · ${enCours.commune}` : ''}`
    : enCours?.phase === 'scoring' ? 'scoring des parcelles'
    : enCours?.phase || 'démarrage'

  return (
    <div className="pb-6">
      {/* ── ÉTAPE 1 · INJECTER ── */}
      <Etape n={1} tone={t1} titre="Injecter"
        sous={`${comptes.surveillees} sources surveillées sur ${comptes.total} · dernière vérification ${fmtReu(flux.genere_le, true)}`}>
        <p className="mt-1.5 text-[12.5px] leading-relaxed text-txt-dim">
          L'agent lit chez chaque producteur et remplit la colonne <b className="text-txt">Amont</b> du Catalogue.
          Quand il trouve du neuf, il vous le propose ici. <b className="text-txt">Rien n'entre sans votre clic.</b>
        </p>
        {injectables.map((s) => (
          <Ligne key={s.id} action={
            <button onClick={() => injecter.mutate(s.id)} disabled={injecter.isPending}
              className="rounded-lg bg-mint px-3 py-2 text-[12.5px] font-semibold text-mint-ink disabled:opacity-40">
              {injecter.isPending && injecter.variables === s.id ? 'Injection…' : `Injecter ${s.amont_vu ? fmtMil(s.amont_vu) : 'cette version'} →`}
            </button>}>
            <b className="text-txt">{s.name}</b>
            <small className="mt-0.5 block text-[11px] text-txt-mut">
              servi {s.millesime || '—'}{s.amont_vu && <> · amont <span className="text-amber">{fmtMil(s.amont_vu)} disponible</span></>} · alimente {alimente(s.moteurs)}
            </small>
          </Ligne>
        ))}
        {injectables.length === 0 && (
          <div className="mt-3 rounded-lg border border-mint/25 bg-mint/5 px-3 py-2 text-[12.5px] text-mint">
            ● Rien à injecter — toutes les sources surveillées sont au niveau du producteur.
          </div>
        )}
        <Ligne tirets action={
          <div className="text-right">
            <button onClick={() => verifierToutes.mutate()} disabled={verifierToutes.isPending} data-verifier-toutes
              className="rounded-lg border border-line px-3 py-2 text-[12.5px] text-txt-mut hover:text-txt disabled:opacity-40">
              {verifierToutes.isPending ? 'Lancement…' : 'Vérifier toutes les sources'}
            </button>
            {verifMsg && <div className="mt-0.5 text-[10.5px] text-mint">{verifMsg}</div>}
          </div>}>
          <span className="text-[12px] text-txt-mut">
            Les {autresSources} autres sont à jour, en rappel manuel, ou non surveillées — détail dans le Catalogue.
            {' '}En local, le CRON ne sonne pas : lancez la vérification à la main.
          </span>
        </Ligne>
      </Etape>

      {/* ── ÉTAPE 2 · CALCULER ── */}
      <Etape n={2} tone={t2} titre="Calculer" sous="un run refait les scores de toutes les parcelles">
        <p className="mt-1.5 text-[12.5px] leading-relaxed text-txt-dim">
          Le run servi <span className="font-mono text-mint">{run.label}</span> a été calculé le <b className="text-txt">{fmtReu(run.calcule_le)}</b>.{' '}
          {plusRecentes > 0
            ? <><b className="text-amber">{plusRecentes} source{plusRecentes > 1 ? 's sont' : ' est'} plus récente{plusRecentes > 1 ? 's' : ''}</b> que lui.</>
            : <>Aucune source n'est plus récente que lui.</>}
          {' '}Un run ne change rien pour les clients tant qu'il n'est pas basculé (étape 3).
        </p>
        <Ligne action={
          <div className="flex items-center gap-2">
            <button onClick={() => lancer.mutate('m36')} disabled={lancer.isPending || !!enCours}
              className="rounded-lg bg-mint px-3.5 py-2 text-[12.5px] font-semibold text-mint-ink disabled:opacity-40">
              {lancer.isPending ? 'Lancement…' : 'Lancer un run →'}
            </button>
            <button onClick={() => lancer.mutate('q_v12')} disabled={lancer.isPending || !!enCours}
              title="Recette candidate SCORING-3 (artefact gelé q_v12), MÊME pipeline — jamais basculée automatiquement"
              className="rounded-lg border border-mint/40 bg-mint/10 px-3 py-2 text-[12px] font-medium text-mint disabled:opacity-40">
              Candidat q_v12 →
            </button>
          </div>}>
          <b className="text-txt">Lancer un nouveau run</b>
          <small className="mt-0.5 block text-[11px] text-txt-mut">recette servie (m36) ou candidate (q_v12) · tourne de nuit de préférence · un seul run à la fois</small>
        </Ligne>
        {lancer.isError && <div className="mt-2 text-[11.5px] text-coral">Un run est déjà en cours (ou un run identique existe) — arrêtez-le d'abord.</div>}

        {/* EN COURS — progression RÉELLE lue de l'état du run (phase, commune, %) + arrêt propre (B3) */}
        {enCours && (
          <div className="mt-2.5 rounded-lg border border-mint/30 bg-mint/[0.04] px-3 py-2.5">
            <div className="flex items-center justify-between gap-2 text-[12.5px]">
              <span className="min-w-0"><span className="text-txt-dim">En cours : </span><span className="font-mono text-mint">{enCours.label}</span>
                {' '}<span className="text-txt-mut">· {phaseLbl}</span></span>
              <button onClick={() => arreter.mutate(enCours.label)} disabled={arreter.isPending}
                className="shrink-0 rounded-lg border border-coral/40 bg-coral/5 px-2.5 py-1 text-[11.5px] font-medium text-coral disabled:opacity-40">
                {arreter.isPending ? 'Arrêt…' : 'Arrêter'}
              </button>
            </div>
            {/* barre RÉELLE si % connu, sinon indéterminée (démarrage) */}
            <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-surface-1">
              {pct != null
                ? <div className="h-full rounded-full bg-mint transition-[width] duration-500" style={{ width: `${Math.max(3, Math.min(100, pct))}%` }} />
                : <div className="h-full w-1/3 animate-pulse rounded-full bg-mint/70" />}
            </div>
            <div className="mt-1.5 text-[10.5px] text-txt-mut">
              {pct != null && <b className="text-txt-dim">{pct}% · </b>}
              {enCours.done != null && enCours.total != null && <>{enCours.done}/{enCours.total} étapes · </>}
              détaché — non servi tant que non basculé. « Arrêter » l'interrompt proprement (il passe « abandonné »).
            </div>
          </div>
        )}
      </Etape>

      {/* ── ÉTAPE 3 · BASCULER ── */}
      <Etape n={3} tone={t3} dernier
        titre="Basculer" sous={`${runs.filter((r) => !r.servi && r.complet).length} run(s) prêt(s) · le geste qui change ce que voient les clients · réversible`}>
        <p className="mt-1.5 text-[12.5px] leading-relaxed text-txt-dim">
          Lisez l'écart et la note de version, puis basculez. La garde de cohérence tourne aussitôt après.
        </p>

        {reconstruire && !cohOk && (
          <div className="mt-2 rounded-lg border border-amber/40 bg-amber/5 px-3 py-2 text-[12px] text-amber">
            ● Reconstruction des tables servies (carte + segments) pour <span className="font-mono">{reconstruire}</span> en cours — la garde de cohérence repasse au vert à la fin (~1–2 min).
          </div>
        )}

        {qRuns.isLoading && <div className="mt-2 text-[12px] text-txt-mut">Calcul des écarts au run servi en cours…</div>}

        {recommande && <RunCard r={recommande} best onBascule={() => bascule.mutate(recommande.label)} pending={bascule.isPending} />}
        {!recommande && !qRuns.isLoading && (
          <div className="mt-2 rounded-lg border border-line bg-surface-1 px-3 py-2.5 text-[12.5px] text-txt-mut">
            Aucun run candidat prêt — lancez-en un à l'étape 2, il apparaîtra ici une fois terminé.
          </div>
        )}

        {rollback && (
          <RunCard r={rollback} onBascule={() => bascule.mutate(rollback.label)} pending={bascule.isPending} />
        )}

        {masques.length > 0 && (
          <div className="mt-2.5">
            <button onClick={() => setVoirAnciens((v) => !v)} className="text-[12px] text-txt-mut hover:text-txt">
              {voirAnciens ? '▾' : '▸'} {masques.length} run{masques.length > 1 ? 's' : ''} ancien{masques.length > 1 ? 's' : ''} ou abandonné{masques.length > 1 ? 's' : ''} ({masques.slice(0, 3).map((r) => r.label).join(', ')}{masques.length > 3 ? '…' : ''})
            </button>
            {voirAnciens && masques.map((r) => (
              <RunCard key={r.label} r={r} onBascule={() => bascule.mutate(r.label)} pending={bascule.isPending} />
            ))}
          </div>
        )}

        {bascule.data && (
          <div className={`mt-2.5 text-[12px] ${bascule.data.ok ? 'text-mint' : 'text-coral'}`}>
            {bascule.data.ok
              ? `Bascule ${bascule.data.ancien} → ${bascule.data.nouveau} · ${bascule.data.caches_purges?.length ?? 0} caches purgés · reconstruction lancée`
              : (bascule.data.motif || 'Bascule refusée')}
          </div>
        )}
        {bascule.isError && <div className="mt-2 text-[12px] text-coral">Bascule refusée (run incomplet ou déjà servi).</div>}

        {/* garde de cohérence — la dernière connue (après la dernière bascule / au dernier passage) */}
        <div className="mt-4 font-mono text-[10px] uppercase tracking-[0.22em] text-txt-mut">
          Garde de cohérence{coherence.verifie_le ? ` · ${fmtReu(coherence.verifie_le, true)}` : ''}
        </div>
        <div className="mt-2 grid grid-cols-1 gap-x-5 sm:grid-cols-2">
          {coherence.checks.length === 0 && <div className="text-[12px] text-txt-mut">{coherence.erreur || 'Non exécutée.'}</div>}
          {coherence.checks.map((c) => (
            <div key={c.libelle} className="flex items-center justify-between gap-3 border-b border-line py-1.5 text-[12px]">
              <span className="text-txt-dim">{c.libelle}{c.detail && !c.ok ? <span className="text-coral"> — {c.detail}</span> : ''}</span>
              <span className={c.ok ? 'text-mint' : 'text-coral'}>{c.ok ? '✓' : '✕'}</span>
            </div>
          ))}
        </div>
        {d.bascule.derniere && (
          <div className="mt-2 text-[11px] text-txt-mut">
            Historique : {fmtReu(d.bascule.derniere.ts)} {d.bascule.derniere.ancien} → {d.bascule.derniere.nouveau}{d.bascule.derniere.par ? ` (${d.bascule.derniere.par})` : ''}
          </div>
        )}
      </Etape>
    </div>
  )
}

// une carte de run (recommandé / retour arrière / ancien / abandonné) avec statut, écart, note et bouton
function RunCard({ r, best, onBascule, pending }: {
  r: FluxRunTermine; best?: boolean; onBascule: () => void; pending: boolean
}) {
  const e = r.ecart
  const derive = e ? `${e.derive_promues_pct > 0 ? '+' : ''}${e.derive_promues_pct} %` : null
  const st = STATUT[r.statut] ?? STATUT.ancien
  const rollback = r.statut === 'retour_arriere'
  return (
    <div className={`mt-2.5 rounded-lg border p-3 ${best ? 'border-mint/50 bg-mint/[0.03]' : 'border-line bg-surface-1'} ${r.statut === 'abandonne' ? 'opacity-70' : ''}`}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="flex items-center gap-2">
          <span className="font-mono text-[13.5px] text-txt">{r.label}</span>
          {r.recette === 'q_v12' && <span className="rounded border border-mint/40 px-1 py-px font-mono text-[10px] text-mint">q_v12</span>}
          <span className={`rounded-full px-2 py-0.5 text-[10.5px] ${st.cls}`} title={r.motif}>{st.txt}</span>
          {best && <span className="rounded-full bg-mint/10 px-2 py-0.5 text-[10.5px] text-mint">recommandé</span>}
        </span>
        <button onClick={onBascule} disabled={!r.complet || pending}
          title={r.complet ? 'Basculer vers ce run' : r.motif}
          className={best
            ? 'rounded-lg bg-mint px-3 py-1.5 text-[12px] font-semibold text-mint-ink disabled:opacity-40'
            : 'rounded-lg border border-mint/40 bg-mint/10 px-3 py-1.5 text-[12px] font-medium text-mint disabled:opacity-30'}>
          {best ? `Basculer vers ${r.label} →` : rollback ? 'Revenir à ce run →' : 'Basculer ce run →'}
        </button>
      </div>
      <div className="mt-1.5 text-[12px] text-txt-dim">
        {r.calcule_le && <>{r.statut === 'abandonne' ? 'lancé le' : 'calculé le'} {fmtReu(r.calcule_le)} · </>}
        {r.statut === 'abandonne'
          ? <span className="text-txt-mut">{r.motif}</span>
          : e
            ? <><b className="text-txt">{e.tiers_changes.toLocaleString('fr-FR')}</b> parcelles changent de palier · Priorité <b className="text-txt">{e.promues_servi.toLocaleString('fr-FR')} → {e.promues_candidat.toLocaleString('fr-FR')}</b>{derive && <> ({derive})</>}</>
            : rollback ? <>c'est le retour arrière</> : <span className="text-txt-mut">écart non calculé (hors des runs affichés)</span>}
      </div>
      {r.note_de_version && (
        <details className="mt-1.5">
          <summary className="cursor-pointer text-[11.5px] text-mint">Note de version ▾</summary>
          <div className="mt-1 whitespace-pre-wrap border-l-2 border-line pl-2.5 text-[11.5px] leading-relaxed text-txt-dim">{r.note_de_version}</div>
        </details>
      )}
    </div>
  )
}
