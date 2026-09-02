// SUITE-1 · S2 bis — CATALOGUE : UNE seule table, une ligne par source (remplace l'ancienne
// SourcesSection empilée : table Sources + panneau Cron + table « Agent de veille » ⇒ chaque source
// apparaissait deux fois). Colonnes de la maquette : SOURCE (nom + fournisseur + méthode de veille) ·
// SERVI (millésime en base) · AMONT (ce que l'agent a vu) · DERNIER PASSAGE · FRAÎCHEUR · ALIMENTE
// (moteurs/surfaces lus de la matrice flux.py) · ACTIONS (une action principale + menu « ⋯ »).
// « Cron nocturne » et « Dernières exécutions » vivent désormais dans l'onglet Horloge (CronSection).
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import { getAdminSources, postAdminCronRun, postAdminSourceAffichage, postAdminSourceCadence, postAdminSourceRelancer, postAdminSourceVeilleActive, postAdminSourceVeilleInjecter, postAdminSourceVeilleMail, postAdminSourceVeilleVerifier, type AdminSource } from '../../lib/api'
import { ActBtn, Chip, Panel } from './AdminView'

// RETOURS-9 (Q2.4) — « Vérifier toutes les sources maintenant » : lance le job `sentinelle-sources`
// à la main (le MÊME que l'Horloge/CRON, verrou flock partagé). Détaché : l'état se met à jour au
// prochain rafraîchissement. Indispensable en local (le cron ne sonne pas sur le Mac de Vic).
function VerifierToutes() {
  const qc = useQueryClient()
  const [msg, setMsg] = useState<string | null>(null)
  const run = useMutation({
    mutationFn: () => postAdminCronRun('sentinelle-sources'),
    onSuccess: (r) => {
      setMsg(r.ok ? 'Vérification lancée — les états se mettront à jour dans une minute.' : (r.motif ?? 'Lancement refusé.'))
      setTimeout(() => qc.invalidateQueries({ queryKey: ['admin-sources'] }), 4000)
    },
    onError: () => setMsg('Lancement impossible.'),
  })
  return (
    <div className="text-right">
      <ActBtn tone="mint" disabled={run.isPending} data-verifier-toutes
        onClick={() => run.mutate()}>
        {run.isPending ? 'Lancement…' : 'Vérifier toutes les sources maintenant'}
      </ActBtn>
      {msg && <div className="mt-0.5 text-[10px] text-mint">{msg}</div>}
    </div>
  )
}

const fmtReu = (iso?: string | null) => {
  if (!iso) return '—'
  try {
    return new Intl.DateTimeFormat('fr-FR', { timeZone: 'Indian/Reunion', day: '2-digit', month: '2-digit' }).format(new Date(iso))
  } catch { return '—' }
}

// SENTINELLE-3 (Y5.4) — libellé court de la méthode de veille, affiché sous le nom (maquette : « page ·
// veille quotidienne », « témoin Saint-Denis »…). On garde une forme compacte et honnête.
const METHODE_LABEL: Record<string, string> = {
  api: 'api', page: 'page', entete: 'entete', temoin: 'témoin', rappel: 'rappel manuel',
}

// RETOURS-9 (Q2.3) — étiquette « qui s'en occupe », lue en une seconde : auto (agent quotidien) /
// manuelle (rappel N j) / non surveillée (avec la raison). Rendue sous le nom de la source.
function responsable(s: AdminSource): { texte: string; tone: 'auto' | 'manuel' | 'non' } {
  const v = s.veille
  if (v.surveillee) return { texte: `auto · agent quotidien · ${METHODE_LABEL[v.methode ?? ''] ?? v.methode ?? 'sonde'}`, tone: 'auto' }
  if (v.nature === 'rappel') return { texte: v.cadence_attendue_jours != null ? `manuelle · rappel ${v.cadence_attendue_jours} j` : 'manuelle · rappel', tone: 'manuel' }
  return { texte: `non surveillée${v.raison ? ` · ${v.raison}` : ''}`, tone: 'non' }
}

