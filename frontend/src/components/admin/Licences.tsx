// COMPTE-2 (Lot 3) — page « Comptes » v2 (maquette maquette-pilotage-comptes-v2). Liste = segments
// (À toucher par défaut / Actifs / Essais / Invités / Suspendus / Tous) + recherche ; une ligne par
// client (initiales · nom+structure · plan · dernière visite · MRR · à faire calculé · un bouton). Le
// rapprochement Stripe est un lien en pied de liste. La fiche est une VRAIE page (« ← Comptes ») à
// onglets Aperçu / Activité / Facturation / IA. Aucun envoi par optimisme ; tout envoi est un clic avec
// aperçu réel. Compteur de licences actives = source unique backend. Plafond IA affiché en EUROS.
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import {
  getAdminLicences, getAdminMailApercu, getAdminMails, getOffres, postAdminLicenceCreer,
  postAdminLicenceCreerEssai, postAdminLicenceConvertir, postAdminLicenceMail, postAdminRetablir,
  postAdminSuspendre, postAdminDeconnecter, type AdminLicence, type AdminLicences, type MailLigne,
} from '../../lib/api'
import { ActBtn } from './AdminView'

const fmtReu = (iso?: string | null, avecHeure = false) => {
  if (!iso) return '—'
  try {
    return new Intl.DateTimeFormat('fr-FR', {
      timeZone: 'Indian/Reunion', day: '2-digit', month: '2-digit',
      ...(avecHeure ? { hour: '2-digit', minute: '2-digit' } : {}),
    }).format(new Date(iso)).replace(',', '')
  } catch { return '—' }
}
const fmtDuree = (min: number) => (min >= 60 ? `${(min / 60).toFixed(1).replace('.', ',')} h` : `${min} min`)
const fmtEur = (v?: number | null) => `${(v ?? 0).toFixed(2).replace('.', ',')} €`
const essaiHeuresRestantes = (l: AdminLicence) =>
  l.essai_expire_at ? Math.round((new Date(l.essai_expire_at).getTime() - Date.now()) / 3_600_000) : null

// « dernière visite » en relatif (aujourd'hui / hier / il y a N j / jamais), heure Réunion pour le jour.
function fmtVisite(iso?: string | null): string {
  if (!iso) return 'jamais'
  try {
    const j = new Intl.DateTimeFormat('fr-CA', { timeZone: 'Indian/Reunion' })
    const d0 = new Date(j.format(new Date())), dv = new Date(j.format(new Date(iso)))
    const n = Math.round((d0.getTime() - dv.getTime()) / 86_400_000)
    return n <= 0 ? "aujourd'hui" : n === 1 ? 'hier' : `il y a ${n} j`
  } catch { return '—' }
}
function initiales(l: AdminLicence): string {
  const base = (l.nom || l.email || '?').replace(/\[CT-TEST\]\s*/i, '').trim()
  const mots = base.split(/\s+/).filter(Boolean)
  return ((mots[0]?.[0] ?? '') + (mots[1]?.[0] ?? '')).toUpperCase() || base.slice(0, 2).toUpperCase()
}

// carte refusée = Stripe past_due OU statut app « paiement_requis » (posé par le webhook).
const carteRefusee = (l: AdminLicence) => l.stripe?.statut === 'past_due' || l.statut === 'paiement_requis'

type Pastille = 'actif' | 'essai' | 'invite' | 'susp' | 'carte'
function pastille(l: AdminLicence): Pastille {
  if (carteRefusee(l)) return 'carte'
  if (l.statut === 'suspendu') return 'susp'
  if (l.statut === 'invite') return 'invite'
  if (l.essai_expire_at && l.statut === 'actif') return 'essai'
  return 'actif'
}
const AV_CLS: Record<Pastille, string> = {
  actif: 'bg-mint/10 text-mint', essai: 'bg-amber/10 text-amber', invite: 'bg-white/5 text-txt-dim',
  susp: 'bg-coral/10 text-coral', carte: 'bg-coral/10 text-coral',
}

interface Action { court: string; titre: string; sous: string; mk?: string }
// DASHBOARD-2 Lot 2 — exportée pour que la jauge Clients du Pilotage lise EXACTEMENT le même
// « à toucher » que le segment par défaut de cette page (une seule fonction, même donnée).
export function prochaineAction(l: AdminLicence): Action | null {
  const sent = (k: string) => l.mails[k]?.statut === 'envoye'
  const rappel = (needle: string) => l.rappels.some((r) => r.includes(needle))
  // carte refusée : priorité (avant tout onboarding) — relance par le template 9.
  if (carteRefusee(l)) {
    return { court: 'carte refusée', titre: 'Carte refusée — renvoyer le lien de paiement',
             sous: 'le paiement a échoué ; Stripe relance, vous pouvez aussi renvoyer le lien', mk: 'relance_carte' }
  }
  // un compte SUSPENDU ne propose jamais « bienvenue » : essai expiré → convertir ; sinon → rétablir.
  if (l.statut === 'suspendu') {
    const h = essaiHeuresRestantes(l)
    if (l.essai_expire_at && h != null && h <= 0) {
      return { court: 'essai expiré', titre: "Prolonger l'essai ou convertir en abonnement",
               sous: "l'essai est arrivé à échéance — proposez l'abonnement", mk: 'souscription' }
    }
    return { court: 'à rétablir', titre: "Rétablir l'accès",
             sous: "compte suspendu — l'accès est rendu au rétablissement" }
  }
  if (l.statut === 'resilie') return null
  if (l.statut === 'invite' && !sent('souscription') && !sent('onboarding1')) {
    return { court: "invitation à envoyer", titre: "Envoyer l'invitation / le lien de souscription",
             sous: "le compte est créé mais l'accès n'a pas encore été transmis au client", mk: 'souscription' }
  }
  if (!sent('onboarding1')) {
    return { court: 'mail de bienvenue à envoyer', titre: 'Envoyer le mail de bienvenue',
             sous: 'ses premiers pas : la carte, une fiche, le Copilote', mk: 'onboarding1' }
  }
  if (rappel('J+3') && !sent('onboarding2')) {
    return { court: 'relance J+3 à envoyer', titre: 'Envoyer la Relance J+3',
             sous: '« avez-vous trouvé votre première parcelle ? »', mk: 'onboarding2' }
  }
  if (rappel('J+10') && !sent('onboarding3')) {
    return { court: 'dernier rappel J+10 à envoyer', titre: 'Envoyer le Dernier rappel J+10',
             sous: "proposition d'appel + lien Stripe", mk: 'onboarding3' }
  }
  const h = essaiHeuresRestantes(l)
  const abonne = l.stripe?.statut === 'active' || l.stripe?.statut === 'trialing'
  if (!abonne && h != null && h < 48) {
    return { court: 'lien Stripe à envoyer', titre: 'Envoyer le lien de souscription Stripe',
             sous: "l'essai touche à sa fin — proposez l'abonnement", mk: 'souscription' }
  }
  return null
}
// verbe court du bouton de ligne (ouvre la fiche pour agir avec aperçu).
function verbe(act: Action | null): string {
  if (!act) return ''
  if (act.court.includes('rétablir')) return 'Rétablir'
  if (act.court.includes('carte')) return 'Renvoyer'
  if (act.court.includes('essai expiré')) return 'Convertir'
  return 'Envoyer'
}

