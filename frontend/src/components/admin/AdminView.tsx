// DASHBOARD-V1 — TOUR DE CONTRÔLE (vue admin plein écran, maquette docs/audit-2026-08/DASHBOARD/
// maquette.html validée par Vic le 26/08 : rail 6 sections + LED santé en pied, héros Pilotage,
// mauve strictement réservé à la section IA). La visibilité côté front est du confort — chaque
// endpoint /admin/* porte la garde exiger_admin (403 client). Horodatages À L'HEURE RÉUNION
// (Indian/Reunion), jamais l'heure serveur brute (dette fuseau connue, mandat D3).
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { getAdminCircuit, getAdminLicences, getAdminPilotage, getMoi, postAdminDegeler, type AdminPilotage } from '../../lib/api'
import { useApp } from '../../store/useApp'
import { LicencesSection, estAToucher } from './Licences'
import { IaSection } from './Ia'
import { DonneesSection } from './Donnees'
import { ProduitSection } from './Produit'
import { CourrierSection } from './Courrier'
import { RadarSection } from './Radar'
import { ContactsSection } from './Contacts'
import { CronSection } from './Cron'

// ADMIN-1 (AD2) — « sources »/« flux » ne sont plus des sections de menu : elles sont FUSIONNÉES
// dans « donnees » (= le Circuit). CIRCUIT-P2 (lot 1.2) — « cron » redevient une page à part
// (lien dans Pilotage). Les valeurs restent dans le type pour REDIRIGER les anciens deep-links
// (voir `_rediriger` plus bas).
export type AdminSection = 'pilotage' | 'licences' | 'ia' | 'donnees' | 'destinations' | 'sources' | 'flux' | 'produit' | 'courrier' | 'radar' | 'cron' | 'contacts' | 'programmes'

