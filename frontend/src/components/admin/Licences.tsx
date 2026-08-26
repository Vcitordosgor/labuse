// DASHBOARD-V1 · D4 — LICENCES : un client, une ligne (abonnement · onboarding · usage), maquette
// validée 26/08. Suspension TOUJOURS MANUELLE (confirmation), réversible, données intactes ;
// mails Brevo déclenchés À LA MAIN (l'app rappelle J+3/J+10, Vic envoie) ; Brevo/Stripe non
// configurés → boutons visibles + raison explicite, jamais un envoi silencieux.
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import {
  getAdminLicences, postAdminLicenceCreer, postAdminLicenceMail, postAdminRetablir,
  postAdminSuspendre, type AdminLicence,
} from '../../lib/api'
import { ActBtn, Chip, H2, Panel } from './AdminView'

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

function chipStatut(l: AdminLicence, stripeConfigure: boolean): { tone: 'ok' | 'err' | 'warn' | 'off'; label: string } {
  if (l.statut === 'suspendu') return { tone: 'off', label: 'Accès suspendu' }
  if (l.statut === 'invite') return { tone: 'warn', label: 'Invitation en attente' }
  if (l.statut === 'paiement_requis') return { tone: 'err', label: 'Paiement requis' }
  if (l.stripe?.statut === 'past_due') return { tone: 'err', label: 'Carte refusée' }
  if (l.stripe?.statut === 'active' || l.stripe?.statut === 'trialing') return { tone: 'ok', label: 'Abonnement actif' }
  if (stripeConfigure) return { tone: 'warn', label: 'Sans abonnement Stripe' }
  return { tone: 'ok', label: 'Compte actif' }
}

function MailChip({ l, mk, label, onSend, busy }: {
  l: AdminLicence; mk: string; label: string; onSend: (k: string) => void; busy: boolean
}) {
  const sent = l.mails[mk]
  if (sent?.statut === 'envoye') {
    return <span className="rounded-md border border-mint/30 bg-mint/5 px-2.5 py-1 font-mono text-[10.5px] text-mint">{label} ✓ {fmtReu(sent.sent_at)}</span>
  }
  return (
    <button data-mail={mk} disabled={busy} onClick={() => onSend(mk)}
      className="rounded-md border border-dashed border-amber/50 bg-amber/5 px-2.5 py-1 font-mono text-[10.5px] text-amber transition-all duration-quick hover:brightness-125 disabled:opacity-40">
      {label} · Envoyer →
    </button>
  )
}