// ── DASHBOARD-4 (K3) — CINQ statuts (Invité · Invitation envoyée · Actif · Suspendu · Expiré) ;
//    « payant / essai » est une COLONNE À PART, lue de Stripe (jamais mélangée au statut). ──
type Statut5 = 'invite' | 'invitation_envoyee' | 'actif' | 'suspendu' | 'expire'
function statut5(l: AdminLicence): Statut5 {
  const h = essaiHeuresRestantes(l)
  const essaiExpire = l.essai_expire_at != null && h != null && h <= 0
  if (l.statut === 'suspendu') return essaiExpire ? 'expire' : 'suspendu'
  if (essaiExpire) return 'expire'
  if (l.statut === 'invite') {
    const invitationEnvoyee = l.mails['souscription']?.statut === 'envoye' || l.mails['onboarding1']?.statut === 'envoye'
    return invitationEnvoyee ? 'invitation_envoyee' : 'invite'
  }
  return 'actif'
}
const STATUT5_LABEL: Record<Statut5, string> = {
  invite: 'Invité', invitation_envoyee: 'Invitation envoyée', actif: 'Actif', suspendu: 'Suspendu', expire: 'Expiré',
}
const STATUT5_DOT: Record<Statut5, string> = {
  invite: 'bg-txt-dim', invitation_envoyee: 'bg-amber', actif: 'bg-mint', suspendu: 'bg-coral', expire: 'bg-coral',
}
function StatutChip({ l }: { l: AdminLicence }) {
  const s = statut5(l)
  return <span className="inline-flex items-center gap-1.5 text-[12.5px] text-txt"><span className={`h-[8px] w-[8px] rounded-full ${STATUT5_DOT[s]}`} />{STATUT5_LABEL[s]}</span>
}
// « payant / essai » — colonne à part, lue de Stripe (carte refusée = état de paiement, pas un statut).
function abonnement(l: AdminLicence): { label: string; cls: string } {
  if (carteRefusee(l)) return { label: 'Carte refusée', cls: 'text-coral' }
  if (l.stripe?.statut === 'active' || l.stripe?.statut === 'trialing') return { label: 'Payant', cls: 'text-mint' }
  const h = essaiHeuresRestantes(l)
  if (l.essai_expire_at != null && h != null && h > 0) return { label: `Essai · ${h} h`, cls: 'text-amber' }
  if (l.essai_expire_at != null) return { label: 'Essai expiré', cls: 'text-coral' }
  return { label: '—', cls: 'text-txt-dim' }
}

// DASHBOARD-4 (K3) — « À toucher » (segment par défaut ET jauge Pilotage, une seule fonction) :
// invitation sans réponse > 7 j · essai qui se termine (< 6 h) · carte refusée.
export function estAToucher(l: AdminLicence): boolean {
  if (l.est_test) return false
  if (carteRefusee(l)) return true
  const abonne = l.stripe?.statut === 'active' || l.stripe?.statut === 'trialing'
  const h = essaiHeuresRestantes(l)
  if (l.essai_expire_at != null && !abonne && h != null && h > 0 && h < 6) return true   // essai < 6 h
  if (l.statut === 'invite' && !l.kpi.derniere_connexion && l.created_at) {              // invitation sans réponse > 7 j
    const ageJ = (Date.now() - new Date(l.created_at).getTime()) / 86_400_000
    if (ageJ > 7) return true
  }
  return false
}

// DASHBOARD-4 (K5) — phrase CALCULÉE sous les faits (« paie depuis 7 jours, connecté 4 fois » /
// « n'est jamais entré dans l'app »).
function phraseCalculee(l: AdminLicence): string {
  if (!l.kpi.derniere_connexion) return "Ce client n'est jamais entré dans l'app."
  const parts: string[] = []
  const abonne = l.stripe?.statut === 'active' || l.stripe?.statut === 'trialing'
  if (abonne && l.stripe?.depuis) {
    const j = Math.max(0, Math.floor((Date.now() / 1000 - l.stripe.depuis) / 86_400))
    parts.push(`paie depuis ${j} jour${j > 1 ? 's' : ''}`)
  } else if (l.essai_expire_at) {
    const h = essaiHeuresRestantes(l)
    parts.push(h != null && h > 0 ? `en essai (encore ${h} h)` : 'essai terminé')
  }
  const min = l.kpi.usage_7j_min
  if (min > 0) parts.push(`actif ${fmtDuree(min)} sur 7 jours`)
  else parts.push('connecté au moins une fois')
  return parts.length ? parts.join(', ').replace(/^./, (c) => c.toUpperCase()) + '.' : 'Compte actif.'
}

