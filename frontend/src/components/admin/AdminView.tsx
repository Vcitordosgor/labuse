// DASHBOARD-V1 — TOUR DE CONTRÔLE (vue admin plein écran, maquette docs/audit-2026-08/DASHBOARD/
// maquette.html validée par Vic le 26/08 : rail 6 sections + LED santé en pied, héros Pilotage,
// mauve strictement réservé à la section IA). La visibilité côté front est du confort — chaque
// endpoint /admin/* porte la garde exiger_admin (403 client). Horodatages À L'HEURE RÉUNION
// (Indian/Reunion), jamais l'heure serveur brute (dette fuseau connue, mandat D3).
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { getAdminPilotage, getMoi, postAdminDegeler, type AdminPilotage } from '../../lib/api'
import { useApp } from '../../store/useApp'
import { LicencesSection } from './Licences'
import { IaSection } from './Ia'
import { DonneesSection } from './Donnees'
import { ProduitSection } from './Produit'
import { CourrierSection } from './Courrier'
import { RadarSection } from './Radar'
import { ContactsSection } from './Contacts'

// ADMIN-1 (AD2) — « sources »/« flux »/« cron » ne sont plus des sections de menu : elles sont
// FUSIONNÉES dans « donnees » (onglets Catalogue/Circuit/Horloge). Les valeurs restent dans le type
// pour REDIRIGER les anciens deep-links (voir `_rediriger` plus bas).
export type AdminSection = 'pilotage' | 'licences' | 'ia' | 'donnees' | 'sources' | 'flux' | 'produit' | 'courrier' | 'radar' | 'cron' | 'contacts' | 'programmes'

// ADMIN-1 (AD2) — redirection des anciennes routes vers la page fusionnée « Données ».
// LOT S1 — `programmes` n'a plus de section admin : le deep-link sort vers l'outil « Scan patrimoine »
// (traité dans le useEffect avec setView/setModule). Ici on retombe sur « pilotage » pour que le shell
// admin ne rende jamais une section morte le temps de la bascule.
const _rediriger = (s: AdminSection): AdminSection =>
  s === 'sources' || s === 'flux' || s === 'cron' ? 'donnees' : s === 'programmes' ? 'pilotage' : s

// ── helpers d'affichage ──
const fmtReu = (iso?: string | null, avecHeure = true) => {
  if (!iso) return '—'
  try {
    return new Intl.DateTimeFormat('fr-FR', {
      timeZone: 'Indian/Reunion', day: '2-digit', month: '2-digit',
      ...(avecHeure ? { hour: '2-digit', minute: '2-digit' } : {}),
    }).format(new Date(iso)).replace(',', '')
  } catch { return '—' }
}
const fmtEur = (v?: number | null, dec = 0) =>
  v == null ? '—' : v.toLocaleString('fr-FR', { minimumFractionDigits: dec, maximumFractionDigits: dec })
const MOIS_COURT = ['janv.', 'févr.', 'mars', 'avr.', 'mai', 'juin', 'juil.', 'août', 'sept.', 'oct.', 'nov.', 'déc.']
const moisLabel = (ym: string) => MOIS_COURT[Number(ym.slice(5, 7)) - 1] ?? ym

