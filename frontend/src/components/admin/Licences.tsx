// ADMIN-1 (AD4) — page « Comptes » (ex-Licences, clé de section 'licences' conservée). Répond à UNE
// question : « que dois-je faire pour ce client, maintenant ? ». Création en une ligne en tête ;
// à gauche la liste avec l'action en attente ; à droite la fiche : carte verte « prochaine action »
// puis le parcours daté qui NOMME chaque mail (fini « Mail 1/2/3 » — via mail_libelles). Aperçu réel
// (template Brevo rendu) avant chaque « Envoyer ». Rien d'automatique : tout envoi est un clic.
// Suspension TOUJOURS manuelle. L'ancien wizard « 3 étapes » a disparu (mandat AD4.6).
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import {
  getAdminLicences, getAdminMailApercu, getOffres, postAdminLicenceCreer, postAdminLicenceCreerEssai,
  postAdminLicenceMail, postAdminRetablir, postAdminSuspendre, type AdminLicence, type AdminLicences,
} from '../../lib/api'
import { ActBtn, Panel } from './AdminView'

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
const essaiHeuresRestantes = (l: AdminLicence) =>
  l.essai_expire_at ? Math.round((new Date(l.essai_expire_at).getTime() - Date.now()) / 3_600_000) : null

// pastille de statut (couleur) — actif=mint, essai=amber, invite=gris, suspendu=coral.
type Pastille = 'actif' | 'essai' | 'invite' | 'susp'
function pastille(l: AdminLicence): Pastille {
  if (l.statut === 'suspendu') return 'susp'
  if (l.statut === 'invite') return 'invite'
  if (l.essai_expire_at && l.statut === 'actif') return 'essai'
  return 'actif'
}
const PAST_CLS: Record<Pastille, string> = {
  actif: 'bg-mint', essai: 'bg-amber', invite: 'bg-txt-dim', susp: 'bg-coral',
}