// DASHBOARD-4 (K3) — l'ancien PlanChip (plan/état mélangés) est remplacé par StatutChip (5 statuts)
// + la colonne Abonnement séparée (abonnement()), lue de Stripe.

// ── panneau APERÇU : template Brevo rendu avec les variables du compte, ou raison honnête ──
function ApercuOverlay({ compteId, mk, onClose }: { compteId: number; mk: string; onClose: () => void }) {
  const q = useQuery({ queryKey: ['mail-apercu', compteId, mk], queryFn: () => getAdminMailApercu(compteId, mk) })
  const a = q.data
  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-black/60 p-6" onClick={onClose}>
      <div className="max-h-[80vh] w-full max-w-[640px] overflow-hidden rounded-xl border border-line bg-surface-2 shadow-2xl" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between border-b border-line px-4 py-3">
          <b className="text-sm text-txt-hi">Aperçu — {a?.libelle ?? mk}</b>
          <button onClick={onClose} className="text-txt-mut hover:text-txt">✕</button>
        </div>
        <div className="max-h-[calc(80vh-52px)] overflow-y-auto px-4 py-3 text-[12.5px] text-txt">
          {!a ? <div className="py-8 text-center text-xs text-txt-mut">Chargement de l'aperçu…</div>
            : a.configure ? (
              <>
                <div className="mb-2 text-txt-mut">Objet : <b className="text-txt">{a.subject || '—'}</b></div>
                <div className="rounded-lg border border-line bg-bg p-3 text-[12px]" dangerouslySetInnerHTML={{ __html: a.html || '<i>(template vide)</i>' }} />
                <div className="mt-2 font-mono text-[10.5px] text-txt-dim">Variables : {Object.entries(a.params).map(([k, v]) => `${k}=${v}`).join(' · ')}</div>
              </>
            ) : (
              <div className="text-amber">
                Aperçu indisponible — {a.raison}
                <div className="mt-2 font-mono text-[10.5px] text-txt-dim">Variables qui seraient injectées : {Object.entries(a.params).map(([k, v]) => `${k}=${v}`).join(' · ')}</div>
              </div>
            )}
        </div>
      </div>
    </div>
  )
}

// ── DASHBOARD-4 (K1/K2) — VRAIE PAGE de création (plus d'accordéon, plus de lien brut affiché).
//    E-mail + prénom + nom. Deux gestes : « Créer et envoyer l'invitation » (principal, envoi Brevo
//    4/5 par la file — dry-run en local, mail_log) · « créer sans envoyer » (lien). LES DEUX arrivent
//    sur la FICHE du client créé (onCree). ──
function CreerPage({ mode, onBack, onCree }: {
  mode: 'client' | 'essai'; onBack: () => void; onCree: (compteId: number) => void
}) {
  const qc = useQueryClient()
  const [email, setEmail] = useState('')
  const [prenom, setPrenom] = useState('')
  const [nom, setNom] = useState('')
  const [err, setErr] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  // le template d'invitation : souscription (Brevo 5) pour un client, essai (Brevo 4) pour un essai.
  const mailKey = mode === 'client' ? 'souscription' : 'essai'
  const nomComplet = [prenom.trim(), nom.trim()].filter(Boolean).join(' ') || undefined
  const lancer = async (envoyer: boolean) => {
    setBusy(true); setErr(null)
    try {
      const r = mode === 'client'
        ? await postAdminLicenceCreer({ email: email.trim(), nom: nomComplet })
        : await postAdminLicenceCreerEssai({ email: email.trim(), nom: nomComplet, heures: 48 })
      if (envoyer) { try { await postAdminLicenceMail(r.compte_id, mailKey) } catch { /* la file dira l'échec sur la fiche */ } }
      qc.invalidateQueries({ queryKey: ['admin-licences'] })
      onCree(r.compte_id)   // K2 — les deux gestes arrivent sur la fiche
    } catch (e) {
      setErr(e instanceof Error ? e.message : 'Création impossible.')
    } finally { setBusy(false) }
  }
  const inp = 'w-full rounded-md border border-line-2 bg-bg px-3 py-2.5 text-[13.5px] text-txt outline-none focus:border-mint'
  const titre = mode === 'client' ? 'Créer un client' : 'Ouvrir un essai 48 h'
  return (
    <div>
      <button onClick={onBack} className="mb-3 text-[12.5px] text-txt-mut hover:text-txt">← Comptes</button>
      <h1 className="mb-4 font-display text-xl font-semibold text-txt-hi">{titre}</h1>
      <div className="max-w-[460px] rounded-xl border border-line bg-surface-2 p-6">
        <label className="mb-1.5 block text-[12px] text-txt-dim">E-mail</label>
        <input autoFocus type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="prenom@societe.re" className={inp} />
        <label className="mb-1.5 mt-3.5 block text-[12px] text-txt-dim">Prénom</label>
        <input value={prenom} onChange={(e) => setPrenom(e.target.value)} className={inp} />
        <label className="mb-1.5 mt-3.5 block text-[12px] text-txt-dim">Nom</label>
        <input value={nom} onChange={(e) => setNom(e.target.value)} className={inp} />
        <div className="mt-5 flex items-center gap-4">
          <ActBtn onClick={() => lancer(true)} disabled={!email.includes('@') || busy}>
            {mode === 'client' ? "Créer et envoyer l'invitation" : "Créer l'essai et envoyer l'invitation"}
          </ActBtn>
          <button onClick={() => lancer(false)} disabled={!email.includes('@') || busy}
            className="text-[13px] text-txt-mut underline underline-offset-2 hover:text-txt disabled:opacity-40">créer sans envoyer</button>
        </div>
        {err && <div className="mt-3 text-[12px] text-coral">{err}</div>}
        <div className="mt-4 text-[11px] text-txt-off">
          En local (Brevo non configuré), l'envoi est un <b>dry-run</b> : l'invitation entre dans la file
          (mail_log) sans partir — visible sur la fiche, onglet Activité.
        </div>
      </div>
    </div>
  )
}

