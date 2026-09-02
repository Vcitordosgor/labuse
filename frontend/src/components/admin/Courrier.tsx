// DASHBOARD-V1 · D8 / CONNEXIONS-2 Lot 4 (KO-6) / ADMIN-1 AD8 — COURRIER admin : « N courriers
// attendent ton dépôt ». VUE PAR COMPTE (sélecteur en tête) + chips de statut UNIFIÉS (Demandé →
// Déposé → Envoyé → Répondu / Sans réponse, libellés servis par le backend courrier.STATUT_LIBELLES,
// « à déposer » présenté ainsi et sélectionné par défaut). Aperçu du courrier réel (PDF), actions
// Marquer déposé / envoyé, lien vers la piste CRM d'origine. AUCUN changement de mécanique : même
// table courrier_demandes, mêmes endpoints — mieux présentée.
import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { getAdminCourrierDemandes, postAdminCourrierStatut, urlCourrierPdf, type AdminDemandeCourrier } from '../../lib/api'
import { ActBtn, Chip, Lbl, Panel } from './AdminView'

const fmtReu = (iso?: string | null, avecHeure = true) => {
  if (!iso) return '—'
  try {
    return new Intl.DateTimeFormat('fr-FR', {
      timeZone: 'Indian/Reunion', day: '2-digit', month: '2-digit',
      ...(avecHeure ? { hour: '2-digit', minute: '2-digit' } : {}),
    }).format(new Date(iso)).replace(',', '')
  } catch { return '—' }
}

// Buckets (mêmes que le KPI Pilotage / courrier.STATUT_BUCKET). Alias legacy tolérés.
const A_DEPOSER = new Set(['demande', 'a_traiter', 'tarif_confirme'])
const EN_COURS = new Set(['depose', 'envoye', 'imprime', 'poste'])
const CLOS = new Set(['repondu', 'sans_reponse'])
// Ordre canonique des chips ; « demande » est présenté « À déposer » (AD8 : c'est le travail du jour).
const ORDRE: string[] = ['demande', 'depose', 'envoye', 'repondu', 'sans_reponse']
const CHIP_LABEL: Record<string, string> = { demande: 'À déposer' }   // le reste = statut_libelles servi

function voirPdf(d: AdminDemandeCourrier) {
  fetch(urlCourrierPdf, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ texte: d.corps ?? '', idu: d.parcelles?.[0] ?? null }),
  }).then(async (r) => {
    if (!r.ok) return
    const blob = await r.blob()
    const url = URL.createObjectURL(blob)
    window.open(url, '_blank')
    setTimeout(() => URL.revokeObjectURL(url), 60_000)
  }).catch(() => {})
}

