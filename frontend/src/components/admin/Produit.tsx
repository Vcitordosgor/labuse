// DASHBOARD-2 (Lot 5) — PRODUIT : ce que les clients utilisent · ce qu'ils nous disent.
// UNE seule file « Retours » : les signalements de la fiche + de l'annonce Radar + le « Signaler »
// global de l'app, fusionnés. Type chip unifié (donnée · bug · idée · question), lien vers l'endroit.
// Les comptes de test/interne (plan 'interne') sont masqués par défaut → le compteur = le même qu'au
// Pilotage (jauge Produit). Usage par outil : noms du MENU Outils (registry), CLIENTS seulement,
// 15 premiers puis « voir les N » ; les clés admin/internes (Tour de contrôle, Sources (page),
// Veille promoteurs) et les doublons `vue:radar`/`radar` sont écartés/fusionnés.
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import {
  getAdminProduit, getAdminSignalements, postAdminRetourStatut, postAdminSignalementStatut,
  postAdminSignalementsTraiterInternes,
} from '../../lib/api'
import { MODULES } from '../outils/registry'
import { ActBtn, Chip, Panel, PHead } from './AdminView'

const fmtReu = (iso?: string | null) => {
  if (!iso) return '—'
  try {
    return new Intl.DateTimeFormat('fr-FR', { timeZone: 'Indian/Reunion', day: '2-digit', month: '2-digit' }).format(new Date(iso))
  } catch { return '—' }
}

// ── libellé d'un outil capté = son nom au MENU (registry). Les vues client gardent un libellé propre ;
//    les clés admin/internes sont écartées (retour null), les doublons `vue:x`/`x` sont fusionnés. ──
const EXCLUS = new Set(['admin', 'sources', 'veille-promoteurs'])   // Tour de contrôle · Sources (page) · Veille promoteurs
const VUE_LABEL: Record<string, string> = {
  cartes: 'Carte / fiches', copilote: 'Copilote', projets: 'Projets', radar: 'Radar', veille: 'Veille', crm: 'CRM',
}
const outilLabel = (k: string): string | null => {
  const nk = k.startsWith('vue:') ? k.slice(4) : k
  if (EXCLUS.has(nk)) return null
  return VUE_LABEL[nk] ?? MODULES.find((m) => m.key === nk)?.label ?? nk
}

const PERIODES = [7, 30, 90] as const

// type unifié de la file « Retours » : donnée · bug · idée · question.
type RType = 'donnee' | 'bug' | 'idee' | 'question' | string
const typeMeta = (t: RType): { label: string; tone: 'ok' | 'err' | 'warn' | 'off' | 'ia' } => {
  switch (t) {
    case 'donnee': return { label: 'donnée', tone: 'ok' }
    case 'bug': return { label: 'bug', tone: 'err' }
    case 'idee': return { label: 'idée', tone: 'ia' }
    case 'question': return { label: 'question', tone: 'warn' }
    default: return { label: t, tone: 'off' }
  }
}
const TYPES = ['tous', 'donnee', 'bug', 'idee', 'question'] as const
type TypeFiltre = (typeof TYPES)[number]

// item fusionné de la file unique.
type RetourItem = {
  key: string; source: 'signalement' | 'retour'; id: number; ts: string | null
  type: RType; compte: string | null; interne: boolean; message: string
  ou: string; lien: string | null; statut: string
}