// ── étape du parcours (onglet Aperçu de la fiche) ──
function Step({ etat, titre, sous, when, mk, onApercu, onSend, sending }: {
  etat: 'done' | 'now' | 'wait'; titre: string; sous: string; when?: string | null
  mk?: string; onApercu?: (k: string) => void; onSend?: (k: string) => void; sending?: boolean
}) {
  const ic = { done: '✓', now: '●', wait: '·' }[etat]
  const icCls = { done: 'bg-mint/10 text-mint', now: 'bg-amber/10 text-amber', wait: 'bg-white/5 text-txt-off' }[etat]
  return (
    <div className="flex items-center gap-3 border-b border-line py-2.5 last:border-b-0 text-[13px]">
      <span className={`grid h-5 w-5 shrink-0 place-items-center rounded-full text-[11px] ${icCls}`}>{ic}</span>
      <div className="min-w-0 flex-1">
        <div className="text-txt">{titre}</div>
        <div className="text-[11px] text-txt-off">{sous}</div>
      </div>
      {mk && etat !== 'done' ? (
        <div className="flex shrink-0 items-center gap-1.5">
          {onApercu && <button onClick={() => onApercu(mk)} className="rounded-md border border-line-2 px-2 py-1 text-[11px] text-txt-mut hover:text-txt">aperçu</button>}
          {onSend && <button onClick={() => onSend(mk)} disabled={sending} className="rounded-md border border-mint/40 bg-mint/10 px-2 py-1 text-[11px] text-mint disabled:opacity-40">Envoyer</button>}
        </div>
      ) : (
        <span className="shrink-0 whitespace-nowrap text-[11.5px] text-txt-dim">{when ?? ''}</span>
      )}
    </div>
  )
}

