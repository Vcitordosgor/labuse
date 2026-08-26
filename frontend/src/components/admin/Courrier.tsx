// DASHBOARD-V1 · D8 — COURRIER : « la page qui manquait ». Tuiles (à traiter / en cours /
// postées ce mois) + table des demandes avec transitions Demandé → Imprimé → Posté (boutons,
// journalisées, le client voit le même statut de son côté) et « Voir le PDF » (corps rendu
// par l'endpoint /courrier/pdf existant — adressage générique, aucune identité de particulier).
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

const LIBELLES: Record<string, string> = {
  demande: 'Demandé', tarif_confirme: 'Tarif confirmé', imprime: 'Imprimé', poste: 'Posté', envoye: 'Envoyé', a_traiter: 'À traiter',
}
const A_TRAITER = new Set(['demande', 'a_traiter'])
const EN_COURS = new Set(['tarif_confirme', 'imprime'])
const POSTEE = new Set(['poste', 'envoye'])

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
  const demandes = q.data?.demandes
  if (!demandes) return <div className="py-10 text-center text-xs text-txt-mut">Chargement…</div>
  const moisCourant = new Date().toISOString().slice(0, 7)
  const nATraiter = demandes.filter((d) => A_TRAITER.has(d.statut)).length
  const nEnCours = demandes.filter((d) => EN_COURS.has(d.statut)).length
  const posteesMois = demandes.filter((d) => POSTEE.has(d.statut) && (d.updated_at ?? '').startsWith(moisCourant))
  const nCourriersMois = posteesMois.reduce((s, d) => s + d.n, 0)
  return (
    <>
      <div className="mb-3.5 grid grid-cols-3 gap-3.5">
        <div className="rounded-xl border border-line bg-surface-2 px-4 py-4">
          <Lbl>À traiter</Lbl>
          <div className={`font-display text-2xl font-semibold ${nATraiter ? 'text-amber' : 'text-txt-hi'}`}>{nATraiter}</div>
          <div className="mt-1 text-[11.5px] text-txt-mut">demande{nATraiter > 1 ? 's' : ''} en attente d'impression</div>
        </div>
        <div className="rounded-xl border border-line bg-surface-2 px-4 py-4">
          <Lbl>En cours</Lbl>
          <div className="font-display text-2xl font-semibold text-txt-hi">{nEnCours}</div>
          <div className="mt-1 text-[11.5px] text-txt-mut">imprimée{nEnCours > 1 ? 's' : ''}, à affranchir et poster</div>
        </div>
        <div className="rounded-xl border border-line bg-surface-2 px-4 py-4">
          <Lbl>Postées ce mois</Lbl>
          <div className="font-display text-2xl font-semibold text-mint">{posteesMois.length}</div>
          <div className="mt-1 text-[11.5px] text-txt-mut">{nCourriersMois} courrier{nCourriersMois > 1 ? 's' : ''} au total</div>
        </div>
      </div>

      <Panel>
        <table className="w-full text-[13px]">
          <thead>
            <tr>
              {['#', 'Client', 'Parcelles', 'Demandé le', 'Statut', 'Action'].map((h, i) => (
                <th key={h} className={`border-b border-line px-4 py-2.5 font-mono text-[9.5px] font-medium uppercase tracking-[0.12em] text-txt-dim ${i === 5 ? 'text-right' : 'text-left'}`}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {demandes.map((d) => (
              <tr key={d.id} className="border-b border-line last:border-b-0 hover:bg-surface-3" data-demande={d.id}>
                <td className="px-4 py-2.5 font-mono text-xs text-txt-dim">{d.id}</td>
                <td className="px-4 py-2.5"><b>{d.client ?? 'pilote/admin'}</b></td>
                <td className="px-4 py-2.5 font-mono text-xs text-txt-mut">{d.n}{d.communes ? ` · ${d.communes}` : ''}</td>
                <td className="px-4 py-2.5 font-mono text-xs text-txt-dim">{fmtReu(d.ts)}</td>
                <td className="px-4 py-2.5">
                  {POSTEE.has(d.statut)
                    ? <Chip tone="ok">Posté ✓ {fmtReu(d.updated_at, false)}</Chip>
                    : <Chip tone={A_TRAITER.has(d.statut) ? 'warn' : 'ok'}>{LIBELLES[d.statut] ?? d.statut}</Chip>}
                </td>
                <td className="px-4 py-2.5 text-right">
                  <span className="inline-flex items-center gap-1.5">
                    <ActBtn tone="ghost" onClick={() => voirPdf(d)}>Voir le PDF</ActBtn>
                    {A_TRAITER.has(d.statut) && (
                      <ActBtn onClick={() => avancer.mutate({ id: d.id, statut: 'imprime' })} disabled={avancer.isPending}>
                        Passer à « Imprimé »
                      </ActBtn>
                    )}
                    {EN_COURS.has(d.statut) && (
                      <ActBtn onClick={() => avancer.mutate({ id: d.id, statut: 'poste' })} disabled={avancer.isPending}>
                        Passer à « Posté »
                      </ActBtn>
                    )}
                    {POSTEE.has(d.statut) && <span className="font-mono text-xs text-txt-dim">terminé</span>}
                  </span>
                </td>
              </tr>
            ))}
            {!demandes.length && <tr><td colSpan={6} className="px-4 py-6 text-center text-xs text-txt-mut">Aucune demande d'envoi.</td></tr>}
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
