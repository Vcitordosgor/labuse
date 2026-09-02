// ADMIN-1 (AD10) — le carnet des communes. Recherche en tête, UNE CARTE PAR COMMUNE : le standard
// officiel (mairie & service urbanisme, source service-public.fr) puis les contacts NOMMÉS ajoutés
// (nom, rôle, tél, mail, note), éditables en place. Communes avec contacts d'abord. Les EPCI et la
// DEAL/ADIL restent accessibles en second. CRUD admin ici ET depuis la fiche commune (carte Mairie).
// S0.2 — UN SEUL bouton « + Ajouter un contact » (en-tête, choix de la commune d'abord) ; sur chaque
// carte, un « + » discret au survol ; communes sans contact reléguées en bas, en lignes compactes.
import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  deleteCommuneContact, getContactsInstitutionnels, patchCommuneContact, postCommuneContact,
  type CommuneContact, type CommuneContactIn, type Mairie,
} from '../../lib/api'
import { Loading } from '../Loading'
import { ActBtn, Chip } from './AdminView'

type ContactForm = { nom: string; role: string; telephone: string; email: string; note: string }
const VIDE: ContactForm = { nom: '', role: '', telephone: '', email: '', note: '' }

function ContactEdit({ init, onCancel, onSave, busy }: {
  init: ContactForm; onCancel: () => void; onSave: (f: ContactForm) => void; busy: boolean
}) {
  const [f, setF] = useState<ContactForm>(init)
  const champ = (k: keyof ContactForm, ph: string, w = 'w-full') => (
    <input value={f[k]} onChange={(e) => setF({ ...f, [k]: e.target.value })} placeholder={ph}
      className={`${w} rounded-md border border-line-2 bg-surface-1 px-2 py-1 text-[11.5px] text-txt`} />
  )
  return (
    <div className="mt-2 rounded-lg border border-mint/30 bg-mint/5 p-2.5">
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

// S0.2 — le formulaire d'ajout global : on CHOISIT d'abord la commune (recherche/select), puis les
// champs contact. Peut être pré-rempli avec une commune (« + » d'une carte).
function AjoutGlobal({ mairies, initInsee, onDone }: {
  mairies: Mairie[]; initInsee: string | null; onDone: () => void
}) {
  const qc = useQueryClient()
  const cibles = useMemo(() => mairies.filter((m) => m.insee), [mairies])
  const [insee, setInsee] = useState<string>(initInsee ?? '')
  const m = cibles.find((x) => x.insee === insee) ?? null
  const creer = useMutation({
    mutationFn: (f: ContactForm) => postCommuneContact({ insee: m?.insee ?? '', commune_nom: m?.commune ?? '', ...trim(f) }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['contacts-institutionnels'] }); onDone() },
  })
  return (
    <div data-contacts-ajout-global className="rounded-xl border border-mint/30 bg-mint/5 p-3.5">
      <div className="flex items-center justify-between">
        <b className="font-display text-sm text-txt-hi">Ajouter un contact</b>
        <ActBtn tone="ghost" onClick={onDone}>Fermer</ActBtn>
      </div>
      <label className="mt-2 block text-[11px] text-txt-mut">Commune</label>
      <select value={insee} onChange={(e) => setInsee(e.target.value)}
        data-contacts-ajout-commune
        className="mt-0.5 h-9 w-full rounded-lg border border-line-2 bg-surface-1 px-2 text-[13px] text-txt">
        <option value="">Choisir une commune…</option>
        {cibles.map((c) => <option key={c.insee} value={c.insee ?? ''}>{c.commune}</option>)}
      </select>
      {m
        ? <ContactEdit init={VIDE} busy={creer.isPending} onCancel={onDone} onSave={(f) => creer.mutate(f)} />
        : <p className="mt-2 text-[11px] text-txt-dim">Choisissez d'abord une commune pour saisir le contact.</p>}
    </div>
  )
}

function CarteCommune({ m }: { m: Mairie }) {
  const qc = useQueryClient()
  const [ajout, setAjout] = useState(false)
  const [edit, setEdit] = useState<number | null>(null)
  const invalider = () => qc.invalidateQueries({ queryKey: ['contacts-institutionnels'] })
  const creer = useMutation({
    mutationFn: (f: ContactForm) => postCommuneContact({ insee: m.insee ?? '', commune_nom: m.commune, ...trim(f) }),
    onSuccess: () => { setAjout(false); invalider() },
  })
  const modifier = useMutation({
    mutationFn: ({ id, f }: { id: number; f: ContactForm }) => patchCommuneContact(id, trim(f)),
    onSuccess: () => { setEdit(null); invalider() },
  })
  const suppr = useMutation({ mutationFn: (id: number) => deleteCommuneContact(id), onSuccess: invalider })
  const contacts = m.contacts ?? []
  return (
    <div data-contacts-commune={m.commune} className="group rounded-xl border border-line bg-surface-2 p-3.5">
      <div className="flex items-center justify-between">
        <div>
          <b className="font-display text-sm text-txt-hi">{m.commune}</b>
          {contacts.length > 0 && <span className="ml-2 text-[11px] text-txt-dim">{contacts.length} contact(s)</span>}
        </div>
      </div>

      {/* standard officiel */}
      <div className="mt-2 border-t border-line pt-2 text-[11.5px]">
        <b className="text-txt">Mairie &amp; service urbanisme</b> <span className="text-txt-dim">· standard officiel</span>
        <div className="mt-0.5 text-txt-mut">
          {[m.adresse, m.telephone].filter(Boolean).join(' · ') || <i className="text-txt-dim">coordonnées absentes</i>}
          {m.email && <> · <a href={`mailto:${m.email}`} className="text-mint hover:underline">{m.email}</a></>}
          {m.site_officiel && <> · <a href={m.site_officiel} target="_blank" rel="noreferrer" className="text-mint hover:underline">site</a></>}
        </div>
      </div>

      {/* contacts nommés */}
      {contacts.map((c) => (
        <div key={c.id} className="mt-2 border-t border-line pt-2 text-[11.5px]">
          {edit === c.id ? (
            <ContactEdit init={toForm(c)} busy={modifier.isPending}
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

      {ajout && <ContactEdit init={VIDE} busy={creer.isPending} onCancel={() => setAjout(false)} onSave={(f) => creer.mutate(f)} />}

      {/* S0.2 — « + » discret en pied de carte : au survol sur desktop, toujours visible sur mobile. */}
      {!ajout && (
        <div className="mt-2 border-t border-line pt-2 opacity-100 transition sm:opacity-0 sm:group-hover:opacity-100">
          {m.insee
            ? <button type="button" onClick={() => { setAjout(true); setEdit(null) }}
                className="text-[11px] font-medium text-mint hover:underline">+ Ajouter un contact</button>
            : <span className="text-[10.5px] text-txt-dim" title="INSEE manquant pour cette commune">INSEE inconnu</span>}
        </div>
      )}
    </div>
  )
}

const trim = (f: ContactForm): Omit<CommuneContactIn, 'insee' | 'commune_nom'> => ({
  nom: f.nom.trim(), role: f.role.trim() || null, telephone: f.telephone.trim() || null,
  email: f.email.trim() || null, note: f.note.trim() || null,
})
const toForm = (c: CommuneContact): ContactForm => ({
  nom: c.nom, role: c.role ?? '', telephone: c.telephone ?? '', email: c.email ?? '', note: c.note ?? '',
})

// S0.2 — carte compacte (une ligne) pour les communes SANS contact nommé : « + » discret pour en ajouter.
function CarteCommuneVide({ m, onAjout }: { m: Mairie; onAjout: (insee: string) => void }) {
  return (
    <div data-contacts-commune={m.commune} data-contacts-vide
      className="group flex items-center justify-between rounded-lg border border-line-2 bg-surface-2 px-3 py-1.5 text-[12px]">
      <div className="min-w-0 truncate">
        <b className="text-txt-hi">{m.commune}</b>
        <span className="ml-2 text-txt-dim">
          {[m.adresse, m.telephone].filter(Boolean).join(' · ') || 'coordonnées absentes'}
        </span>
      </div>
      {m.insee
        ? <button type="button" onClick={() => onAjout(m.insee ?? '')}
            className="ml-2 shrink-0 text-[11px] font-medium text-mint opacity-100 transition hover:underline sm:opacity-0 sm:group-hover:opacity-100">
            + contact
          </button>
        : <span className="ml-2 shrink-0 text-[10.5px] text-txt-dim" title="INSEE manquant">INSEE inconnu</span>}
    </div>
  )
}

export function ContactsSection() {
  const q = useQuery({ queryKey: ['contacts-institutionnels'], queryFn: getContactsInstitutionnels })
  const [filtre, setFiltre] = useState('')
  // S0.2 — un seul flux d'ajout : null = fermé, '' = ouvert sans commune, '<insee>' = pré-rempli.
  const [ajout, setAjout] = useState<string | null>(null)

  const mairies = q.data?.mairies ?? []

  const { avecContacts, sansContacts } = useMemo(() => {
    const f = filtre.trim().toLowerCase()
    const filtered = f ? mairies.filter((m) => m.commune.toLowerCase().includes(f)) : mairies
    const tri = (a: Mairie, b: Mairie) => a.commune.localeCompare(b.commune)
    return {
      avecContacts: filtered.filter((m) => (m.contacts?.length ?? 0) > 0).sort(tri),
      sansContacts: filtered.filter((m) => (m.contacts?.length ?? 0) === 0).sort(tri),
    }
  }, [mairies, filtre])

  if (q.isLoading) return <Loading label="Contacts…" className="mx-auto mt-6 text-xs" />
  const d = q.data
  if (!d) return null

  return (
    <div data-admin-contacts className="flex flex-col gap-4 text-[12.5px]">
      <div className="flex items-center gap-2.5">
        <input data-contacts-filtre value={filtre} onChange={(e) => setFiltre(e.target.value)}
          placeholder="🔍  Chercher une commune… (Saint-André)"
          className="h-9 min-w-0 flex-1 rounded-lg border border-line-2 bg-surface-1 px-3 text-[13px] text-txt" />
        <ActBtn onClick={() => setAjout((a) => (a === null ? '' : null))}>+ Ajouter un contact</ActBtn>
      </div>

      {ajout !== null && (
        <AjoutGlobal mairies={mairies} initInsee={ajout || null} onDone={() => setAjout(null)} />
      )}

      {avecContacts.length > 0 && (
        <div className="grid grid-cols-2 gap-2.5 max-[900px]:grid-cols-1">
          {avecContacts.map((m) => <CarteCommune key={m.commune} m={m} />)}
        </div>
      )}

      {sansContacts.length > 0 && (
        <section>
          <h3 className="mb-1.5 font-display text-sm font-bold text-txt-hi">
            Sans contact nommé <span className="text-txt-dim">· {sansContacts.length}</span>
          </h3>
          <div className="flex flex-col gap-1">
            {sansContacts.map((m) => <CarteCommuneVide key={m.commune} m={m} onAjout={setAjout} />)}
          </div>
        </section>
      )}

      {/* EPCI */}
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

      {/* DEAL / ADIL */}
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

      <p className="text-[10px] leading-snug text-txt-dim">
        Standard officiel = source service-public.fr (service urbanisme non porté → absent, jamais inventé).
        Les contacts nommés sont ajoutés à la main et visibles sur la fiche commune de tous les comptes.
      </p>
    </div>
  )
}