// AMONT (colonne « ce que l'agent a vu ») — un badge par état. Jamais un blanc.
function AmontBadge({ s }: { s: AdminSource }) {
  const v = s.veille
  if (!v.surveillee) {
    if (v.nature === 'rappel') return <Chip>manuelle</Chip>
    return <span title={v.raison ?? undefined} className="cursor-help"><Chip>non surveillée</Chip></span>
  }
  if (v.nouvelle_version) return <Chip tone="warn">{v.millesime_amont ?? 'nouvelle'} disponible</Chip>
  if (v.echec_confirme) return <span title={v.message ?? undefined} className="cursor-help"><Chip tone="off">sonde en échec</Chip></span>
  // RETOURS-9 (Q2.2) — surveillée mais l'agent n'est pas encore passé : jamais « — », on l'annonce.
  if (s.etat === 'jamais_verifiee') return <Chip tone="warn">en attente de la 1ʳᵉ vérification</Chip>
  if (v.statut === 'ok') return <Chip tone="ok">{v.nature === 'changement' ? 'pas de changement' : 'identique'}</Chip>
  return <Chip>{v.statut ? v.statut.replace(/_/g, ' ') : 'jamais sondée'}</Chip>
}

// FRAÎCHEUR — à jour (ok) · à rafraîchir (warn/err) · sans échéance. Un rappel en retard = err chiffré.
function FraicheurBadge({ s }: { s: AdminSource }) {
  const v = s.veille
  if (v.nature === 'rappel' && v.rappel_retard)
    return <Chip tone="err">{v.jours_depuis_maj != null ? `${v.jours_depuis_maj} j — à rafraîchir` : 'à rafraîchir'}</Chip>
  if (s.a_jour === true) return <Chip tone="ok">à jour</Chip>
  if (s.a_jour === false) return <Chip tone="warn">à rafraîchir</Chip>
  return <span className="text-txt-dim">—</span>
}

// ALIMENTE — moteurs + surfaces nourris, LUS de la matrice flux.py (jamais écrits à la main).
function AlimenteCell({ s }: { s: AdminSource }) {
  const a = s.alimente
  if (!a || !a.cable) return <span className="text-[11px] text-txt-dim">non câblée</span>
  const chips = [...a.moteurs.map((m) => m.key), ...a.surfaces.slice(0, 3).map((x) => x.key)]
  const reste = a.surfaces.length > 3 ? a.surfaces.length - 3 : 0
  return (
    <div className="flex flex-wrap gap-1" title={[...a.moteurs, ...a.surfaces].map((x) => x.label).join(' · ')}>
      {chips.map((c) => <span key={c} className="rounded bg-surface-3 px-1.5 py-0.5 font-mono text-[9.5px] text-txt-mut">{c}</span>)}
      {reste > 0 && <span className="font-mono text-[9.5px] text-txt-dim">+{reste}</span>}
    </div>
  )
}

