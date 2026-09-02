// ADMIN-1 (AD10) · RETOURS-8 (R6) — le carnet des communes en LISTE + PANNEAU. Plus de barre de
// recherche ni de bouton global en tête : on clique une commune à gauche, sa fiche s'ouvre à droite,
// et « + Ajouter » ouvre UNE LIGNE VIDE DANS CETTE COMMUNE (nom · rôle · tél · email · note). Pas de
// formulaire séparé, pas de modale. Les communes avec contacts nommés portent un badge (leur nombre).
// Le même composant d'édition (ContactEdit, partagé) sert ici ET dans la fiche commune (carte Mairie).
import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  deleteCommuneContact, getContactsInstitutionnels, patchCommuneContact, postCommuneContact,
  type Mairie,
} from '../../lib/api'
import { Loading } from '../Loading'
import { ActBtn, Chip } from './AdminView'
import { CONTACT_VIDE, ContactEdit, contactToForm, trimContact, type ContactForm } from '../shared/ContactEdit'

// Panneau droit : la commune choisie — standard officiel (lecture seule), contacts nommés (édition en
// place), et « + Ajouter » qui insère une ligne vide DANS cette commune (reste à sa place après save).
function PanneauCommune({ m }: { m: Mairie }) {
  const qc = useQueryClient()
  const [ajout, setAjout] = useState(false)
  const [edit, setEdit] = useState<number | null>(null)
  const invalider = () => qc.invalidateQueries({ queryKey: ['contacts-institutionnels'] })
  const creer = useMutation({
    mutationFn: (f: ContactForm) => postCommuneContact({ insee: m.insee ?? '', commune_nom: m.commune, ...trimContact(f) }),
    onSuccess: () => { setAjout(false); invalider() },
  })
  const modifier = useMutation({
    mutationFn: ({ id, f }: { id: number; f: ContactForm }) => patchCommuneContact(id, trimContact(f)),
    onSuccess: () => { setEdit(null); invalider() },
  })
  const suppr = useMutation({ mutationFn: (id: number) => deleteCommuneContact(id), onSuccess: invalider })
  const contacts = m.contacts ?? []
  return (
    <div data-contacts-commune={m.commune} className="rounded-xl border border-line bg-surface-2 p-4">
      <div className="flex items-center justify-between">
        <b className="font-display text-[15px] text-txt-hi">{m.commune}</b>
        {m.insee
          ? <ActBtn onClick={() => { setAjout((a) => !a); setEdit(null) }}>+ Ajouter</ActBtn>
          : <span className="text-[10.5px] text-txt-dim" title="INSEE manquant pour cette commune">INSEE inconnu</span>}
      </div>

      {/* standard officiel (Mairie & service urbanisme) — lecture seule */}
      <div className="mt-3 border-t border-line pt-2.5 text-[12px]">
        <b className="text-txt">Mairie &amp; service urbanisme</b> <span className="text-txt-dim">· standard officiel</span>
        <div className="mt-0.5 text-txt-mut">
          {[m.adresse, m.telephone].filter(Boolean).join(' · ') || <i className="text-txt-dim">coordonnées absentes</i>}
          {m.email && <> · <a href={`mailto:${m.email}`} className="text-mint hover:underline">{m.email}</a></>}
          {m.site_officiel && <> · <a href={m.site_officiel} target="_blank" rel="noreferrer" className="text-mint hover:underline">site</a></>}
        </div>
      </div>

      {/* contacts nommés — édition en place */}
      {contacts.map((c) => (
        <div key={c.id} className="mt-2.5 border-t border-line pt-2.5 text-[12px]">
          {edit === c.id ? (
            <ContactEdit init={contactToForm(c)} busy={modifier.isPending}
              onCancel={() => setEdit(null)} onSave={(f) => modifier.mutate({ id: c.id, f })} />
          ) : (
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0">
                <b className="text-txt-hi">{c.nom}</b> {c.role && <Chip tone="ok">{c.role}</Chip>}
                <div className="mt-0.5 text-txt-mut">
                  {[c.telephone, c.email].filter(Boolean).join('  ·  ') || <i className="text-txt-dim">—</i>}
                </div>
                {c.note && <div className="mt-0.5 text-[10.5px] text-txt-dim">note : {c.note}</div>}
              </div>
              <div className="flex shrink-0 gap-1">
                <ActBtn tone="ghost" onClick={() => { setEdit(c.id); setAjout(false) }}>✎</ActBtn>
                <ActBtn tone="danger" disabled={suppr.isPending}
                  onClick={() => { if (window.confirm(`Supprimer le contact « ${c.nom} » ?`)) suppr.mutate(c.id) }}>🗑</ActBtn>
              </div>
            </div>
          )}
        </div>
      ))}

      {/* la ligne d'ajout apparaît DANS la commune, sous les contacts existants */}
      {ajout && <ContactEdit init={CONTACT_VIDE} busy={creer.isPending} onCancel={() => setAjout(false)} onSave={(f) => creer.mutate(f)} />}

      <p className="mt-3 text-[10px] leading-snug text-txt-dim">
        Le contact ajouté est visible ensuite sur la fiche commune de tous les comptes. Standard officiel =
        source service-public.fr (service urbanisme non porté → absent, jamais inventé).
      </p>
    </div>
  )
}