// ── briques DA (maquette : lbl mono-caps, big display, chips, panels) ──
export function Lbl({ children }: { children: React.ReactNode }) {
  return <div className="mb-2 flex flex-wrap items-center gap-2 font-mono text-[10px] uppercase tracking-[0.15em] text-txt-dim">{children}</div>
}
export function Chip({ tone = 'off', children, onClick }: { tone?: 'ok' | 'err' | 'warn' | 'off' | 'ia'; children: React.ReactNode; onClick?: () => void }) {
  const tones = {
    ok: 'text-mint border-mint/30 bg-mint/5', err: 'text-coral border-coral/30 bg-coral/5',
    warn: 'text-amber border-amber/30 bg-amber/5', off: 'text-txt-dim border-line-2',
    ia: 'text-cp-ia border-cp-ia-border bg-cp-ia-bg/40',
  }
  return (
    <span onClick={onClick} className={`inline-flex items-center gap-1.5 whitespace-nowrap rounded-full border px-2.5 py-0.5 font-mono text-[10.5px] ${tones[tone]} ${onClick ? 'cursor-pointer' : ''}`}>
      {children}
    </span>
  )
}
export function Panel({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return <div className={`mb-3.5 overflow-hidden rounded-xl border border-line bg-surface-2 ${className}`}>{children}</div>
}
export function PHead({ children }: { children: React.ReactNode }) {
  return <div className="flex items-center gap-2.5 border-b border-line px-4 py-3 font-mono text-[10px] uppercase tracking-[0.16em] text-txt-dim">{children}</div>
}
export function ActBtn({ children, onClick, tone = 'mint', disabled, title }: {
  children: React.ReactNode; onClick?: () => void; tone?: 'mint' | 'ghost' | 'danger' | 'ia'; disabled?: boolean; title?: string
}) {
  const tones = {
    mint: 'border-mint/40 bg-mint/10 text-mint', ghost: 'border-line-2 text-txt-mut hover:text-txt',
    danger: 'border-coral/40 bg-coral/5 text-coral', ia: 'border-cp-ia-border bg-cp-ia-bg/50 text-cp-ia',
  }
  return (
    <button onClick={onClick} disabled={disabled} title={title}
      className={`rounded-lg border px-3 py-1.5 text-xs font-medium transition-colors duration-quick disabled:opacity-40 ${tones[tone]}`}>
      {children}
    </button>
  )
}
export function H2({ children }: { children: React.ReactNode }) {
  return (
    <h2 className="mb-3 mt-7 flex items-center gap-2.5 font-mono text-[11px] uppercase tracking-[0.18em] text-txt-dim first:mt-0">
      {children}<span className="h-px min-w-[40px] flex-1 bg-line" />
    </h2>
  )
}

// ADMIN-1 (AD5) — tuile « À faire » : ambre dès qu'un geste attend (n>0), neutre sinon ; cliquable.
function ActTuile({ n, label, onClick }: { n: number; label: string; onClick: () => void }) {
  const actif = n > 0
  return (
    <div onClick={onClick}
      className={`cursor-pointer rounded-xl border px-4 py-4 transition-colors duration-quick ${
        actif ? 'border-amber/40 bg-gradient-to-b from-amber/5 to-transparent hover:border-amber' : 'border-line bg-surface-2 hover:border-line-2'}`}>
      <div className={`font-display text-2xl font-semibold ${actif ? 'text-amber' : 'text-txt-hi'}`}>{n}</div>
      <div className="mt-1 text-[11.5px] leading-snug text-txt-mut">{label}</div>
    </div>
  )
}

// A4 — mini-compteur des retours « Signaler » ouverts, ventilés par type. Une puce par type présent
// (bug/idée/question/donnée), cliquable → Produit. Un type inconnu s'affiche tel quel, jamais avalé.
const RETOUR_TYPE_LABELS: Record<string, string> = { bug: 'bug', idee: 'idée', question: 'question', donnee: 'donnée' }
const rtLabel = (n: number, t: string) => `${n} ${RETOUR_TYPE_LABELS[t] ?? t}${n > 1 ? 's' : ''}`
function RetoursParType({ data, onClick }: { data?: Record<string, number>; onClick: () => void }) {
  const entries = Object.entries(data ?? {}).filter(([, n]) => n > 0).sort((a, b) => b[1] - a[1])
  if (!entries.length) return null
  return (
    <div onClick={onClick} className="mt-2.5 flex cursor-pointer flex-wrap items-center gap-1.5 text-[11px] text-txt-mut hover:text-txt">
      <span className="font-mono uppercase tracking-[0.12em] text-txt-dim">retours →</span>
      {entries.map(([t, n]) => (
        <Chip key={t} tone="warn">{rtLabel(n, t)}</Chip>
      ))}
    </div>
  )
}

// ── sparkline CA (héros) ──
function Spark({ mois }: { mois: Record<string, number> }) {
  const entries = Object.entries(mois).slice(-6)
  if (entries.length < 2) return null
  const vals = entries.map(([, v]) => v)
  const max = Math.max(...vals, 1)
  const pts = vals.map((v, i) => [i * (300 / (vals.length - 1)), 40 - (v / max) * 36] as const)
  const line = pts.map(([x, y], i) => `${i ? 'L' : 'M'}${x.toFixed(1)},${y.toFixed(1)}`).join(' ')
  return (
    <svg viewBox="0 0 300 42" preserveAspectRatio="none" className="mt-3 h-[42px] w-full" aria-hidden="true">
      <defs>
        <linearGradient id="admin-spark" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#4ADE80" stopOpacity="0.3" /><stop offset="1" stopColor="#4ADE80" stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={`${line} L300,42 L0,42 Z`} fill="url(#admin-spark)" stroke="none" />
      <path d={line} fill="none" stroke="#4ADE80" strokeWidth="2" />
    </svg>
  )
}

// ═══════════════ PILOTAGE (D3) ═══════════════
function PilotageSection({ data, go }: { data: AdminPilotage | undefined; go: (s: AdminSection) => void }) {
  const qc = useQueryClient()
  const [degel, setDegel] = useState<string | null>(null)
  if (!data) return <div className="py-10 text-center text-xs text-txt-mut">Chargement…</div>
  const st = data.stripe
  const caEntries = Object.entries(st.ca_mois ?? {})
  const caCourant = caEntries.at(-1)
  const caPrec = caEntries.at(-2)
  const delta = caCourant && caPrec ? caCourant[1] - caPrec[1] : null
  const echecs = st.paiements_en_echec ?? 0
  const clientEchec = st.abonnements?.find((a) => a.statut === 'past_due')
  const sync = st.rapprochement && !st.rapprochement.indisponible
    ? st.rapprochement.comptes_sans_abo.length + st.rapprochement.abos_sans_compte.length === 0
    : null
  const degeler = async (sujet: string) => {
    setDegel(sujet)
    try { await postAdminDegeler(sujet); qc.invalidateQueries({ queryKey: ['admin-pilotage'] }) } finally { setDegel(null) }
  }
  const feedTone = (source: string | null): 'ok' | 'err' | 'warn' | 'off' =>
    source === 'E-mail' ? 'err' : source === 'Sécurité' ? 'warn' : source === 'Courrier' || source === 'Retour' ? 'ok' : 'off'
  return (
    <>
      {/* héros : CA · paiement en échec · licences actives */}
      <div className="mb-3.5 grid grid-cols-[1.4fr_1fr_1fr] gap-3.5 max-[1100px]:grid-cols-1">
        <div className="rounded-xl border border-line bg-surface-2 p-5">
          <Lbl>CA du mois · Stripe</Lbl>
          {st.configure ? st.erreur ? (
            <div className="text-sm text-amber">{st.erreur}</div>
          ) : (
            <>
              <div className="font-display text-4xl font-semibold tracking-tight text-txt-hi">
                {fmtEur(caCourant?.[1] ?? 0)}<span className="ml-1 text-base font-medium text-txt-mut">€</span>
              </div>
              {delta != null && (
                <div className={`mt-2 font-mono text-[11px] ${delta >= 0 ? 'text-mint' : 'text-coral'}`}>
                  {delta >= 0 ? '▲ +' : '▼ '}{fmtEur(delta)} € vs {caPrec ? moisLabel(caPrec[0]) : '—'}
                </div>
              )}
              <Spark mois={st.ca_mois ?? {}} />
            </>
          ) : (
            <div className="text-sm leading-relaxed text-txt-mut">
              <Chip tone="warn">Stripe non configuré</Chip>
              <p className="mt-2 text-xs">{st.raison}</p>
            </div>
          )}
        </div>
        <div className={`rounded-xl border p-5 ${echecs > 0 ? 'border-coral/40 bg-gradient-to-b from-coral/5 to-transparent' : 'border-line bg-surface-2'}`}>
          <Lbl>Paiement en échec</Lbl>
          <div className={`font-display text-4xl font-semibold ${echecs > 0 ? 'text-coral' : 'text-txt-hi'}`}>{st.configure ? echecs : '—'}</div>
          {clientEchec && (
            <div className="mt-2 text-xs text-txt-mut">
              <b className="text-txt">{clientEchec.nom_stripe ?? clientEchec.email ?? clientEchec.customer_id}</b>
              {clientEchec.prochaine_retentative && <><br />Stripe retente le {fmtReu(new Date(clientEchec.prochaine_retentative * 1000).toISOString(), false)}</>}
            </div>
          )}
          {echecs > 0 && <div className="mt-3"><ActBtn onClick={() => go('licences')}>Voir la licence →</ActBtn></div>}
          {st.configure && echecs === 0 && !st.erreur && <div className="mt-2 text-xs text-txt-mut">aucun — tout est encaissé</div>}
        </div>
        <div className="rounded-xl border border-line bg-surface-2 p-5">
          <Lbl>Licences actives</Lbl>
          <div className="font-display text-4xl font-semibold text-txt-hi">{data.licences_actives}</div>
          <div className="mt-2 text-xs text-txt-mut">
            Stripe ⇄ comptes app :{' '}
            {sync == null ? <span className="text-txt-dim">{st.configure ? 'indisponible' : 'Stripe non configuré'}</span>
              : sync ? <b className="text-mint">synchronisés ✓</b>
                : <b className="cursor-pointer text-amber" onClick={() => go('licences')}>orphelins à voir →</b>}
          </div>
        </div>
      </div>

      {/* ADMIN-1 (AD5) — deux rangées sémantiques : « À faire » (ambre, un geste attendu, cliquable) et
          « Santé · traction » (vert). La tuile Courrier a disparu (le courrier vit dans sa page). */}
      <H2>À faire</H2>
      <div className="grid grid-cols-4 gap-3.5 max-[1100px]:grid-cols-2">
        <ActTuile n={data.a_faire?.sources_nouvelle_version ?? 0}
          label="source(s) ont une nouvelle version → Données" onClick={() => go('donnees')} />
        <ActTuile n={data.a_faire?.essais_24h ?? 0}
          label="essai(s) expire(nt) sous 24 h → Comptes" onClick={() => go('licences')} />
        <ActTuile n={data.a_faire?.signalements_ouverts ?? 0}
          label="signalement(s) ouvert(s) → Produit" onClick={() => go('produit')} />
        <ActTuile n={data.a_faire?.manuelles_retard ?? 0}
          label="donnée(s) manuelle(s) en retard → Données" onClick={() => go('donnees')} />
      </div>

      {/* A4 — ventilation PAR TYPE des retours « Signaler » ouverts (bug/idée/question/donnée). Petites
          puces sous la rangée, cliquables → Produit. Absent/vide = « aucun retour ouvert ». */}
      <RetoursParType data={data.retours_par_type} onClick={() => go('produit')} />

      <H2>Santé · traction</H2>
      <div className="grid grid-cols-4 gap-3.5 max-[1100px]:grid-cols-2">
        <div className="rounded-xl border border-line bg-surface-2 px-4 py-4">
          <Lbl>MRR · licences</Lbl>
          <div className="font-display text-2xl font-semibold text-mint">
            {data.traction?.mrr_eur != null ? `${fmtEur(data.traction.mrr_eur)} €` : '—'}
          </div>
          <div className="mt-1 text-[11.5px] text-txt-mut">{data.licences_actives} licence(s) active(s)</div>
        </div>
        <div className="rounded-xl border border-line bg-surface-2 px-4 py-4">
          <Lbl>Garde de cohérence</Lbl>
          <div className={`font-display text-2xl font-semibold ${
            data.traction?.coherence?.ok === false ? 'text-coral' : data.traction?.coherence?.ok ? 'text-mint' : 'text-txt-mut'}`}>
            {data.traction?.coherence?.ok == null ? '—'
              : data.traction.coherence.ok ? `${data.traction.coherence.n_surfaces ?? ''} ✓`.trim() : 'divergence'}
          </div>
          <div className="mt-1 text-[11.5px] text-txt-mut">
            {data.traction?.coherence?.verifie_le ? `vérifié ${fmtReu(data.traction.coherence.verifie_le)}` : 'jamais passée'}
          </div>
        </div>
        <div className="rounded-xl border border-line bg-surface-2 px-4 py-4">
          <Lbl>Veilles · 7 jours</Lbl>
          <div className="font-display text-2xl font-semibold text-mint">{data.traction?.veilles_7j ?? 0}</div>
          <div className="mt-1 text-[11.5px] text-txt-mut">
            alertes zones suivies
            {/* SCORING-3 (L5.3) — retour terrain : étiquettes posées / semaine (cumul → seuil TERRAIN-1 : 200) */}
            {' '}· <span title={`Étiquettes de retour terrain posées (7 j) — ${data.etiquettes_terrain?.total ?? 0} au total, seuil TERRAIN-1 : 200`}>
              <b className="text-txt">{data.etiquettes_terrain?.semaine ?? 0}</b> retour{(data.etiquettes_terrain?.semaine ?? 0) > 1 ? 's' : ''} terrain
            </span>
          </div>
        </div>
        {/* FLUX-1 F3.5 — paires annonce ↔ vente DVF (mesure de finesse) ; cliquable vers Données/Circuit. */}
        <div className="cursor-pointer rounded-xl border border-line bg-surface-2 px-4 py-4 hover:border-line-2" onClick={() => go('donnees')}>
          <Lbl>Radar · paires DVF</Lbl>
          <div className="font-display text-2xl font-semibold text-mint">
            {data.radar ? data.radar.compteurs.paires.toLocaleString('fr-FR') : '—'}
            {data.radar && data.radar.compteurs.paires_semaine > 0 && <span className="ml-1 text-sm font-normal text-mint">+{data.radar.compteurs.paires_semaine}</span>}
          </div>
          <div className="mt-1 text-[11.5px] text-txt-mut">
            {data.radar ? `${data.radar.compteurs.annonces.toLocaleString('fr-FR')} annonces` : ''} · <span className="text-mint hover:underline">le flux →</span>
          </div>
          {/* S5 — annonces rattachées N / M (M = total biens ; repli sur annonces si l'ancien back ne l'envoie pas). */}
          {data.radar && (() => {
            const c = data.radar.compteurs as typeof data.radar.compteurs & { biens?: number }
            return (
              <div className="mt-0.5 text-[11.5px] text-txt-mut">
                <b className="text-txt">{c.rattachees.toLocaleString('fr-FR')}</b> / {(c.biens ?? c.annonces).toLocaleString('fr-FR')} rattachées
              </div>
            )
          })()}
        </div>
      </div>

      {/* fil : activité récente (event_log admin) + gels actifs avec Dégeler */}
      <H2>Activité récente</H2>
      <Panel>
        <ul>
          {data.gels.map((g) => (
            <li key={g.sujet} className="flex items-center gap-3.5 border-b border-line px-4 py-2.5 text-[13px] last:border-b-0">
              <span className="min-w-[92px] font-mono text-[10.5px] text-txt-dim">{fmtReu(g.ts)}</span>
              <Chip tone="warn">sécurité</Chip>
              <span className="min-w-0 flex-1 truncate">Gel anti-burst actif sur <span className="font-mono text-xs">{g.sujet}</span>{g.motif ? ` — ${g.motif}` : ''}</span>
              <ActBtn tone="ghost" disabled={degel === g.sujet} onClick={() => degeler(g.sujet)}>
                {degel === g.sujet ? 'Dégel…' : 'Dégeler'}
              </ActBtn>
            </li>
          ))}
          {data.fil.map((e) => (
            <li key={e.id} className="flex items-center gap-3.5 border-b border-line px-4 py-2.5 text-[13px] last:border-b-0">
              <span className="min-w-[92px] font-mono text-[10.5px] text-txt-dim">{fmtReu(e.ts)}</span>
              <Chip tone={feedTone(e.source)}>{(e.source ?? e.kind).toLowerCase()}</Chip>
              <span className="min-w-0 flex-1 truncate" title={e.detail ?? undefined}>{e.titre}</span>
              {e.source === 'Courrier' && <ActBtn tone="ghost" onClick={() => go('courrier')}>Traiter</ActBtn>}
              {e.source === 'Retour' && <ActBtn tone="ghost" onClick={() => go('produit')}>Voir</ActBtn>}
            </li>
          ))}
          {!data.fil.length && !data.gels.length && (
            <li className="px-4 py-6 text-center text-xs text-txt-mut">Aucun événement système récent.</li>
          )}
        </ul>
      </Panel>
    </>
  )
}

// ═══════════════ SHELL ═══════════════
// ADMIN-1 (AD2/AD4) — « Données » remplace Sources/Flux/Cron ; « Licences » devient « Comptes ».
const SECTIONS: { key: AdminSection; label: string; ic: string; ia?: boolean }[] = [
  { key: 'pilotage', label: 'Pilotage', ic: '◉' },
  { key: 'licences', label: 'Comptes', ic: '▣' },
  { key: 'ia', label: 'IA', ic: '✦', ia: true },
  { key: 'donnees', label: 'Données', ic: '☰' },
  { key: 'produit', label: 'Produit', ic: '◫' },
  { key: 'courrier', label: 'Courrier', ic: '✉' },
  { key: 'radar', label: 'Radar', ic: '◎' },
  { key: 'contacts', label: 'Contacts', ic: '☎' },
  // LOT S1 — « Programmes » n'est plus une section de menu : la collecte a été REPLIÉE dans l'outil
  // « Scan patrimoine » (onglet « Ce qu'ils construisent », geste admin discret). Les anciens
  // deep-links `programmes` atterrissent désormais sur le Scan (voir `_rediriger`).
]
// SOUS_TITRES : Partial car les valeurs de redirection (sources/flux/cron) n'ont pas de sous-titre propre.
const SOUS_TITRES: Partial<Record<AdminSection, string>> = {
  pilotage: 'comment va LABUSE ce matin ?',
  licences: 'que dois-je faire pour ce client, maintenant ?',
  ia: 'consommation, plafonds par compte, registre modèle',
  donnees: 'mes données sont-elles à jour ? — Catalogue · Circuit · CRON',
  produit: 'ce qui est utilisé · ce que les clients demandent',
  courrier: 'les demandes d’envoi — la page qui manquait',
  radar: 'la pige d’annonces — déposer, valider, re-vérifier',
  contacts: 'le carnet des communes — standard + contacts nommés',
  // LOT S1 — plus de sous-titre `programmes` : la collecte vit dans « Scan patrimoine ».
}

function Led({ ok, label, value }: { ok: 'ok' | 'warn' | 'err' | 'off'; label: string; value: string }) {
  const c = { ok: 'bg-mint shadow-[0_0_6px_#4ADE80]', warn: 'bg-amber shadow-[0_0_6px_#E0A94F]', err: 'bg-coral shadow-[0_0_6px_#E2726A]', off: 'bg-line-3' }[ok]
  return (
    <div className="flex items-center gap-2 py-1 text-xs text-txt-mut">
      <span className={`h-[7px] w-[7px] shrink-0 rounded-full ${c}`} />
      {label} <b className="font-mono text-[11px] font-medium text-txt">{value}</b>
    </div>
  )
}

export function AdminView() {
  const setView = useApp((s) => s.setView)
  const setModule = useApp((s) => s.setModule)
  const adminSection = useApp((s) => s.adminSection)
  const clearAdminSection = useApp((s) => s.clearAdminSection)
  const [section, setSection] = useState<AdminSection>(_rediriger((adminSection as AdminSection) || 'pilotage'))
  // SECTEUR-2 (T3) — deep-link depuis « Publier une annonce » (en-tête Radar) : ouvre la section
  // demandée puis consomme l'intention (le retour manuel sur une autre section n'est pas réécrasé).
  // ADMIN-1 (AD2) — les anciens deep-links sources/flux/cron sont redirigés vers « donnees ».
  // LOT S1 — un deep-link `programmes` sort de l'admin et ouvre l'outil « Scan patrimoine »
  // (setModule bascule déjà view→'cartes'), où la collecte vit désormais (onglet « construit »).
  useEffect(() => {
    if (!adminSection) return
    clearAdminSection()
    if (adminSection === 'programmes') { setModule('patrimoine'); return }
    setSection(_rediriger(adminSection as AdminSection))
  }, [adminSection, clearAdminSection, setModule])
  const moi = useQuery({ queryKey: ['moi'], queryFn: getMoi, staleTime: 3_600_000 })
  const admin = moi.data == null || moi.data.mode !== 'compte' || moi.data.role === 'admin'
  const pilotage = useQuery({ queryKey: ['admin-pilotage'], queryFn: getAdminPilotage, refetchInterval: 60_000, enabled: admin })
  if (!admin) {
    return (
      <div className="grid flex-1 place-items-center text-sm text-txt-mut">
        Tour de contrôle — réservée à l'administrateur LABUSE.
      </div>
    )
  }
  const d = pilotage.data
  const echecs = d?.stripe.paiements_en_echec ?? 0
  return (
    <div className="grid min-h-0 flex-1 grid-cols-[216px_1fr] overflow-hidden">
      {/* rail de la Tour de contrôle (maquette) */}
      <aside className="flex flex-col border-r border-line bg-surface-1 py-5">
        <div className="px-5 pb-5">
          <div className="font-display text-[17px] font-bold tracking-wide text-txt-hi">LA<em className="not-italic text-mint">BUSE</em></div>
          <div className="mt-1 font-mono text-[9.5px] tracking-[0.34em] text-txt-dim">TOUR DE CONTRÔLE</div>
        </div>
        <div className="flex flex-col gap-0.5 px-3">
          {SECTIONS.map((s) => {
            const on = section === s.key
            return (
              <button key={s.key} data-admin-section={s.key} onClick={() => setSection(s.key)}
                className={`flex items-center gap-2.5 rounded-lg px-3 py-2.5 text-left text-[13.5px] font-medium transition-colors duration-quick ${
                  on ? (s.ia ? 'bg-cp-ia-bg text-cp-ia' : 'bg-mint/10 text-mint') : 'text-txt-mut hover:bg-surface-2 hover:text-txt'}`}>
                <span className="w-[17px] text-center text-[13px] opacity-85">{s.ic}</span>{s.label}
                {s.key === 'pilotage' && echecs > 0 && (
                  <span className="ml-auto rounded-full bg-coral px-1.5 font-mono text-[10px] font-medium text-bg">{echecs}</span>
                )}
              </button>
            )
          })}
        </div>
        <div className="mt-auto border-t border-line px-5 pt-4">
          <Led ok={d?.sante.ok === false ? 'err' : d?.sante.ok ? 'ok' : 'off'} label="Serveur" value={d?.sante.ok == null ? '—' : d.sante.ok ? 'OK' : 'dégradé'} />
          <Led ok={d?.run.label ? 'ok' : 'off'} label="Run" value={d?.run.label ?? '—'} />
          <Led ok={d?.run.carte_le ? 'ok' : 'off'} label="Carte" value={fmtReu(d?.run.carte_le, false)} />
          {/* RETOURS-8 (R10) — la tuile lit le même endroit/motif que le job (cron .sql.gz + CLI .dump).
              « répertoire non configuré » distinct d'« aucun » (dossier vide) ; date + taille du dernier. */}
          <Led ok={d ? ({ ok: 'ok', ambre: 'warn', rouge: 'err', absent: 'err', non_configure: 'off' } as const)[d.backup.etat] ?? 'off' : 'off'}
            label="Backup" value={
              d?.backup.etat === 'non_configure' ? 'répertoire non configuré'
                : d?.backup.etat === 'absent' ? 'aucun'
                  : d?.backup.age_jours != null
                    ? `il y a ${Math.floor(d.backup.age_jours)} j${d.backup.taille_mo != null ? ` · ${d.backup.taille_mo} Mo` : ''}`
                    : '—'} />
          <button onClick={() => setView('cartes')} className="mt-3 text-xs text-mint hover:underline">Ouvrir l'app cliente →</button>
        </div>
      </aside>

      {/* contenu */}
      <div className="min-w-0 overflow-y-auto px-9 py-7">
        <div className="mx-auto max-w-[1120px]">
          <header className="mb-6 flex flex-wrap items-baseline gap-3.5">
            <h1 className="font-display text-2xl font-semibold tracking-tight text-txt-hi">{SECTIONS.find((s) => s.key === section)?.label}</h1>
            <span className="text-[13px] text-txt-dim">{SOUS_TITRES[section]}</span>
            <span className="ml-auto flex items-center gap-2">
              {section === 'pilotage' && d?.stripe.maj && <Chip>màj {fmtReu(d.stripe.maj)}</Chip>}
            </span>
          </header>
          {section === 'ia' && (
            <div className="mb-4 rounded-r-xl border-l-[3px] border-cp-ia bg-gradient-to-r from-cp-ia-bg/60 to-transparent px-4 py-2.5 font-mono text-[11px] tracking-[0.1em] text-cp-ia">
              SURFACE IA — le mauve est réservé à cette section, comme dans l'app
            </div>
          )}
          {section === 'pilotage' && <PilotageSection data={d} go={setSection} />}
          {section === 'licences' && <LicencesSection />}
          {section === 'ia' && <IaSection />}
          {section === 'donnees' && <DonneesSection />}
          {section === 'produit' && <ProduitSection />}
          {section === 'courrier' && <CourrierSection />}
          {section === 'radar' && <RadarSection />}
          {section === 'contacts' && <ContactsSection />}
        </div>
      </div>
    </div>
  )
}