// ADMIN-1 (AD2) — redirection des anciennes routes vers la page fusionnée « Données ».
// LOT S1 — `programmes` n'a plus de section admin : le deep-link sort vers l'outil « Scan patrimoine »
// (traité dans le useEffect avec setView/setModule). Ici on retombe sur « pilotage » pour que le shell
// admin ne rende jamais une section morte le temps de la bascule.
// CIRCUIT-P2 (lot 1.2) — le CRON a quitté « Données » : c'est de nouveau une page à part
// (`/admin/cron`, CronSection inchangée), son lien vit dans Pilotage. Les vieux deep-links
// sources/flux atterrissent toujours sur « donnees » (= le Circuit).
// DASHBOARD-2 (Lot 7) — « destinations » a quitté le rail : les vieux deep-links atterrissent sur
// « donnees » (le Circuit), où sa calibration vit désormais (détail du réservoir plu_destinations).
const _rediriger = (s: AdminSection): AdminSection =>
  s === 'sources' || s === 'flux' || s === 'destinations' ? 'donnees' : s === 'programmes' ? 'pilotage' : s

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
export function ActBtn({ children, onClick, tone = 'mint', disabled }: {
  children: React.ReactNode; onClick?: () => void; tone?: 'mint' | 'ghost' | 'danger' | 'ia'; disabled?: boolean; title?: string
}) {
  const tones = {
    mint: 'border-mint/40 bg-mint/10 text-mint', ghost: 'border-line-2 text-txt-mut hover:text-txt',
    danger: 'border-coral/40 bg-coral/5 text-coral', ia: 'border-cp-ia-border bg-cp-ia-bg/50 text-cp-ia',
  }
  return (
    <button onClick={onClick} disabled={disabled}
      className={`rounded-lg border px-3 py-1.5 text-xs font-medium transition-colors duration-quick ${tones[tone]}`}>
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

// ═══ DASHBOARD-4 (Lot 1) — briques du poste de pilotage (maquette v5) ═══
// UNE tuile = un grand nombre PLEIN ET OPAQUE + une étiquette, cliquable vers sa page. La charte (P2) :
// vert = normal · mauve = IA (famille, pas état) · rouge = EN RETARD ou À VÉRIFIER. Un compteur élevé
// n'est jamais rouge. Le chiffre est LU de la fonction serveur de sa page (jamais recompté ici).
type TuileTone = 'ok' | 'ia' | 'retard'
function Tuile({ valeur, unite, label, sous, tone, onClick }: {
  valeur: React.ReactNode; unite?: string; label: string; sous?: string; tone: TuileTone; onClick: () => void
}) {
  const fond = { ok: 'bg-mint text-[#08150C]', ia: 'bg-cp-ia text-[#140F26]', retard: 'bg-coral text-[#2A0D0D]' }[tone]
  return (
    <button type="button" onClick={onClick} data-tuile={label}
      className={`flex flex-col items-start rounded-xl px-[18px] pb-4 pt-[17px] text-left transition-[filter] duration-quick hover:brightness-[1.08] ${fond}`}>
      <div className="font-display text-[30px] font-bold leading-[1.05] tracking-[-0.03em]">
        {valeur}{unite && <span className="ml-0.5 text-[15px] font-medium opacity-[0.62]">{unite}</span>}
      </div>
      <div className="mt-2 text-[13px] font-semibold opacity-80">{label}</div>
      {sous && <div className="mt-0.5 text-[11px] font-medium opacity-[0.72]">{sous}</div>}
    </button>
  )
}

// « À faire, dans l'ordre » — une ligne = pastille · titre · phrase · verbe (maquette v5). `tone` r
// (ce qui cloche, pastille rouge), a (à faire, pastille verte), ok (rien). Le tri (poids) place ce
// qui cloche d'abord. La liste est CALCULÉE (jamais codée en dur) : deploiement + jobs + comptes.
type Todo = { cle: string; titre: string; phrase?: string; verbe: string; cible: AdminSection; tone: 'r' | 'a'; poids: number }
function TodoLigne({ t, go }: { t: Todo; go: (s: AdminSection) => void }) {
  const past = t.tone === 'r' ? 'bg-coral' : 'bg-mint'
  return (
    <div data-todo={t.cle} data-tone={t.tone}
      className="flex items-center gap-3.5 border-t border-line px-4 py-3 first:border-t-0">
      <span className={`h-[9px] w-[9px] flex-none rounded-full ${past}`} />
      <div className="min-w-0 flex-1 text-[13.5px] text-txt">
        {t.titre}{t.phrase && <small className="block text-[12px] text-txt-mut">{t.phrase}</small>}
      </div>
      <ActBtn tone="mint" onClick={() => go(t.cible)}>{t.verbe}</ActBtn>
    </div>
  )
}

// ═══════════════ PILOTAGE (DASHBOARD-2 · Lot 1) ═══════════════
// Poste de pilotage pleine largeur : 8 jauges (Argent · Clients · Circuit · Courrier · Radar · Produit ·
// IA · Système) sur deux rangées, chacune LIT la fonction serveur de sa page (compteur unique — jamais
// un chiffre inventé ici). Dessous : « À faire, dans l'ordre » (ce qui cloche d'abord) et le Journal.
const feedTone = (source: string | null): 'ok' | 'err' | 'warn' | 'off' =>
  source === 'E-mail' ? 'err' : source === 'Sécurité' ? 'warn' : source === 'Courrier' || source === 'Retour' ? 'ok' : 'off'
// famille de journal (chips), dérivée de la source de l'événement.
const familleDe = (source: string | null, kind: string): string => {
  const s = (source ?? '').toLowerCase()
  if (s.includes('courrier')) return 'Courrier'
  if (s.includes('retour')) return 'Produit'
  if (s.includes('radar') || s.includes('pige')) return 'Radar'
  if (s.includes('compte') || s.includes('licence') || s.includes('stripe')) return 'Comptes'
  if (s.includes('circuit') || s.includes('run') || s.includes('donnée') || s.includes('source')) return 'Circuit'
  if (s.includes('mail') || s.includes('sécurité') || s.includes('securite') || kind === 'systeme') return 'Système'
  return 'Système'
}

// ── Journal : filtrable par famille, groupé par jour (« passage »), « Voir plus — N / M » ──
type JournalItem = { key: string; ts: string | null; famille: string; source: string | null; titre: string; detail?: string | null; action?: 'courrier' | 'produit' | 'degel'; sujet?: string }
function Journal({ items, degel, degeler, go }: {
  items: JournalItem[]; degel: string | null; degeler: (s: string) => void; go: (s: AdminSection) => void
}) {
  const [famille, setFamille] = useState<string>('Tout')
  const [limite, setLimite] = useState(200)   // RECETTE-10 T6 — sous 200, tout d'un coup
  const familles = ['Tout', ...Array.from(new Set(items.map((i) => i.famille)))]
  const filtres = famille === 'Tout' ? items : items.filter((i) => i.famille === famille)
  const visibles = filtres.slice(0, limite)
  // en-têtes de jour (« passage » de l'horloge) : un séparateur quand le jour change.
  const jourDe = (iso: string | null) => (iso ? fmtReu(iso, false) : '—')
  let dernierJour = ''
  return (
    <>
      <div className="mb-2.5 flex flex-wrap items-center gap-1.5">
        {familles.map((f) => (
          <Chip key={f} tone={famille === f ? 'ok' : 'off'} onClick={() => { setFamille(f); setLimite(200) }}>{f}</Chip>
        ))}
      </div>
      <Panel>
        <ul>
          {visibles.map((e) => {
            const jour = jourDe(e.ts)
            const nouveauJour = jour !== dernierJour
            dernierJour = jour
            return (
              <li key={e.key}>
                {nouveauJour && (
                  <div className="border-b border-line bg-surface-1 px-4 py-1 font-mono text-[9.5px] uppercase tracking-[0.14em] text-txt-dim">{jour}</div>
                )}
                <div className="flex items-center gap-3.5 border-b border-line px-4 py-2.5 text-[13px] last:border-b-0">
                  <span className="min-w-[64px] font-mono text-[10.5px] text-txt-dim">{fmtReu(e.ts)?.slice(-5)}</span>
                  <Chip tone={feedTone(e.source)}>{e.famille.toLowerCase()}</Chip>
                  <span className="min-w-0 flex-1 truncate">{e.titre}</span>
                  {e.action === 'courrier' && <ActBtn tone="ghost" onClick={() => go('courrier')}>Traiter</ActBtn>}
                  {e.action === 'produit' && <ActBtn tone="ghost" onClick={() => go('produit')}>Voir</ActBtn>}
                  {e.action === 'degel' && (
                    <ActBtn tone="ghost" disabled={degel === e.sujet} onClick={() => e.sujet && degeler(e.sujet)}>
                      {degel === e.sujet ? 'Dégel…' : 'Dégeler'}
                    </ActBtn>
                  )}
                  {!e.action && <span className="whitespace-nowrap font-mono text-[10px] text-txt-dim">par système</span>}
                </div>
              </li>
            )
          })}
          {!filtres.length && <li className="px-4 py-6 text-center text-xs text-txt-mut">Aucun événement système récent.</li>}
        </ul>
        {limite < filtres.length && (
          <button onClick={() => setLimite((n) => n + 200)} className="w-full border-t border-line px-4 py-2.5 text-xs text-txt-mut hover:text-txt">
            Voir {Math.min(200, filtres.length - visibles.length)} de plus — {visibles.length} / {filtres.length}
          </button>
        )}
      </Panel>
    </>
  )
}

// DASHBOARD-4 (P4) — un compte de TEST ne doit apparaître nulle part dans le Journal.
const estCompteTest = (s?: string | null): boolean => {
  const t = (s ?? '').toLowerCase()
  return t.includes('[ct-test]') || t.includes('@labuse.test') || t.includes('@test.com') || t.includes('ton-email@test')
}

function PilotageSection({ data, go, majAt }: { data: AdminPilotage | undefined; go: (s: AdminSection) => void; majAt?: number }) {
  const qc = useQueryClient()
  const [degel, setDegel] = useState<string | null>(null)
  // compteur unique : la tuile « Tâches » lit le MÊME endpoint que la page Données (le Circuit).
  const circuit = useQuery({ queryKey: ['admin-circuit'], queryFn: getAdminCircuit, refetchInterval: 120_000 })
  // « à toucher » = MÊME endpoint + MÊME fonction (prochaineAction) que le segment par défaut de Comptes.
  const licencesQ = useQuery({ queryKey: ['admin-licences'], queryFn: getAdminLicences, refetchInterval: 120_000 })
  const degeler = async (sujet: string) => {
    setDegel(sujet)
    try { await postAdminDegeler(sujet); qc.invalidateQueries({ queryKey: ['admin-pilotage'] }) } finally { setDegel(null) }
  }
  if (!data) return <div className="py-10 text-center text-xs text-txt-mut">Chargement…</div>
  const st = data.stripe
  const caCourant = Object.entries(st.ca_mois ?? {}).at(-1)?.[1] ?? 0

  // ── les cinq chiffres des tuiles, chacun LU de la fonction serveur de sa page (jamais recompté ici) ──
  const licencesActives = data.licences_actives
  const iaMois = data.ia_mois?.cout_eur ?? 0
  // Courriers DÉPOSABLES (P1) : ce qui peut réellement partir (≠ a_deposer), + ancienneté du plus vieux.
  const cr = data.courrier ?? { a_deposer: 0, en_cours: 0, clos: 0 }
  const deposables = cr.deposables ?? cr.a_deposer ?? 0
  const plusAncienJ = cr.plus_ancien_ouvre_j ?? null
  const SEUIL_COURRIER_J = 5   // P2 — rouge seulement si le plus ancien attend > 5 jours OUVRÉS.
  const courrierRouge = plusAncienJ != null && plusAncienJ > SEUIL_COURRIER_J
  // Tâches du circuit (P1) = le total du Résumé de la page Données. Rouge = « à corriger » (une ligne
  // rouge du Résumé) ou un verrou cassé — jamais rouge juste parce que le compteur est élevé (P2).
  const resume = circuit.data?.resume as { total?: number; groupes?: { lignes?: { couleur?: string }[] }[] } | undefined
  const circuitTotal = resume?.total ?? null
  const verrousCasses = data.verrous && data.verrous.ok != null && data.verrous.sur != null ? data.verrous.sur - data.verrous.ok : 0
  const circuitRouge = verrousCasses > 0 || (resume?.groupes ?? []).some((g) => (g.lignes ?? []).some((l) => l.couleur === 'rouge'))

  // DASHBOARD-4 (K3) — MÊME fonction que le segment « À toucher » de Comptes (une seule définition).
  const aToucher = (licencesQ.data?.licences ?? []).filter((l) => estAToucher(l)).length

  // ── cinq tuiles pleines et opaques, dans l'ordre de la maquette (P1) ──
  const tuiles: { cle: string; valeur: React.ReactNode; unite?: string; label: string; sous?: string; tone: TuileTone; cible: AdminSection }[] = [
    { cle: 'ca', valeur: st.configure ? fmtEur(caCourant) : '—', unite: st.configure ? '€' : undefined,
      label: "Chiffre d'affaires du mois", tone: 'ok', cible: 'licences' },
    { cle: 'licences', valeur: licencesActives, label: `Licence${licencesActives > 1 ? 's' : ''} active${licencesActives > 1 ? 's' : ''}`, tone: 'ok', cible: 'licences' },
    { cle: 'ia', valeur: fmtEur(iaMois, 2), unite: '€', label: 'Coût IA du mois', tone: 'ia', cible: 'ia' },
    { cle: 'courrier', valeur: deposables, label: `Courrier${deposables > 1 ? 's' : ''} à déposer`,
      sous: plusAncienJ != null ? `le plus ancien attend ${plusAncienJ} j ouvré${plusAncienJ > 1 ? 's' : ''} · seuil ${SEUIL_COURRIER_J} j` : undefined,
      tone: courrierRouge ? 'retard' : 'ok', cible: 'courrier' },
    { cle: 'taches', valeur: circuitTotal ?? '…', label: 'Tâches à effectuer', tone: circuitTotal != null && circuitRouge ? 'retard' : 'ok', cible: 'donnees' },
  ]

  // ── « À faire, dans l'ordre » : UNE liste CALCULÉE (deploiement + jobs + comptes), jamais codée en
  //    dur. Chaque ligne = pastille · titre · phrase · verbe. Triée par poids (ce qui cloche d'abord). ──
  const dep = data.deploiement
  const avance = dep?.avance ?? null
  const sondesN = data.sondes_muettes?.n ?? null
  const horlogeManquant = (data.horloge?.attendus ?? 0) - (data.horloge?.poses ?? 0)
  const depDate = dep?.depuis ? fmtReu(dep.depuis, false) : null
  const aFaire: Todo[] = []
  // Déployer : main en avance sur la prod de N commits — rouge tant que N > 0 (P3).
  if (avance != null && avance > 0) aFaire.push({ cle: 'deployer', tone: 'r', poids: 100,
    titre: `Déployer — ${avance} commit${avance > 1 ? 's' : ''} d'avance sur la prod`,
    phrase: `main est en avance sur la production${depDate ? `, dernier déploiement le ${depDate}` : ''} — lancer deploy.sh sur le VPS`,
    verbe: 'Voir', cible: 'cron' })
  // Sondes muettes : G8 les compte ; la CAUSE vraie est que les horloges ne sont pas posées en prod →
  // UNE ligne (pas N), qui renvoie à Déployer (P3).
  if (sondesN != null && sondesN > 0 && horlogeManquant > 0) aFaire.push({ cle: 'sondes', tone: 'r', poids: 96,
    titre: `Sondes muettes en prod — ${sondesN} source${sondesN > 1 ? 's' : ''} sans contrôle`,
    phrase: 'les horloges ne sont pas posées en prod : rien ne se met à jour seul — déployer les pose',
    verbe: 'Voir', cible: 'cron' })
  // Sauvegarde : rouge si > 24 h (ou absente / non configurée) (P3).
  const bk = data.backup
  const bkRetard = bk?.etat === 'rouge' || bk?.etat === 'ambre' || bk?.etat === 'absent' || bk?.etat === 'non_configure' || (bk?.age_jours != null && bk.age_jours > 1)
  if (bkRetard) aFaire.push({ cle: 'backup', tone: 'r', poids: 92,
    titre: 'Sauvegarder la base',
    phrase: bk.etat === 'non_configure' ? 'aucun répertoire de sauvegarde configuré'
      : bk.etat === 'absent' ? 'aucun dump connu — la base n\'est pas sauvegardée'
        : `dernière sauvegarde il y a ${bk.age_jours != null ? Math.floor(bk.age_jours) : '?'} j — seuil 24 h`,
    verbe: 'Voir', cible: 'cron' })
  // Courriers déposables : rouge seulement au-delà du seuil ouvré, sinon simple tâche (P1/P2).
  if (deposables > 0) aFaire.push({ cle: 'courrier', tone: courrierRouge ? 'r' : 'a', poids: courrierRouge ? 84 : 60,
    titre: `Déposer ${deposables} courrier${deposables > 1 ? 's' : ''}`,
    phrase: plusAncienJ != null ? `le plus ancien attend ${plusAncienJ} j ouvré${plusAncienJ > 1 ? 's' : ''}${courrierRouge ? ` (seuil ${SEUIL_COURRIER_J} j dépassé)` : ''}` : undefined,
    verbe: 'Déposer', cible: 'courrier' })
  // Sources signalées par les agents (une version plus récente publiée) (P3).
  const srcSignalees = data.a_faire?.sources_nouvelle_version ?? 0
  if (srcSignalees > 0) aFaire.push({ cle: 'sources', tone: 'a', poids: 55,
    titre: `Relire ${srcSignalees} source${srcSignalees > 1 ? 's' : ''} signalée${srcSignalees > 1 ? 's' : ''} par les agents`,
    phrase: 'une version plus récente a été publiée', verbe: 'Voir', cible: 'donnees' })
  // Comptes à toucher (P3) — même fonction que le segment « À toucher » de Comptes.
  if (aToucher > 0) aFaire.push({ cle: 'comptes', tone: 'a', poids: 50,
    titre: `Toucher ${aToucher} client${aToucher > 1 ? 's' : ''}`,
    phrase: 'invitation, essai qui se termine ou carte à relancer', verbe: 'Ouvrir', cible: 'licences' })
  aFaire.sort((a, b) => b.poids - a.poids)

  // ── journal : gels (sécurité) + fil (event_log système). Les 3 derniers jours, comptes de test
  //    masqués (P4). Fusionnés, triés récents d'abord. ──
  const il3jours = Date.now() - 3 * 86_400_000
  const items: JournalItem[] = [
    ...data.gels.map((g) => ({ key: `g${g.sujet}`, ts: g.ts, famille: 'Système', source: 'Sécurité',
      titre: `Gel anti-burst sur ${g.sujet}${g.motif ? ` — ${g.motif}` : ''}`, action: 'degel' as const, sujet: g.sujet })),
    ...data.fil.map((e) => ({ key: `f${e.id}`, ts: e.ts, famille: familleDe(e.source, e.kind), source: e.source,
      titre: e.titre, detail: e.detail, action: e.source === 'Courrier' ? 'courrier' as const : e.source === 'Retour' ? 'produit' as const : undefined })),
  ]
    .filter((e) => e.ts != null && new Date(e.ts).getTime() >= il3jours)          // P4 — les 3 derniers jours
    .filter((e) => !estCompteTest(e.titre) && !estCompteTest((e as { detail?: string | null }).detail) && !estCompteTest((e as { sujet?: string }).sujet))   // P4 — tests masqués
    .sort((a, b) => (b.ts ?? '').localeCompare(a.ts ?? ''))

  return (
    <>
      {/* cinq tuiles pleines et opaques (maquette v5) — un grand nombre + une étiquette, cliquables. */}
      <div className="grid grid-cols-5 gap-3.5 max-[1100px]:grid-cols-2">
        {tuiles.map((t) => (
          <Tuile key={t.cle} valeur={t.valeur} unite={t.unite} label={t.label} sous={t.sous} tone={t.tone} onClick={() => go(t.cible)} />
        ))}
      </div>

      <H2>À faire, dans l'ordre</H2>
      <Panel>
        {aFaire.length
          ? aFaire.map((t) => <TodoLigne key={t.cle} t={t} go={go} />)
          : <div className="px-4 py-4 text-[13px] text-txt-mut">Rien à faire aujourd'hui — tout est à jour.</div>}
      </Panel>
      <p className="mt-1.5 text-[10.5px] text-txt-dim">Liste calculée en direct (déploiement, jobs, comptes) — les lignes à zéro ne s'affichent pas.</p>

      <H2>Journal</H2>
      <Journal items={items} degel={degel} degeler={degeler} go={go} />
      <p className="mt-2 text-[10.5px] text-txt-dim">
        {/* P4 — les trois derniers jours, comptes de test masqués. Chiffres relus en direct de la base. */}
        Les trois derniers jours, comptes de test masqués. Chiffres relevés en direct{majAt ? ` · dernier relevé à ${fmtReu(new Date(majAt).toISOString())}` : ''}.
        Chaque tuile lit la fonction serveur de sa page — ouvrir la page donne le même nombre.
      </p>
    </>
  )
}

// ═══════════════ SHELL ═══════════════
// ADMIN-1 (AD2/AD4) — « Données » remplace Sources/Flux/Cron ; « Licences » devient « Comptes ».
// DASHBOARD-2 (Lot 1) — ordre du rail = maquette v1 (Pilotage · Comptes · Données · Courrier · Radar ·
// Produit · IA · Contacts). Destinations a quitté le rail (Lot 7 : devient un détail du Circuit).
const SECTIONS: { key: AdminSection; label: string; ic: string; ia?: boolean }[] = [
  { key: 'pilotage', label: 'Pilotage', ic: '◉' },
  { key: 'licences', label: 'Comptes', ic: '▣' },
  { key: 'donnees', label: 'Données', ic: '☰' },
  { key: 'courrier', label: 'Courrier', ic: '✉' },
  { key: 'radar', label: 'Radar', ic: '◎' },
  { key: 'produit', label: 'Produit', ic: '◫' },
  { key: 'ia', label: 'IA', ic: '✦', ia: true },
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
  donnees: 'le circuit de la donnée : d’où elle vient, où elle va, ce qui cloche',
  cron: 'les jobs planifiés — dernier passage, prochain, lancer maintenant',
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
  // DASHBOARD-2 (Lot 1) — le compteur « Données » du rail lit la MÊME fonction que la page Circuit et
  // que la jauge Circuit (queryKey partagée : un seul calcul, trois lectures — compteur unique).
  const circuit = useQuery({ queryKey: ['admin-circuit'], queryFn: getAdminCircuit, refetchInterval: 120_000, enabled: admin })
  if (!admin) {
    return (
      <div className="grid flex-1 place-items-center text-sm text-txt-mut">
        Tour de contrôle — réservée à l'administrateur LABUSE.
      </div>
    )
  }
  const d = pilotage.data
  const echecs = d?.stripe.paiements_en_echec ?? 0
  // DASHBOARD-2 (Lot 1) — chaque nav porte le compteur de sa page (le même nombre que la page ouvre).
  const circuitTotal = (circuit.data?.resume?.total as number | undefined) ?? null
  const produitOuverts = d ? (d.a_faire?.signalements_ouverts ?? 0) + Object.values(d.retours_par_type ?? {}).reduce((a, b) => a + b, 0) : 0
  const navCount: Partial<Record<AdminSection, number>> = {
    licences: d?.licences_actives ?? 0,
    donnees: circuitTotal ?? 0,
    courrier: d?.courrier?.a_deposer ?? 0,
    produit: produitOuverts,
  }
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
            const cnt = navCount[s.key]
            return (
              <button key={s.key} data-admin-section={s.key} onClick={() => setSection(s.key)}
                className={`flex items-center gap-2.5 rounded-lg px-3 py-2.5 text-left text-[13.5px] font-medium transition-colors duration-quick ${
                  on ? (s.ia ? 'bg-cp-ia-bg text-cp-ia' : 'bg-mint/10 text-mint') : 'text-txt-mut hover:bg-surface-2 hover:text-txt'}`}>
                <span className="w-[17px] text-center text-[13px] opacity-85">{s.ic}</span>{s.label}
                {s.key === 'pilotage' && echecs > 0 && (
                  <span className="ml-auto rounded-full bg-coral px-1.5 font-mono text-[10px] font-medium text-bg">{echecs}</span>
                )}
                {/* compteur de la page (maquette : la pastille .n) — masqué à 0, jamais décoratif. */}
                {cnt != null && cnt > 0 && (
                  <span className={`ml-auto rounded-full px-1.5 font-mono text-[10px] font-medium ${on ? 'bg-mint/20 text-mint' : 'bg-surface-2 text-txt-mut'}`}>{cnt}</span>
                )}
              </button>
            )
          })}
        </div>
        <div className="mt-auto border-t border-line px-5 pt-4">
          <Led ok={d?.sante.ok === false ? 'err' : d?.sante.ok ? 'ok' : 'off'} label="Serveur" value={d?.sante.ok == null ? '—' : d.sante.ok ? 'OK' : 'dégradé'} />
          <Led ok={d?.run.label ? 'ok' : 'off'} label="Run servi" value={d?.run.label ?? '—'} />
          {/* RETOURS-8 (R10) — la tuile lit le même endroit/motif que le job (cron .sql.gz + CLI .dump).
              DASHBOARD-2 (Lot 1) — la VRAIE date du dernier dump (mtime), pas « répertoire non configuré »
              par défaut : ambre/rouge selon l'âge, « non configuré » / « aucun » distincts. */}
          <Led ok={d ? ({ ok: 'ok', ambre: 'warn', rouge: 'err', absent: 'err', non_configure: 'off' } as const)[d.backup.etat] ?? 'off' : 'off'}
            label="Backup" value={
              d?.backup.etat === 'non_configure' ? 'non configuré'
                : d?.backup.etat === 'absent' ? 'aucun'
                  : d?.backup.mtime
                    ? fmtReu(d.backup.mtime)
                    : d?.backup.age_jours != null ? `il y a ${Math.floor(d.backup.age_jours)} j` : '—'} />
          {/* DASHBOARD-2 (Lot 1) — Horloge : jobs posés / attendus. Écart = ambre (« ce qui cloche »). */}
          <Led ok={d?.horloge?.poses == null ? 'off' : d.horloge.poses < (d.horloge.attendus ?? 0) ? 'warn' : 'ok'}
            label="Horloge" value={d?.horloge?.poses == null ? '—' : `${d.horloge.poses} / ${d.horloge.attendus}`} />
          {/* DASHBOARD-2 (Lot 1) — Verrous : n / 16 (verrous de cohérence du Circuit, dernier passage). */}
          <Led ok={d?.verrous?.ok == null ? 'off' : d.verrous.ok < (d.verrous.sur ?? 16) ? 'err' : 'ok'}
            label="Verrous" value={d?.verrous?.ok == null ? '—' : `${d.verrous.ok} / ${d.verrous.sur}`} />
          <button onClick={() => setView('cartes')} className="mt-3 text-xs text-mint hover:underline">Ouvrir l'app cliente →</button>
        </div>
      </aside>

      {/* contenu */}
      <div className="min-w-0 overflow-y-auto px-9 py-7">
        <div className="mx-auto max-w-[1120px]">
          <header className="mb-6 flex flex-wrap items-baseline gap-3.5">
            <h1 className="font-display text-2xl font-semibold tracking-tight text-txt-hi">{SECTIONS.find((s) => s.key === section)?.label ?? (section === 'cron' ? 'Horloge' : '')}</h1>
            <span className="text-[13px] text-txt-dim">{SOUS_TITRES[section]}</span>
            {/* DASHBOARD-4 (P3) — l'horodatage Stripe du haut disparaît : la fraîcheur est dite en pied
                du Pilotage (« Chiffres relevés en direct »), pas en bandeau d'en-tête. */}
          </header>
          {section === 'ia' && (
            <div className="mb-4 rounded-r-xl border-l-[3px] border-cp-ia bg-gradient-to-r from-cp-ia-bg/60 to-transparent px-4 py-2.5 font-mono text-[11px] tracking-[0.1em] text-cp-ia">
              SURFACE IA — le mauve est réservé à cette section, comme dans l'app
            </div>
          )}
          {section === 'pilotage' && <PilotageSection data={d} go={setSection} majAt={pilotage.dataUpdatedAt} />}
          {section === 'licences' && <LicencesSection />}
          {section === 'ia' && <IaSection />}
          {section === 'donnees' && <DonneesSection />}
          {section === 'cron' && <CronSection />}
          {section === 'produit' && <ProduitSection />}
          {section === 'courrier' && <CourrierSection />}
          {section === 'radar' && <RadarSection />}
          {section === 'contacts' && <ContactsSection />}
        </div>
      </div>
    </div>
  )
}