// Menu « ⋯ » — le reste des actions (Vérifier · cadence · suspendre la veille · alerte mail · désactiver
// la source). Une seule action PRINCIPALE reste en bouton dans la colonne ACTIONS.
function MenuActions({ s, cadences }: { s: AdminSource; cadences: string[] }) {
  const qc = useQueryClient()
  const inval = () => qc.invalidateQueries({ queryKey: ['admin-sources'] })
  const v = s.veille
  const cad = useMutation({ mutationFn: (val: string | null) => postAdminSourceCadence(s.id, val), onSuccess: inval })
  const verifier = useMutation({ mutationFn: () => postAdminSourceVeilleVerifier(s.id), onSuccess: inval })
  const active = useMutation({ mutationFn: (actif: boolean) => postAdminSourceVeilleActive(s.id, actif), onSuccess: inval })
  const mail = useMutation({ mutationFn: (on: boolean) => postAdminSourceVeilleMail(s.id, on), onSuccess: inval })
  const aff = useMutation({ mutationFn: (actif: boolean) => postAdminSourceAffichage(s.id, actif), onSuccess: inval })
  return (
    <details className="relative ml-1.5 inline-block">
      <summary className="cursor-pointer list-none rounded-md border border-line px-2 py-1 text-txt-mut hover:text-txt [&::-webkit-details-marker]:hidden" title="Plus d'actions">⋯</summary>
      <div className="absolute right-0 z-20 mt-1 w-60 rounded-lg border border-line bg-surface-1 p-2 text-[12px] shadow-lg">
        {v.surveillee && (
          <button onClick={() => verifier.mutate()} disabled={verifier.isPending}
            className="block w-full rounded px-2 py-1.5 text-left text-txt-mut hover:bg-surface-3 hover:text-txt">
            {verifier.isPending ? 'Sonde…' : 'Vérifier maintenant'}
          </button>
        )}
        <label className="flex items-center gap-2 px-2 py-1.5 text-txt-mut">
          <span>Cadence</span>
          <select value={s.cadence ?? ''} onChange={(e) => cad.mutate(e.target.value || null)} data-cadence={s.id}
            className="ml-auto rounded-md border border-line-2 bg-bg px-1.5 py-1 font-mono text-[11px] text-txt-mut outline-none focus:border-mint">
            <option value="">—</option>
            {cadences.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
        </label>
        {v.surveillee && (
          <>
            <button onClick={() => active.mutate(!(v.actif ?? true))} disabled={active.isPending}
              className="block w-full rounded px-2 py-1.5 text-left text-txt-mut hover:bg-surface-3 hover:text-txt">
              {v.actif === false ? 'Réactiver la veille' : 'Suspendre la veille'}
            </button>
            {/* SUITE-1 S4.1 — alerte mail optionnelle par source (défaut off ; l'alerte in-app reste). */}
            <label className="flex cursor-pointer items-center gap-2 rounded px-2 py-1.5 text-txt-mut hover:bg-surface-3">
              <input type="checkbox" checked={s.veille.mail_alerte} disabled={mail.isPending} data-mail={s.id}
                onChange={(e) => mail.mutate(e.target.checked)} />
              M'alerter aussi par mail
            </label>
          </>
        )}
        <button onClick={() => { if (window.confirm(s.affichage_desactive
          ? `Réactiver « ${s.name} » ? Elle réapparaîtra dans la vitrine et les consommateurs.`
          : `Désactiver « ${s.name} » ? Elle sortira de la vitrine ; les couches/outils afficheront « source désactivée ».`)) aff.mutate(s.affichage_desactive) }}
          disabled={aff.isPending} data-affichage={s.id}
          className="mt-1 block w-full rounded border-t border-line px-2 py-1.5 text-left text-txt-mut hover:bg-surface-3 hover:text-txt">
          {s.affichage_desactive ? 'Réactiver la source' : 'Désactiver la source'}
        </button>
      </div>
    </details>
  )
}

// Action PRINCIPALE (S2) — un seul bouton par état : Injecter (nouvelle version, tracé X6) OU Recharger
// (recharge la même version, avec une confirmation qui dit EXACTEMENT ce qui va se passer). Si la sonde
// n'a pas tourné depuis > 48 h, Recharger VÉRIFIE d'abord et bascule sur Injecter si du neuf apparaît.
const H48_MS = 48 * 3600 * 1000
function ActionPrincipale({ s }: { s: AdminSource }) {
  const qc = useQueryClient()
  const inval = () => qc.invalidateQueries({ queryKey: ['admin-sources'] })
  const [msg, setMsg] = useState<string | null>(null)
  const v = s.veille
  const injecter = useMutation({
    mutationFn: () => postAdminSourceVeilleInjecter(s.id),
    onSuccess: (r) => { setMsg(`Injection lancée (${r.label})${r.millesime ? ` → ${r.millesime}` : ''} — suivi dans le CRON.`); inval() },
    onError: () => setMsg("Injection impossible (aucune commande d'ingestion connue ?)."),
  })
  const recharger = useMutation({
    mutationFn: () => postAdminSourceRelancer(s.id),
    onSuccess: (r) => { setMsg(`Rechargée (${r.label})${r.millesime ? ` — version ${r.millesime}` : ''}.`); inval() },
    onError: () => setMsg('Rechargement impossible.'),
  })
  const verifierAvant = useMutation({ mutationFn: () => postAdminSourceVeilleVerifier(s.id) })
  const verifier = useMutation({
    mutationFn: () => postAdminSourceVeilleVerifier(s.id),
    onSuccess: (r) => { setMsg(r.statut === 'nouvelle_version'
      ? `Nouvelle version (${r.millesime_amont ?? '?'}) — utilisez « Injecter ».`
      : 'Vérifiée — l\'amont est à jour.'); inval() },
    onError: () => setMsg('Sonde impossible.'),
  })

  // RETOURS-9 (Q2.2) — source surveillée jamais sondée : l'action PRINCIPALE est « Vérifier maintenant »
  // (pas un « — »). Elle lance la sonde amont de CETTE source (le job global reste « Vérifier toutes »).
  if (s.etat === 'jamais_verifiee') {
    return (
      <div className="inline-block text-right" data-verifier={s.id}>
        <ActBtn tone="mint" disabled={verifier.isPending}
          onClick={() => verifier.mutate()}>
          {verifier.isPending ? 'Sonde…' : 'Vérifier maintenant'}
        </ActBtn>
        {msg && <div className="mt-0.5 text-[10px] text-mint">{msg}</div>}
      </div>
    )
  }

  if (v.nouvelle_version && v.injectable) {
    return (
      <div className="inline-block text-right">
        <ActBtn tone="mint" disabled={injecter.isPending} data-injecter={s.id}
          onClick={() => { if (window.confirm(`Injecter « ${v.millesime_amont ?? 'la nouvelle version'} » pour « ${s.name} » ?\n\nLance le job d'ingestion EXISTANT (même commande que le cron, détachée — peut durer plusieurs minutes). Rien n'entre sans ce clic.`)) injecter.mutate() }}>
          {injecter.isPending ? 'Lancement…' : `Injecter ${v.millesime_amont ?? ''} →`.trim()}
        </ActBtn>
        {msg && <div className="mt-0.5 text-[10px] text-mint">{msg}</div>}
      </div>
    )
  }
  if (v.nouvelle_version && !v.injectable) {
    return <span className="text-[10.5px] text-txt-dim" title="Aucune commande d'ingestion mappée : injection manuelle.">injection manuelle</span>
  }
  if (!s.relance) {
    return <span className="text-[10.5px] text-txt-dim">—</span>
  }
  // Recharger (S2) : confirmation exacte + garde des > 48 h.
  const stale = !v.passage_at || (Date.now() - new Date(v.passage_at).getTime()) > H48_MS
  const lancerRecharge = () => {
    if (!window.confirm(`Recharger « ${s.name} » ?\n\nRetélécharge depuis la source et recharge la base. Version attendue : ${s.millesime ?? '?'} (identique à celle servie). Peut durer plusieurs minutes.`)) return
    recharger.mutate()
  }
  const onClick = async () => {
    if (v.surveillee && stale) {
      setMsg('Vérification de l\'amont…')
      try {
        const r = await verifierAvant.mutateAsync()
        if (r.statut === 'nouvelle_version') {
          setMsg(`Une version plus récente (${r.millesime_amont ?? '?'}) est apparue — utilisez « Injecter ».`)
          inval()
          return
        }
      } catch { /* sonde impossible : on retombe sur le rechargement classique */ }
      setMsg(null)
    }
    lancerRecharge()
  }
  return (
    <div className="inline-block text-right">
      <ActBtn tone="ghost" disabled={recharger.isPending || verifierAvant.isPending} data-recharger={s.id}
        title={`Recharge la MÊME version (${s.millesime ?? '?'}) depuis la source — réparation. ${stale ? 'La sonde n\'a pas tourné depuis > 48 h : une vérification part d\'abord.' : ''}`}
        onClick={onClick}>
        {recharger.isPending ? 'Rechargement…' : verifierAvant.isPending ? 'Vérification…' : 'Recharger'}
      </ActBtn>
      {msg && <div className="mt-0.5 text-[10px] text-mint">{msg}</div>}
    </div>
  )
}

function CatalogueRow({ s, cadences }: { s: AdminSource; cadences: string[] }) {
  const v = s.veille
  return (
    <tr className={`border-b border-line last:border-b-0 hover:bg-surface-3 ${s.affichage_desactive ? 'opacity-55' : ''}`}>
      <td className="px-3 py-2.5">
        <b className="text-txt">{s.name}</b>
        {s.affichage_desactive && <span className="ml-1"><Chip tone="warn">désactivée</Chip></span>}
        <div className="mt-0.5 text-[10.5px] text-txt-dim">{s.fournisseur ?? '—'}</div>
        {/* RETOURS-9 (Q2.3) — qui s'occupe de cette source, en une ligne */}
        {(() => { const r = responsable(s); return (
          <div data-responsable={r.tone}
            className={`mt-0.5 text-[10px] ${r.tone === 'auto' ? 'text-mint' : r.tone === 'manuel' ? 'text-amber' : 'text-txt-mut'}`}
            title={r.texte}>{r.texte}</div>
        ) })()}
      </td>
      <td className="px-3 py-2.5 font-mono text-[11.5px] text-txt-mut">{s.millesime ?? '—'}</td>
      <td className="px-3 py-2.5"><AmontBadge s={s} /></td>
      <td className="px-3 py-2.5 font-mono text-[11px] text-txt-dim">{v.surveillee ? fmtReu(v.passage_at) : (v.nature === 'rappel' ? fmtReu(s.ingere_le) : '—')}</td>
      <td className="px-3 py-2.5"><FraicheurBadge s={s} /></td>
      <td className="px-3 py-2.5"><AlimenteCell s={s} /></td>
      <td className="px-3 py-2.5 text-right whitespace-nowrap">
        <ActionPrincipale s={s} />
        <MenuActions s={s} cadences={cadences} />
      </td>
    </tr>
  )
}

// RETOURS-9 (Q2.1) — les chips comptent les 64 par ÉTAT UNIQUE (arbitre serveur `s.etat`). Les cinq
// états PARTITIONNENT le catalogue : leur somme = le total (verrouillé par test). « Toutes » remet à plat.
type CatFiltre = 'toutes' | 'a_jour' | 'nouvelle_version' | 'a_rafraichir' | 'non_surveillee' | 'jamais_verifiee'
const CAT_PRED: Record<CatFiltre, (s: AdminSource) => boolean> = {
  toutes: () => true,
  a_jour: (s) => s.etat === 'a_jour',
  nouvelle_version: (s) => s.etat === 'nouvelle_version',
  a_rafraichir: (s) => s.etat === 'a_rafraichir',
  non_surveillee: (s) => s.etat === 'non_surveillee',
  jamais_verifiee: (s) => s.etat === 'jamais_verifiee',
}
// ordre du mandat Q2.1 : à jour · nouvelle version · à rafraîchir · non surveillée · jamais vérifiée
const CAT_LABELS: Array<[CatFiltre, string]> = [
  ['toutes', 'Toutes'], ['a_jour', 'À jour'], ['nouvelle_version', 'Nouvelle version'],
  ['a_rafraichir', 'À rafraîchir'], ['non_surveillee', 'Non surveillée'], ['jamais_verifiee', 'Jamais vérifiée'],
]

// Table présentationnelle (testable en isolation) : filtres + recherche + regroupement par fournisseur
// avec en-têtes repliables. Chaque source UNE FOIS.
export function Catalogue({ sources, cadences }: { sources: AdminSource[]; cadences: string[] }) {
  const [filtre, setFiltre] = useState<CatFiltre>('toutes')
  const n = (f: CatFiltre) => sources.filter(CAT_PRED[f]).length
  const visibles = useMemo(() => sources.filter(CAT_PRED[filtre]), [sources, filtre])
  // regroupement par fournisseur, en gardant l'ordre d'apparition des fournisseurs
  const groupes = useMemo(() => {
    const m = new Map<string, AdminSource[]>()
    for (const s of visibles) {
      const k = s.fournisseur ?? 'Autres'
      if (!m.has(k)) m.set(k, [])
      m.get(k)!.push(s)
    }
    return Array.from(m.entries())
  }, [visibles])
  return (
    <>
      <div className="mb-3 flex flex-wrap items-center gap-1.5">
        {CAT_LABELS.map(([f, lbl]) => (
          <button key={f} onClick={() => setFiltre(f)} data-cat-filtre={f}
            className={`rounded-full border px-2.5 py-1 text-[11.5px] transition ${filtre === f ? 'border-mint bg-mint text-mint-ink font-medium' : 'border-line bg-surface-1 text-txt-dim hover:text-txt-mut'}`}>
            {lbl} <span className={`font-bold ${f === 'nouvelle_version' && n(f) > 0 ? 'text-amber' : ''}`}>{n(f)}</span>
          </button>
        ))}
        {/* Q2.4 — lance le job sentinelle-sources À LA MAIN (le même que l'Horloge). Indispensable en local. */}
        <div className="ml-auto"><VerifierToutes /></div>
      </div>
      <Panel>
        <table className="w-full text-[12.5px]">
          <thead>
            <tr>
              {['Source', 'Servi', 'Amont (agent)', 'Dernier passage', 'Fraîcheur', 'Alimente', ''].map((h) => (
                <th key={h} className="border-b border-line px-3 py-2 text-left font-mono text-[9px] font-medium uppercase tracking-[0.14em] text-txt-dim">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {groupes.map(([fournisseur, lignes]) => (
              <GroupeFournisseur key={fournisseur} fournisseur={fournisseur} lignes={lignes} cadences={cadences} />
            ))}
            {!visibles.length && <tr><td colSpan={7} className="px-4 py-6 text-center text-xs text-txt-mut">Aucune source dans ce filtre.</td></tr>}
          </tbody>
        </table>
        <div className="border-t border-line bg-surface-1 px-4 py-2.5 text-[11.5px] leading-relaxed text-txt-mut">
          Une source injoignable/illisible signale que la <b className="text-txt">sentinelle</b> a échoué, jamais que la donnée est en erreur.
          « Recharger » relance la même version (réparation) ; « Injecter » charge une nouvelle version détectée. Une sonde n'alerte qu'après <b className="text-txt">3 échecs</b> d'affilée.
        </div>
      </Panel>
    </>
  )
}

// En-tête de fournisseur REPLIABLE (native <details> via une ligne <tr> pleine largeur qui bascule).
function GroupeFournisseur({ fournisseur, lignes, cadences }: { fournisseur: string; lignes: AdminSource[]; cadences: string[] }) {
  const [ouvert, setOuvert] = useState(true)
  return (
    <>
      <tr className="cursor-pointer select-none bg-surface-2" onClick={() => setOuvert((o) => !o)} data-groupe={fournisseur}>
        <td colSpan={7} className="px-3 py-1.5 font-mono text-[10px] uppercase tracking-[0.1em] text-txt-dim">
          <span className="mr-1.5 inline-block w-2">{ouvert ? '▾' : '▸'}</span>{fournisseur} <span className="text-txt-dim/70">· {lignes.length}</span>
        </td>
      </tr>
      {ouvert && lignes.map((s) => <CatalogueRow key={s.id} s={s} cadences={cadences} />)}
    </>
  )
}

export function SourcesSection() {
  const q = useQuery({ queryKey: ['admin-sources'], queryFn: getAdminSources, refetchInterval: 300_000 })
  const d = q.data
  if (!d) return <div className="py-10 text-center text-xs text-txt-mut">Chargement…</div>
  // RETOURS-9 (Q2.1) — l'ancien bandeau de synthèse comptait la FRAÎCHEUR heuristique (« 3 à jour »
  // sur 64) et contredisait tout. Retiré : les chips du Catalogue comptent désormais les 64 par
  // état unique R1 (à jour · nouvelle version · à rafraîchir · non surveillée · jamais vérifiée),
  // et leur somme fait le total. Une seule vérité.
  return <Catalogue sources={d.sources} cadences={d.cadences} />
}
