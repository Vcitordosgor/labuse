// DASHBOARD-V1 — TOUR DE CONTRÔLE (vue admin plein écran, maquette docs/audit-2026-08/DASHBOARD/
// maquette.html validée par Vic le 26/08 : rail 6 sections + LED santé en pied, héros Pilotage,
// mauve strictement réservé à la section IA). La visibilité côté front est du confort — chaque
// endpoint /admin/* porte la garde exiger_admin (403 client). Horodatages À L'HEURE RÉUNION
// (Indian/Reunion), jamais l'heure serveur brute (dette fuseau connue, mandat D3).
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { getAdminCircuit, getAdminLicences, getAdminPilotage, getMoi, getOffres, getRadarCheck, postAdminDegeler, type AdminPilotage } from '../../lib/api'
import { useApp } from '../../store/useApp'
import { LicencesSection, prochaineAction } from './Licences'
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

// ═══ DASHBOARD-2 (Lot 1) — briques du poste de pilotage ═══
// UNE jauge = un grand nombre + une étiquette + un liseré (vert/ambre/rouge), cliquable vers sa page.
// « rien d'autre » (le détail vit sur la page). Le chiffre est LU de la fonction serveur de sa page.
type JaugeTone = 'ok' | 'warn' | 'err' | 'off'
function Jauge({ valeur, label, tone, onClick, title }: {
  valeur: React.ReactNode; label: string; tone: JaugeTone; onClick?: () => void; title?: string
}) {
  const bord = { ok: 'border-l-mint', warn: 'border-l-amber', err: 'border-l-coral', off: 'border-l-line-3' }[tone]
  const encre = { ok: 'text-txt-hi', warn: 'text-amber', err: 'text-coral', off: 'text-txt-mut' }[tone]
  return (
    <button type="button" onClick={onClick} disabled={!onClick} title={title}
      className={`flex flex-col items-start rounded-xl border border-line border-l-[3px] ${bord} bg-surface-2 px-4 py-3.5 text-left transition-colors duration-quick ${onClick ? 'hover:border-line-2' : 'cursor-default'}`}>
      <div className={`font-display text-[26px] font-semibold leading-none ${encre}`}>{valeur}</div>
      <div className="mt-2 font-mono text-[10px] uppercase tracking-[0.14em] text-txt-dim">{label}</div>
    </button>
  )
}

// « À faire, dans l'ordre » — une ligne = chiffre · phrase · verbe. `tone` r (ce qui cloche, rouge),
// a (à faire, ambre), ok (rien, grisé). Le tri (poids) place ce qui cloche d'abord (Pilotage).
type Todo = { cle: string; n: number | string; titre: string; phrase?: string; verbe: string; cible: AdminSection; tone: 'r' | 'a' | 'ok'; poids: number }
function TodoLigne({ t, go }: { t: Todo; go: (s: AdminSection) => void }) {
  const kcol = t.tone === 'r' ? 'text-coral' : t.tone === 'ok' ? 'text-txt-dim' : 'text-amber'
  const bord = t.tone === 'r' ? 'border-coral/40' : 'border-line'
  return (
    <button type="button" data-todo={t.cle} onClick={() => go(t.cible)}
      className={`grid w-full grid-cols-[44px_1fr_auto] items-center gap-3.5 rounded-lg border ${bord} bg-surface-2 px-3.5 py-2.5 text-left transition-colors duration-quick hover:border-line-2`}>
      <div className={`text-right font-mono text-[20px] font-medium ${kcol}`}>{t.n}</div>
      <div className="min-w-0 text-[13.5px] text-txt">
        {t.titre}{t.phrase && <small className="block text-[12px] text-txt-mut">{t.phrase}</small>}
      </div>
      <span className={`whitespace-nowrap text-[13px] font-medium ${t.tone === 'ok' ? 'text-txt-dim' : 'text-mint'}`}>{t.verbe} →</span>
    </button>
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
  const [limite, setLimite] = useState(8)
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
          <Chip key={f} tone={famille === f ? 'ok' : 'off'} onClick={() => { setFamille(f); setLimite(8) }}>{f}</Chip>
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
                  <span className="min-w-0 flex-1 truncate" title={e.detail ?? undefined}>{e.titre}</span>
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
          <button onClick={() => setLimite((n) => n + 12)} className="w-full border-t border-line px-4 py-2.5 text-xs text-txt-mut hover:text-txt">
            Voir plus — {visibles.length} / {filtres.length} chargés
          </button>
        )}
      </Panel>
    </>
  )
}