// ── chip d'état d'un mail de la file (onglets Activité / Facturation) ──
function EtatChip({ etat }: { etat: string }) {
  const cls = etat === 'recu' ? 'bg-mint/10 text-mint' : etat === 'echec' ? 'bg-coral/10 text-coral'
    : etat === 'annule' ? 'bg-white/5 text-txt-dim' : 'bg-amber/10 text-amber'
  const lib = { recu: 'Reçu', echec: 'Échec', annule: 'Annulé', en_attente: 'En attente', parti: 'Parti' }[etat] ?? etat
  return <span className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${cls}`}>{lib}</span>
}
function MailList({ lignes, vide }: { lignes: MailLigne[]; vide: string }) {
  if (!lignes.length) return <div className="rounded-lg border border-line bg-surface-1 px-4 py-6 text-center text-[12px] text-txt-mut">{vide}</div>
  return (
    <div className="overflow-hidden rounded-lg border border-line">
      {lignes.map((m) => (
        <div key={m.id} className="flex items-center gap-3 border-b border-line px-3 py-2 text-[12.5px] last:border-b-0">
          <span className="font-mono text-[11px] text-txt-dim">{fmtReu(m.parti_at ?? m.cree_at, true)}</span>
          <span className="min-w-0 flex-1 truncate text-txt">{m.template_nom ?? m.mail_key}
            {m.erreur && <span className="ml-2 text-[11px] text-coral">{m.erreur}</span>}</span>
          <span className="shrink-0 font-mono text-[10.5px] text-txt-off">{m.demandeur}</span>
          <EtatChip etat={m.etat} />
        </div>
      ))}
    </div>
  )
}

// ── la fiche = VRAIE PAGE à onglets ──
type Onglet = 'apercu' | 'activite' | 'facturation' | 'ia'
function FichePage({ l, libelles, stripeConfigure, onBack }: {
  l: AdminLicence; libelles: Record<string, string>; stripeConfigure: boolean; onBack: () => void
}) {
  const qc = useQueryClient()
  const [onglet, setOnglet] = useState<Onglet>('apercu')
  const [msg, setMsg] = useState<string | null>(null)
  const [apercu, setApercu] = useState<string | null>(null)
  const [decoMsg, setDecoMsg] = useState<string | null>(null)
  const refresh = () => qc.invalidateQueries({ queryKey: ['admin-licences'] })
  const mail = useMutation({
    mutationFn: (key: string) => postAdminLicenceMail(l.id, key),
    onSuccess: (r) => { setMsg(r.envoye ? '✓ Envoyé.' : (r.raison ?? 'Envoi impossible.')); refresh(); qc.invalidateQueries({ queryKey: ['admin-mails', l.id] }) },
    onError: () => setMsg('Envoi impossible — réessayez.'),
  })
  const susp = useMutation({ mutationFn: () => postAdminSuspendre(l.id), onSuccess: refresh })
  const retab = useMutation({ mutationFn: () => postAdminRetablir(l.id), onSuccess: refresh })
  // DASHBOARD-4 (K4) — « Transformer en client » : lève l'essai, le compte paie par le parcours officiel.
  const transformer = useMutation({ mutationFn: () => postAdminLicenceConvertir(l.id), onSuccess: (r) => { setMsg(r.detail); refresh() } })
  const deco = useMutation({
    mutationFn: () => postAdminDeconnecter(l.id),
    onSuccess: (r) => { setDecoMsg(`${r.sessions_fermees} session${r.sessions_fermees > 1 ? 's' : ''} fermée${r.sessions_fermees > 1 ? 's' : ''}`); refresh() },
  })
  const suspendu = l.statut === 'suspendu'
  const act = prochaineAction(l)
  const sent = (k: string) => l.mails[k]?.statut === 'envoye'
  const rappel = (n: string) => l.rappels.some((r) => r.includes(n))
  const h = essaiHeuresRestantes(l)
  const abonne = l.stripe?.statut === 'active' || l.stripe?.statut === 'trialing'
  const lib = (k: string) => libelles[k] ?? k
  const suspendre = () => { if (window.confirm("Suspendre l'accès de ce client ?\n\nIl verra « abonnement à régulariser » avec le lien de paiement. Données intactes, réversible.")) susp.mutate() }
  const etat = (k: string, du: boolean): 'done' | 'now' | 'wait' => sent(k) ? 'done' : (du ? 'now' : 'wait')
  const TABS: [Onglet, string][] = [['apercu', 'Aperçu'], ['activite', 'Activité'], ['facturation', 'Facturation'], ['ia', 'IA']]
  return (
    <div>
      {apercu && <ApercuOverlay compteId={l.id} mk={apercu} onClose={() => setApercu(null)} />}
      {/* DASHBOARD-4 (K5) — fil d'Ariane + gestes EN HAUT À DROITE (tous les gestes partent d'ici). */}
      <div className="mb-2 text-[12.5px] text-txt-dim"><button onClick={onBack} className="hover:text-txt">Comptes</button> › {l.nom}</div>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <span className={`grid h-10 w-10 place-items-center rounded-full text-[13px] font-semibold ${AV_CLS[pastille(l)]}`}>{initiales(l)}</span>
          <div>
            <h2 className="font-display text-lg font-semibold text-txt-hi">{l.nom}</h2>
            <div className="flex items-center gap-2 text-[12.5px] text-txt-dim"><StatutChip l={l} /> · créé le {fmtReu(l.created_at)}
              {l.essai_expire_at && l.statut === 'actif' && <span className="rounded-full bg-amber/10 px-2.5 py-0.5 text-[11px] font-semibold text-amber">ESSAI — {h != null && h > 0 ? `expire dans ${h} h` : 'expiré'}</span>}
            </div>
          </div>
        </div>
        <div className="flex shrink-0 flex-wrap items-center gap-2">
          {/* Renvoyer l'invitation (souscription) — utile tant que le client n'est pas entré. */}
          {!l.kpi.derniere_connexion && (
            <ActBtn tone="ghost" onClick={() => mail.mutate('souscription')} disabled={mail.isPending}>Renvoyer l'invitation</ActBtn>
          )}
          {/* Transformer en client (K4) — pour un essai en cours. */}
          {l.essai_expire_at != null && l.statut === 'actif' && (
            <ActBtn onClick={() => transformer.mutate()} disabled={transformer.isPending}>Transformer en client</ActBtn>
          )}
          {suspendu
            ? <ActBtn onClick={() => retab.mutate()} disabled={retab.isPending}>Rétablir</ActBtn>
            : <button onClick={suspendre} disabled={susp.isPending} className="rounded-lg border border-coral/40 px-3 py-1.5 text-xs font-medium text-coral disabled:opacity-40">Suspendre</button>}
        </div>
      </div>

      {/* DASHBOARD-4 (K5) — faits + phrase CALCULÉE sous les faits. */}
      <div className="mt-3 grid gap-4 rounded-xl border border-line bg-surface-1 px-4 py-3 sm:grid-cols-[1fr_auto]">
        <dl className="grid grid-cols-2 gap-x-6 gap-y-1.5 text-[12.5px]">
          <div><dt className="text-txt-dim">E-mail</dt><dd className="font-mono text-txt">{l.email}</dd></div>
          <div><dt className="text-txt-dim">Abonnement</dt><dd className={abonnement(l).cls}>{abonnement(l).label}</dd></div>
          <div><dt className="text-txt-dim">Dernière connexion</dt><dd className="text-txt">{fmtReu(l.kpi.derniere_connexion, true)}</dd></div>
          <div><dt className="text-txt-dim">Usage 7 j</dt><dd className="text-txt">{fmtDuree(l.kpi.usage_7j_min)}</dd></div>
        </dl>
      </div>
      <p className="mt-2 border-t border-line pt-2 text-[13px] text-txt">{phraseCalculee(l)}</p>

      <div className="mt-4 mb-4 flex gap-1 border-b border-line">
        {TABS.map(([k, label]) => (
          <button key={k} onClick={() => setOnglet(k)}
            className={`-mb-px border-b-2 px-3 py-2 text-[13px] transition-colors duration-quick ${
              onglet === k ? 'border-mint text-txt-hi' : 'border-transparent text-txt-mut hover:text-txt'}`}>{label}</button>
        ))}
      </div>

      {onglet === 'apercu' && (
        <div>
          {act && (
            <div className="mb-4 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-mint/40 bg-gradient-to-br from-mint/10 to-transparent px-4 py-3">
              <div className="min-w-0">
                <div className="font-mono text-[11px] tracking-[0.2em] text-mint">À FAIRE</div>
                <div className="mt-1 text-[14.5px] font-semibold text-txt-hi">{act.titre}</div>
                <div className="text-[12px] text-txt-dim">{act.sous}</div>
              </div>
              {act.mk && (
                <div className="flex shrink-0 items-center gap-2">
                  <button onClick={() => setApercu(act.mk!)} className="rounded-md border border-line-2 px-2.5 py-1.5 text-[11.5px] text-txt-mut hover:text-txt">aperçu</button>
                  <ActBtn onClick={() => mail.mutate(act.mk!)} disabled={mail.isPending}>Envoyer →</ActBtn>
                </div>
              )}
              {!act.mk && !suspendu && <ActBtn onClick={() => retab.mutate()} disabled={retab.isPending}>Rétablir l'accès</ActBtn>}
            </div>
          )}
          {!act && <div className="mb-4 rounded-xl border border-line bg-surface-1 px-4 py-3 text-[12.5px] text-txt-mut">Rien à faire pour ce client — le parcours est à jour.</div>}
          {msg && <div className="mb-2 text-[11.5px] text-amber">{msg}</div>}

          <div className="mb-1 font-mono text-[10.5px] tracking-[0.22em] text-txt-dim">PARCOURS</div>
          <Step etat="done" titre="Invitation envoyée" sous="lien de création de compte — mécanisme cloisonné" when={fmtReu(l.created_at, true)} />
          <Step etat={l.statut === 'invite' ? 'now' : 'done'} titre={l.essai_expire_at ? 'Compte créé — essai' : 'Compte créé'} sous="accès complet, comme une licence" when={fmtReu(l.created_at, true)} />
          <Step etat={etat('onboarding1', act?.mk === 'onboarding1')} titre={lib('onboarding1')} sous="premiers pas : la carte, une fiche, le Copilote"
            when={sent('onboarding1') ? fmtReu(l.mails.onboarding1?.sent_at, true) : undefined}
            mk="onboarding1" onApercu={setApercu} onSend={mail.mutate} sending={mail.isPending} />
          <Step etat={etat('onboarding2', act?.mk === 'onboarding2')} titre={lib('onboarding2')} sous="« avez-vous trouvé votre première parcelle ? »"
            when={sent('onboarding2') ? fmtReu(l.mails.onboarding2?.sent_at, true) : (rappel('J+3') ? undefined : 'dès J+3')}
            mk={rappel('J+3') || sent('onboarding2') ? 'onboarding2' : undefined} onApercu={setApercu} onSend={mail.mutate} sending={mail.isPending} />
          <Step etat={etat('onboarding3', act?.mk === 'onboarding3')} titre={lib('onboarding3')} sous="proposition d'appel + lien Stripe"
            when={sent('onboarding3') ? fmtReu(l.mails.onboarding3?.sent_at, true) : (rappel('J+10') ? undefined : 'dès J+10')}
            mk={rappel('J+10') || sent('onboarding3') ? 'onboarding3' : undefined} onApercu={setApercu} onSend={mail.mutate} sending={mail.isPending} />
          <Step etat={abonne ? 'done' : 'wait'} titre="Abonnement Stripe" sous="la licence passe « active » au premier paiement"
            when={abonne ? 'actif' : (stripeConfigure ? 'à souscrire' : 'Stripe non configuré')}
            mk={abonne ? undefined : 'souscription'} onApercu={setApercu} onSend={mail.mutate} sending={mail.isPending} />

          {/* DASHBOARD-4 (K5) — suspension/transformation vivent EN HAUT À DROITE ; ici on garde le
              rappel « manuelle » + la déconnexion à distance (geste rare, jamais dans le bandeau). */}
          <div className="mt-5 flex items-center justify-between gap-3 rounded-lg border border-line px-3 py-2.5 text-[12px] text-txt-dim">
            <span>La suspension est toujours <b className="text-coral">manuelle</b> — jamais automatique sur un échec de carte (le geste est en haut de la fiche).</span>
          </div>
          <div className="mt-2.5 flex items-center justify-between gap-3 rounded-lg border border-line px-3 py-2.5 text-[12px] text-txt-dim">
            <span>Déconnexion à distance — ferme toutes les sessions ouvertes du client (il pourra se reconnecter).{decoMsg && <b className="ml-2 text-mint">{decoMsg}</b>}</span>
            <button onClick={() => deco.mutate()} disabled={deco.isPending} className="shrink-0 rounded-md border border-line px-2.5 py-1 text-[12px] text-txt-hi disabled:opacity-40">Déconnecter partout</button>
          </div>
        </div>
      )}

      {onglet === 'activite' && <ActiviteTab compteId={l.id} />}
      {onglet === 'facturation' && <FacturationTab l={l} />}
      {onglet === 'ia' && <IaTab l={l} />}
    </div>
  )
}

function ActiviteTab({ compteId }: { compteId: number }) {
  const q = useQuery({ queryKey: ['admin-mails', compteId], queryFn: () => getAdminMails(compteId) })
  return (
    <div>
      <div className="mb-2 font-mono text-[10.5px] tracking-[0.22em] text-txt-dim">MAILS DE CE COMPTE</div>
      {!q.data ? <div className="py-6 text-center text-xs text-txt-mut">Chargement…</div>
        : <MailList lignes={q.data.lignes} vide="Aucun mail pour ce compte pour l'instant." />}
      <div className="mt-3 text-[11.5px] text-txt-off">Le fil complet (connexions, outils ouverts, questions Copilote, signalements) arrive au lot Activité.</div>
    </div>
  )
}

function FacturationTab({ l }: { l: AdminLicence }) {
  const q = useQuery({ queryKey: ['admin-mails', l.id], queryFn: () => getAdminMails(l.id) })
  const facts = (q.data?.lignes ?? []).filter((m) => ['relance_carte', 'suspension', 'retablissement', 'souscription', 'flash_pret'].includes(m.mail_key))
  const s = l.stripe
  const cusUrl = s?.customer_id ? `https://dashboard.stripe.com/customers/${s.customer_id}` : null
  return (
    <div>
      <div className="grid grid-cols-3 gap-2">
        <div className="rounded-lg border border-line bg-surface-1 px-3 py-2">
          <div className="font-display text-base font-bold text-txt-hi">{s?.statut ?? '—'}</div>
          <div className="text-[10.5px] text-txt-dim">abonnement Stripe</div>
        </div>
        <div className="rounded-lg border border-line bg-surface-1 px-3 py-2">
          <div className="font-display text-base font-bold text-txt-hi">{s?.montant_eur_mois ? `${s.montant_eur_mois} €` : '—'}</div>
          <div className="text-[10.5px] text-txt-dim">par mois</div>
        </div>
        <div className="rounded-lg border border-line bg-surface-1 px-3 py-2">
          {cusUrl ? <a href={cusUrl} target="_blank" rel="noreferrer" className="font-mono text-[12px] text-jaune hover:underline">{s!.customer_id}</a>
            : <div className="font-display text-base font-bold text-txt-dim">non lié</div>}
          <div className="text-[10.5px] text-txt-dim">client Stripe</div>
        </div>
      </div>
      <div className="mb-2 mt-4 font-mono text-[10.5px] tracking-[0.22em] text-txt-dim">MAILS DE FACTURATION</div>
      {!q.data ? <div className="py-6 text-center text-xs text-txt-mut">Chargement…</div>
        : <MailList lignes={facts} vide="Aucun mail de facturation pour ce compte." />}
    </div>
  )
}