function ClientRow({ l, stripeConfigure }: { l: AdminLicence; stripeConfigure: boolean }) {
  const qc = useQueryClient()
  const [msg, setMsg] = useState<string | null>(null)
  const refresh = () => qc.invalidateQueries({ queryKey: ['admin-licences'] })
  const mail = useMutation({
    mutationFn: (key: string) => postAdminLicenceMail(l.id, key),
    onSuccess: (r) => { setMsg(r.envoye ? null : (r.raison ?? 'Envoi impossible.')); refresh() },
    onError: () => setMsg('Envoi impossible — réessayez.'),
  })
  const susp = useMutation({
    mutationFn: () => postAdminSuspendre(l.id),
    onSuccess: refresh,
  })
  const retab = useMutation({ mutationFn: () => postAdminRetablir(l.id), onSuccess: refresh })
  const st = chipStatut(l, stripeConfigure)
  const suspendu = l.statut === 'suspendu'
  const suspendre = () => {
    if (window.confirm("Suspendre l'accès de ce client ?\n\nIl verra « abonnement à régulariser » avec le lien de paiement. Ses données restent intactes. Réversible en un clic.")) susp.mutate()
  }
  return (
    <div data-licence={l.id} className={`grid grid-cols-[196px_1fr_168px] gap-5 border-b border-line px-5 py-4 last:border-b-0 max-[1100px]:grid-cols-1 ${
      suspendu ? 'opacity-55' : ''} ${st.label === 'Carte refusée' ? 'bg-gradient-to-r from-coral/5 to-transparent' : ''}`}>
      <div>
        <b className="font-display text-[15.5px] font-semibold text-txt-hi">{l.nom}</b>
        <span className="mt-0.5 block font-mono text-xs text-txt-dim">
          {suspendu ? `suspendu — données conservées` : <>depuis le {fmtReu(l.created_at)}{l.stripe ? ` · ${l.stripe.montant_eur_mois} €/mois` : ''}</>}
        </span>
        <div className="mt-2"><Chip tone={st.tone}>{st.label}{st.label === 'Carte refusée' && l.stripe?.prochaine_retentative ? ` · retente le ${fmtReu(new Date(l.stripe.prochaine_retentative * 1000).toISOString())}` : ''}</Chip></div>
      </div>
      {suspendu ? (
        <div className="text-xs leading-relaxed text-txt-dim">
          Données conservées — rien n'est supprimé. Il voit « abonnement à régulariser » avec le lien de paiement.
        </div>
      ) : (
        <div className="flex min-w-0 flex-col gap-2.5">
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="mr-1 font-mono text-[9.5px] tracking-[0.14em] text-txt-dim">ONBOARDING</span>
            {l.statut === 'invite' && <MailChip l={l} mk="souscription" label="Lien de souscription" onSend={mail.mutate} busy={mail.isPending} />}
            <MailChip l={l} mk="onboarding1" label="Mail 1" onSend={mail.mutate} busy={mail.isPending} />
            <MailChip l={l} mk="onboarding2" label="Mail 2" onSend={mail.mutate} busy={mail.isPending} />
            <MailChip l={l} mk="onboarding3" label="Mail 3" onSend={mail.mutate} busy={mail.isPending} />
          </div>
          {l.rappels.map((r) => <div key={r} className="text-[11px] text-amber">⏱ {r}</div>)}
          {msg && <div className="text-[11px] text-amber">{msg}</div>}
          <div className="grid max-w-[520px] grid-cols-3 gap-2.5">
            <div className="rounded-lg border border-line bg-surface-1 px-3 py-2">
              <b className="block font-display text-[15px] font-semibold text-txt-hi">{fmtDuree(l.kpi.usage_7j_min)}</b>
              <span className="text-[10.5px] text-txt-dim">usage / 7 j (estimé)</span>
            </div>
            <div className="rounded-lg border border-line bg-surface-1 px-3 py-2">
              <b className="block font-display text-[15px] font-semibold text-txt-hi">{fmtReu(l.kpi.derniere_connexion, true)}</b>
              <span className="text-[10.5px] text-txt-dim">dernière connexion</span>
            </div>
            <div className="rounded-lg border border-line bg-surface-1 px-3 py-2">
              <b className="block font-display text-[15px] font-semibold text-txt-hi">{l.kpi.copilote_jour} / {l.kpi.copilote_quota}</b>
              <span className="text-[10.5px] text-txt-dim">Copilote aujourd'hui</span>
            </div>
          </div>
          {st.label === 'Carte refusée' && (
            <div>
              <ActBtn onClick={() => mail.mutate('relance_carte')} disabled={mail.isPending}>Relancer par mail — lien de paiement</ActBtn>
              {l.stripe?.prochaine_retentative && (
                <span className="ml-2.5 font-mono text-xs text-txt-dim">Stripe retente le {fmtReu(new Date(l.stripe.prochaine_retentative * 1000).toISOString())}</span>
              )}
            </div>
          )}
        </div>
      )}
      <div className="flex flex-col items-stretch gap-2 max-[1100px]:flex-row">
        {suspendu ? (
          <ActBtn onClick={() => retab.mutate()} disabled={retab.isPending}>Rétablir l'accès</ActBtn>
        ) : (
          <ActBtn tone="danger" onClick={suspendre} disabled={susp.isPending}>Suspendre l'accès</ActBtn>
        )}
      </div>
    </div>
  )
}

