// RETOURS-8 (R6) — LE composant d'édition d'un contact de commune, PARTAGÉ entre la page admin
// « Contacts » (liste + panneau) et la fiche commune (carte Mairie). Un seul geste d'ajout/édition :
// nom · rôle · tél · email · note · Enregistrer/annuler. Extrait de l'ancien Contacts.tsx (S0.2) pour
// que les deux surfaces partagent EXACTEMENT le même formulaire (plus de divergence de champs).
import { useState } from 'react'
import type { CommuneContact, CommuneContactIn } from '../../lib/api'
import { ActBtn } from '../admin/AdminView'

export type ContactForm = { nom: string; role: string; telephone: string; email: string; note: string }
export const CONTACT_VIDE: ContactForm = { nom: '', role: '', telephone: '', email: '', note: '' }

/** Corps de contact (sans insee/commune) prêt pour l'API — trim + null sur les champs vides. */
export const trimContact = (f: ContactForm): Omit<CommuneContactIn, 'insee' | 'commune_nom'> => ({
  nom: f.nom.trim(), role: f.role.trim() || null, telephone: f.telephone.trim() || null,
  email: f.email.trim() || null, note: f.note.trim() || null,
})
export const contactToForm = (c: CommuneContact): ContactForm => ({
  nom: c.nom, role: c.role ?? '', telephone: c.telephone ?? '', email: c.email ?? '', note: c.note ?? '',
})

export function ContactEdit({ init, onCancel, onSave, busy }: {
  init: ContactForm; onCancel: () => void; onSave: (f: ContactForm) => void; busy: boolean
}) {
  const [f, setF] = useState<ContactForm>(init)
  const champ = (k: keyof ContactForm, ph: string, w = 'w-full') => (
    <input value={f[k]} onChange={(e) => setF({ ...f, [k]: e.target.value })} placeholder={ph}
      className={`${w} rounded-md border border-line-2 bg-surface-1 px-2 py-1 text-[11.5px] text-txt`} />
  )
  return (
    <div className="mt-2 rounded-lg border border-mint/30 bg-mint/5 p-2.5" data-contact-edit>
      <div className="grid grid-cols-2 gap-1.5">
        {champ('nom', 'Nom (ex. Mme Gwenaëlle Serveau)')}
        {champ('role', 'Rôle (ex. resp. PLU)')}
        {champ('telephone', 'Téléphone')}
        {champ('email', 'Email')}
      </div>
      {champ('note', 'Note (ex. joignable le matin — zone AU nord)')}
      <div className="mt-2 flex items-center gap-2">
        <ActBtn onClick={() => onSave(f)} disabled={busy || !f.nom.trim()}>{busy ? 'Enregistrement…' : 'Enregistrer'}</ActBtn>
        <ActBtn tone="ghost" onClick={onCancel}>Annuler</ActBtn>
      </div>
    </div>
  )
}