function IaTab({ l }: { l: AdminLicence }) {
  const dep = l.kpi.ia_depense_eur ?? 0
  const bud = l.kpi.ia_budget_eur ?? 2
  const pct = bud > 0 ? Math.min(100, Math.round((dep / bud) * 100)) : 0
  const atteint = dep >= bud
  return (
    <div>
      <div className="rounded-xl border border-line bg-surface-1 p-4">
        <div className="font-mono text-[10.5px] tracking-[0.22em] text-txt-dim">CONSOMMATION IA — AUJOURD'HUI (HEURE RÉUNION)</div>
        <div className="mt-2 font-display text-2xl font-bold text-txt-hi">
          <span className={atteint ? 'text-coral' : ''}>{fmtEur(dep)}</span> <span className="text-base text-txt-dim">/ {fmtEur(bud)}</span>
        </div>
        <div className="mt-2 h-2 overflow-hidden rounded-full bg-white/5">
          <div className={`h-full ${atteint ? 'bg-coral' : 'bg-mint'}`} style={{ width: `${pct}%` }} />
        </div>
        <div className="mt-2 text-[11.5px] text-txt-off">
          Le plafond IA est en <b>euros par jour</b> et se renouvelle à minuit (heure Réunion).
          {atteint ? ' Plafond atteint : les questions sont refusées jusqu\'à minuit.' : ''}
          <span className="ml-1 text-txt-dim">· {l.kpi.copilote_jour} appel{l.kpi.copilote_jour > 1 ? 's' : ''} aujourd'hui</span>
        </div>
      </div>
      <div className="mt-3 text-[11.5px] text-txt-off">Le budget se règle au dashboard IA ; la question suivante le lit tout de suite.</div>
    </div>
  )
}

