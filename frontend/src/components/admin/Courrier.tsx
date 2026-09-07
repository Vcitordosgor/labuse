// DASHBOARD-2 (Lot 3) — COURRIER : « N courriers attendent ton dépôt ». UNE grammaire, UNE table.
// Vocabulaire de statut UNIQUE, partagé avec le client, le CRM et le journal :
//   à déposer → déposé → envoyé → répondu / sans réponse.  « imprimé » et « posté » sont MIGRÉS
// (affichés « déposé » / « envoyé »), plus jamais montrés tels quels.
// Colonnes maquette : Client · Parcelle · Propriétaire (jamais un particulier) · Demandé le ·
// Piste CRM · Statut · gestes. Bouton « Marquer les N déposés » en bloc. Les demandes de test/interne
// (compte plan 'interne') sont masquées par défaut derrière un chip « N masquées » — hors de tout chiffre.
// AUCUNE mécanique réécrite : mêmes endpoints, chaque transition journalisée + cloche client.
import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  getAdminCourrierDemandes, postAdminCourrierDeposerTout, postAdminCourrierStatut,
  urlCourrierPdf, type AdminDemandeCourrier,
} from '../../lib/api'
import { ActBtn, Chip, Panel } from './AdminView'

const fmtReu = (iso?: string | null, avecHeure = true) => {
  if (!iso) return '—'
  try {
    return new Intl.DateTimeFormat('fr-FR', {
      timeZone: 'Indian/Reunion', day: '2-digit', month: '2-digit',
      ...(avecHeure ? { hour: '2-digit', minute: '2-digit' } : {}),
    }).format(new Date(iso)).replace(',', '')
  } catch { return '—' }
}

// Vocabulaire canonique unique + migration des legacy (imprimé→déposé, posté→envoyé, tarif→à déposer).
const canon = (s: string): string =>
  s === 'imprime' ? 'depose' : s === 'poste' ? 'envoye' : s === 'tarif_confirme' || s === 'a_traiter' ? 'demande' : s
const ORDRE = ['demande', 'depose', 'envoye', 'repondu', 'sans_reponse'] as const
const CLOS = new Set(['repondu', 'sans_reponse'])
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

// compte de test / interne : masqué par défaut (règle §14) — jamais compté nulle part.
const estTest = (d: AdminDemandeCourrier) => d.compte_plan === 'interne'