// ADMIN-1 (AD4.3) — l'ACTION EN ATTENTE, calculée depuis les données (statut, mails envoyés, rappels
// backend J+3/J+10, essai). Renvoie la 1re action attendue (ou null = rien à faire). `mk` = clé de mail
// à envoyer (aperçu + Envoyer) ; sans `mk` = geste hors mail (ex. lien Stripe à copier).
interface Action { court: string; titre: string; sous: string; mk?: string }
function prochaineAction(l: AdminLicence): Action | null {
  const sent = (k: string) => l.mails[k]?.statut === 'envoye'
  const rappel = (needle: string) => l.rappels.some((r) => r.includes(needle))
  if (l.statut === 'invite' && !sent('souscription') && !sent('onboarding1')) {
    return { court: 'invitation à envoyer', titre: "Envoyer l'invitation / le lien de souscription",
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

// ── panneau APERÇU (AD4.4) : template Brevo rendu avec les variables du compte, ou raison honnête ──
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

// ── barre de création en une ligne (AD4.1) — Créer NE POSTE AUCUN MAIL ──
function NewBar() {
  const qc = useQueryClient()
  const [email, setEmail] = useState('')
  const [nom, setNom] = useState('')
  const [lien, setLien] = useState<string | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const ok = (r: { lien: string }) => { setLien(r.lien); setErr(null); setEmail(''); setNom(''); qc.invalidateQueries({ queryKey: ['admin-licences'] }) }
  const ko = (e: unknown) => setErr(e instanceof Error ? e.message : 'Création impossible.')
  const creer = useMutation({ mutationFn: () => postAdminLicenceCreer({ email: email.trim(), nom: nom.trim() || undefined }), onSuccess: ok, onError: ko })
  const essai = useMutation({ mutationFn: () => postAdminLicenceCreerEssai({ email: email.trim(), nom: nom.trim() || undefined, heures: 48 }), onSuccess: ok, onError: ko })
  const inp = 'rounded-md border border-line-2 bg-bg px-2.5 py-2 text-[13px] text-txt outline-none focus:border-mint'
  return (
    <div className="mb-4 rounded-xl border border-line bg-surface-2 px-3 py-2.5">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-[12.5px] text-txt-dim">Nouveau client :</span>
        <input data-nouveau-email value={email} onChange={(e) => setEmail(e.target.value)} placeholder="email@client.re" className={`${inp} w-56`} />
        <input value={nom} onChange={(e) => setNom(e.target.value)} placeholder="Nom (option)" className={`${inp} w-40`} />
        <ActBtn onClick={() => creer.mutate()} disabled={!email.includes('@') || creer.isPending}>Créer &amp; préparer l'invitation →</ActBtn>
        <ActBtn tone="ghost" onClick={() => essai.mutate()} disabled={!email.includes('@') || essai.isPending}>ou essai 48 h</ActBtn>
        <span className="text-[11.5px] text-txt-off">l'invitation ne part jamais seule — tu l'envoies depuis la fiche</span>
      </div>
      {lien && (
        <div className="mt-2 flex items-center gap-2">
          <span className="text-[11px] text-mint">Compte créé.</span>
          <code className="max-w-[440px] truncate rounded bg-surface-1 px-2 py-1 font-mono text-[10.5px] text-mint">{lien}</code>
          <ActBtn tone="ghost" onClick={() => navigator.clipboard?.writeText(lien)}>Copier le lien</ActBtn>
        </div>
      )}
      {err && <div className="mt-1 text-[11px] text-coral">{err}</div>}
    </div>
  )
}

// ── étape du parcours ──
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

// ── fiche client (colonne droite) ──
function Fiche({ l, libelles, stripeConfigure }: { l: AdminLicence; libelles: Record<string, string>; stripeConfigure: boolean }) {
  const qc = useQueryClient()
  const [msg, setMsg] = useState<string | null>(null)
  const [apercu, setApercu] = useState<string | null>(null)
  const refresh = () => qc.invalidateQueries({ queryKey: ['admin-licences'] })
  const mail = useMutation({
    mutationFn: (key: string) => postAdminLicenceMail(l.id, key),
    onSuccess: (r) => { setMsg(r.envoye ? '✓ Envoyé.' : (r.raison ?? 'Envoi impossible.')); refresh() },
    onError: () => setMsg('Envoi impossible — réessayez.'),
  })
  const susp = useMutation({ mutationFn: () => postAdminSuspendre(l.id), onSuccess: refresh })
  const retab = useMutation({ mutationFn: () => postAdminRetablir(l.id), onSuccess: refresh })
  const suspendu = l.statut === 'suspendu'
  const act = prochaineAction(l)
  const sent = (k: string) => l.mails[k]?.statut === 'envoye'
  const rappel = (n: string) => l.rappels.some((r) => r.includes(n))
  const h = essaiHeuresRestantes(l)
  const abonne = l.stripe?.statut === 'active' || l.stripe?.statut === 'trialing'
  const lib = (k: string) => libelles[k] ?? k
  const suspendre = () => { if (window.confirm("Suspendre l'accès de ce client ?\n\nIl verra « abonnement à régulariser » avec le lien de paiement. Données intactes, réversible.")) susp.mutate() }
  // état de chaque mail dans le parcours : envoyé=done, dû (=prochaine action)=now, sinon wait.
  const etat = (k: string, du: boolean): 'done' | 'now' | 'wait' => sent(k) ? 'done' : (du ? 'now' : 'wait')
  return (
    <div className="rounded-xl border border-line bg-surface-2 p-5">
      {apercu && <ApercuOverlay compteId={l.id} mk={apercu} onClose={() => setApercu(null)} />}
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="font-display text-lg font-semibold text-txt-hi">{l.nom}</h2>
          <div className="mt-0.5 text-[12.5px] text-txt-dim">
            {l.email} · compte créé le {fmtReu(l.created_at)}
            {l.essai_expire_at && l.statut === 'actif' && <span className="ml-2 rounded-full bg-amber/10 px-2.5 py-0.5 text-[11px] font-semibold text-amber">ESSAI — {h != null && h > 0 ? `expire dans ${h} h` : 'expiré'}</span>}
          </div>
        </div>
        <ActBtn tone="ghost" onClick={() => setApercu('souscription')}>Lien de souscription Stripe</ActBtn>
      </div>

      {/* PROCHAINE ACTION (AD4.3) */}
      {!suspendu && act && (
        <div className="mt-4 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-mint/40 bg-gradient-to-br from-mint/10 to-transparent px-4 py-3">
          <div className="min-w-0">
            <div className="font-mono text-[11px] tracking-[0.2em] text-mint">PROCHAINE ACTION</div>
            <div className="mt-1 text-[14.5px] font-semibold text-txt-hi">{act.titre}</div>
            <div className="text-[12px] text-txt-dim">{act.sous}</div>
          </div>
          {act.mk && (
            <div className="flex shrink-0 items-center gap-2">
              <button onClick={() => setApercu(act.mk!)} className="rounded-md border border-line-2 px-2.5 py-1.5 text-[11.5px] text-txt-mut hover:text-txt">aperçu</button>
              <ActBtn onClick={() => mail.mutate(act.mk!)} disabled={mail.isPending}>Envoyer →</ActBtn>
            </div>
          )}
        </div>
      )}
      {!suspendu && !act && <div className="mt-4 rounded-xl border border-line bg-surface-1 px-4 py-3 text-[12.5px] text-txt-mut">Rien à faire pour ce client — le parcours est à jour.</div>}
      {msg && <div className="mt-2 text-[11.5px] text-amber">{msg}</div>}

      {/* PARCOURS (AD4.3) */}
      <div className="mt-5">
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
      </div>

      {/* KPI (AD4.5) */}
      <div className="mt-5 grid grid-cols-3 gap-2">
        <div className="rounded-lg border border-line bg-surface-1 px-3 py-2">
          <div className="font-display text-base font-bold text-txt-hi">{fmtDuree(l.kpi.usage_7j_min)}</div>
          <div className="text-[10.5px] text-txt-dim">usage sur 7 j</div>
        </div>
        <div className="rounded-lg border border-line bg-surface-1 px-3 py-2">
          <div className="font-display text-base font-bold text-txt-hi">{fmtReu(l.kpi.derniere_connexion, true)}</div>
          <div className="text-[10.5px] text-txt-dim">dernière connexion</div>
        </div>
        <div className="rounded-lg border border-line bg-surface-1 px-3 py-2">
          <div className="font-display text-base font-bold text-txt-hi">{l.kpi.copilote_jour} / {l.kpi.copilote_quota}</div>
          <div className="text-[10.5px] text-txt-dim">Copilote aujourd'hui</div>
        </div>
      </div>

      {/* SUSPENSION MANUELLE (AD4.5) */}
      <div className="mt-5 flex items-center justify-between gap-3 rounded-lg border border-line px-3 py-2.5 text-[12px] text-txt-dim">
        <span>La suspension est toujours <b className="text-coral">manuelle</b> — jamais automatique sur un échec de carte.</span>
        {suspendu
          ? <ActBtn onClick={() => retab.mutate()} disabled={retab.isPending}>Rétablir l'accès</ActBtn>
          : <button onClick={suspendre} disabled={susp.isPending} className="shrink-0 rounded-md border border-coral/40 px-2.5 py-1 text-[12px] text-coral disabled:opacity-40">Suspendre le compte</button>}
      </div>
    </div>
  )
}

type Filtre = 'tous' | 'actif' | 'essai' | 'invite' | 'susp'

export function LicencesSection() {
  const q = useQuery({ queryKey: ['admin-licences'], queryFn: getAdminLicences, refetchInterval: 120_000 })
  const offres = useQuery({ queryKey: ['offres'], queryFn: getOffres, staleTime: Infinity })
  const [filtre, setFiltre] = useState<Filtre>('tous')
  const [sel, setSel] = useState<number | null>(null)
  const d: AdminLicences | undefined = q.data
  if (!d) return <div className="py-10 text-center text-xs text-txt-mut">Chargement…</div>
  const prixIntegral = offres.data?.integral.eur_mois
  const libelles = d.mail_libelles ?? {}
  const par = (p: Pastille) => d.licences.filter((l) => pastille(l) === p)
  const compteurs = { actif: par('actif').length, essai: par('essai').length, invite: par('invite').length, susp: par('susp').length }
  const mrr = d.licences.filter((l) => l.stripe?.statut === 'active' || l.stripe?.statut === 'trialing')
    .reduce((s, l) => s + (l.stripe?.montant_eur_mois ?? 0), 0)
  const visibles = filtre === 'tous' ? d.licences : d.licences.filter((l) => pastille(l) === filtre)
  const selectionne = d.licences.find((l) => l.id === sel) ?? visibles[0] ?? d.licences[0]
  const orphelins = d.rapprochement && !d.rapprochement.indisponible
    ? [...d.rapprochement.comptes_sans_abo.map((o) => `Compte app « ${o.nom} » sans abonnement Stripe actif`),
       ...d.rapprochement.abos_sans_compte.map((o) => `Abonnement Stripe ${o.email ?? o.customer_id} sans compte app lié`)]
    : []
  const CHIPS: [Filtre, string, number][] = [
    ['tous', 'Tous', d.licences.length], ['actif', 'Actifs', compteurs.actif], ['essai', 'Essai', compteurs.essai],
    ['invite', 'Invités', compteurs.invite], ['susp', 'Suspendus', compteurs.susp],
  ]
  return (
    <>
      <div className="mb-3 font-display text-[15px] text-txt-hi">
        {d.licences.length} compte{d.licences.length > 1 ? 's' : ''} · {compteurs.actif} licence{compteurs.actif > 1 ? 's' : ''} active{compteurs.actif > 1 ? 's' : ''}
        {mrr > 0 && <> · {mrr.toLocaleString('fr-FR')} € / mois</>}
      </div>
      {!d.brevo.api && (
        <div className="mb-3.5 rounded-lg border border-amber/30 bg-amber/5 px-4 py-2.5 text-xs text-amber">
          Brevo non configuré (LABUSE_BREVO_API_KEY) — les envois et aperçus restent visibles et le diront : aucun envoi silencieux.
        </div>
      )}
      {orphelins.length > 0 && (
        <div className="mb-3.5 rounded-lg border border-amber/30 bg-amber/5 px-4 py-2.5 text-xs text-amber">
          <b>Rapprochement Stripe ⇄ comptes :</b> {orphelins.join(' · ')}
        </div>
      )}

      <NewBar />

      <div className="grid grid-cols-[340px_1fr] gap-4 max-[1100px]:grid-cols-1">
        {/* LISTE (AD4.2) */}
        <div>
          <div className="mb-2.5 flex flex-wrap gap-1.5">
            {CHIPS.map(([k, label, n]) => (
              <button key={k} onClick={() => setFiltre(k)}
                className={`rounded-full border px-2.5 py-1 text-[11.5px] transition-colors duration-quick ${
                  filtre === k ? 'border-mint/45 bg-mint/10 text-mint' : 'border-line-2 text-txt-dim hover:text-txt'}`}>
                {label} {n}
              </button>
            ))}
          </div>
          <div className="flex flex-col gap-1.5">
            {visibles.map((l) => {
              const act = prochaineAction(l)
              const on = selectionne?.id === l.id
              return (
                <button key={l.id} data-licence={l.id} onClick={() => setSel(l.id)}
                  className={`flex items-center gap-2.5 rounded-lg border px-3 py-2.5 text-left transition-colors duration-quick ${
                    on ? 'border-mint bg-surface-2' : 'border-line bg-surface-2 hover:border-line-2'}`}>
                  <span className={`h-2.5 w-2.5 shrink-0 rounded-full ${PAST_CLS[pastille(l)]}`} />
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-[13.5px] font-semibold text-txt-hi">{l.nom}</span>
                    <span className="block truncate text-[11px] text-txt-off">{l.email}</span>
                  </span>
                  {act
                    ? <span className="shrink-0 text-[10.5px] text-amber">⚑ {act.court}</span>
                    : <span className="shrink-0 text-[10.5px] text-txt-dim">{l.stripe?.montant_eur_mois ? `actif · ${l.stripe.montant_eur_mois} €` : (l.statut === 'suspendu' ? 'suspendu' : (prixIntegral ? 'actif' : ''))}</span>}
                </button>
              )
            })}
            {!visibles.length && <div className="rounded-lg border border-line bg-surface-2 px-3 py-6 text-center text-xs text-txt-mut">Aucun compte dans ce filtre.</div>}
          </div>
        </div>

        {/* FICHE (AD4.3-5) */}
        {selectionne
          ? <Fiche l={selectionne} libelles={libelles} stripeConfigure={d.stripe_configure} />
          : <Panel><div className="px-5 py-10 text-center text-xs text-txt-mut">Aucun compte — créez le premier ci-dessus.</div></Panel>}
      </div>
    </>
  )
}