function NouveauClient() {
  const qc = useQueryClient()
  const [email, setEmail] = useState('')
  const [nom, setNom] = useState('')
  const [lien, setLien] = useState<string | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const creer = useMutation({
    mutationFn: () => postAdminLicenceCreer({ email: email.trim(), nom: nom.trim() || undefined }),
    onSuccess: (r) => { setLien(r.lien); setErr(null); qc.invalidateQueries({ queryKey: ['admin-licences'] }) },
    onError: (e) => setErr(e instanceof Error ? e.message : 'Création impossible.'),
  })
  return (
    <Panel>
      <div className="[counter-reset:s]">
        <div className="flex items-center gap-4 border-b border-line px-5 py-3.5 before:grid before:h-[30px] before:w-[30px] before:shrink-0 before:place-items-center before:rounded-full before:bg-mint/10 before:font-display before:text-[13px] before:font-semibold before:text-mint before:content-['1']">
          <div className="min-w-0 flex-1">
            <b className="text-sm text-txt-hi">Créer le compte</b>
            <div className="text-xs text-txt-dim">email + invitation (mécanisme officiel, cloisonné dès la création) — le lien s'envoie à la main</div>
            {lien && (
              <div className="mt-2 flex items-center gap-2">
                <code className="max-w-[420px] truncate rounded bg-surface-1 px-2 py-1 font-mono text-[10.5px] text-mint">{lien}</code>
                <ActBtn tone="ghost" onClick={() => navigator.clipboard?.writeText(lien)}>Copier</ActBtn>
              </div>
            )}
            {err && <div className="mt-1 text-[11px] text-coral">{err}</div>}
          </div>
          <div className="flex shrink-0 items-center gap-2">
            <input value={email} onChange={(e) => setEmail(e.target.value)} placeholder="email@client.re" data-nouveau-email
              className="w-44 rounded-md border border-line-2 bg-bg px-2 py-1.5 text-xs text-txt outline-none focus:border-mint" />
            <input value={nom} onChange={(e) => setNom(e.target.value)} placeholder="Nom (option)"
              className="w-32 rounded-md border border-line-2 bg-bg px-2 py-1.5 text-xs text-txt outline-none focus:border-mint" />
            <ActBtn onClick={() => creer.mutate()} disabled={!email.includes('@') || creer.isPending}>Créer →</ActBtn>
          </div>
        </div>
        <div className="flex items-center gap-4 border-b border-line px-5 py-3.5 before:grid before:h-[30px] before:w-[30px] before:shrink-0 before:place-items-center before:rounded-full before:bg-mint/10 before:font-display before:text-[13px] before:font-semibold before:text-mint before:content-['2']">
          <div>
            <b className="text-sm text-txt-hi">Lier l'abonnement Stripe</b>
            <div className="text-xs text-txt-dim">bouton « Lien de souscription » sur la fiche du client (349 €/mois) — la licence passe « active » au premier paiement</div>
          </div>
        </div>
        <div className="flex items-center gap-4 px-5 py-3.5 before:grid before:h-[30px] before:w-[30px] before:shrink-0 before:place-items-center before:rounded-full before:bg-mint/10 before:font-display before:text-[13px] before:font-semibold before:text-mint before:content-['3']">
          <div>
            <b className="text-sm text-txt-hi">Dérouler la séquence d'onboarding</b>
            <div className="text-xs text-txt-dim">Mail 1 → 2 → 3 sur sa fiche — vous déclenchez chaque envoi à votre rythme (templates Brevo) ; l'app rappelle à J+3 et J+10</div>
          </div>
        </div>
      </div>
    </Panel>
  )
}

export function LicencesSection() {
  const q = useQuery({ queryKey: ['admin-licences'], queryFn: getAdminLicences, refetchInterval: 120_000 })
  const d = q.data
  if (!d) return <div className="py-10 text-center text-xs text-txt-mut">Chargement…</div>
  const orphelins = d.rapprochement && !d.rapprochement.indisponible
    ? [...d.rapprochement.comptes_sans_abo.map((o) => `Compte app « ${o.nom} » sans abonnement Stripe actif`),
       ...d.rapprochement.abos_sans_compte.map((o) => `Abonnement Stripe ${o.email ?? o.customer_id} sans compte app lié`)]
    : []
  return (
    <>
      {!d.brevo.api && (
        <div className="mb-3.5 rounded-lg border border-amber/30 bg-amber/5 px-4 py-2.5 text-xs text-amber">
          Brevo non configuré (LABUSE_BREVO_API_KEY) — les boutons d'envoi restent visibles et le diront : aucun envoi silencieux.
        </div>
      )}
      {orphelins.length > 0 && (
        <div className="mb-3.5 rounded-lg border border-amber/30 bg-amber/5 px-4 py-2.5 text-xs text-amber">
          <b>Rapprochement Stripe ⇄ comptes :</b> {orphelins.join(' · ')}
        </div>
      )}
      <Panel>
        {d.licences.map((l) => <ClientRow key={l.id} l={l} stripeConfigure={d.stripe_configure} />)}
        {!d.licences.length && <div className="px-5 py-8 text-center text-xs text-txt-mut">Aucun compte client — créez le premier ci-dessous.</div>}
        <div className="border-t border-line bg-surface-1 px-5 py-3 text-xs text-txt-mut">
          <b className="text-txt">Règle :</b> la suspension est toujours <b className="text-txt">manuelle</b> (votre bouton) — jamais automatique
          sur un échec de carte. Alerte ambre si un compte app existe sans abonnement Stripe actif, ou l'inverse.
        </div>
      </Panel>
      <H2>Onboarder un nouveau client</H2>
      <NouveauClient />
    </>
  )
}