export function CourrierSection() {
  const qc = useQueryClient()
  const q = useQuery({ queryKey: ['admin-courrier'], queryFn: getAdminCourrierDemandes, refetchInterval: 60_000 })
  const avancer = useMutation({
    mutationFn: ({ id, statut }: { id: number; statut: string }) => postAdminCourrierStatut(id, statut),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['admin-courrier'] }); qc.invalidateQueries({ queryKey: ['admin-pilotage'] }) },
  })
  const deposerTout = useMutation({
    mutationFn: postAdminCourrierDeposerTout,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['admin-courrier'] }); qc.invalidateQueries({ queryKey: ['admin-pilotage'] }) },
  })
  const [statut, setStatut] = useState<string>('demande')   // « À déposer » par défaut
  const [voirTests, setVoirTests] = useState(false)

  const demandes = q.data?.demandes
  const libelles = q.data?.statut_libelles ?? {}
  const lib = (s: string) => CHIP_LABEL[s] ?? libelles[s] ?? s

  const nMasques = useMemo(() => (demandes ?? []).filter(estTest).length, [demandes])
  if (!demandes) return <div className="py-10 text-center text-xs text-txt-mut">Chargement…</div>

  const visibles = voirTests ? demandes : demandes.filter((d) => !estTest(d))
  const compteurs: Record<string, number> = Object.fromEntries(ORDRE.map((s) => [s, 0]))
  for (const d of visibles) { const s = canon(d.statut); if (s in compteurs) compteurs[s] += 1 }
  const lignes = statut === 'tous' ? visibles : visibles.filter((d) => canon(d.statut) === statut)
  const nADeposer = compteurs['demande']

  return (
    <>
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <Chip tone={statut === 'tous' ? 'ok' : 'off'} onClick={() => setStatut('tous')}>Tous {visibles.length}</Chip>
        {ORDRE.map((s) => (
          <Chip key={s} tone={statut === s ? (s === 'demande' ? 'warn' : 'ok') : 'off'} onClick={() => setStatut(s)}>
            {lib(s)} {compteurs[s]}
          </Chip>
        ))}
        {nMasques > 0 && (
          <Chip tone="off" onClick={() => setVoirTests((v) => !v)}>
            {voirTests ? 'masquer les tests' : `${nMasques} demande${nMasques > 1 ? 's' : ''} de test masquée${nMasques > 1 ? 's' : ''}`}
          </Chip>
        )}
        {nADeposer > 0 && (
          <span className="ml-auto">
            <ActBtn onClick={() => { if (window.confirm(`Marquer les ${nADeposer} demande(s) à déposer comme « Déposé » ? Chaque client sera prévenu.`)) deposerTout.mutate() }}
              disabled={deposerTout.isPending}>
              {deposerTout.isPending ? 'Marquage…' : `Marquer les ${nADeposer} déposés`}
            </ActBtn>
          </span>
        )}
      </div>

      <Panel>
        <table className="w-full text-[13px]">
          <thead>
            <tr>
              {['Client', 'Parcelle', 'Propriétaire', 'Demandé le', 'Piste CRM', 'Statut', 'Gestes'].map((h, i) => (
                <th key={h} className={`border-b border-line px-4 py-2.5 font-mono text-[9.5px] font-medium uppercase tracking-[0.12em] text-txt-dim ${i === 6 ? 'text-right' : 'text-left'}`}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {lignes.map((d) => {
              const s = canon(d.statut)
              return (
                <tr key={d.id} className="border-b border-line last:border-b-0 hover:bg-surface-3" data-demande={d.id}>
                  <td className="px-4 py-2.5"><b>{d.client ?? 'interne'}</b></td>
                  <td className="px-4 py-2.5 font-mono text-xs text-txt-mut">
                    {d.parcelles?.[0] ?? `${d.n} parcelle${d.n > 1 ? 's' : ''}`}
                    {d.communes ? <span className="text-txt-dim"> · {d.communes}</span> : null}
                  </td>
                  {/* propriétaire : NOMBRE de personnes morales (jamais une identité de particulier). */}
                  <td className="px-4 py-2.5 text-xs text-txt-mut">{d.proprietaire ?? <span className="text-txt-dim">—</span>}</td>
                  <td className="px-4 py-2.5 font-mono text-xs text-txt-dim">{fmtReu(d.ts)}</td>
                  <td className="px-4 py-2.5 text-xs">
                    {d.pipeline_entry_id != null
                      ? <span className="whitespace-nowrap font-mono text-amber" title={`Née de la piste CRM n°${d.pipeline_entry_id} (côté client, cloisonnée) — son statut suit celui-ci`}>piste #{d.pipeline_entry_id} ↗</span>
                      : <span className="text-txt-dim">—</span>}
                  </td>
                  <td className="px-4 py-2.5">
                    {CLOS.has(s)
                      ? <Chip tone="ok">{lib(s)} ✓ {fmtReu(d.updated_at, false)}</Chip>
                      : s === 'envoye'
                        ? <Chip tone="ok">{lib(s)} {fmtReu(d.updated_at, false)}</Chip>
                        : <Chip tone={s === 'demande' ? 'warn' : 'ok'}>{lib(s)}</Chip>}
                  </td>
                  <td className="px-4 py-2.5 text-right">
                    <span className="inline-flex items-center gap-1.5">
                      <ActBtn tone="ghost" onClick={() => voirPdf(d)}>aperçu</ActBtn>
                      {s === 'demande' && (
                        <ActBtn onClick={() => avancer.mutate({ id: d.id, statut: 'depose' })} disabled={avancer.isPending}>Déposé</ActBtn>
                      )}
                      {s === 'depose' && (
                        <ActBtn onClick={() => avancer.mutate({ id: d.id, statut: 'envoye' })} disabled={avancer.isPending}>Envoyé</ActBtn>
                      )}
                      {s === 'envoye' && (
                        <>
                          <ActBtn onClick={() => avancer.mutate({ id: d.id, statut: 'repondu' })} disabled={avancer.isPending}>Répondu</ActBtn>
                          <ActBtn tone="ghost" onClick={() => avancer.mutate({ id: d.id, statut: 'sans_reponse' })} disabled={avancer.isPending}>Sans réponse</ActBtn>
                        </>
                      )}
                      {CLOS.has(s) && <span className="font-mono text-xs text-txt-dim">clos</span>}
                    </span>
                  </td>
                </tr>
              )
            })}
            {!lignes.length && <tr><td colSpan={7} className="px-4 py-6 text-center text-xs text-txt-mut">Aucune demande pour ce filtre.</td></tr>}
          </tbody>
        </table>
        <div className="border-t border-line bg-surface-1 px-4 py-2.5 text-xs text-txt-mut">
          Un seul vocabulaire : à déposer → déposé → envoyé → répondu / sans réponse. Le client voit le même
          statut de son côté · la piste CRM suit · la cloche client sonne · chaque geste entre au journal Pilotage ·
          adressage générique SPF/CERFA — <b className="text-txt">aucune identité de particulier</b>.
        </div>
      </Panel>
    </>
  )
}