export function ContactsSection() {
  const q = useQuery({ queryKey: ['contacts-institutionnels'], queryFn: getContactsInstitutionnels })
  const [insee, setInsee] = useState<string | null>(null)

  const mairies = q.data?.mairies ?? []
  const communes = useMemo(
    () => mairies.filter((m) => m.insee).sort((a, b) => a.commune.localeCompare(b.commune)),
    [mairies])
  // par défaut : la première commune (ou la première qui a des contacts nommés).
  const choisie = communes.find((m) => m.insee === insee)
    ?? communes.find((m) => (m.contacts?.length ?? 0) > 0) ?? communes[0] ?? null

  if (q.isLoading) return <Loading label="Contacts…" className="mx-auto mt-6 text-xs" />
  const d = q.data
  if (!d) return null

  return (
    <div data-admin-contacts className="flex flex-col gap-4 text-[12.5px]">
      <div className="grid grid-cols-[260px_1fr] gap-3.5 max-[900px]:grid-cols-1">
        {/* colonne gauche : les communes, badge = nombre de contacts NOMMÉS */}
        <div data-contacts-liste className="flex flex-col gap-1">
          {communes.map((m) => {
            const n = m.contacts?.length ?? 0
            const on = choisie?.insee === m.insee
            return (
              <button key={m.insee} type="button" onClick={() => setInsee(m.insee ?? null)}
                data-contacts-item={m.commune}
                className={`flex items-center justify-between rounded-lg border px-3 py-2 text-left text-[12.5px] transition-colors duration-quick ${
                  on ? 'border-mint bg-mint/[0.06] text-txt-hi' : 'border-line bg-surface-2 text-txt hover:border-line-2'}`}>
                <span className="min-w-0 truncate">{m.commune}</span>
                {n > 0 && <span className="ml-2 shrink-0 rounded-full bg-mint/12 px-1.5 text-[10.5px] text-mint">{n}</span>}
              </button>
            )
          })}
          {!communes.length && <div className="py-4 text-center text-xs text-txt-dim">Aucune commune.</div>}
        </div>

        {/* panneau droit : la commune choisie */}
        {choisie ? <PanneauCommune key={choisie.insee} m={choisie} />
          : <div className="rounded-xl border border-line bg-surface-2 p-4 text-xs text-txt-dim">Choisissez une commune à gauche.</div>}
      </div>

      {/* EPCI (secondaire, conservé) */}
      <section className="mt-2">
        <h3 className="mb-2 font-display text-sm font-bold text-txt-hi">Intercommunalités (EPCI)</h3>
        <div className="flex flex-col gap-1.5">
          {d.epci.map((e) => (
            <div key={e.code} data-contacts-epci={e.code} className="rounded-lg border border-line-2 bg-surface-2 p-2.5">
              <b className="text-[12.5px] text-txt-hi">{e.code}</b> <span className="text-txt-mut">— {e.nom}</span>
              <p className="mt-0.5 text-[11px] text-txt-dim">{e.communes.length} communes : {e.communes.join(', ')}</p>
            </div>
          ))}
        </div>
      </section>

      {/* DEAL / ADIL (secondaire, conservé) */}
      <section>
        <h3 className="mb-2 font-display text-sm font-bold text-txt-hi">Services de l'État &amp; information logement</h3>
        <div className="flex flex-col gap-1.5">
          {d.autres.map((a) => (
            <div key={a.type} data-contacts-autre={a.type} className="rounded-lg border border-line-2 bg-surface-2 p-2.5">
              <div className="flex items-baseline gap-2">
                <span className="rounded bg-mint/12 px-1.5 py-0.5 font-mono text-[10px] text-mint">{a.type}</span>
                <b className="text-[12px] text-txt-hi">{a.nom}</b>
              </div>
              <p className="mt-1 text-[11px] text-txt-mut">{a.adresse}</p>
              <p className="mt-0.5 text-[11px] text-txt-dim">{a.telephone} · <a href={a.site} target="_blank" rel="noreferrer" className="text-mint hover:underline">{a.site.replace(/^https?:\/\//, '')}</a></p>
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}