export function ProduitSection() {
  const qc = useQueryClient()
  const [jours, setJours] = useState<7 | 30 | 90>(30)
  const [voirTout, setVoirTout] = useState(false)
  const q = useQuery({ queryKey: ['admin-produit', jours], queryFn: () => getAdminProduit(jours), refetchInterval: 120_000 })
  const sig = useQuery({ queryKey: ['admin-signalements'], queryFn: () => getAdminSignalements(), refetchInterval: 120_000 })
  const [fStatut, setFStatut] = useState<'tous' | 'nouveau' | 'traite'>('nouveau')
  const [fType, setFType] = useState<TypeFiltre>('tous')
  const [voirTests, setVoirTests] = useState(false)

  // invalide TOUT ce qui porte un compteur Produit (les deux tables + le Pilotage).
  const invalider = () => {
    qc.invalidateQueries({ queryKey: ['admin-signalements'] })
    qc.invalidateQueries({ queryKey: ['admin-produit'] })
    qc.invalidateQueries({ queryKey: ['admin-pilotage'] })
  }
  const majSignalement = useMutation({
    mutationFn: ({ id, s }: { id: number; s: 'nouveau' | 'traite' }) => postAdminSignalementStatut(id, s), onSuccess: invalider,
  })
  const majRetour = useMutation({
    mutationFn: ({ id, s }: { id: number; s: 'nouveau' | 'traite' }) => postAdminRetourStatut(id, s), onSuccess: invalider,
  })
  const traiterInternes = useMutation({ mutationFn: postAdminSignalementsTraiterInternes, onSuccess: invalider })

  const d = q.data
  // ── file UNIQUE : signalements (fiche + annonce) + retours « Signaler » global ──
  const items: RetourItem[] = useMemo(() => {
    const out: RetourItem[] = []
    for (const r of sig.data?.signalements ?? []) {
      out.push({
        key: `s${r.id}`, source: 'signalement', id: r.id, ts: r.created_at,
        type: 'donnee', compte: r.compte_nom, interne: r.compte_plan === 'interne' || r.compte_id == null,
        message: r.commentaire ?? r.type_erreur, statut: r.statut,
        ou: r.type === 'fiche' ? `fiche ${r.parcelle_id ?? ''}${r.champ ? ` · ${r.champ}` : ''}` : `annonce${r.bien_id ? ` #${r.bien_id}` : ''}`,
        lien: r.fiche_lien,
      })
    }
    for (const r of d?.retours ?? []) {
      out.push({
        key: `r${r.id}`, source: 'retour', id: r.id, ts: r.ts,
        type: r.type, compte: r.compte, interne: r.compte_plan === 'interne' || r.compte == null,
        message: r.message, statut: r.statut,
        ou: r.section ? `fiche · ${r.section}` : 'app', lien: r.fiche_lien ?? null,
      })
    }
    return out.sort((a, b) => (b.ts ?? '').localeCompare(a.ts ?? ''))
  }, [sig.data, d])

  const nMasques = items.filter((r) => r.interne).length
  const baseVisibles = voirTests ? items : items.filter((r) => !r.interne)
  const nNouveaux = baseVisibles.filter((r) => r.statut === 'nouveau').length
  const retours = baseVisibles.filter((r) =>
    (fStatut === 'tous' || (fStatut === 'nouveau' ? r.statut === 'nouveau' : r.statut !== 'nouveau'))
    && (fType === 'tous' || r.type === fType))

  // ── usage par outil : agrégé par LIBELLÉ menu (dédup vue:x/x), clients seulement (déjà filtré back) ──
  const usageAgg = useMemo(() => {
    const m = new Map<string, number>()
    for (const u of d?.usage ?? []) { const lab = outilLabel(u.outil); if (lab == null) continue; m.set(lab, (m.get(lab) ?? 0) + u.n) }
    return [...m.entries()].map(([label, n]) => ({ label, n })).sort((a, b) => b.n - a.n)
  }, [d])
  const jamais = useMemo(() => {
    const vus = new Set(usageAgg.map((u) => u.label))
    return MODULES.filter((m) => !m.hidden && !vus.has(m.label)).map((m) => m.label)
  }, [usageAgg])

  if (!d) return <div className="py-10 text-center text-xs text-txt-mut">Chargement…</div>
  const usageVues = voirTout ? usageAgg : usageAgg.slice(0, 15)
  const max = Math.max(...usageAgg.map((u) => u.n), 1)

  return (
    <>
      {/* ── UNE file « Retours » : le même nombre qu'au Pilotage (tests masqués) ── */}
      <Panel>
        <PHead>
          Retours
          <span className="text-txt-dim">— fiche + annonce + « Signaler » global · {nNouveaux} nouveau{nNouveaux > 1 ? 'x' : ''}</span>
          <span className="ml-auto flex flex-wrap items-center gap-1.5">
            {(['nouveau', 'traite', 'tous'] as const).map((f) => (
              <Chip key={f} tone={fStatut === f ? 'ok' : 'off'} onClick={() => setFStatut(f)}>
                {f === 'nouveau' ? 'Nouveaux' : f === 'traite' ? 'Traités' : 'Tous'}
              </Chip>
            ))}
            <span className="mx-1 h-3 w-px bg-line-2" />
            {TYPES.map((t) => (
              <Chip key={t} tone={fType === t ? 'ok' : 'off'} onClick={() => setFType(t)}>{t === 'tous' ? 'Tous types' : typeMeta(t).label}</Chip>
            ))}
          </span>
        </PHead>
        <div className="flex flex-wrap items-center gap-2 border-b border-line px-4 py-2">
          {nMasques > 0 && (
            <Chip tone="off" onClick={() => setVoirTests((v) => !v)}>
              {voirTests ? 'masquer les tests' : `${nMasques} retour${nMasques > 1 ? 's' : ''} de test masqué${nMasques > 1 ? 's' : ''}`}
            </Chip>
          )}
          <ActBtn tone="ghost" onClick={() => traiterInternes.mutate()} disabled={traiterInternes.isPending}>
            {traiterInternes.isSuccess ? `✓ ${traiterInternes.data?.traites ?? 0} internes traités` : 'Traiter les internes/test'}
          </ActBtn>
        </div>
        <table className="w-full text-[13px]">
          <thead>
            <tr>
              {['Date', 'Client', 'Type', 'Où', 'Message', 'Statut'].map((h, i) => (
                <th key={h} className={`border-b border-line px-4 py-2.5 font-mono text-[9.5px] font-medium uppercase tracking-[0.12em] text-txt-dim ${i === 5 ? 'text-right' : 'text-left'}`}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {retours.map((r) => {
              const tm = typeMeta(r.type)
              const maj = r.source === 'signalement' ? majSignalement : majRetour
              return (
                <tr key={r.key} className="border-b border-line last:border-b-0 hover:bg-surface-3">
                  <td className="px-4 py-2.5 font-mono text-xs text-txt-dim">{fmtReu(r.ts)}</td>
                  <td className="px-4 py-2.5">{r.compte ?? <span className="text-txt-dim">interne</span>}</td>
                  <td className="px-4 py-2.5"><Chip tone={tm.tone}>{tm.label}</Chip></td>
                  <td className="px-4 py-2.5 text-xs">
                    {r.lien
                      ? <a href={`/socle/${r.lien}`} className="text-mint hover:underline">{r.ou} ↗</a>
                      : <span className="text-txt-dim">{r.ou}</span>}
                  </td>
                  <td className="max-w-[380px] px-4 py-2.5 text-txt-mut">« {r.message} »</td>
                  <td className="px-4 py-2.5 text-right">
                    {r.statut === 'nouveau'
                      ? <ActBtn tone="ghost" onClick={() => maj.mutate({ id: r.id, s: 'traite' })}>Traiter</ActBtn>
                      : <Chip tone="ok" onClick={() => maj.mutate({ id: r.id, s: 'nouveau' })}>Traité ✓ — rouvrir</Chip>}
                  </td>
                </tr>
              )
            })}
            {!retours.length && <tr><td colSpan={6} className="px-4 py-6 text-center text-xs text-txt-mut">Aucun retour {fStatut !== 'tous' || fType !== 'tous' ? 'pour ce filtre' : ''} — « Signaler » vit dans la fiche, sur les annonces Radar et en haut de l'app.</td></tr>}
          </tbody>
        </table>
        <div className="border-t border-line bg-surface-1 px-4 py-2.5 text-xs text-txt-mut">
          UNE file : signalements fiche + annonce + « Signaler » global. Le même nombre de nouveaux qu'à la
          jauge Produit du Pilotage (comptes de test/interne masqués, hors de tout chiffre).
        </div>
      </Panel>

      {/* ── Usage par outil — clients seulement, noms du menu Outils ── */}
      <Panel>
        <PHead>
          Usage par outil <span className="text-txt-dim">— clients seulement</span>
          <span className="ml-auto flex gap-1.5">
            {PERIODES.map((p) => (
              <Chip key={p} tone={jours === p ? 'ok' : 'off'} onClick={() => setJours(p)}>{p} j</Chip>
            ))}
          </span>
        </PHead>
        <div className="grid gap-2.5 p-4">
          {usageVues.map((u) => (
            <div key={u.label} className="grid grid-cols-[160px_1fr_70px] items-center gap-3 text-xs">
              <b className="truncate font-medium text-txt-mut">{u.label}</b>
              <div className="h-3.5 overflow-hidden rounded border border-line bg-bg">
                <div className="h-full rounded-sm bg-gradient-to-r from-mint-sub to-mint" style={{ width: `${Math.max(2, (u.n / max) * 100)}%` }} />
              </div>
              <span className="text-right font-mono text-xs text-txt">{u.n.toLocaleString('fr-FR')}</span>
            </div>
          ))}
          {!usageAgg.length && <div className="py-4 text-center text-xs text-txt-mut">Aucune ouverture d'outil captée côté client sur {jours} jours.</div>}
        </div>
        {usageAgg.length > 15 && (
          <button onClick={() => setVoirTout((v) => !v)} className="w-full border-t border-line px-4 py-2 text-[12.5px] text-mint hover:underline">
            {voirTout ? 'Réduire' : `Voir les ${usageAgg.length} outils ▸`}
          </button>
        )}
        <div className="border-t border-amber/40 bg-amber/[0.06] px-4 py-3 text-[12.5px]">
          <b className="text-amber">Jamais ouverts sur {jours} j :</b>{' '}
          {jamais.length
            ? <span className="text-txt-mut">{jamais.join(' · ')} — à montrer en démo, ou à repenser.</span>
            : <span className="text-txt-mut">aucun — tous les outils du menu ont été ouverts.</span>}
        </div>
        <div className="border-t border-line bg-surface-1 px-4 py-2.5 text-xs text-txt-mut">
          Ouvertures d'outil (événement léger, par licence). Noms = ceux du menu Outils ; l'admin et les
          surfaces internes (Tour de contrôle, Sources) sont exclus. « Jamais ouverts » = menu moins les outils captés.
        </div>
      </Panel>
    </>
  )
}