export function CourrierSection() {
  const qc = useQueryClient()
  const q = useQuery({ queryKey: ['admin-courrier'], queryFn: getAdminCourrierDemandes, refetchInterval: 60_000 })
  const avancer = useMutation({
    mutationFn: ({ id, statut }: { id: number; statut: string }) => postAdminCourrierStatut(id, statut),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['admin-courrier'] }); qc.invalidateQueries({ queryKey: ['admin-pilotage'] }) },
  })
  const [compte, setCompte] = useState<string>('tous')
  const [statut, setStatut] = useState<string>('demande')   // AD8 — « À déposer » par défaut

  const demandes = q.data?.demandes
  const libelles = q.data?.statut_libelles ?? {}
  const lib = (s: string) => CHIP_LABEL[s] ?? libelles[s] ?? s

  // options de compte (clients distincts) — dérivées des demandes
  const comptes = useMemo(() => {
    const set = new Set<string>()
    for (const d of demandes ?? []) set.add(d.client ?? 'interne')
    return Array.from(set).sort((a, b) => a.localeCompare(b, 'fr'))
  }, [demandes])

  if (!demandes) return <div className="py-10 text-center text-xs text-txt-mut">Chargement…</div>

  const parCompte = compte === 'tous' ? demandes : demandes.filter((d) => (d.client ?? 'interne') === compte)
  const compteurs: Record<string, number> = {}
  for (const s of ORDRE) compteurs[s] = 0
  for (const d of parCompte) {
    const s = A_DEPOSER.has(d.statut) ? 'demande' : EN_COURS.has(d.statut) && d.statut !== 'envoye' ? 'depose'
      : d.statut === 'poste' ? 'envoye' : d.statut
    if (s in compteurs) compteurs[s] += 1
  }
  const lignes = parCompte.filter((d) => {
    if (statut === 'tous') return true
    if (statut === 'demande') return A_DEPOSER.has(d.statut)
    if (statut === 'depose') return d.statut === 'depose' || d.statut === 'imprime'
    if (statut === 'envoye') return d.statut === 'envoye' || d.statut === 'poste'
    return d.statut === statut
  })

  const moisCourant = new Date().toISOString().slice(0, 7)
  const nADeposer = parCompte.filter((d) => A_DEPOSER.has(d.statut)).length
  const nEnCours = parCompte.filter((d) => EN_COURS.has(d.statut)).length
  const closMois = parCompte.filter((d) => CLOS.has(d.statut) && (d.updated_at ?? '').startsWith(moisCourant))
  const nCourriersMois = closMois.reduce((s, d) => s + d.n, 0)

  return (
    <>
      <div className="mb-3.5 grid grid-cols-3 gap-3.5">
        <div className="rounded-xl border border-line bg-surface-2 px-4 py-4">
          <Lbl>À déposer</Lbl>
          <div className={`font-display text-2xl font-semibold ${nADeposer ? 'text-amber' : 'text-txt-hi'}`}>{nADeposer}</div>
          <div className="mt-1 text-[11.5px] text-txt-mut">demande{nADeposer > 1 ? 's' : ''} à déposer{compte !== 'tous' ? ' · ce compte' : ''}</div>
        </div>
        <div className="rounded-xl border border-line bg-surface-2 px-4 py-4">
          <Lbl>En cours</Lbl>
          <div className="font-display text-2xl font-semibold text-txt-hi">{nEnCours}</div>
          <div className="mt-1 text-[11.5px] text-txt-mut">déposée{nEnCours > 1 ? 's' : ''} / envoyée{nEnCours > 1 ? 's' : ''}, en attente de retour</div>
        </div>
        <div className="rounded-xl border border-line bg-surface-2 px-4 py-4">
          <Lbl>Clos ce mois</Lbl>
          <div className="font-display text-2xl font-semibold text-mint">{closMois.length}</div>
          <div className="mt-1 text-[11.5px] text-txt-mut">{nCourriersMois} courrier{nCourriersMois > 1 ? 's' : ''} (répondu / sans réponse)</div>
        </div>
      </div>

      {/* barre de filtres : compte + chips de statut unifiés */}
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <select value={compte} onChange={(e) => setCompte(e.target.value)}
          className="rounded-lg border border-line-2 bg-surface-2 px-2.5 py-1.5 text-xs text-txt">
          <option value="tous">Compte : tous</option>
          {comptes.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
        <Chip tone={statut === 'tous' ? 'ok' : 'off'} onClick={() => setStatut('tous')}>Tous {parCompte.length}</Chip>
        {ORDRE.map((s) => (
          <Chip key={s} tone={statut === s ? (s === 'demande' ? 'warn' : 'ok') : 'off'} onClick={() => setStatut(s)}>
            {lib(s)} {compteurs[s]}
          </Chip>
        ))}
      </div>

      <Panel>
        <table className="w-full text-[13px]">
          <thead>
            <tr>
              {['Compte', 'Parcelle · propriétaire', 'Demandé le', 'Statut', 'Actions'].map((h, i) => (
                <th key={h} className={`border-b border-line px-4 py-2.5 font-mono text-[9.5px] font-medium uppercase tracking-[0.12em] text-txt-dim ${i === 4 ? 'text-right' : 'text-left'}`}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {lignes.map((d) => (
              <tr key={d.id} className="border-b border-line last:border-b-0 hover:bg-surface-3" data-demande={d.id}>
                <td className="px-4 py-2.5"><b>{d.client ?? 'interne'}</b></td>
                <td className="px-4 py-2.5 text-xs text-txt-mut">
                  <span className="font-mono">{d.parcelles?.[0] ?? `${d.n} parcelle${d.n > 1 ? 's' : ''}`}</span>
                  {d.communes ? <span className="text-txt-dim"> · {d.communes}</span> : null}
                  {d.pipeline_entry_id != null && (
                    <span className="ml-1.5 font-mono text-[11px] text-amber" title={`Née de la piste CRM n°${d.pipeline_entry_id} (côté client, cloisonnée)`}>→ piste CRM #{d.pipeline_entry_id} ↗</span>
                  )}
                </td>
                <td className="px-4 py-2.5 font-mono text-xs text-txt-dim">{fmtReu(d.ts)}</td>
                <td className="px-4 py-2.5">
                  {CLOS.has(d.statut)
                    ? <Chip tone="ok">{lib(d.statut)} ✓ {fmtReu(d.updated_at, false)}</Chip>
                    : <Chip tone={A_DEPOSER.has(d.statut) ? 'warn' : 'ok'}>{A_DEPOSER.has(d.statut) ? 'À déposer' : lib(d.statut)}</Chip>}
                </td>
                <td className="px-4 py-2.5 text-right">
                  <span className="inline-flex items-center gap-1.5">
                    <ActBtn tone="ghost" onClick={() => voirPdf(d)}>aperçu</ActBtn>
                    {A_DEPOSER.has(d.statut) && (
                      <ActBtn onClick={() => avancer.mutate({ id: d.id, statut: 'depose' })} disabled={avancer.isPending}>
                        Marquer déposé
                      </ActBtn>
                    )}
                    {(d.statut === 'depose' || d.statut === 'imprime') && (
                      <ActBtn onClick={() => avancer.mutate({ id: d.id, statut: 'envoye' })} disabled={avancer.isPending}>
                        Marquer envoyé
                      </ActBtn>
                    )}
                    {(d.statut === 'envoye' || d.statut === 'poste') && (
                      <>
                        <ActBtn onClick={() => avancer.mutate({ id: d.id, statut: 'repondu' })} disabled={avancer.isPending}>Marquer répondu</ActBtn>
                        <ActBtn tone="ghost" onClick={() => avancer.mutate({ id: d.id, statut: 'sans_reponse' })} disabled={avancer.isPending}>Sans réponse</ActBtn>
                      </>
                    )}
                    {CLOS.has(d.statut) && <span className="font-mono text-xs text-txt-dim">clos</span>}
                  </span>
                </td>
              </tr>
            ))}
            {!lignes.length && <tr><td colSpan={5} className="px-4 py-6 text-center text-xs text-txt-mut">Aucune demande pour ce filtre.</td></tr>}
          </tbody>
        </table>
        <div className="border-t border-line bg-surface-1 px-4 py-2.5 text-xs text-txt-mut">
          Le client voit le même statut de son côté · chaque changement est journalisé (fil Pilotage + cloche client) ·
          adressage générique SPF/CERFA — <b className="text-txt">aucune identité de particulier</b>, comme dans l'app.
        </div>
      </Panel>
    </>
  )
}
