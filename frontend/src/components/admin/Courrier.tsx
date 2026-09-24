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
  getAdminOppositions, postAdminOpposition, deleteAdminOpposition,
  getCourrierConfig, putCourrierConfig, postAdminCourrierPrix,
  urlCourrierPdf, ApiError, type AdminDemandeCourrier,
} from '../../lib/api'
import { ActBtn, Chip, Panel } from './AdminView'
import { Chip as ChipUi } from '../ui/Chip'

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
// COURRIER-2 Lot 4 — plus d'override : le libellé vient de STATUT_LIBELLES servi (source unique).
const CHIP_LABEL: Record<string, string> = {}

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
  // COURRIER-2 Lot 1 — le dépôt peut être REFUSÉ (opposition) : on sert le motif servi par le back.
  const [erreur, setErreur] = useState<string | null>(null)
  const motifDe = (e: unknown) => (e instanceof ApiError && e.detail) ? e.detail : 'Action refusée.'
  const avancer = useMutation({
    mutationFn: ({ id, statut }: { id: number; statut: string }) => postAdminCourrierStatut(id, statut),
    onSuccess: () => { setErreur(null); qc.invalidateQueries({ queryKey: ['admin-courrier'] }); qc.invalidateQueries({ queryKey: ['admin-pilotage'] }) },
    onError: (e) => setErreur(motifDe(e)),
  })
  const deposerTout = useMutation({
    mutationFn: postAdminCourrierDeposerTout,
    onSuccess: (r) => {
      setErreur(r.bloquees_opposition ? `${r.deposes} déposé(s) · ${r.bloquees_opposition} laissée(s) : ${'Opposition enregistrée'}.` : null)
      qc.invalidateQueries({ queryKey: ['admin-courrier'] }); qc.invalidateQueries({ queryKey: ['admin-pilotage'] })
    },
    onError: (e) => setErreur(motifDe(e)),
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
      {erreur && (
        <div data-courrier-erreur className="mb-3 rounded-md border border-amber/40 bg-amber/10 px-4 py-2 text-[13px] text-amber">
          {erreur}
        </div>
      )}
      <CoutEditor />
      <div className="mb-3 flex flex-wrap items-center gap-2">
        {/* DA-028 — « Tous » passe en DERNIER (à droite) ; puces alignées sur le Chip partagé. */}
        {ORDRE.map((s) => (
          <ChipUi key={s} on={statut === s} ton="vert" onClick={() => setStatut(s)}>
            {lib(s)} {compteurs[s]}
          </ChipUi>
        ))}
        <ChipUi on={statut === 'tous'} ton="vert" onClick={() => setStatut('tous')}>Tous {visibles.length}</ChipUi>
        {nMasques > 0 && (
          <ChipUi on={voirTests} ton="neutre" onClick={() => setVoirTests((v) => !v)}>
            {voirTests ? 'masquer les tests' : `${nMasques} demande${nMasques > 1 ? 's' : ''} de test masquée${nMasques > 1 ? 's' : ''}`}
          </ChipUi>
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
              {['Client', 'Parcelle', 'Propriétaire', 'Demandé le', 'Piste CRM', 'Statut', 'Prix (saisi)', 'Gestes'].map((h, i) => (
                <th key={h} className={`border-b border-line px-4 py-2.5 font-mono text-[9.5px] font-medium uppercase tracking-[0.12em] text-txt-dim ${i >= 6 ? 'text-right' : 'text-left'}`}>{h}</th>
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
                  {/* DASHBOARD-4 (C1) — le n° de piste CRM était un id GLOBAL (« piste #12 ») : il fuyait
                      le volume plateforme (même défaut que « Demande n° 44 », RECETTE-3) et la piste CRM
                      est cloisonnée côté client (aucun usage admin de ce numéro). On garde la PROVENANCE
                      (« issue du CRM »), sans le numéro global. */}
                  <td className="px-4 py-2.5 text-xs">
                    {d.pipeline_entry_id != null
                      ? <span className="whitespace-nowrap font-mono text-amber">issue du CRM</span>
                      : <span className="text-txt-dim">—</span>}
                  </td>
                  <td className="px-4 py-2.5">
                    {CLOS.has(s)
                      ? <Chip tone="ok">{lib(s)} ✓ {fmtReu(d.updated_at, false)}</Chip>
                      : s === 'envoye'
                        ? <Chip tone="ok">{lib(s)} {fmtReu(d.updated_at, false)}</Chip>
                        : <Chip tone={s === 'demande' ? 'warn' : 'ok'}>{lib(s)}</Chip>}
                  </td>
                  <td className="px-4 py-2.5 text-right"><PrixCell d={d} /></td>
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
            {!lignes.length && <tr><td colSpan={8} className="px-4 py-6 text-center text-xs text-txt-mut">Aucune demande pour ce filtre.</td></tr>}
          </tbody>
        </table>
        <div className="border-t border-line bg-surface-1 px-4 py-2.5 text-xs text-txt-mut">
          Un seul vocabulaire : à déposer → déposé → envoyé → répondu / sans réponse. Le client voit le même
          statut de son côté · la piste CRM suit · la cloche client sonne · chaque geste entre au journal Pilotage ·
          adressage générique SPF/CERFA — <b className="text-txt">aucune identité de particulier</b>.
        </div>
      </Panel>

      <OppositionPanel />
    </>
  )
}

// COURRIER-2 Lot 5 — PRIX SAISI par Vic (facturation manuelle) ; jamais calculé. Édition inline.
function PrixCell({ d }: { d: AdminDemandeCourrier }) {
  const qc = useQueryClient()
  const [val, setVal] = useState(d.prix_eur != null ? String(d.prix_eur) : '')
  const m = useMutation({
    mutationFn: (v: number | null) => postAdminCourrierPrix(d.id, v),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin-courrier'] }),
  })
  const save = () => { const v = val.trim() === '' ? null : Number(val); if (v === null || !Number.isNaN(v)) m.mutate(v) }
  return (
    <span className="inline-flex items-center gap-1">
      <input data-courrier-prix={d.id} value={val} onChange={(e) => setVal(e.target.value)}
        onBlur={save} onKeyDown={(e) => { if (e.key === 'Enter') (e.target as HTMLInputElement).blur() }}
        inputMode="decimal" placeholder="—"
        className="w-16 rounded border border-line bg-surface-1 px-1.5 py-0.5 text-right font-mono text-xs text-txt" />
      <span className="text-txt-dim">€</span>
    </span>
  )
}

// COURRIER-2 Lot 5 — COÛT PRESTATAIRE : paramètre admin daté (jamais servi au client).
function CoutEditor() {
  const qc = useQueryClient()
  const q = useQuery({ queryKey: ['courrier-config'], queryFn: getCourrierConfig })
  const [val, setVal] = useState('')
  const m = useMutation({
    mutationFn: (v: number) => putCourrierConfig(v),
    onSuccess: () => { setVal(''); qc.invalidateQueries({ queryKey: ['courrier-config'] }) },
  })
  const cfg = q.data
  return (
    <div className="mb-3 flex flex-wrap items-center gap-2 rounded-md border border-line bg-surface-1 px-4 py-2 text-[12px] text-txt-mut">
      <span>Coût prestataire (lettre) :</span>
      <b data-courrier-cout className="tnum text-txt">{cfg ? cfg.cout_lettre_eur.toFixed(2) : '…'} €</b>
      {cfg?.maj_at && <span className="text-txt-dim">màj {fmtReu(cfg.maj_at, false)}{cfg.maj_par ? ` · ${cfg.maj_par}` : ''}</span>}
      <span className="ml-2 flex items-center gap-1">
        <input data-courrier-cout-input value={val} onChange={(e) => setVal(e.target.value)} inputMode="decimal"
          placeholder="nouveau" className="w-20 rounded border border-line bg-surface-2 px-1.5 py-0.5 text-right font-mono text-xs text-txt" />
        <ActBtn onClick={() => { const v = Number(val); if (val.trim() && !Number.isNaN(v)) m.mutate(v) }} disabled={m.isPending || !val.trim()}>Modifier</ActBtn>
      </span>
      <span className="text-txt-dim">— non affiché au client (tarif donné au rappel).</span>
    </div>
  )
}

// COURRIER-2 Lot 1 — REGISTRE D'OPPOSITION : Vic saisit à la main ce qui arrive sur stop@labuse.immo.
// Une adresse OU une parcelle opposée bloque tout dépôt d'un pli, pour TOUS les comptes.
function OppositionPanel() {
  const qc = useQueryClient()
  const q = useQuery({ queryKey: ['admin-oppositions'], queryFn: getAdminOppositions })
  const [adresse, setAdresse] = useState('')
  const [idu, setIdu] = useState('')
  const [reference, setReference] = useState('')
  const [err, setErr] = useState<string | null>(null)
  const ajout = useMutation({
    mutationFn: () => postAdminOpposition({ adresse: adresse || undefined, idu: idu || undefined, reference: reference || undefined }),
    onSuccess: () => { setAdresse(''); setIdu(''); setReference(''); setErr(null); qc.invalidateQueries({ queryKey: ['admin-oppositions'] }); qc.invalidateQueries({ queryKey: ['admin-courrier'] }) },
    onError: (e) => setErr(e instanceof ApiError && e.detail ? e.detail : 'Saisie refusée.'),
  })
  const suppr = useMutation({
    mutationFn: (id: number) => deleteAdminOpposition(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin-oppositions'] }),
  })
  const opps = q.data?.oppositions ?? []
  return (
    <Panel>
      <div className="border-b border-line px-4 py-2.5 text-xs text-txt-mut">
        <b className="text-txt">Opposition (stop@labuse.immo)</b> — saisissez ici toute demande d’arrêt reçue.
        Une adresse ou une parcelle opposée <b className="text-txt">bloque tout dépôt</b>, pour tous les comptes.
      </div>
      <div className="flex flex-wrap items-end gap-2 px-4 py-3">
        <label className="flex flex-col gap-1 text-[11px] text-txt-dim">Adresse postale
          <input data-opp-adresse value={adresse} onChange={(e) => setAdresse(e.target.value)} placeholder="12 rue du Port, 97420 Le Port"
            className="w-64 rounded border border-line bg-surface-1 px-2 py-1 text-[13px] text-txt" />
        </label>
        <label className="flex flex-col gap-1 text-[11px] text-txt-dim">IDU parcelle
          <input data-opp-idu value={idu} onChange={(e) => setIdu(e.target.value)} placeholder="97411000BZ1065"
            className="w-40 rounded border border-line bg-surface-1 px-2 py-1 font-mono text-[13px] text-txt" />
        </label>
        <label className="flex flex-col gap-1 text-[11px] text-txt-dim">Référence citée
          <input data-opp-ref value={reference} onChange={(e) => setReference(e.target.value)} placeholder="BZ 1065"
            className="w-32 rounded border border-line bg-surface-1 px-2 py-1 text-[13px] text-txt" />
        </label>
        <ActBtn onClick={() => ajout.mutate()} disabled={ajout.isPending || (!adresse && !idu)}>
          {ajout.isPending ? 'Enregistrement…' : 'Enregistrer l’opposition'}
        </ActBtn>
        {err && <span data-opp-erreur className="text-[12px] text-amber">{err}</span>}
      </div>
      {opps.length > 0 && (
        <table className="w-full text-[13px]">
          <thead><tr>{['Adresse', 'Parcelle', 'Référence', 'Origine', 'Enregistrée le', ''].map((h, i) => (
            <th key={h} className={`border-b border-line px-4 py-2 font-mono text-[9.5px] font-medium uppercase tracking-[0.12em] text-txt-dim ${i === 5 ? 'text-right' : 'text-left'}`}>{h}</th>
          ))}</tr></thead>
          <tbody>
            {opps.map((o) => (
              <tr key={o.id} className="border-b border-line last:border-b-0" data-opposition={o.id}>
                <td className="px-4 py-2 text-xs text-txt-mut">{o.adresse_norm ?? <span className="text-txt-dim">—</span>}</td>
                <td className="px-4 py-2 font-mono text-xs text-txt-mut">{o.idu ?? <span className="text-txt-dim">—</span>}</td>
                <td className="px-4 py-2 text-xs text-txt-mut">{o.reference ?? <span className="text-txt-dim">—</span>}</td>
                <td className="px-4 py-2 text-xs text-txt-dim">{o.origine}</td>
                <td className="px-4 py-2 font-mono text-xs text-txt-dim">{fmtReu(o.cree_at)}</td>
                <td className="px-4 py-2 text-right"><ActBtn tone="ghost" onClick={() => suppr.mutate(o.id)} disabled={suppr.isPending}>lever</ActBtn></td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </Panel>
  )
}
