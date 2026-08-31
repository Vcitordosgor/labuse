// SECTEUR-1 (S2) — Contacts institutionnels : les 24 mairies (adresse, téléphone, courriel, site),
// les EPCI, la DEAL et l'ADIL. La MÊME donnée que la fiche commune (mairie_de), réunie et triable.
// Pas de notes de relation — le CRM de Vic reste dans Notion.
import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getContactsInstitutionnels, type Mairie } from '../../lib/api'
import { Loading } from '../Loading'

type Cle = 'commune' | 'telephone' | 'email'
const COLS: { cle: Cle; label: string }[] = [
  { cle: 'commune', label: 'Commune' },
  { cle: 'telephone', label: 'Téléphone' },
  { cle: 'email', label: 'Courriel' },
]

const val = (m: Mairie, c: Cle) => (m[c] ?? '').toString().toLowerCase()

export function ContactsSection() {
  const q = useQuery({ queryKey: ['contacts-institutionnels'], queryFn: getContactsInstitutionnels })
  const [tri, setTri] = useState<Cle>('commune')
  const [asc, setAsc] = useState(true)
  const [filtre, setFiltre] = useState('')

  const mairies = useMemo(() => {
    const src = q.data?.mairies ?? []
    const f = filtre.trim().toLowerCase()
    const filtered = f ? src.filter((m) => `${m.commune} ${m.email ?? ''} ${m.telephone ?? ''}`.toLowerCase().includes(f)) : src
    return [...filtered].sort((a, b) => (asc ? 1 : -1) * val(a, tri).localeCompare(val(b, tri)))
  }, [q.data, tri, asc, filtre])

  if (q.isLoading) return <Loading label="Contacts…" className="mx-auto mt-6 text-xs" />
  const d = q.data
  if (!d) return null
  const setTriCol = (c: Cle) => (c === tri ? setAsc((v) => !v) : (setTri(c), setAsc(true)))

  return (
    <div data-admin-contacts className="flex flex-col gap-5 text-[12.5px]">
      {/* Les 24 mairies — tableau triable */}
      <section>
        <div className="mb-2 flex items-center gap-3">
          <h3 className="font-display text-sm font-bold text-txt-hi">Les 24 mairies</h3>
          <span className="text-[11px] text-txt-dim">{mairies.length} affichées</span>
          <input data-contacts-filtre value={filtre} onChange={(e) => setFiltre(e.target.value)} placeholder="Filtrer…"
                 className="ml-auto h-7 w-40 rounded-md border border-line-2 bg-surface-1 px-2 text-[11.5px] text-txt" />
        </div>
        <div className="overflow-hidden rounded-lg border border-line-2">
          <div className="grid grid-cols-[1.1fr_1fr_1.6fr_1.4fr] bg-surface-2 text-[11px] font-semibold text-txt-mut">
            {COLS.map((c) => (
              <button key={c.cle} data-contacts-tri={c.cle} onClick={() => setTriCol(c.cle)}
                      className="flex items-center gap-1 px-3 py-2 text-left hover:text-txt">
                {c.label}{tri === c.cle && <span className="text-mint">{asc ? '▲' : '▼'}</span>}
              </button>
            ))}
            <span className="px-3 py-2">Adresse · site</span>
          </div>
          {mairies.map((m) => (
            <div key={m.commune} data-contacts-mairie={m.commune}
                 className="grid grid-cols-[1.1fr_1fr_1.6fr_1.4fr] border-t border-line-2 text-[11.5px]">
              <span className="px-3 py-2 font-semibold text-txt-hi">{m.commune}</span>
              <span className="px-3 py-2 text-txt-mut">{m.telephone ?? <i className="text-txt-dim">absent</i>}</span>
              <span className="truncate px-3 py-2 text-txt-mut" title={m.email ?? ''}>
                {m.email ? <a href={`mailto:${m.email}`} className="text-mint hover:underline">{m.email}</a> : <i className="text-txt-dim">absent</i>}
              </span>
              <span className="truncate px-3 py-2 text-txt-dim" title={m.adresse ?? ''}>
                {m.adresse ?? '—'}
                {m.site_officiel && <> · <a href={m.site_officiel} target="_blank" rel="noreferrer" className="text-mint hover:underline">site</a></>}
              </span>
            </div>
          ))}
        </div>
        <p className="mt-1 text-[10px] text-txt-dim">Service urbanisme non porté par la source (service-public.fr) → absent, jamais inventé.</p>
      </section>

      {/* EPCI */}
      <section>
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
        <h3 className="mb-2 font-display text-sm font-bold text-txt-hi">Services de l'État & information logement</h3>
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

      <p className="text-[10px] leading-snug text-txt-dim">{d.note}</p>
    </div>
  )
}