function PilotageSection({ data, go, majAt }: { data: AdminPilotage | undefined; go: (s: AdminSection) => void; majAt?: number }) {
  const qc = useQueryClient()
  const [degel, setDegel] = useState<string | null>(null)
  // compteur unique : le Pilotage lit les MÊMES endpoints que les pages Données (Circuit) et Radar.
  const circuit = useQuery({ queryKey: ['admin-circuit'], queryFn: getAdminCircuit, refetchInterval: 120_000 })
  const radarChk = useQuery({ queryKey: ['radar-check'], queryFn: getRadarCheck, refetchInterval: 120_000 })
  // Argent = MRR (récurrent contractuel = licences × prix intégral) ; l'encaissé du mois passe en légende.
  const offres = useQuery({ queryKey: ['offres'], queryFn: getOffres, staleTime: 3_600_000 })
  // Lot 2 §1 — la jauge Clients affiche « à toucher » : le MÊME endpoint que la page Comptes, lu avec
  // la MÊME fonction (prochaineAction) que son segment par défaut → même nombre, une seule fonction.
  const licencesQ = useQuery({ queryKey: ['admin-licences'], queryFn: getAdminLicences, refetchInterval: 120_000 })
  const degeler = async (sujet: string) => {
    setDegel(sujet)
    try { await postAdminDegeler(sujet); qc.invalidateQueries({ queryKey: ['admin-pilotage'] }) } finally { setDegel(null) }
  }
  if (!data) return <div className="py-10 text-center text-xs text-txt-mut">Chargement…</div>
  const st = data.stripe
  const caEntries = Object.entries(st.ca_mois ?? {})
  const caCourant = caEntries.at(-1)?.[1] ?? 0
  const echecs = st.paiements_en_echec ?? 0
  const clientEchec = st.abonnements?.find((a) => a.statut === 'past_due')

  // ── les 8 chiffres, chacun LU de sa page ──
  const circuitTotal = (circuit.data?.resume?.total as number | undefined) ?? null
  const enVie = radarChk.data?.annonces_en_vie ?? null
  const reverifDues = radarChk.data?.reverif_dues ?? 0
  const aDeposer = data.courrier?.a_deposer ?? 0
  const retoursTot = Object.values(data.retours_par_type ?? {}).reduce((a, b) => a + b, 0)
  // Produit = file unique des retours (signalements fiche/annonce + « Signaler ») ouverts — cf. Lot 5.
  const produitOuverts = (data.a_faire?.signalements_ouverts ?? 0) + retoursTot
  const iaMois = data.ia_mois?.cout_eur ?? 0
  // « à toucher » = clients (hors test) ayant une action en attente — même filtre + même fonction que
  // le segment « À toucher » (défaut) de la page Comptes (COMPTE-2). licences_actives reste le compteur
  // unique (comptes.licences_actives), lu par le rail et l'Argent.
  const licencesActives = data.licences_actives
  const aToucher = (licencesQ.data?.licences ?? []).filter((l) => !l.est_test && prochaineAction(l) != null).length
  const mailEchecs = data.mail_echecs_jour ?? 0
  const horlogeManquant = (data.horloge?.attendus ?? 0) - (data.horloge?.poses ?? 0)
  const verrousCasses = data.verrous && data.verrous.ok != null && data.verrous.sur != null ? data.verrous.sur - data.verrous.ok : 0
  const moisNom = new Intl.DateTimeFormat('fr-FR', { month: 'long' }).format(new Date())
  // Argent = MRR récurrent = licences actives × prix intégral (le vrai « par mois », pas l'encaissé
  // qui reste à 0 tant que Stripe n'encaisse rien) ; repli sur le MRR Stripe si le prix est indisponible.
  const prixIntegral = offres.data?.integral?.eur_mois ?? null
  const mrr = prixIntegral != null ? data.licences_actives * prixIntegral : (data.traction?.mrr_eur ?? null)

  // ── « À faire, dans l'ordre » : ce qui CLOCHE (rouge) d'abord — c'est AUSSI la source de la jauge
  //    Système (un seul calcul) — puis les tâches par urgence. Les lignes à ZÉRO ne sont pas des tâches. ──
  const rouges: Todo[] = []
  if (horlogeManquant > 0) rouges.push({ cle: 'horloge', n: horlogeManquant, titre: 'Poser les horloges sur le VPS',
    phrase: `${data.horloge?.poses ?? 0} posées / ${data.horloge?.attendus ?? 0} attendues — le wrapper des crons n'a jamais été déployé`, verbe: "Voir l'horloge", cible: 'cron', tone: 'r', poids: 100 })
  if (verrousCasses > 0) rouges.push({ cle: 'verrous', n: verrousCasses, titre: 'Réparer les verrous de cohérence',
    phrase: 'le Circuit ne dit plus la même chose partout', verbe: 'Ouvrir Données', cible: 'donnees', tone: 'r', poids: 95 })
  if (echecs > 0) rouges.push({ cle: 'paiement', n: echecs, titre: `Régler ${echecs} paiement${echecs > 1 ? 's' : ''} en échec`,
    phrase: clientEchec ? (clientEchec.nom_stripe ?? clientEchec.email ?? clientEchec.customer_id ?? undefined) : undefined, verbe: 'Voir la licence', cible: 'licences', tone: 'r', poids: 90 })
  if (['rouge', 'absent', 'non_configure'].includes(data.backup?.etat)) rouges.push({ cle: 'backup', n: '!',
    titre: data.backup.etat === 'non_configure' ? 'Configurer la sauvegarde' : data.backup.etat === 'absent' ? 'Configurer la sauvegarde' : 'Rattraper la sauvegarde en retard',
    phrase: data.backup.etat === 'rouge' ? undefined : 'aucun dump connu — la base n\'est pas sauvegardée', verbe: "Voir l'horloge", cible: 'cron', tone: 'r', poids: 85 })
  // Lot 2 §2 — les échecs d'envoi du jour (mail_queue) sont une alerte système (rejouables d'un clic).
  if (mailEchecs > 0) rouges.push({ cle: 'mail', n: mailEchecs, titre: `Rejouer ${mailEchecs} échec${mailEchecs > 1 ? 's' : ''} d'envoi de mail`,
    phrase: 'file mail_queue — la raison est lisible, rejouable d\'un clic', verbe: 'Ouvrir Comptes', cible: 'licences', tone: 'r', poids: 88 })
  // alertes système ouvertes = les lignes rouges (même calcul, jamais un chiffre à part) : ce qui cloche
  // sur le serveur + les échecs d'envoi du jour.
  const nSysteme = rouges.length

  const taches: Todo[] = []
  if (aToucher > 0) taches.push({ cle: 'comptes', n: aToucher, titre: 'Toucher les clients',
    phrase: 'client(s) avec une action en attente', verbe: 'Ouvrir Comptes', cible: 'licences', tone: 'a', poids: 80 })
  if ((circuitTotal ?? 0) > 0) taches.push({ cle: 'circuit', n: circuitTotal as number, titre: 'Regarder le circuit', verbe: 'Ouvrir Données', cible: 'donnees', tone: 'a', poids: 70 })
  if (aDeposer > 0) taches.push({ cle: 'courrier', n: aDeposer, titre: 'Déposer les courriers', verbe: 'Ouvrir Courrier', cible: 'courrier', tone: 'a', poids: 60 })
  if (produitOuverts > 0) taches.push({ cle: 'produit', n: produitOuverts, titre: 'Traiter les retours clients', verbe: 'Ouvrir Produit', cible: 'produit', tone: 'a', poids: 50 })
  if (reverifDues > 0) taches.push({ cle: 'radar', n: reverifDues, titre: 'Re-vérifier des annonces', verbe: 'Ouvrir Radar', cible: 'radar', tone: 'a', poids: 40 })
  const aFaire = [...rouges, ...taches].sort((a, b) => b.poids - a.poids)

  const jauges: { valeur: React.ReactNode; label: string; tone: JaugeTone; cible?: AdminSection; title?: string }[] = [
    // Argent : MRR en grand, encaissé du mois en légende (une jauge à 0 permanent ne sert à rien).
    { valeur: mrr != null ? <>{fmtEur(mrr)} <span className="text-base font-medium text-txt-mut">€</span></> : '—',
      label: `Argent · par mois · ${st.configure ? fmtEur(caCourant) + ' € encaissé en ' + moisNom : 'Stripe non configuré'}`, tone: 'ok',
      cible: 'licences', title: prixIntegral != null ? `MRR = ${data.licences_actives} licences × ${fmtEur(prixIntegral)} €/mois` : undefined },
    // Clients : Lot 2 §1 — la jauge affiche le « à toucher » (segment par défaut de la page Comptes),
    // pas le nombre de licences ; le compteur de licences vit sur le rail, la page et l'Argent.
    { valeur: aToucher, label: `Clients · à toucher · ${licencesActives} active${licencesActives > 1 ? 's' : ''}`,
      tone: aToucher > 0 ? 'warn' : 'ok', cible: 'licences' },
    { valeur: circuitTotal ?? '—', label: 'Circuit · à regarder', tone: circuitTotal == null ? 'off' : circuitTotal > 0 ? 'warn' : 'ok', cible: 'donnees' },
    { valeur: aDeposer, label: 'Courrier · à déposer', tone: aDeposer > 0 ? 'warn' : 'ok', cible: 'courrier' },
    { valeur: enVie ?? '—', label: 'Radar · annonces en vie', tone: enVie == null ? 'off' : 'ok', cible: 'radar' },
    { valeur: produitOuverts, label: 'Produit · retours ouverts', tone: produitOuverts > 0 ? 'warn' : 'ok', cible: 'produit' },
    { valeur: <>{fmtEur(iaMois, 2)} <span className="text-base font-medium text-txt-mut">€</span></>, label: 'IA · conso du mois', tone: 'ok', cible: 'ia' },
    // Système : le NOMBRE d'alertes ouvertes réelles (= lignes rouges), rouge dès qu'il y en a.
    { valeur: nSysteme, label: 'Système · alertes ouvertes', tone: nSysteme > 0 ? 'err' : 'ok', cible: 'cron' },
  ]
  // Jauges triées par URGENCE : rouge, puis ambre, puis vert ; à état égal, l'ordre de la maquette.
  const tonePrio: Record<JaugeTone, number> = { err: 0, warn: 1, ok: 2, off: 2 }
  const jaugesTriees = jauges.map((g, i) => ({ g, i })).sort((a, b) => (tonePrio[a.g.tone] - tonePrio[b.g.tone]) || (a.i - b.i)).map((x) => x.g)

  // ── journal : gels (sécurité) + fil (event_log système), fusionnés, triés récents d'abord ──
  const items: JournalItem[] = [
    ...data.gels.map((g) => ({ key: `g${g.sujet}`, ts: g.ts, famille: 'Système', source: 'Sécurité',
      titre: `Gel anti-burst sur ${g.sujet}${g.motif ? ` — ${g.motif}` : ''}`, action: 'degel' as const, sujet: g.sujet })),
    ...data.fil.map((e) => ({ key: `f${e.id}`, ts: e.ts, famille: familleDe(e.source, e.kind), source: e.source,
      titre: e.titre, detail: e.detail, action: e.source === 'Courrier' ? 'courrier' as const : e.source === 'Retour' ? 'produit' as const : undefined })),
  ].sort((a, b) => (b.ts ?? '').localeCompare(a.ts ?? ''))

  return (
    <>
      {/* 8 jauges — un grand nombre + une étiquette. Triées par urgence : rouge, ambre, vert. */}
      <div className="grid grid-cols-4 gap-3 max-[1100px]:grid-cols-2">
        {jaugesTriees.map((g) => (
          <Jauge key={g.label} valeur={g.valeur} label={g.label} tone={g.tone} title={g.title}
            onClick={g.cible ? () => go(g.cible!) : undefined} />
        ))}
      </div>

      <H2>À faire, dans l'ordre</H2>
      <div className="grid gap-1.5">
        {aFaire.length
          ? aFaire.map((t) => <TodoLigne key={t.cle} t={t} go={go} />)
          : <div className="rounded-lg border border-line bg-surface-2 px-3.5 py-3 text-[13px] text-txt-mut">Rien à faire aujourd'hui — tout est à jour.</div>}
      </div>
      <p className="mt-2 text-[10.5px] text-txt-dim">Les lignes à zéro ne s'affichent pas — une ligne à zéro n'est pas une tâche.</p>

      <H2>Journal</H2>
      <Journal items={items} degel={degel} degeler={degeler} go={go} />
      <p className="mt-2 text-[10.5px] text-txt-dim">
        {/* Lot 1 §24 — fraîcheur honnête : le Pilotage est relu en direct de la base (pas de cache). */}
        Chiffres relevés en direct{majAt ? ` · dernier relevé à ${fmtReu(new Date(majAt).toISOString())}` : ''}.
        Chaque jauge lit la fonction serveur de sa page — ouvrir la page donne le même nombre.
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
            <span className="ml-auto flex items-center gap-2">
              {/* DASHBOARD-2 recette §5 — les chiffres du Pilotage sont en direct ; SEUL Stripe est
                  daté d'un cache. On affiche la vraie date du cache en heure Réunion (fmtReu). */}
              {section === 'pilotage' && d?.stripe.maj && (
                <Chip tone={Date.now() - new Date(d.stripe.maj).getTime() > 3_600_000 ? 'warn' : 'off'}>
                  chiffres à l'instant · Stripe daté du {fmtReu(d.stripe.maj)}
                </Chip>
              )}
            </span>
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