type Seg = 'toucher' | 'actif' | 'essai' | 'invite' | 'susp' | 'tous'

export function LicencesSection() {
  const q = useQuery({ queryKey: ['admin-licences'], queryFn: getAdminLicences, refetchInterval: 120_000 })
  const offres = useQuery({ queryKey: ['offres'], queryFn: getOffres, staleTime: Infinity })
  const [seg, setSeg] = useState<Seg>('toucher')
  const [recherche, setRecherche] = useState('')
  const [sel, setSel] = useState<number | null>(null)
  const [creer, setCreer] = useState<'client' | 'essai' | null>(null)
  const d: AdminLicences | undefined = q.data

  const clientes = useMemo(() => (d?.licences ?? []).filter((l) => !l.est_test), [d])
  // DASHBOARD-4 (K3) — « À toucher » = estAToucher (invitation sans réponse > 7 j · essai < 6 h · carte refusée).
  const aToucher = useMemo(() => clientes.filter((l) => estAToucher(l)), [clientes])

  if (!d) return <div className="py-10 text-center text-xs text-txt-mut">Chargement…</div>

  // DASHBOARD-4 (K1) — « Créer un client » / « Ouvrir un essai 48 h » sont de VRAIES pages.
  if (creer) return <CreerPage mode={creer} onBack={() => setCreer(null)} onCree={(id) => { setCreer(null); setSel(id) }} />
  const prixIntegral = offres.data?.integral.eur_mois
  const libelles = d.mail_libelles ?? {}
  const masques = d.compteurs?.masques ?? d.licences.filter((l) => l.est_test).length
  const actives = d.compteurs?.licences_actives ?? clientes.filter((l) => pastille(l) === 'actif').length
  const mrr = clientes.filter((l) => l.stripe?.statut === 'active' || l.stripe?.statut === 'trialing')
    .reduce((s, l) => s + (l.stripe?.montant_eur_mois ?? 0), 0)
  const sansAbo = d.rapprochement && !d.rapprochement.indisponible ? d.rapprochement.comptes_sans_abo.length : 0

  // fiche = vraie page (remplace la liste)
  const selectionne = sel != null ? clientes.find((l) => l.id === sel) : undefined
  if (selectionne) {
    return (
      <FichePage l={selectionne} libelles={libelles} stripeConfigure={d.stripe_configure} onBack={() => setSel(null)} />
    )
  }

  const par = (p: Pastille) => clientes.filter((l) => pastille(l) === p)
  const nb = { toucher: aToucher.length, actif: par('actif').length, essai: par('essai').length,
    invite: par('invite').length, susp: par('susp').length, tous: clientes.length }
  const SEGS: [Seg, string][] = [
    ['toucher', 'À toucher'], ['actif', 'Actifs'], ['essai', 'Essais'],
    ['invite', 'Invités'], ['susp', 'Suspendus'], ['tous', 'Tous'],
  ]
  const base = seg === 'toucher' ? aToucher : seg === 'tous' ? clientes : clientes.filter((l) => pastille(l) === seg)
  const rech = recherche.trim().toLowerCase()
  const lignes = rech ? base.filter((l) => (l.nom || '').toLowerCase().includes(rech) || (l.email || '').toLowerCase().includes(rech)) : base

  return (
    <>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-baseline gap-3">
          <h1 className="font-display text-xl font-semibold text-txt-hi">Comptes</h1>
          <span className="text-[13px] text-txt-mut">{actives} licence{actives > 1 ? 's' : ''} active{actives > 1 ? 's' : ''}{mrr > 0 && ` · ${mrr.toLocaleString('fr-FR')} € par mois`}</span>
        </div>
        {/* DASHBOARD-4 (K1) — deux entrées en haut à droite, vraies pages (plus d'accordéon). */}
        <div className="flex gap-2">
          <ActBtn tone="ghost" onClick={() => setCreer('essai')}>Ouvrir un essai 48 h</ActBtn>
          <ActBtn onClick={() => setCreer('client')}>Créer un client</ActBtn>
        </div>
      </div>

      {!d.brevo.api && (
        <div className="mb-3.5 rounded-lg border border-amber/30 bg-amber/5 px-4 py-2.5 text-xs text-amber">
          Brevo non configuré (LABUSE_BREVO_API_KEY) — les envois et aperçus restent visibles et le diront : aucun envoi silencieux.
        </div>
      )}

      <div className="mb-3.5 flex flex-wrap items-center gap-3">
        <div className="flex overflow-hidden rounded-lg border border-line-2">
          {SEGS.map(([k, label], i) => (
            <button key={k} onClick={() => setSeg(k)}
              className={`px-3 py-1.5 text-[13px] transition-colors duration-quick ${i > 0 ? 'border-l border-line-2' : ''} ${
                seg === k ? 'bg-mint text-ink font-medium' : 'text-txt-mut hover:text-txt'}`}>
              {label} <span className="font-mono text-[11px] opacity-70">{nb[k]}</span>
            </button>
          ))}
        </div>
        <input value={recherche} onChange={(e) => setRecherche(e.target.value)} placeholder="Nom, e-mail…"
          className="ml-auto w-60 rounded-lg border border-line-2 bg-surface-2 px-3 py-1.5 text-[13px] text-txt outline-none focus:border-mint" />
      </div>

      <div className="overflow-hidden rounded-xl border border-line bg-surface-2">
        {/* DASHBOARD-4 (K3) — colonne STATUT (5 statuts) + colonne ABONNEMENT séparée (payant/essai, Stripe). */}
        <div className="grid grid-cols-[38px_1.7fr_1fr_0.9fr_0.9fr_1fr_auto] items-center gap-3 border-b border-line px-4 py-2 text-[11px] uppercase tracking-wide text-txt-dim">
          <span /><span>Client</span><span>Statut</span><span>Dernière visite</span><span>Abonnement</span><span>À faire</span><span />
        </div>
        {lignes.map((l) => {
          const act = prochaineAction(l)
          const p = pastille(l)
          const abo = abonnement(l)
          return (
            <button key={l.id} data-licence={l.id} onClick={() => setSel(l.id)}
              className="grid w-full grid-cols-[38px_1.7fr_1fr_0.9fr_0.9fr_1fr_auto] items-center gap-3 border-b border-line px-4 py-2.5 text-left text-[13.5px] transition-colors duration-quick last:border-b-0 hover:bg-surface-1">
              <span className={`grid h-[30px] w-[30px] place-items-center rounded-full text-[11.5px] font-semibold ${AV_CLS[p]}`}>{initiales(l)}</span>
              <span className="min-w-0">
                <span className="block truncate font-medium text-txt-hi">{l.nom}</span>
                <span className="block truncate text-[12px] text-txt-mut">{l.email}</span>
              </span>
              <span><StatutChip l={l} /></span>
              <span className={l.kpi.derniere_connexion ? 'text-txt-mut' : 'text-txt-dim'}>{fmtVisite(l.kpi.derniere_connexion)}</span>
              <span className={`text-[12.5px] ${abo.cls}`}>{abo.label}</span>
              <span className={act ? (p === 'carte' ? 'text-coral' : 'text-amber') : 'text-txt-dim'}>{act ? act.court : '—'}</span>
              <span>{act ? <span className="rounded-md border border-mint/40 bg-mint/10 px-2.5 py-1 text-[12px] text-mint">{verbe(act)}</span> : ''}</span>
            </button>
          )
        })}
        {!lignes.length && <div className="px-4 py-8 text-center text-xs text-txt-mut">Aucun compte dans ce filtre.</div>}
        <div className="flex flex-wrap items-center justify-between gap-2 px-4 py-3 text-[12px] text-txt-mut">
          <span>{clientes.length} client{clientes.length > 1 ? 's' : ''} · {actives} licence{actives > 1 ? 's' : ''}{mrr > 0 && ` · ${mrr.toLocaleString('fr-FR')} € par mois`}</span>
          <span>
            {masques > 0 && <span className="text-jaune">{masques} compte{masques > 1 ? 's' : ''} de test masqué{masques > 1 ? 's' : ''}</span>}
            {masques > 0 && sansAbo > 0 && ' · '}
            {sansAbo > 0 && <button onClick={() => { setSeg('actif'); }} className="text-jaune hover:underline">{sansAbo} compte{sansAbo > 1 ? 's' : ''} sans abonnement Stripe</button>}
          </span>
        </div>
      </div>
      <div className="mt-2.5 text-[11.5px] text-txt-off">
        Les comptes <span className="font-mono">[CT-TEST]</span>, <span className="font-mono">@labuse.test</span> et les comptes admin ne comptent dans aucun chiffre.{prixIntegral ? '' : ''}
        {/* DASHBOARD-4 (K6) — ton-email@test.com est masqué comme les autres tests ; on le SIGNALE
            (compte réel de démo) et on n'y touche jamais. */}
        {(d.licences ?? []).some((l) => (l.email ?? '').toLowerCase().includes('ton-email@test.com')) && (
          <span className="ml-1 text-jaune"> <span className="font-mono">ton-email@test.com</span> est présent et masqué — ne pas y toucher (compte de démo signalé).</span>
        )}
      </div>
    </>
  )
}
